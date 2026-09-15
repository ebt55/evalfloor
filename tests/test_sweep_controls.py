"""The three controls named in the build guide, run against real tasks.

1.  **Positive control.** A task scored with ``exact()`` / ``match(numeric=True)``
    over numeric targets must show every content-free member at or near zero. If
    it does not, the harness credits completions it should not and no other
    number in this repository means anything.
2.  **Synthetic negative control.** A purpose-built task with a deliberately
    loose scorer, committed under ``tests/fixtures``, must be flagged. A detector
    that cannot fail on a case built to fail is not a gate.
3.  **Determinism control.** Two sweeps of the smoke set must produce an
    identical digest. Any difference is an instrument defect and gets logged
    rather than smoothed.

``tests/test_controls.py`` holds the fast, no-network versions of the same
ideas. This file is the version that runs against the real collection, and is
marked ``dataset`` accordingly.
"""

from __future__ import annotations

import asyncio

import pytest

from evalfloor.aggregate import aggregate_run, sweep_digest
from evalfloor.battery import CONTENT_FREE_NAMES
from evalfloor.cli import SMOKE_TASKS
from evalfloor.drive import drive_task_async
from fixtures import loose_eval

#: A content-free member at or below this on a tight scorer counts as "near zero".
NEAR_ZERO = 0.05


def _run(task_obj, name: str):
    return asyncio.run(drive_task_async(name, task=task_obj))


def _run_named(name: str, limit: int | None = None):
    return asyncio.run(drive_task_async(name, limit=limit))


# --------------------------------------------------------------------------
# 1. Positive control, against a real eval
# --------------------------------------------------------------------------


@pytest.mark.dataset
def test_positive_control_gsm8k_scores_near_zero_throughout() -> None:
    """gsm8k: ``match(numeric=True)`` over numeric answers.

    Nothing content-free should get near it. ``echo`` is the one that scores at
    all -- echoing a word problem back returns numbers that appear in the
    problem statement, and occasionally one of them is the answer. It stays far
    below the majority line.
    """
    run = _run_named("inspect_evals/gsm8k")
    assert run.error is None, run.error
    floor = aggregate_run(run)[0]
    assert floor.scorer == "inspect_ai/match"

    for name in CONTENT_FREE_NAMES:
        score = floor.members.get(name)
        if score is None or not score.applicable:
            continue
        assert score.mean <= NEAR_ZERO, (
            f"{name} scored {score.mean:.3f} on a numeric match() task; "
            "the harness is crediting something it should not"
        )
    assert floor.flagged is False


@pytest.mark.dataset
def test_positive_control_holds_on_both_arms() -> None:
    """The rendering rule must not manufacture a score on a tight task."""
    run = _run_named("inspect_evals/gsm8k")
    floor = aggregate_run(run)[0]
    assert floor.answer_template == "bare"
    for name in CONTENT_FREE_NAMES:
        raw = floor.members_raw.get(name)
        if raw is None or not raw.applicable:
            continue
        assert raw.mean <= NEAR_ZERO
    assert floor.flagged_raw is False


def test_positive_control_fixture_exact_numeric() -> None:
    """The same control with no network, on the committed fixture."""
    run = _run(loose_eval.exact_numeric(), "evalfloor_fixtures/exact_numeric")
    floor = aggregate_run(run)[0]
    for name in CONTENT_FREE_NAMES:
        score = floor.members.get(name)
        if score is None or not score.applicable:
            continue
        assert score.n_correct == 0, f"{name} scored on exact() numerics"
    assert floor.flagged is False


# --------------------------------------------------------------------------
# 2. Synthetic negative control
# --------------------------------------------------------------------------


def test_synthetic_negative_control_is_flagged() -> None:
    """The fixture is built to fail. The flag rule must catch it."""
    run = _run(loose_eval.loose_refusal(), "evalfloor_fixtures/loose_refusal")
    assert run.error is None
    floor = aggregate_run(run)[0]

    assert floor.flagged is True, "the detector failed to detect a case built to fail"
    assert "all_labels" in floor.flagged_by
    assert floor.members["all_labels"].mean == 1.0
    assert floor.members["all_labels"].example_completion == "compliance refusal"


