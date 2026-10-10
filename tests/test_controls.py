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
    a = sorted(
        (x.seed, x.n_correct)
        for x in run_a.arms
        if x.member == "uniform" and x.arm == "rendered"
    )
    b = sorted(
        (x.seed, x.n_correct)
        for x in run_b.arms
        if x.member == "uniform" and x.arm == "rendered"
    )
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


def _ruling_row(**over) -> str:
    import json

    row = {
        "task": "inspect_evals/tau2_airline",
        "action": "not_counted",
        "treatment": "needs solver state",
        "reason": "fixture",
        "source": "tests/test_controls.py",
        "date": "2026-10-10",
        "author": "ebt55",
    }
    row.update(over)
    return json.dumps({k: v for k, v in row.items() if v is not None}) + "\n"


def test_a_not_counted_row_must_name_its_treatment(tmp_path) -> None:
    from evalfloor.rulings import RulingError, load_rulings

    path = tmp_path / "rulings.jsonl"
    path.write_text(_ruling_row(), encoding="utf-8")
    (row,) = load_rulings(path)
    assert (row.action, row.treatment) == ("not_counted", "needs solver state")

    for bad in (
        _ruling_row(treatment=None),                    # no treatment
        _ruling_row(treatment="  "),                    # an empty one
        _ruling_row(scorer="inspect_ai/choice"),        # half a task
        _ruling_row(action="unflag"),                   # treatment on another action
    ):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(RulingError):
            load_rulings(path)


def test_not_counted_rows_are_listed_not_swept(tmp_path) -> None:
    """A not_counted task is never swept, so matching no floor is its normal
    state: it is listed with its treatment, never as "matched no task". Listed
    on the deterministic arm only; the graded arm's files do not change."""
    import json
    import pathlib

    from evalfloor.aggregate import flag_rate
    from evalfloor.cli import CLOSEOUT_TASKS, closeout_task_list
    from evalfloor.report import read_sweep, write_all
    from evalfloor.rulings import apply_rulings, load_rulings

    path = tmp_path / "rulings.jsonl"
    path.write_text(
        _ruling_row()
        + _ruling_row(task="evalfloor/control_loose", treatment="needs a judge"),
        encoding="utf-8",
    )
    rules = load_rulings(path)

    # The list: a not_counted task never reaches the sweep at all.
    assert "inspect_evals/tau2_airline" not in CLOSEOUT_TASKS
    assert closeout_task_list(rules) == list(CLOSEOUT_TASKS)
    lab = tmp_path / "lab.jsonl"
    lab.write_text(_ruling_row(task="inspect_evals/lab_bench_dbqa"), encoding="utf-8")
    dropped = load_rulings(lab)
    assert "inspect_evals/lab_bench_dbqa" not in closeout_task_list(dropped)
    assert len(closeout_task_list(dropped)) == len(CLOSEOUT_TASKS) - 1

    # Matching nothing is not "unmatched"; matching a floor takes it out of
    # every rate, with the treatment as the reason.
    floors = aggregate_run(_run(controls.control_loose(), "evalfloor/control_loose"))
    assert flag_rate(floors) == (1, 1)
    after, applied, unmatched = apply_rulings(floors, rules)
    assert unmatched == []
    assert after[0].error == "not counted: needs a judge"
    assert flag_rate(after) == (0, 0)
    assert [a.effect for a in applied] == [
        "evalfloor/control_loose: not counted (needs a judge)"
    ]

    # Rendered: the deterministic arm lists the treatments...
    inventory = [
        {
            "name": "inspect_evals/tau2_airline", "reachable": True,
            "exclusion_reason": "", "exclusion_detail": "",
            "scorer_expr": "airline_scorer()", "scorer_class": "deterministic_custom",
        }
    ]
    payload = {"arm": "deterministic", "pins": {}, "tasks": [], "floors": [], "runs": []}
    write_all(payload, tmp_path / "det", path, inventory=inventory)
    coverage = (tmp_path / "det" / "coverage.md").read_text(encoding="utf-8")
    applied_md = (tmp_path / "det" / "rulings_applied.md").read_text(encoding="utf-8")
    assert "| `inspect_evals/tau2_airline` | `airline_scorer()` | " in coverage
    assert "| not counted | `not_counted` | needs solver state |" in coverage
    assert "| needs solver state | 1 | `tau2_airline` |" in coverage
    assert "## Not counted: listed, never swept" in applied_md
    assert "matched no task" not in applied_md

    # ...and the graded arm's files are byte-identical with or without the rows.
    root = pathlib.Path(__file__).resolve().parent.parent
    graded = read_sweep(root / "results" / "graded" / "sweep.json")
    committed_rules = (root / "rulings.jsonl").read_text(encoding="utf-8")
    plain = tmp_path / "plain.jsonl"
    plain.write_text(committed_rules, encoding="utf-8")
    plus = tmp_path / "plus.jsonl"
    plus.write_text(committed_rules + path.read_text(encoding="utf-8"), encoding="utf-8")
    full_inventory = json.loads(
        (root / "results" / "task_inventory.json").read_text(encoding="utf-8")
    )
    write_all(graded, tmp_path / "g_plain", plain, inventory=full_inventory)
    write_all(graded, tmp_path / "g_plus", plus, inventory=full_inventory)
    for name in ("floor_matrix.md", "coverage.md", "rulings_applied.md"):
        a = (tmp_path / "g_plain" / name).read_text(encoding="utf-8")
        b = (tmp_path / "g_plus" / name).read_text(encoding="utf-8")
        assert a == b, f"graded {name} changed when not_counted rows were added"


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


