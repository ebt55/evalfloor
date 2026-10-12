"""B7's computed lines: every branch, from arguments alone.

The close-out README must not carry a typed number, and must not claim the
``paws`` fix is confirmed unless the floors say so. Every test builds its
floors in memory, or drives the committed fixture tasks, and pins the release
at a made-up ``9.9.0`` so a typed "0.24.0" anywhere would show.
"""

from __future__ import annotations

import asyncio
import datetime

import pytest

from evalfloor.aggregate import MemberScore, TaskFloor, aggregate_run, collision_count, flag_rate
from evalfloor.battery import CONTENT_FREE_NAMES
from evalfloor.closeout import (
    LIST_FIXED_AT,
    NON_DETERMINISTIC,
    CloseoutCounts,
    citations_line,
    counts,
    representative_floor,
    denominator_line,
    determinism_line,
    first_line,
    fix_confirmed,
    pins_line,
    preregistration_line,
    section1_sentence,
    status_line,
)
from evalfloor.drive import drive_task_async
from evalfloor.rulings import Ruling
from fixtures import loose_eval

RELEASE = "9.9.0"
PINS = {"inspect_ai": "0.3.263", "inspect_evals": RELEASE}
PAWS = "inspect_evals/paws"
BOOLQ = "inspect_evals/boolq"

#: Words no close-out surface may carry (Acceptance, README).
FORBIDDEN = ("planned", "WIP", "not merged", "in flight")


def _score(member: str, mean: float) -> MemberScore:
    return MemberScore(
        member=member, mean=mean, n_correct=round(mean * 100), n_scored=100, applicable=True
    )


def _floor(
    task: str,
    *,
    flag: str | None = None,
    best_member: str | None = None,
    mean: float = 0.0,
    majority: float = 0.25,
    collision: bool = False,
    scorer: str = "inspect_ai/choice",
    nothing_scored: bool = False,
) -> TaskFloor:
    """A floor shaped the way aggregate_run leaves one: every content-free
    member present, ``flagged_by`` naming the members that reach ``majority``,
    and ``gap_to_majority`` the best content-free mean minus ``majority``."""
    members = {name: _score(name, 0.0) for name in CONTENT_FREE_NAMES}
    members["majority"] = _score("majority", majority)
    best = flag or best_member
    if best:
        members[best] = _score(best, mean)
    return TaskFloor(
        task=task,
        scorer=scorer,
        n_samples=100,
        sampled=False,
        majority_label="A",
        majority=majority,
        members=members,
        best_member=best or CONTENT_FREE_NAMES[0],
        best_mean=mean,
        gap_to_majority=mean - majority,
        flagged=bool(flag),
        flagged_by=[flag] if flag else [],
        collision=collision,
        nothing_scored=nothing_scored,
    )


def _errored(task: str, error: str) -> TaskFloor:
    return TaskFloor(task=task, scorer="-", n_samples=0, sampled=False, error=error)


def _tie(task: str) -> TaskFloor:
    return _floor(task, flag="format_only", mean=0.25, majority=0.25, collision=True)


def _inventory(reachable: list[str], unreachable: list[str] = ()) -> list[dict]:
    return [{"name": n, "reachable": True} for n in reachable] + [
        {"name": n, "reachable": False} for n in unreachable
    ]


def _counts(floors, tasks, rulings=(), inventory=None, anchor=None, **kw) -> CloseoutCounts:
    return counts(
        floors,
        {"tasks": tasks, "pins": PINS},
        rulings,
        inventory if inventory is not None else _inventory(tasks),
        anchor if anchor is not None else _inventory(tasks),
        **kw,
    )


def _clean_fix() -> list[TaskFloor]:
    return [_floor(PAWS, majority=0.558), _floor(BOOLQ, majority=0.622)]


def _ruling(task: str, action: str, source: str, scorer: str | None = None) -> Ruling:
    return Ruling(task=task, action=action, reason="why", source=source, scorer=scorer)


# --------------------------------------------------------------------------
# counts
# --------------------------------------------------------------------------