def test_synthetic_negative_control_chance_line_is_computed() -> None:
    """Two thirds "compliance", so the line is 0.667 and not 0.5."""
    run = _run(loose_eval.loose_refusal(), "evalfloor_fixtures/loose_refusal")
    floor = aggregate_run(run)[0]
    assert floor.majority_label == "compliance"
    assert floor.majority == pytest.approx(2 / 3, abs=1e-9)
    assert floor.n_samples == loose_eval.FIXTURE_N


def test_the_same_scorer_is_not_flagged_when_the_target_is_the_ground_truth() -> None:
    """``tight_flags`` uses the identical ``includes()`` scorer as the loose
    fixture. It is not flagged, because its targets are CTF-style flags rather
    than natural-language property names. The flag rule is about the floor under
    a task, not about which scorer function appears in its source."""
    run = _run(loose_eval.tight_flags(), "evalfloor_fixtures/tight_flags")
    floor = aggregate_run(run)[0]
    assert floor.scorer == "inspect_ai/includes"
    assert floor.flagged is False
    # Every target is unique, so there is no closed label set at all.
    assert floor.members["all_labels"].applicable is False


def test_the_gate_exits_non_zero_on_the_fixture() -> None:
    from evalfloor.cli import main

    assert main(["check", "evalfloor_fixtures/loose_refusal"]) == 1
    assert main(["check", "evalfloor_fixtures/tight_flags"]) == 0
    assert main(["check", "evalfloor_fixtures/exact_numeric"]) == 0


# --------------------------------------------------------------------------
# 3. Determinism control, over the smoke set
# --------------------------------------------------------------------------


@pytest.mark.dataset
def test_two_sweeps_of_the_smoke_set_have_the_same_digest() -> None:
    """Two independent sweeps of the real smoke set, digests compared.

    The digest deliberately excludes wall-clock timings, which vary by design,
    and covers every score, count and completion that must not.
    """
    first = [_run_named(name, limit=200) for name in SMOKE_TASKS]
    second = [_run_named(name, limit=200) for name in SMOKE_TASKS]

    assert [r.error for r in first] == [None] * len(SMOKE_TASKS)
    assert sweep_digest(first) == sweep_digest(second)


@pytest.mark.dataset
def test_shuffled_datasets_still_yield_a_stable_limited_subset() -> None:
    """Instrument defect 004, pinned.

    ``paws`` and ``boolq`` both declare ``shuffle: bool = True`` and do not seed
    the shuffle, so two calls to the task function return the same samples in a
    different order. Before ``task_samples`` sorted by id, any ``--limit`` took a
    different subset each run and the determinism control failed for a reason
    that had nothing to do with this harness.
    """
    from evalfloor.drive import resolve_task, task_samples

    for name in ("inspect_evals/paws", "inspect_evals/boolq"):
        first = [s.id for s in task_samples(resolve_task(name), limit=50)]
        second = [s.id for s in task_samples(resolve_task(name), limit=50)]
        assert first == second, f"{name}: limited subset is not stable across calls"


@pytest.mark.dataset
def test_the_smoke_set_covers_every_scorer_family_in_the_twenty() -> None:
    """If this fails the smoke set has stopped being representative."""
    families = set()
    for name in SMOKE_TASKS:
        run = _run_named(name, limit=1)
        assert run.error is None, f"{name}: {run.error}"
        families.update(run.scorers)
    assert families == {
        "inspect_ai/choice",
        "inspect_ai/match",
        "inspect_ai/pattern",
        "inspect_ai/includes",
        "inspect_ai/f1",
    }


def test_generated_markdown_is_byte_identical_for_the_fixture_sweep() -> None:
    """Determinism at the report level, with no network involved."""
    from evalfloor.report import render_matrix

    a = aggregate_run(_run(loose_eval.loose_refusal(), "evalfloor_fixtures/loose_refusal"))
    b = aggregate_run(_run(loose_eval.loose_refusal(), "evalfloor_fixtures/loose_refusal"))
    assert render_matrix(a) == render_matrix(b)
