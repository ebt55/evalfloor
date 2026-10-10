"""Instrument defect 010, pinned: every load seeds the shuffles a task left unseeded.

The three 17 Sep sweeps of the twenty gave three digests and counted 4, 5 and 5
of 20. The difference was ``truthfulqa``, which passes ``shuffle=True,
shuffle_choices=True`` and no seed, so the correct answer could sit under a
different letter on every load. ``drive.seeded_shuffles`` makes the call
upstream adopted in #2404 and #2406, ``seed=42, shuffle_choices=42``, around
every load.

Everything here runs without the network except the last test, which loads the
real ``truthfulqa`` twice through the harness's own load path. It is marked
``dataset`` accordingly; ``truthfulqa`` is one of the original twenty, so on
``inspect_evals`` 0.20.0 it is already cached.
"""

from __future__ import annotations

import inspect
import json
import pathlib
from typing import Any, Iterable
from unittest import mock

import inspect_ai.dataset
import pytest
from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import choice
from inspect_evals.utils.huggingface import hf_dataset as util_hf_dataset

from evalfloor import battery
from evalfloor.battery import SHUFFLE_SEED, battery_fingerprint, run_fingerprint
from evalfloor.drive import resolve_task, seeded_shuffles, task_samples
from evalfloor.graded import GradedCache

REPO = pathlib.Path(__file__).resolve().parent.parent

#: The fingerprint both 17 Sep arms ran under. Every committed graded cache key
#: hashes it, so it must not move when the shuffle seed is added.
FIRST_SWEEP_FINGERPRINT = "b019ebb6ecee"

#: Captured at import, before any test replaces it.
REAL_HF_DATASET = inspect_ai.dataset.hf_dataset

N = 40
CHOICES = ("alpha", "beta", "gamma", "delta")


def _dataset() -> MemoryDataset:
    """Forty four-way samples with the correct answer always first."""
    return MemoryDataset(
        [
            Sample(id=i, input=f"question {i}", choices=list(CHOICES), target="A")
            for i in range(N)
        ]
    )


def _view(samples: Iterable[Any]) -> list[tuple[Any, tuple[str, ...], Any]]:
    """(id, choices, target) per sample, in iteration order."""
    return [
        (
            s.id,
            tuple(s.choices or ()),
            tuple(s.target) if isinstance(s.target, list) else s.target,
        )
        for s in samples
    ]


def _originals() -> tuple[Any, Any, Any]:
    """The three things the block replaces, read straight off their owners."""
    return (
        vars(inspect_ai.dataset)["hf_dataset"],
        vars(MemoryDataset)["shuffle"],
        vars(MemoryDataset)["shuffle_choices"],
    )


def _received(fake: Any) -> dict[str, Any]:
    """What the replaced ``hf_dataset`` was called with, defaults filled in."""
    bound = inspect.signature(REAL_HF_DATASET).bind(
        *fake.call_args.args, **fake.call_args.kwargs
    )
    bound.apply_defaults()
    return dict(bound.arguments)


# -- probe tasks, loaded through resolve_task like any other task -------------


@task(name="evalfloor_fixtures/seeded_memory_probe")
def seeded_memory_probe() -> Task:
    """Shuffles a dataset it built itself, unseeded, the way ``bbq`` does."""
    dataset = _dataset()
    dataset.shuffle()
    dataset.shuffle_choices()
    return Task(dataset=dataset, scorer=choice())


@task(name="evalfloor_fixtures/seeded_hf_probe")
def seeded_hf_probe() -> Task:
    """Loads through the binding ``truthfulqa`` holds, with its arguments."""
    dataset = util_hf_dataset(
        path="evalfloor/probe",
        split="train",
        revision="probe",
        shuffle=True,
        shuffle_choices=True,
    )
    return Task(dataset=dataset, scorer=choice())


@task(name="evalfloor_fixtures/seeded_load_fails")
def seeded_load_fails() -> Task:
    raise RuntimeError("the dataset could not be read")


# --------------------------------------------------------------------------
# The backstop, on an in-memory dataset
# --------------------------------------------------------------------------


def test_an_unseeded_choice_shuffle_differs_between_loads() -> None:
    """The defect itself, outside the block: ``random.Random(None)`` per load.

    Forty four-way samples agree by chance with probability 24 ** -40.
    """
    a, b = _dataset(), _dataset()
    a.shuffle_choices()
    b.shuffle_choices()
    assert _view(a) != _view(b)