# --------------------------------------------------------------------------
# 7. Instrument defects, pinned so they cannot come back
# --------------------------------------------------------------------------


def test_multiple_choice_tasks_are_actually_driven() -> None:
    """Defect found in the first smoke sweep, 2026-09-15.

    ``choice()`` does not read the completion text. It reads which entries of
    ``state.choices`` are marked correct, and only the ``multiple_choice()``
    solver marks them, by parsing "ANSWER: X" after generation. Driving the
    scorer without that step scored every member zero on every multiple-choice
    task -- including the reference baselines -- so ``majority`` was 0 and the
    whole battery satisfied ``0 >= 0``. Every choice() task in the collection
    would have been reported as flagged.
    """
    from inspect_ai import Task
    from inspect_ai.dataset import MemoryDataset, Sample
    from inspect_ai.scorer import choice

    samples = [
        Sample(
            id=i,
            input="pick one",
            choices=["alpha", "beta", "gamma", "delta"],
            target="B" if i % 2 else "A",
        )
        for i in range(40)
    ]
    run = _run(Task(dataset=MemoryDataset(samples), scorer=choice()), "evalfloor/mc_probe")
    floor = aggregate_run(run)[0]

    # The chance line must be a real chance line, not zero.
    assert floor.majority > 0.0, "majority baseline failed to parse: instrument defect"
    assert floor.majority == pytest.approx(0.5, abs=1e-9)
    # format_only is "ANSWER: A", which genuinely selects option A.
    assert floor.members["format_only"].mean == pytest.approx(0.5, abs=1e-9)
    # A bare letter list is not an answer, so it selects nothing.
    assert floor.members["all_letters"].mean == 0.0


def test_a_task_where_nothing_scores_is_not_flagged() -> None:
    """The zero guard on the flag rule. 0 >= 0 is a defect signature, not a floor.

    A scorer that never credits anything stands in for the real case: a scorer
    the harness cannot drive. Before the guard, its majority line was 0 and every
    content-free member satisfied ``0 >= 0``, so the task reported as flagged by
    the entire battery -- which is exactly what ``sec_qa_v2`` did.
    """
    from inspect_ai import Task
    from inspect_ai.dataset import MemoryDataset, Sample
    from inspect_ai.scorer import INCORRECT, Score, Target, accuracy, scorer
    from inspect_ai.solver import TaskState

    @scorer(metrics=[accuracy()], name="evalfloor/never_scores")
    def never_scores():
        async def score(state: TaskState, target: Target) -> Score:
            return Score(value=INCORRECT)

        return score

    samples = [Sample(id=i, input="q", target="Yes" if i % 2 else "No") for i in range(20)]
    run = _run(
        Task(dataset=MemoryDataset(samples), scorer=never_scores()), "evalfloor/null_probe"
    )
    floor = aggregate_run(run)[0]
    assert floor.majority == 0.0
    assert all(s.mean == 0.0 for s in floor.members.values() if s.applicable)
    assert floor.flagged is False, "a task where nothing scores must not be flagged"
    assert floor.flagged_by == []