def test_counts_reads_every_number_from_its_arguments() -> None:
    floors = [
        *_clean_fix(),
        _tie("inspect_evals/tie"),
        _floor("inspect_evals/real", flag="echo", mean=0.6, majority=0.5),
        _floor("inspect_evals/clean"),
        _errored("inspect_evals/broken", "dataset load failed: OSError: gone"),
        _floor("inspect_evals/wobbly"),
        _floor("inspect_evals/silent", nothing_scored=True),
        _floor("inspect_evals/not_listed", flag="echo", mean=0.9),
    ]
    listed = [
        PAWS, BOOLQ, "inspect_evals/tie", "inspect_evals/real", "inspect_evals/clean",
        "inspect_evals/broken", "inspect_evals/wobbly", "inspect_evals/silent",
        "inspect_evals/missing",
    ]
    c = _counts(
        floors,
        listed,
        inventory=_inventory(listed + ["inspect_evals/extra"], ["inspect_evals/gated"]),
        anchor=_inventory(listed[:4], ["inspect_evals/old"]),
        nondeterministic={"inspect_evals/wobbly"},
    )

    assert (c.N, c.C, c.F, c.K, c.real) == (5, 9, 2, 1, 1)
    assert (c.R, c.D, c.R0) == (10, 11, 4)
    assert c.X == ("inspect_evals/extra",)
    assert c.flagged == ("inspect_evals/real", "inspect_evals/tie")
    assert c.ties == ("inspect_evals/tie",)
    assert c.real_flags == ("inspect_evals/real",)
    assert dict(c.not_run) == {
        "inspect_evals/broken": "dataset load failed: OSError: gone",
        "inspect_evals/wobbly": NON_DETERMINISTIC,
        "inspect_evals/silent": "nothing scored",
        "inspect_evals/missing": "no result in the payload",
    }
    assert c.N + len(c.not_run) == c.C
    assert c.release == RELEASE


def test_x_leaves_out_listed_and_not_counted_tasks_only() -> None:
    listed = [PAWS, BOOLQ]
    rulings = [
        _ruling("inspect_evals/tau2_airline", "not_counted", "src/x.py:1: needs solver state"),
        # A ruling of any other action does not take a task off the X list.
        _ruling("inspect_evals/bbh", "note", "src/bbh.py:9: a note"),
    ]
    inventory = _inventory(
        listed + ["inspect_evals/tau2_airline", "inspect_evals/bbh", "inspect_evals/arc"],
        ["inspect_evals/unreachable"],
    )
    c = _counts(_clean_fix(), listed, rulings, inventory=inventory)
    assert c.X == ("inspect_evals/arc", "inspect_evals/bbh")


def test_a_task_is_a_tie_only_when_every_flagged_floor_is_one() -> None:
    """A real flag on one scorer must never hide behind a tie on another."""
    both = [
        _tie("inspect_evals/two_scorers"),
        _floor(
            "inspect_evals/two_scorers", flag="echo", mean=0.5, scorer="inspect_ai/match"
        ),
    ]
    c = _counts([*_clean_fix(), *both], [PAWS, BOOLQ, "inspect_evals/two_scorers"])
    assert (c.F, c.K, c.real) == (1, 0, 1)


def test_counts_matches_aggregate_on_the_fixture_tasks() -> None:
    """The fixtures through the real driver and aggregate: ``template_collision``
    is a tie, ``loose_refusal`` a real flag, ``tight_flags`` clean."""
    driven = [
        (loose_eval.template_collision(), "evalfloor_fixtures/template_collision"),
        (loose_eval.loose_refusal(), "evalfloor_fixtures/loose_refusal"),
        (loose_eval.tight_flags(), "evalfloor_fixtures/tight_flags"),
    ]
    floors = [
        f
        for task, name in driven
        for f in aggregate_run(asyncio.run(drive_task_async(name, task=task)))
    ]
    c = _counts(floors, [name for _, name in driven])
    assert (c.F, c.N) == flag_rate(floors)
    assert c.K == collision_count(floors)
    assert c.ties == ("evalfloor_fixtures/template_collision",)
    assert c.real_flags == ("evalfloor_fixtures/loose_refusal",)