def test_inside_the_block_an_unseeded_shuffle_is_the_seed_42_shuffle() -> None:
    seeded = []
    for _ in range(2):
        dataset = _dataset()
        with seeded_shuffles():
            dataset.shuffle()
            dataset.shuffle_choices()
        seeded.append(_view(dataset))

    explicit = _dataset()
    explicit.shuffle(seed=SHUFFLE_SEED)
    explicit.shuffle_choices(seed=SHUFFLE_SEED)

    assert SHUFFLE_SEED == 42
    assert seeded[0] == seeded[1] == _view(explicit)
    # The seed pins the shuffle; it does not switch it off.
    assert [row[0] for row in seeded[0]] != list(range(N))
    assert len({row[2] for row in seeded[0]}) > 1


def test_an_explicit_seed_is_left_alone() -> None:
    inside, outside, default = _dataset(), _dataset(), _dataset()
    with seeded_shuffles():
        inside.shuffle(seed=7)
        inside.shuffle_choices(seed=7)
        default.shuffle()
        default.shuffle_choices()
    outside.shuffle(seed=7)
    outside.shuffle_choices(seed=7)
    assert _view(inside) == _view(outside)
    assert _view(inside) != _view(default)


# --------------------------------------------------------------------------
# The main hook, on hf_dataset, with the real function mocked out
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # The call #2404 and #2406 make, from the call truthfulqa makes today.
        (
            {"shuffle": True, "shuffle_choices": True},
            {"shuffle": True, "seed": 42, "shuffle_choices": 42},
        ),
        ({"shuffle": True}, {"seed": 42, "shuffle_choices": None}),
        ({"shuffle": True, "seed": None}, {"seed": 42}),
        ({"shuffle": True, "seed": 7}, {"seed": 7}),
        ({"shuffle": True, "seed": 0}, {"seed": 0}),
        ({"shuffle": False}, {"shuffle": False, "seed": None}),
        ({}, {"shuffle": False, "seed": None, "shuffle_choices": None}),
        ({"shuffle_choices": True}, {"seed": None, "shuffle_choices": 42}),
        ({"shuffle_choices": 3}, {"shuffle_choices": 3}),
        ({"shuffle_choices": False}, {"shuffle_choices": False}),
    ],
)
def test_the_hf_hook_seeds_only_an_unseeded_shuffle(
    monkeypatch: pytest.MonkeyPatch, given: dict[str, Any], expected: dict[str, Any]
) -> None:
    fake = mock.create_autospec(REAL_HF_DATASET, return_value=None)
    monkeypatch.setattr(inspect_ai.dataset, "hf_dataset", fake)
    with seeded_shuffles():
        inspect_ai.dataset.hf_dataset(path="p", split="train", **given)
    received = _received(fake)
    assert {name: received[name] for name in expected} == expected
    # A seed that stayed a bool would compare equal to 1, not 42; check the type.
    if expected.get("shuffle_choices") == 42:
        assert type(received["shuffle_choices"]) is int