# --------------------------------------------------------------------------
# 8. Generated prose carries generated numbers
# --------------------------------------------------------------------------


def _floor_with_echo(task: str, echo_correct: int, n: int, template: str = "bare"):
    from evalfloor.aggregate import MemberScore, TaskFloor, wilson_interval

    low, high = wilson_interval(echo_correct, n)

    def _echo(arm: str):
        return MemberScore(
            member="echo",
            mean=echo_correct / n,
            n_correct=echo_correct,
            n_scored=n,
            applicable=True,
            arm=arm,
            ci_low=low,
            ci_high=high,
        )

    # Both arms, as the deterministic sweep always scores them. A floor with no
    # raw arm is one the report prints as "not run" (defect 009).
    return TaskFloor(
        task=task,
        scorer="inspect_ai/includes",
        n_samples=n,
        sampled=False,
        answer_template=template,
        members={"echo": _echo("rendered")},
        members_raw={"echo": _echo("raw")},
    )


def test_echo_headline_counts_are_computed_not_typed() -> None:
    from evalfloor.report import echo_headline

    floors = [
        _floor_with_echo("inspect_evals/paws", 970, 8000),
        _floor_with_echo("inspect_evals/gsm8k", 28, 1319),
        _floor_with_echo("inspect_evals/boolq", 0, 3270),
    ]
    line = echo_headline(floors)
    assert line is not None
    assert "2 of 3" in line, "only the tasks scoring above zero are counted"
    assert "970 of 8,000" in line, "the worst task is named with its own counts"
    assert "paws" in line


def test_echo_headline_is_absent_when_there_is_nothing_to_report() -> None:
    from evalfloor.report import echo_headline

    assert echo_headline([]) is None


def test_rendering_finding_states_the_collapse_and_the_tightness() -> None:
    from evalfloor.aggregate import MemberScore
    from evalfloor.report import rendering_finding

    floor = _floor_with_echo("inspect_evals/sec_qa_v2", 0, 100, template="choice")
    floor.majority = 0.31
    floor.majority_raw = 0.0
    floor.flagged_raw = True
    floor.flagged = False
    floor.members["all_labels"] = MemberScore(
        member="all_labels", mean=0.0, n_correct=0, n_scored=100, applicable=True
    )
    text = rendering_finding([floor])
    assert text is not None
    assert "collapses to zero" in text
    assert "0.000" in text
    assert "raw arm" in text


def test_rendering_finding_says_so_when_no_task_declares_a_template() -> None:
    from evalfloor.report import rendering_finding

    text = rendering_finding([_floor_with_echo("inspect_evals/paws", 970, 8000)])
    assert text is not None
    assert "identical by construction" in text


# --------------------------------------------------------------------------
# The README's defect table against the lessons file
#
# The table is written by hand in report.py and the write-ups live in
# INSTRUMENT_LESSONS.md. It silently went three defects stale once already, so
# the agreement between the two is a control rather than a habit.
# --------------------------------------------------------------------------


def _lesson_headings() -> list[tuple[str, str]]:
    """``(number, heading)`` for every entry in ``INSTRUMENT_LESSONS.md``."""
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parent.parent
    text = (root / "INSTRUMENT_LESSONS.md").read_text(encoding="utf-8")
    return re.findall(r"^## (\d{3}) -- (.+)$", text, flags=re.MULTILINE)


def test_the_readme_defect_table_lists_every_logged_defect() -> None:
    from evalfloor.report import INSTRUMENT_DEFECT_ROWS

    logged = _lesson_headings()
    assert logged, "INSTRUMENT_LESSONS.md has no numbered entries to check against"

    in_file = [number for number, _heading in logged]
    in_table = [number for number, _defect, _invalidated in INSTRUMENT_DEFECT_ROWS]

    assert in_table == in_file, (
        "the README defect table and INSTRUMENT_LESSONS.md disagree: "
        f"table has {in_table}, file has {in_file}"
    )
    # Numbered newest last, with no hole: a gap means an entry was never written.
    assert in_file == [f"{n:03d}" for n in range(1, len(in_file) + 1)], (
        f"instrument defect numbers are not contiguous from 001: {in_file}"
    )