@pytest.mark.parametrize(
    "payload",
    [
        {"pins": PINS},
        {"tasks": [PAWS], "pins": {"inspect_ai": "0.3.263"}},
        {"tasks": [PAWS, PAWS], "pins": PINS},
    ],
)
def test_counts_refuses_a_payload_it_cannot_count(payload: dict) -> None:
    with pytest.raises(ValueError):
        counts(_clean_fix(), payload, [], [], [])


def test_the_list_was_fixed_against_the_58_reachable_at_list_fixed_at() -> None:
    """``counts`` takes the 0.20.0 inventory as an argument and reads no git;
    the constant says where a caller gets it, and this test gets it there."""
    import json
    import pathlib
    import subprocess

    assert LIST_FIXED_AT == "316f142"
    proc = subprocess.run(
        ["git", "show", f"{LIST_FIXED_AT}:results/task_inventory.json"],
        cwd=str(pathlib.Path(__file__).resolve().parent.parent),
        capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        pytest.skip(f"{LIST_FIXED_AT} is not in this clone's history")
    anchor = json.loads(proc.stdout)
    c = _counts(_clean_fix(), [PAWS, BOOLQ], anchor=anchor)
    assert c.R0 == 58
    assert len(anchor) == 237


# --------------------------------------------------------------------------
# representative_floor
# --------------------------------------------------------------------------

TASK = "inspect_evals/multi"


def _pick(*floors: TaskFloor) -> TaskFloor:
    """The chosen floor, which must not depend on the order floors arrive in."""
    import itertools

    picks = {id(representative_floor(list(p))) for p in itertools.permutations(floors)}
    assert len(picks) == 1, "the choice moved with the input order"
    return representative_floor(list(floors))


def test_a_real_flag_stands_for_the_task_before_a_tie_or_a_bigger_gap() -> None:
    real = _floor(TASK, flag="echo", mean=0.3, majority=0.3, scorer="s/c")
    tie = _floor(TASK, flag="format_only", mean=0.9, majority=0.9, collision=True, scorer="s/a")
    errored = _errored(TASK, "boom")
    assert _pick(real, tie, errored) is real


def test_a_tie_stands_before_an_unflagged_floor() -> None:
    tie = _floor(TASK, flag="format_only", mean=0.25, collision=True, scorer="s/z")
    close = _floor(TASK, best_member="echo", mean=0.24, majority=0.25, scorer="s/a")
    assert _pick(tie, close) is tie


def test_unflagged_floors_go_by_the_largest_gap_then_scorer_name() -> None:
    far = _floor(TASK, best_member="echo", mean=0.0, majority=0.5, scorer="s/a")
    near = _floor(TASK, best_member="echo", mean=0.4, majority=0.5, scorer="s/b")
    assert _pick(far, near) is near
    level = _floor(TASK, best_member="echo", mean=0.4, majority=0.5, scorer="s/a")
    assert _pick(near, level) is level


def test_flags_of_one_class_go_by_scorer_name() -> None:
    b = _floor(TASK, flag="echo", mean=0.9, majority=0.5, scorer="s/b")
    a = _floor(TASK, flag="refusal", mean=0.6, majority=0.5, scorer="s/a")
    assert _pick(a, b) is a
    tie_b = _floor(TASK, flag="format_only", mean=0.5, majority=0.5, collision=True, scorer="s/b")
    tie_a = _floor(TASK, flag="format_only", mean=0.5, majority=0.5, collision=True, scorer="s/a")
    assert _pick(tie_a, tie_b) is tie_a


def test_a_scored_floor_stands_before_an_errored_or_silent_one() -> None:
    """An errored floor's gap defaults to 0.0, above any real negative gap, so
    the scored class has to come first or the error would win."""
    scored = _floor(TASK, best_member="echo", mean=0.0, majority=0.5, scorer="s/z")
    errored = _errored(TASK, "boom")
    silent = _floor(TASK, nothing_scored=True, scorer="s/a")
    assert _pick(scored, errored, silent) is scored
    assert _pick(errored, silent).scorer == "-"


def test_representative_floor_refuses_nothing_and_mixed_tasks() -> None:
    with pytest.raises(ValueError):
        representative_floor([])
    with pytest.raises(ValueError):
        representative_floor([_floor("a/one"), _floor("a/two")])


def _every_kind_of_single_floor() -> list[TaskFloor]:
    """One floor per task, of every kind a sweep can leave after rulings."""
    flagged_then_not_counted = _floor("k/not_counted", flag="echo", mean=0.9)
    flagged_then_not_counted.error = "not counted: needs a judge"  # what apply_rulings does
    return [
        *_clean_fix(),
        _floor("k/clean", best_member="echo", mean=0.1),
        _floor("k/real", flag="all_labels", mean=1.0, majority=0.558),
        _floor("k/real_at_the_line", flag="refusal", mean=0.3, majority=0.3),
        _tie("k/tie"),
        _errored("k/errored", "dataset load failed: OSError"),
        _floor("k/silent", nothing_scored=True),
        flagged_then_not_counted,
        _floor("k/unflagged", best_member="echo", mean=0.9, majority=0.5),
    ]


def test_a_single_floor_is_its_own_representative() -> None:
    for floor in _every_kind_of_single_floor():
        assert representative_floor([floor]) is floor


def test_single_scorer_counts_are_what_aggregate_counts() -> None:
    """``representative_floor`` changes nothing for a one-scorer task: N, F and
    K are exactly ``aggregate.flag_rate`` and ``collision_count``, and each
    task lands where the per-floor rule puts it."""
    floors = _every_kind_of_single_floor()
    c = _counts(floors, [f.task for f in floors])

    assert (c.F, c.N) == flag_rate(floors)
    assert c.K == collision_count(floors)
    assert c.ran == tuple(sorted(f.task for f in floors if f.error is None and not f.nothing_scored))
    assert c.flagged == tuple(sorted(f.task for f in floors if f.error is None and f.flagged))
    assert c.ties == tuple(
        sorted(f.task for f in floors if f.error is None and f.flagged and f.collision)
    )
    assert dict(c.not_run) == {
        "k/errored": "dataset load failed: OSError",
        "k/silent": "nothing scored",
        "k/not_counted": "not counted: needs a judge",
    }
    assert (c.N, c.F, c.K, c.real) == (7, 3, 1, 2)


def test_counts_counts_each_task_on_its_representative_floor() -> None:
    tasks = [PAWS, BOOLQ, "t/tie_and_clean", "t/error_and_scored", "t/all_errored"]
    floors = [
        *_clean_fix(),
        _tie("t/tie_and_clean"),
        _floor("t/tie_and_clean", scorer="inspect_ai/match"),
        _errored("t/error_and_scored", "one scorer failed"),
        _floor("t/error_and_scored", scorer="inspect_ai/match"),
        _errored("t/all_errored", "both failed"),
    ]
    c = _counts(floors, tasks)
    assert c.ties == ("t/tie_and_clean",)
    assert "t/error_and_scored" in c.ran
    assert dict(c.not_run) == {"t/all_errored": "both failed"}


# --------------------------------------------------------------------------
# section1_sentence
# --------------------------------------------------------------------------

NEGATIVE = "Preregistered negative result."


@pytest.mark.parametrize("F, K", [(0, 0), (4, 0), (4, 4), (1, 0)])
def test_fewer_than_five_is_the_negative_result(F: int, K: int) -> None:
    assert section1_sentence(F, K) == NEGATIVE


@pytest.mark.parametrize("F", [5, 7])
def test_five_or_more_all_ties_is_crossed_only_by_ties(F: int) -> None:
    assert section1_sentence(F, F) == (
        f"{F} flagged under the preregistered rule, all of them ties by construction; "
        "the threshold of five is crossed only by ties, so the negative result does "
        "not hold as written."
    )


@pytest.mark.parametrize("F, K", [(5, 4), (6, 0), (7, 5)])
def test_five_or_more_with_a_real_flag_does_not_hold(F: int, K: int) -> None:
    assert section1_sentence(F, K) == (
        f"{F} flagged under the preregistered rule, {K} of them ties; the "
        "preregistered negative result does not hold."
    )


def test_section1_takes_its_threshold_and_refuses_impossible_counts() -> None:
    assert section1_sentence(3, 3, threshold=3).count("the threshold of three") == 1
    assert section1_sentence(2, 0, threshold=3) == NEGATIVE
    with pytest.raises(ValueError):
        section1_sentence(2, 3)
    with pytest.raises(ValueError):
        section1_sentence(2, -1)


# --------------------------------------------------------------------------
# first_line
# --------------------------------------------------------------------------


def _opening(n: int) -> str:
    return (
        f"I fed eight answers with no content to the real scorers of {n} Inspect "
        f"Evals tasks that run without a model, on `inspect_evals` {RELEASE}."
    )


CONFIRMED = (
    "The one loose scorer this tool found on 0.20.0, `paws` (reported first by "
    "caiotheodoro, #2331), was fixed upstream in v0.21.0. This sweep confirms "
    "the fix."
)


def _ties(K: int, more: bool) -> str:
    return (
        f"On {K}{' more' if more else ''}, the placeholder answer is also the most "
        "common answer, so its score ties the baseline by construction (§8.5)."
    )


def test_no_real_flag_and_fewer_than_five_is_the_guides_paragraph() -> None:
    floors = [*_clean_fix(), _tie("inspect_evals/t1"), _floor("inspect_evals/c1")]
    tasks = [PAWS, BOOLQ, "inspect_evals/t1", "inspect_evals/c1"]
    c = _counts(floors, tasks)
    assert (c.F, c.K, c.real) == (1, 1, 0)
    assert first_line(c, floors, []) == (
        f"{_opening(4)} None reached its majority baseline except as a tie. "
        f"{_ties(1, more=False)} " + CONFIRMED
    )
    assert section1_sentence(c.F, c.K) == NEGATIVE


def test_no_flag_at_all_drops_the_tie_clause() -> None:
    c = _counts(_clean_fix(), [PAWS, BOOLQ])
    assert first_line(c, _clean_fix(), []) == (
        f"{_opening(2)} None reached its majority baseline. {CONFIRMED}"
    )


def test_five_ties_and_no_real_flag() -> None:
    ties = [_tie(f"inspect_evals/t{i}") for i in range(5)]
    floors = [*_clean_fix(), *ties]
    c = _counts(floors, [f.task for f in floors])
    assert (c.F, c.K, c.real) == (5, 5, 0)
    line = first_line(c, floors, [])
    assert "None reached its majority baseline except as a tie. On 5," in line
    assert line.endswith(CONFIRMED)
    assert "crossed only by ties" in section1_sentence(c.F, c.K)


def test_five_ties_and_two_real_flags_names_each_real_flag() -> None:
    real = [
        _floor("inspect_evals/r_one", flag="echo", mean=0.61, majority=0.5),
        _floor("inspect_evals/r_two", flag="all_labels", mean=1.0, majority=0.558),
    ]
    ties = [_tie(f"inspect_evals/t{i}") for i in range(5)]
    floors = [*_clean_fix(), *real, *ties]
    c = _counts(floors, [f.task for f in floors])
    assert (c.F, c.K, c.real) == (7, 5, 2)
    rulings = [_ruling("inspect_evals/r_two", "note", "src/r_two.py:41: scorer=includes()")]
    assert first_line(c, floors, rulings) == (
        f"{_opening(9)} 2 reached their majority baselines outright, not as ties. "
        "On `inspect_evals/r_one`, `echo` scores 61.0% against a 50.0% baseline. "
        "The cause is unclassified. On `inspect_evals/r_two`, `all_labels` scores "
        "100.0% against a 55.8% baseline. The reason is that scorer=includes(). "
        f"{_ties(5, more=True)} " + CONFIRMED
    )
    assert citations_line(c, floors, rulings) == (
        "Lines cited in the `inspect_evals/r_two` ruling: src/r_two.py:41."
    )
    assert section1_sentence(c.F, c.K).endswith("does not hold.")


def test_the_lead_drops_cited_asides_and_the_section_end_keeps_the_lines() -> None:
    source = (
        "its few-shot examples end in `ANSWER: <label>` (bbh.py:98-108) and the "
        "scorers keep the last `ANSWER:` (_multiple_choice.py:106-115, "
        "_util/pattern.py:1-8), so echo gives one fixed label per subset"
    )
    floors = [*_clean_fix(), _floor("inspect_evals/bbh", flag="echo", mean=0.262, majority=0.158)]
    rulings = [_ruling("inspect_evals/bbh", "note", source)]
    c = _counts(floors, [f.task for f in floors])
    assert (c.F, c.K, c.real) == (1, 0, 1)
    line = first_line(c, floors, rulings)
    assert ".py:" not in line
    assert ";" not in line
    assert (
        "On `inspect_evals/bbh`, `echo` scores 26.2% against a 15.8% baseline. The "
        "reason is that its few-shot examples end in `ANSWER: <label>` and the "
        "scorers keep the last `ANSWER:`, so echo gives one fixed label per subset. "
    ) in line
    assert citations_line(c, floors, rulings) == (
        "Lines cited in the `inspect_evals/bbh` ruling: bbh.py:98-108, "
        "_multiple_choice.py:106-115, _util/pattern.py:1-8."
    )
    assert citations_line(c, floors, []) == ""


def test_one_real_flag_under_five_reads_its_cause_from_the_last_matching_note() -> None:
    floors = [
        *_clean_fix(),
        _floor("inspect_evals/r", flag="refusal", mean=0.3, majority=0.3, scorer="s/a"),
    ]
    rulings = [
        _ruling("inspect_evals/r", "note", "src/r.py:1: first"),
        _ruling("inspect_evals/r", "note", "src/r.py:2: second"),
        _ruling("inspect_evals/r", "note", "src/r.py:3: another scorer", scorer="s/b"),
        _ruling("inspect_evals/r", "unflag", "src/r.py:4: not a note"),
    ]
    c = _counts(floors, [f.task for f in floors])
    assert (c.F, c.K, c.real) == (1, 0, 1)
    line = first_line(c, floors, rulings)
    assert (
        "1 reached its majority baseline outright, not as a tie. "
        "On `inspect_evals/r`, `refusal` scores 30.0% against a 30.0% baseline. "
        "The reason is that second."
    ) in line
    assert "the placeholder answer is also the most common answer" not in line  # K == 0
    assert section1_sentence(c.F, c.K) == NEGATIVE


def test_a_flagged_paws_gets_no_confirmation() -> None:
    floors = [_floor(PAWS, flag="all_labels", mean=1.0, majority=0.558), _floor(BOOLQ)]
    c = _counts(floors, [PAWS, BOOLQ])
    line = first_line(c, floors, [])
    assert "confirms" not in line
    assert line.endswith(
        "was fixed upstream in v0.21.0. In this sweep `paws` is flagged, so it does "
        "not confirm the fix."
    )
    assert not fix_confirmed(c, floors)


def test_a_missing_paws_gets_no_confirmation() -> None:
    floors = [_floor(BOOLQ)]
    c = _counts(floors, [BOOLQ])
    line = first_line(c, floors, [])
    assert "confirms" not in line
    assert "In this sweep `paws` has no result, so it does not confirm the fix." in line


def test_an_errored_or_non_deterministic_fix_task_gets_no_confirmation() -> None:
    floors = [_errored(PAWS, "dataset load failed: TimeoutError"), _floor(BOOLQ)]
    c = _counts(floors, [PAWS, BOOLQ], nondeterministic={BOOLQ})
    line = first_line(c, floors, [])
    assert (
        "In this sweep `paws` did not run and `boolq` did not run, so it does not "
        "confirm the fix."
    ) in line
    assert c.N == 0


# --------------------------------------------------------------------------
# The other lines
# --------------------------------------------------------------------------


def test_status_line() -> None:
    assert status_line("2026-10-14") == "Status: closed 2026-10-14; no further sweeps."
    assert status_line(datetime.date(2026, 10, 14)) == status_line("2026-10-14")
    with pytest.raises(ValueError):
        status_line("mid-October")


def test_denominator_line_names_what_it_leaves_off() -> None:
    listed = [PAWS, BOOLQ]
    none_off = _counts(_clean_fix(), listed, anchor=_inventory(listed + ["a/b"]))
    assert denominator_line(none_off) == (
        f"2 of 2 countable on {RELEASE}. The list was fixed in §11 from the 3 tasks "
        f"reachable on 0.20.0; {RELEASE} reaches 2 of 2 declared, and no reachable "
        "task is left off the list."
    )
    one_off = _counts(_clean_fix(), listed, inventory=_inventory(listed + ["i/x"]))
    assert denominator_line(one_off).endswith(
        "and the 1 reachable task not on the list is named, not run: `i/x`."
    )
    two_off = _counts(
        _clean_fix(), listed, inventory=_inventory(listed + ["i/y", "i/x"], ["i/z"])
    )
    assert denominator_line(two_off).endswith(
        f"{RELEASE} reaches 4 of 5 declared, and the 2 reachable tasks not on the list "
        "are named, not run: `i/x`, `i/y`."
    )


def test_determinism_line_every_branch() -> None:
    a, b = "a" * 64, "b" * 64
    assert determinism_line(a, a) == (
        f"Two runs in separate processes, digest `{a[:16]}` both times."
    )
    assert determinism_line(a, b, ["t/two", "t/one"]) == (
        f"Two runs in separate processes, digests `{a[:16]}` and `{b[:16]}`. 2 tasks "
        "differ between them and are not run under §11.7: `t/one`, `t/two`."
    )
    assert "1 task differs between them and is not run" in determinism_line(a, b, ["t"])
    assert "does not show the sweep is deterministic" in determinism_line(a, None)
    for args in ((a, a, ["t"]), (a, b, []), (a, None, ["t"])):
        with pytest.raises(ValueError):
            determinism_line(*args)


def test_pins_line_reads_each_arm_from_its_own_pins() -> None:
    graded = {"inspect_ai": "0.3.263", "inspect_evals": "0.20.0"}
    assert pins_line(PINS, graded) == (
        f"Deterministic arm: `inspect_evals` {RELEASE}. Graded arm: 0.20.0, not "
        "re-run. Arms are never added."
    )
    # "not re-run" is only true when the graded arm is on another release.
    assert "not re-run" not in pins_line(PINS, PINS)
    assert "Graded arm: none recorded." in pins_line(PINS, None)
    with pytest.raises(ValueError):
        pins_line({"inspect_ai": "0.3.263"}, graded)


def test_preregistration_line_prints_both_hashes() -> None:
    p, a = "912345f8d5be" + "0" * 28, "abcdef123456" + "1" * 28
    assert preregistration_line(p, a) == (
        "Preregistration committed at `912345f8d5be`; its close-out addendum, §11, at "
        "`abcdef123456`. `git log --format='%H %ad' -- PREREGISTRATION.md` lists both."
    )
    assert preregistration_line(p, None).endswith("no close-out addendum is recorded.")
    assert preregistration_line(None, None) == "No preregistration commit is recorded."


# --------------------------------------------------------------------------
# Nothing typed, nothing stale
# --------------------------------------------------------------------------


def _every_output() -> list[str]:
    real = _floor("inspect_evals/r", flag="echo", mean=0.6, majority=0.5)
    scenarios = [
        ([*_clean_fix()], [PAWS, BOOLQ]),
        ([*_clean_fix(), _tie("inspect_evals/t"), real], [PAWS, BOOLQ, "inspect_evals/t", "inspect_evals/r"]),
        ([_floor(PAWS, flag="all_labels", mean=1.0)], [PAWS, BOOLQ]),
    ]
    out: list[str] = []
    for floors, tasks in scenarios:
        c = _counts(floors, tasks, inventory=_inventory(tasks + ["i/x"]))
        out += [first_line(c, floors, []), denominator_line(c), section1_sentence(c.F, c.K)]
    out += [section1_sentence(5, 5), section1_sentence(6, 5)]
    out += [status_line("2026-10-14"), pins_line(PINS, {"inspect_evals": "0.20.0"})]
    out += [determinism_line("a" * 64, "a" * 64), determinism_line("a" * 64, "b" * 64, ["t"])]
    out += [preregistration_line("a" * 40, "b" * 40), determinism_line("a" * 64, None)]
    return out


def test_no_output_says_planned_wip_not_merged_or_in_flight() -> None:
    for text in _every_output():
        for word in FORBIDDEN:
            assert word.lower() not in text.lower(), (word, text)


def test_no_output_types_the_release() -> None:
    """The release comes from the pins, so a made-up one is all that appears."""
    for text in _every_output():
        assert "0.24.0" not in text, text
    assert all(RELEASE in t for t in _every_output()[:2])