def test_the_hook_reaches_the_binding_inspect_evals_tasks_hold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``truthfulqa.py:23`` and ``lab_bench.py:30`` bind
    ``inspect_evals.utils.huggingface.hf_dataset`` by name at import, on 0.20.0
    and 0.24.0 alike, and that wrapper looks ``inspect_ai.dataset.hf_dataset`` up
    on every call (``huggingface.py:203``). So the attribute is the thing to
    replace, and replacing it reaches a binding taken before the block opened."""
    fake = mock.create_autospec(REAL_HF_DATASET, return_value=None)
    monkeypatch.setattr(inspect_ai.dataset, "hf_dataset", fake)
    with seeded_shuffles():
        util_hf_dataset(
            path="p", split="train", revision="r", shuffle=True, shuffle_choices=True
        )
    received = _received(fake)
    assert (received["seed"], received["shuffle_choices"]) == (42, 42)


# --------------------------------------------------------------------------
# The call site: resolve_task
# --------------------------------------------------------------------------


def test_resolve_task_seeds_the_hf_load(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = mock.create_autospec(REAL_HF_DATASET, return_value=_dataset())
    monkeypatch.setattr(inspect_ai.dataset, "hf_dataset", fake)
    resolve_task("evalfloor_fixtures/seeded_hf_probe")
    received = _received(fake)
    assert (received["seed"], received["shuffle_choices"]) == (42, 42)


def test_resolve_task_seeds_a_tasks_own_memory_shuffle() -> None:
    first = _view(task_samples(resolve_task("evalfloor_fixtures/seeded_memory_probe")))
    second = _view(task_samples(resolve_task("evalfloor_fixtures/seeded_memory_probe")))

    explicit = _dataset()
    explicit.shuffle(seed=SHUFFLE_SEED)
    explicit.shuffle_choices(seed=SHUFFLE_SEED)
    expected = _view(task_samples(Task(dataset=explicit, scorer=choice())))

    assert first == second == expected


# --------------------------------------------------------------------------
# Nothing leaks out of the block
# --------------------------------------------------------------------------


def test_everything_is_put_back_after_the_block_and_after_an_exception() -> None:
    before = _originals()

    with seeded_shuffles():
        inside = _originals()
    assert all(now is not then for now, then in zip(inside, before))
    assert all(now is then for now, then in zip(_originals(), before))

    with pytest.raises(RuntimeError, match="mid-load"):
        with seeded_shuffles():
            raise RuntimeError("mid-load")
    assert all(now is then for now, then in zip(_originals(), before))


def test_a_task_that_fails_to_load_leaves_nothing_replaced() -> None:
    before = _originals()
    with pytest.raises(Exception, match="could not be read"):
        resolve_task("evalfloor_fixtures/seeded_load_fails")
    assert all(now is then for now, then in zip(_originals(), before))


# --------------------------------------------------------------------------
# Fingerprints: the seed is in the run's, not the battery's
# --------------------------------------------------------------------------


def test_the_battery_fingerprint_did_not_move() -> None:
    assert battery_fingerprint() == FIRST_SWEEP_FINGERPRINT


def test_the_shuffle_seed_is_in_the_run_fingerprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = run_fingerprint()
    assert before != battery_fingerprint()
    monkeypatch.setattr(battery, "SHUFFLE_SEED", SHUFFLE_SEED + 1)
    assert run_fingerprint() != before
    assert battery_fingerprint() == FIRST_SWEEP_FINGERPRINT


@pytest.mark.parametrize(
    "arm_dir", ["results/graded", "results/smoke/graded", "results/smoke/graded_vocab"]
)
def test_the_committed_graded_cache_keys_still_resolve(arm_dir: str) -> None:
    """Keys recomputed today must find the rows the 17 Sep runs wrote.

    A cache row stores only its key, but every refusal row records the cell it
    came from: task, scorer, sample, member, arm and judge, though not the seed.
    Seed 0 is graded for every member, ``uniform`` included, so the seed-0 key
    of every cell the log names was written. Every one must be found.
    """
    directory = REPO / arm_dir

    def rows(name: str) -> list[dict[str, Any]]:
        lines = (directory / name).read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    keys = {row["key"] for row in rows("graded_cache.jsonl")}
    refusals = rows("refusals.jsonl")
    assert refusals
    missing = [
        r
        for r in refusals
        if GradedCache.key(
            r["task"], r["scorer"], r["sample_id"], r["member"], 0, r["arm"],
            r["grader_model"],
        )
        not in keys
    ]
    assert not missing, f"{len(missing)} of {len(refusals)} keys no longer resolve"


# --------------------------------------------------------------------------
# The real task
# --------------------------------------------------------------------------


@pytest.mark.dataset
def test_two_truthfulqa_loads_agree_on_every_choice_and_target() -> None:
    """The check B4 names. Two loads through ``resolve_task`` and
    ``task_samples``, compared on (id, choices, target) for all 817 samples.

    Before the hook, the choice shuffle drew its seed from the system on every
    load, so this comparison failed. The last assertion checks the choices are
    still shuffled: the seed pins the shuffle, it does not switch it off.
    """

    def load() -> list[tuple[Any, tuple[str, ...], Any]]:
        return _view(task_samples(resolve_task("inspect_evals/truthfulqa")))

    first, second = load(), load()
    assert len(first) == 817
    assert all(choices for _, choices, _ in first)
    assert first == second
    assert len({target for _, _, target in first}) > 1