def test_the_readme_defect_table_quotes_the_lessons_headings_verbatim() -> None:
    from evalfloor.report import INSTRUMENT_DEFECT_ROWS

    headings = dict(_lesson_headings())
    for number, defect, invalidated in INSTRUMENT_DEFECT_ROWS:
        assert defect == headings[number], (
            f"defect {number} is summarised differently in the README table "
            f"({defect!r}) and in INSTRUMENT_LESSONS.md ({headings[number]!r})"
        )
        assert invalidated.strip(), f"defect {number} says nothing about its effect"


def test_the_rendered_readme_carries_every_defect_row() -> None:
    from evalfloor.report import INSTRUMENT_DEFECT_ROWS, render_readme

    text = render_readme(None, None)
    for number, defect, _invalidated in INSTRUMENT_DEFECT_ROWS:
        assert f"| {number} | {defect} |" in text


# --------------------------------------------------------------------------
# 8. The format_only / majority template collision (preregistration 8.5)
# --------------------------------------------------------------------------


def _collision_floor():
    from fixtures import loose_eval  # noqa: F401  (registers the fixture tasks)

    run = asyncio.run(
        drive_task_async("evalfloor_fixtures/template_collision")
    )
    return aggregate_run(run)[0]


def test_a_flag_that_rests_only_on_the_template_collision_is_marked() -> None:
    """`format_only` is defined as the answer template with a placeholder,
    `ANSWER: A`. `majority` is the modal target written in that same template.
    Where the modal target IS `A` they are one string, they score identically,
    and the `>=` in the flag rule fires on a tie between a member and itself.

    Section 8.5 decides both halves: the tie rule stays exactly as written, and
    a flag resting only on the collision is marked rather than silently counted.
    """
    floor = _collision_floor()

    # The flag itself is unchanged. The rule is not weakened after seeing data.
    assert floor.flagged is True
    assert floor.flagged_by == ["format_only"]

    assert floor.collision is True
    assert floor.members["format_only"].example_completion == "ANSWER: A"
    assert (
        floor.members["format_only"].example_completion
        == floor.members["majority"].example_completion
    )
    assert "format_only" in floor.collision_note
    assert "ANSWER: A" in floor.collision_note


def test_a_flag_with_another_member_behind_it_is_not_a_collision() -> None:
    """The mark is for a flag that rests ONLY on the collision. The synthetic
    negative control is flagged by `all_labels`, which is a finding."""
    from fixtures import loose_eval  # noqa: F401

    run = asyncio.run(drive_task_async("evalfloor_fixtures/loose_refusal"))
    floor = aggregate_run(run)[0]
    assert floor.flagged is True
    assert "all_labels" in floor.flagged_by
    assert floor.collision is False
    assert floor.collision_note == ""


def test_the_collision_is_counted_and_never_removed_from_the_rate() -> None:
    from evalfloor.aggregate import collision_count, flag_rate

    floor = _collision_floor()
    assert flag_rate([floor]) == (1, 1), (
        "a marked collision is still a flag; 8.5 marks it rather than dropping it"
    )
    assert collision_count([floor]) == 1


def test_the_matrix_and_the_readme_carry_the_collision_mark() -> None:
    from evalfloor.report import render_matrix, render_readme

    floor = _collision_floor()
    matrix = render_matrix([floor], [floor], digest="d", payload={})
    assert "| collision |" in matrix
    assert "**yes**" in matrix
    assert "rest on the template collision" in matrix
    assert floor.collision_note[:40] in matrix

    inventory = [
        {
            "name": floor.task,
            "reachable": True,
            "exclusion_reason": "",
            "exclusion_detail": "",
            "scorer_expr": "exact()",
            "scorer_class": "deterministic",
        }
    ]
    readme = render_readme([floor], inventory, {})
    assert "rest on the template collision" in readme


# --------------------------------------------------------------------------
# 9. The README reads both arms, whichever command triggered it
# --------------------------------------------------------------------------


def _payload(floors, **over):
    payload = {
        "schema": 2,
        "pins": {},
        "tasks": [f.task for f in floors],
        "digest": "fixture",
        "smoke": False,
        "runs": [],
        "floors": [f.to_dict() for f in floors],
    }
    payload.update(over)
    return payload


