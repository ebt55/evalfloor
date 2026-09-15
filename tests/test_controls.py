"""Controls. None of these needs a network or a dataset download.

If the positive control fails, the harness credits completions it should not and
nothing else in the repository means anything. If the synthetic negative control
fails, the detector does not detect and the exit code is worthless.
"""

from __future__ import annotations

import asyncio

import pytest

from evalfloor import controls
from evalfloor.aggregate import aggregate_run, sweep_digest, wilson_interval
from evalfloor.battery import CONTENT_FREE_NAMES, LabelSet, MEMBERS_BY_NAME
from evalfloor.drive import drive_task_async


def _run(task_obj, name: str):
    return asyncio.run(drive_task_async(name, task=task_obj))


# --------------------------------------------------------------------------
# 1. Positive control
# --------------------------------------------------------------------------


def test_positive_control_scores_zero_for_every_content_free_member() -> None:
    run = _run(controls.control_tight(), "evalfloor/control_tight")
    assert run.error is None
    assert run.n_samples == controls.CONTROL_N
    floor = aggregate_run(run)[0]
    for name in CONTENT_FREE_NAMES:
        score = floor.members[name]
        if not score.applicable:
            continue
        assert score.n_correct == 0, f"{name} scored {score.n_correct} on exact() numerics"
    assert floor.flagged is False


def test_positive_control_majority_is_near_zero_because_targets_are_unique() -> None:
    """Every target appears once, so there is no label set and the modal target
    carries one sample in 120. The flag rule still has a line to compare to."""
    run = _run(controls.control_tight(), "evalfloor/control_tight")
    floor = aggregate_run(run)[0]
    assert floor.majority == pytest.approx(1 / controls.CONTROL_N)
    assert floor.members["all_labels"].applicable is False
    assert floor.members["uniform"].applicable is False


# --------------------------------------------------------------------------
# 2. Synthetic negative control
# --------------------------------------------------------------------------


def test_synthetic_negative_control_is_flagged() -> None:
    run = _run(controls.control_loose(), "evalfloor/control_loose")
    assert run.error is None
    floor = aggregate_run(run)[0]
    assert floor.flagged is True
    assert "all_labels" in floor.flagged_by
    assert floor.members["all_labels"].mean == 1.0


def test_synthetic_negative_control_majority_is_computed_not_assumed() -> None:
    """Two thirds "No", so the chance line is 0.667 and not 0.5."""
    run = _run(controls.control_loose(), "evalfloor/control_loose")
    floor = aggregate_run(run)[0]
    assert floor.majority_label == "No"
    assert floor.majority == pytest.approx(2 / 3, abs=1e-9)


def test_the_gate_separates_the_two_controls() -> None:
    from evalfloor.cli import main

    assert main(["check", "evalfloor/control_tight"]) == 0
    assert main(["check", "evalfloor/control_loose"]) == 1


# --------------------------------------------------------------------------
# 3. Determinism control
# --------------------------------------------------------------------------


def test_two_sweeps_produce_the_same_digest() -> None:
    first = [
        _run(controls.control_tight(), "evalfloor/control_tight"),
        _run(controls.control_loose(), "evalfloor/control_loose"),
    ]
    second = [
        _run(controls.control_tight(), "evalfloor/control_tight"),
        _run(controls.control_loose(), "evalfloor/control_loose"),
    ]
    assert sweep_digest(first) == sweep_digest(second)


def test_generated_markdown_is_byte_identical_across_runs() -> None:
    """The determinism control is a plain file comparison, so the report must
    carry no timestamp and no wall-clock timing."""
    from evalfloor.report import render_matrix

    runs = [_run(controls.control_loose(), "evalfloor/control_loose")]
    floors_a = aggregate_run(runs[0])
    floors_b = aggregate_run(_run(controls.control_loose(), "evalfloor/control_loose"))
    assert render_matrix(floors_a) == render_matrix(floors_b)


