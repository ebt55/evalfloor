"""The anchor. Reproduces Inspect Evals issue #2331 from committed code.

Issue #2331 was opened on 2026-08-31 by **caiotheodoro**, who showed that the
constant string ``"yesno"`` scores 8000 of 8000 on ``paws`` because the eval is
scored with ``includes()`` and both labels are substrings of the constant. That
finding is theirs. This test does not claim it; it pins it, so that the harness
is anchored to a known answer before it is pointed at anything unknown.

What this test adds to the issue is that the result is a property of the scorer
rather than of the particular constant someone picked. The ``all_labels`` battery
member is not ``"yesno"`` -- it is ``"No Yes"``, built mechanically from the
dataset's own distinct targets -- and it reaches the same 8000 of 8000.

**Pinned versions.** ``inspect_evals==0.20.0`` (the newest release; its
``src/inspect_evals/paws/paws.py`` still reads ``scorer=includes()``) and
``inspect_ai==0.3.263``. PR #2334 replaces that scorer with an anchored pattern
and, as of 2026-09-15, is open and unmerged, so no release contains it. When it
merges and ships, this test is expected to fail on the newer version, and that
failure is the correct signal -- do not "fix" it, re-pin it and say so.

Marked ``dataset``, because it downloads the PAWS labeled_final test split (8000
samples, about 123 MiB of Hub repository, cached after the first run). It runs by
default -- it is the anchor, so a bare ``pytest`` should exercise it. Skip it on
a machine with no network with ``pytest -m "not dataset"``.
"""

from __future__ import annotations

import importlib.metadata as md

import pytest

from evalfloor.battery import BATTERY, MEMBERS_BY_NAME
from evalfloor.drive import drive_task_async, label_set, resolve_task, task_samples

PINNED_INSPECT_EVALS = "0.20.0"
PINNED_INSPECT_AI = "0.3.263"

TASK = "inspect_evals/paws"
EXPECTED_SAMPLES = 8000

pytestmark = pytest.mark.dataset


def test_pins_are_what_the_measurement_assumes() -> None:
    """The reproduction is only meaningful on the versions it claims."""
    assert md.version("inspect_evals") == PINNED_INSPECT_EVALS
    assert md.version("inspect_ai") == PINNED_INSPECT_AI


def test_paws_still_scores_with_includes() -> None:
    """The precondition for the whole issue: paws uses a substring scorer.

    If PR #2334 has landed in the pinned version, this fails first and says so,
    rather than leaving a confusing 0/8000 further down.
    """
    from inspect_ai._util.registry import registry_info
    from inspect_evals.paws.paws import paws as paws_module_task

    import inspect_evals.paws.paws as paws_src

    source = __import__("inspect", fromlist=["getsource"]).getsource(paws_src)
    assert "scorer=includes()" in source, (
        "paws no longer uses includes() in the pinned version. PR #2334 has "
        "probably landed. Re-pin the test to a version that still has it and "
        "record the change in NOTES.md -- do not relax the assertion."
    )
    assert paws_module_task is not None
    assert registry_info(paws_module_task).name == TASK


@pytest.fixture(scope="module")
def paws_run():
    task = resolve_task(TASK)
    import asyncio

    return asyncio.run(drive_task_async(TASK, task=task))


def test_dataset_is_the_one_the_issue_describes(paws_run) -> None:
    assert paws_run.error is None, paws_run.error
    assert paws_run.n_samples == EXPECTED_SAMPLES
    assert paws_run.scorers == ["inspect_ai/includes"]
    assert paws_run.n_distinct_labels == 2
    assert paws_run.labels_closed is True


def test_all_labels_is_the_constant_string_no_yes() -> None:
    """The member is built from the dataset, not hand-written."""
    task = resolve_task(TASK)
    samples = task_samples(task)
    labels = label_set(samples)
    member = MEMBERS_BY_NAME["all_labels"]
    completion = member.completion(samples[0], labels)
    assert completion == "No Yes"
    # Constant: the same string for every sample, by construction.
    assert {member.completion(s, labels) for s in samples[:200]} == {"No Yes"}


def test_2331_all_labels_scores_every_sample(paws_run) -> None:
    """THE ANCHOR. 8000 of 8000, on the pinned version."""
    arm = next(a for a in paws_run.arms if a.member == "all_labels")
    assert arm.n_errors == 0
    assert arm.n_scored == EXPECTED_SAMPLES
    assert arm.n_correct == EXPECTED_SAMPLES, (
        f"expected {EXPECTED_SAMPLES}/{EXPECTED_SAMPLES}, got "
        f"{arm.n_correct}/{arm.n_scored}"
    )
    assert arm.mean == 1.0


def test_a_content_free_member_beats_the_majority_baseline(paws_run) -> None:
    """The flag rule fires on paws, which is what makes it a flagged task.

    The majority baseline is computed from the dataset, not assumed to be 0.5:
    the PAWS test split is 55.8 per cent "No".
    """
    majority = next(a for a in paws_run.arms if a.member == "majority")
    all_labels = next(a for a in paws_run.arms if a.member == "all_labels")
    assert majority.n_correct == 4464
    assert majority.mean == pytest.approx(0.558, abs=1e-9)
    assert all_labels.mean >= majority.mean


def test_the_empty_and_boilerplate_members_score_nothing(paws_run) -> None:
    """A control inside the anchor: not everything scores, so the harness is
    not simply crediting every completion it is handed."""
    for name in ("empty", "whitespace", "refusal", "all_letters", "boilerplate", "format_only"):
        arm = next(a for a in paws_run.arms if a.member == name)
        assert arm.n_correct == 0, f"{name} unexpectedly scored {arm.n_correct}"
        assert arm.n_errors == 0


def test_echo_scores_without_being_designed_to(paws_run) -> None:
    """A secondary finding, pinned so a version bump cannot silently change it.

    Echoing the input back scores on 970 of 8000 samples, because that many of
    the paired sentences happen to contain "yes" or "no" as a substring
    somewhere in their natural-language text. Nobody constructed that; it falls
    out of substring matching over prose.
    """
    arm = next(a for a in paws_run.arms if a.member == "echo")
    assert arm.n_correct == 970
    assert arm.mean == pytest.approx(0.12125, abs=1e-9)


def test_every_battery_member_produced_an_arm(paws_run) -> None:
    """Every member, every seed, in both the raw and the rendered arm."""
    from evalfloor.battery import ARMS

    expected = sum(len(m.seeds) for m in BATTERY) * len(ARMS)
    assert len(paws_run.arms) == expected
    assert all(a.applicable for a in paws_run.arms)


def test_paws_declares_no_answer_template_so_the_arms_coincide(paws_run) -> None:
    """paws is scored by ``includes()`` over free prose, not by a choice
    template, so rendering is the identity here and the two arms must be
    identical. That is what makes the 8000/8000 result independent of the
    rendering rule: no choice made about templates can have produced it."""
    assert paws_run.answer_template == "bare"
    raw = {(a.member, a.seed): a.n_correct for a in paws_run.arms if a.arm == "raw"}
    rendered = {
        (a.member, a.seed): a.n_correct for a in paws_run.arms if a.arm == "rendered"
    }
    assert raw == rendered
    assert raw[("all_labels", 0)] == EXPECTED_SAMPLES