def _fixture_inventory(floors):
    return [
        {
            "name": f.task,
            "reachable": True,
            "exclusion_reason": "",
            "exclusion_detail": "",
            "scorer_expr": "includes()",
            "scorer_class": "deterministic",
        }
        for f in floors
    ]


def _deterministic_floors():
    from fixtures import loose_eval  # noqa: F401

    floors = []
    for name in (
        "evalfloor_fixtures/loose_refusal",   # flagged
        "evalfloor_fixtures/tight_flags",     # clean
    ):
        floors.extend(aggregate_run(asyncio.run(drive_task_async(name))))
    return floors


def _graded_floors(tmp_path):
    from evalfloor.graded import GRADERS, GradedCache, RefusalLog, grade_task_async

    run, _ = asyncio.run(
        grade_task_async(
            "evalfloor_fixtures/loose_refusal", GRADERS["mock"], cap=4,
            cache=GradedCache.load(tmp_path / "gc.jsonl"),
            refusals=RefusalLog(tmp_path / "gr.jsonl"),
            print_estimate=False,
        )
    )
    return aggregate_run(run)


def test_a_graded_regenerate_does_not_overwrite_the_deterministic_headline(
    tmp_path,
) -> None:
    """`sweep --first-sweep --graded` wrote the deterministic headline into
    README.md and then, seconds later, overwrote it with the graded arm's --
    a headline whose denominator is 8 capped samples instead of 58 whole
    datasets, under a sentence that says "of the whole collection". Nothing
    failed; which arm the README quoted depended on command order.
    """
    from evalfloor.report import write_all, write_sweep

    results = tmp_path / "results"
    readme = tmp_path / "README.md"
    rulings = tmp_path / "rulings.jsonl"

    det_floors = _deterministic_floors()
    det_payload = _payload(det_floors)
    write_sweep(det_payload, results / "sweep.json")

    graded_floors = _graded_floors(tmp_path)
    graded_payload = _payload(
        graded_floors, arm="graded", cap=4, grader={"model": "mockllm/model"}
    )

    # The graded arm regenerates SECOND, which is the order that used to lose
    # the deterministic headline.
    write_all(
        graded_payload,
        results / "graded",
        rulings,
        inventory=_fixture_inventory(det_floors),
        readme_path=readme,
    )
    text = readme.read_text(encoding="utf-8")

    assert "**1 of 2 tasks** swept" in text, (
        "the headline must come from results/sweep.json, which has two tasks"
    )
    assert "**1 of 1 tasks** swept" not in text
    # ...and the graded arm still appears, in its own section with its own
    # denominator, never added to the one above.
    assert "## The model-graded arm" in text
    assert "never added" in text


def test_a_deterministic_regenerate_picks_up_the_graded_section(tmp_path) -> None:
    from evalfloor.report import write_all, write_sweep

    results = tmp_path / "results"
    readme = tmp_path / "README.md"
    rulings = tmp_path / "rulings.jsonl"

    graded_floors = _graded_floors(tmp_path)
    write_sweep(
        _payload(graded_floors, arm="graded", cap=4, grader={"model": "mockllm/model"}),
        results / "graded" / "sweep.json",
    )

    det_floors = _deterministic_floors()
    write_all(
        _payload(det_floors),
        results,
        rulings,
        inventory=_fixture_inventory(det_floors),
        readme_path=readme,
    )
    text = readme.read_text(encoding="utf-8")
    assert "**1 of 2 tasks** swept" in text
    assert "## The model-graded arm" in text, (
        "order must not decide whether the graded arm appears at all"
    )


def test_a_smoke_payload_never_reaches_the_readme_through_the_other_arm(
    tmp_path,
) -> None:
    """results/smoke/ is exempt from the ordering gate because it is not a
    result. Reading the other arm off disk must not let one in by the side
    door."""
    from evalfloor.report import readme_arms, write_sweep

    results = tmp_path / "results"
    det_floors = _deterministic_floors()
    write_sweep(
        _payload(det_floors, arm="graded", smoke=True), results / "graded" / "sweep.json"
    )
    arms = readme_arms(_payload(det_floors), det_floors, results, [])
    assert arms["graded_payload"] is None
    assert arms["graded_floors"] == []