def test_uniform_member_is_seeded_reproducibly() -> None:
    run_a = _run(controls.control_loose(), "evalfloor/control_loose")
    run_b = _run(controls.control_loose(), "evalfloor/control_loose")
    a = sorted((x.seed, x.n_correct) for x in run_a.arms if x.member == "uniform")
    b = sorted((x.seed, x.n_correct) for x in run_b.arms if x.member == "uniform")
    assert a == b
    assert len(a) == 5


# --------------------------------------------------------------------------
# 4. The battery itself
# --------------------------------------------------------------------------


def test_label_set_thresholds() -> None:
    closed = LabelSet.from_targets(["Yes", "No", "No", "No"])
    assert closed.is_closed
    assert closed.majority_label == "No"
    assert closed.majority_share == 0.75

    unique = LabelSet.from_targets([f"answer {i}" for i in range(10)])
    assert not unique.is_closed

    long_labels = LabelSet.from_targets(["x" * 200, "x" * 200, "y" * 200])
    assert not long_labels.is_closed


def test_all_labels_is_a_constant_string_over_the_dataset() -> None:
    labels = LabelSet.from_targets(["Yes", "No", "No"])
    member = MEMBERS_BY_NAME["all_labels"]
    assert member.completion(object(), labels) == "No Yes"


def test_members_that_need_a_label_set_say_so_rather_than_guessing() -> None:
    labels = LabelSet.from_targets([f"free text answer {i}" for i in range(10)])
    for name in ("all_labels", "uniform"):
        assert MEMBERS_BY_NAME[name].applies_to(labels) is False
        assert MEMBERS_BY_NAME[name].completion(object(), labels) is None
    for name in ("empty", "whitespace", "refusal", "boilerplate", "format_only"):
        assert MEMBERS_BY_NAME[name].applies_to(labels) is True


# --------------------------------------------------------------------------
# 5. Rulings are applied mechanically
# --------------------------------------------------------------------------


def test_a_ruling_changes_the_after_number_and_not_the_before_number(tmp_path) -> None:
    from evalfloor.aggregate import flag_rate
    from evalfloor.rulings import apply_rulings, load_rulings

    run = _run(controls.control_loose(), "evalfloor/control_loose")
    before = aggregate_run(run)
    assert flag_rate(before) == (1, 1)

    path = tmp_path / "rulings.jsonl"
    path.write_text(
        '{"task": "evalfloor/control_loose", "action": "unflag", '
        '"reason": "control task, not part of the collection", '
        '"source": "src/evalfloor/controls.py:79: scorer=includes()", '
        '"date": "2026-09-15", "author": "ebt55"}\n',
        encoding="utf-8",
    )
    after, applied, unmatched = apply_rulings(before, load_rulings(path))
    assert len(applied) == 1
    assert unmatched == []
    assert flag_rate(after) == (0, 1)
    assert flag_rate(before) == (1, 1), "the before numbers must not be mutated"


def test_a_malformed_ruling_is_an_error_not_a_warning(tmp_path) -> None:
    from evalfloor.rulings import RulingError, load_rulings

    path = tmp_path / "rulings.jsonl"
    path.write_text('{"task": "x", "action": "unflag"}\n', encoding="utf-8")
    with pytest.raises(RulingError):
        load_rulings(path)

    path.write_text(
        '{"task": "x", "action": "nonsense", "reason": "r", "source": "s"}\n',
        encoding="utf-8",
    )
    with pytest.raises(RulingError):
        load_rulings(path)


# --------------------------------------------------------------------------
# 6. Interval arithmetic
# --------------------------------------------------------------------------


def test_wilson_interval_brackets_the_point_estimate() -> None:
    low, high = wilson_interval(50, 100)
    assert low < 0.5 < high
    assert 0.0 <= low and high <= 1.0
    # a wider interval on fewer samples
    low_small, high_small = wilson_interval(5, 10)
    assert (high_small - low_small) > (high - low)
    assert wilson_interval(0, 0) == (0.0, 0.0)
