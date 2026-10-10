"""Write ``results/*.md`` and ``README.md``. No number is typed by hand.

Every figure that appears in the matrix, the coverage file, the rulings log or
the README is computed here from a committed sweep payload plus
``rulings.jsonl`` plus the generated inventory. The files carry a "GENERATED"
banner and the pins the measurement was taken under, so a row produced under one
version pair can never be silently read next to another.

Generated markdown deliberately contains **no timestamps and no wall-clock
timings**, so two sweeps of the deterministic arms produce byte-identical output
and the determinism control is a plain file comparison.
"""

from __future__ import annotations

import datetime
import html
import json
import pathlib
import re
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from . import closeout
from .aggregate import TaskFloor, collision_count, flag_rate
from .battery import (
    ARMS,
    BATTERY,
    BOILERPLATE_TEXT,
    CONTENT_FREE_NAMES,
    FORMAT_ONLY_TEXT,
    REFERENCE_NAMES,
    REFUSAL_TEXT,
)
from .rulings import AppliedRuling, Ruling

GENERATED_BANNER = (
    "<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. "
    "Every number here is computed from results/sweep.json and rulings.jsonl. -->"
)

#: Fewer than this many flagged reachable tasks is the preregistered negative
#: result: the collection is tighter than the single known case suggested.
#: PREREGISTRATION.md section 1.
NEGATIVE_RESULT_THRESHOLD = 5

#: The model-graded arm's own threshold, fixed separately in section 8A because
#: its denominator is 8, not 58. Until 2026-10-10 the report applied the five
#: above to both arms, and so printed "Preregistered negative result" over a
#: graded 3 of 7 that section 8A says is not one. Instrument defect 009.
GRADED_NEGATIVE_RESULT_THRESHOLD = 3

#: One threshold per arm, keyed by the payload's ``"arm"``.
NEGATIVE_RESULT_THRESHOLDS: dict[str, int] = {
    "deterministic": NEGATIVE_RESULT_THRESHOLD,
    "graded": GRADED_NEGATIVE_RESULT_THRESHOLD,
}

#: The heading of PREREGISTRATION.md section 11. ``git log -S`` on this string
#: finds the commit that added it, which the close-out sweep stamps and the
#: generated files print beside the original preregistration commit.
ADDENDUM_HEADING = "## 11. Close-out addendum"

#: The error a task gets when its two runs disagree (section 11.7). Set before
#: rulings, so the task leaves every rate, before and after, and says why.
NOT_RUN_NONDETERMINISTIC = "not run: non-deterministic"

#: What two runs must share before their per-task digests are comparable.
REPEAT_MUST_MATCH = ("pins", "run_fingerprint", "tasks")

#: What a cell prints for an arm that was never scored. Never ``0.0%``.
NOT_RUN = "not run"

#: What a cell prints where the arm ran but not one item scored. Never ``0.0%``.
NO_RESULT = "NO RESULT"

#: What provenance prints for a field the payload does not carry. Never filled
#: in from the environment ``report`` happens to run in.
NOT_RECORDED = "not recorded"

#: Beside an interval whose own point estimate falls outside it.
POINT_OUTSIDE_MARK = "**point outside**"

_NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven",
                 "eight", "nine", "ten")

#: Exclusion reasons, with the plain-English meaning printed beside each count.
EXCLUSION_MEANINGS: dict[str, str] = {
    "sandbox_required": "the task or its scorer needs a container",
    "extra_dependency": "needs an optional dependency group that is not installed",
    "model_graded": "the scorer needs a grader model; not part of the deterministic arm",
    "network_required": "fetches from a URL or clones a repository at run time",
    "gated_dataset": "the Hugging Face dataset requires accepting terms or an access grant",
    "too_large": "the dataset exceeds the disk cap recorded in PREREGISTRATION.md",
    "unclassified_scorer": "the scorer could not be resolved statically",
    "not_registered": "no entry in inspect_evals._registry",
    "load_error": "the task function raised when it was run",
}


def _pct(x: float | None) -> str:
    # None is an arm that was never scored, which is not a score of zero.
    if x is None:
        return NOT_RUN
    return f"{100 * x:.1f}%"


def _esc(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _spelled(n: int) -> str:
    return _NUMBER_WORDS[n] if 0 <= n < len(_NUMBER_WORDS) else str(n)


def payload_arm(payload: dict[str, Any] | None) -> str:
    """The arm a payload came from. A payload with no ``"arm"`` is deterministic:
    until 2026-10-10 only ``cmd_graded`` wrote the key."""
    return (payload or {}).get("arm") or "deterministic"


def negative_result_threshold(payload: dict[str, Any] | None) -> int:
    """The preregistered negative-result threshold for this payload's arm."""
    arm = payload_arm(payload)
    if arm not in NEGATIVE_RESULT_THRESHOLDS:
        raise ValueError(f"no preregistered negative-result threshold for arm {arm!r}")
    return NEGATIVE_RESULT_THRESHOLDS[arm]


def graded_verdict(
    flagged: int, denom: int, threshold: int = GRADED_NEGATIVE_RESULT_THRESHOLD
) -> str:
    """Section 8A's verdict as one sentence, generated either way it falls."""
    head = (
        f"{flagged} of {denom} flagged at the Wilson lower bound; the arm's "
        f"preregistered negative result (fewer than {_spelled(threshold)})"
    )
    if flagged < threshold:
        return (
            f"{head} holds: model-graded scoring in this collection has no "
            "content-free floor above chance."
        )
    return f"{head} does not hold."


#: A graded task whose verdict map records no polarity. Never read as credit.
POLARITY_NOT_RECORDED = "polarity not recorded"


def graded_polarities(
    floors: Sequence[TaskFloor], maps: dict[str, Any] | None = None
) -> dict[str, str | None]:
    """Each graded task's polarity, from the committed ``verdict_maps.jsonl``.

    Attached here, at render time, rather than carried on ``TaskFloor``: it is a
    reading of the eval's source, not something the sweep measured.
    """
    from .graded import load_verdict_maps, polarity_for

    maps = load_verdict_maps() if maps is None else maps
    return {f.task: polarity_for(f.task, maps) for f in floors}


def polarity_sentence(
    floors: Sequence[TaskFloor], polarity: dict[str, str | None]
) -> str | None:
    """Said only when it is true: every flag is on an inverted task."""
    scored = {f.task for f in _scored(floors)}
    flagged = sorted({f.task for f in floors if f.error is None and f.flagged} & scored)
    if not flagged or any(polarity.get(t) != "inverted" for t in flagged):
        return None
    if len(flagged) == 1:
        return "The one flag is on a task whose high score is the bad outcome."
    return f"All {len(flagged)} flags are on tasks whose high score is the bad outcome."


def _raw_ran(floor: TaskFloor) -> bool:
    """Was the raw arm scored on this floor at all?

    The graded arm skips it where a task declares no answer template
    (``graded.arms_for_template``), and its payload then carries
    ``majority_raw: 0.0`` and ``members_raw: {}`` -- field defaults, not
    measurements. ``report`` rebuilds floors from the payload and never
    re-aggregates, so this is decided here, at render time. Printing those
    defaults as a raw "0 of 7", "0.0%" and "disagree on 3" was half of
    instrument defect 009.
    """
    return bool(floor.members_raw)


def _scored(floors: Sequence[TaskFloor]) -> list[TaskFloor]:
    return [f for f in floors if f.error is None and f.members and not f.nothing_scored]


def _raw_not_run_reason(floors: Sequence[TaskFloor]) -> str:
    if floors and all(f.answer_template == "bare" for f in floors):
        return (
            "none of those tasks declares an answer template, so both arms would "
            "score the same strings and only the rendered arm was scored"
        )
    return "the sweep payload carries no raw-arm score for those tasks"


def raw_arm_clause(floors: Sequence[TaskFloor], bold: bool = True) -> str:
    """The raw arm's count as one sentence, or "not run" where it never ran."""
    b = "**" if bold else ""
    gloss = "members written plainly, ignoring each task's answer template"
    scored = _scored(floors)
    ran = [f for f in scored if _raw_ran(f)]
    ran_tasks = {f.task for f in ran}
    unrun = [f for f in scored if f.task not in ran_tasks]
    n_unrun = len({f.task for f in unrun})
    flagged_raw, denom_raw = flag_rate(ran, arm="raw")
    if not unrun:
        return f"On the raw arm -- {gloss} -- it is {b}{flagged_raw} of {denom_raw}{b}."
    reason = _raw_not_run_reason(unrun)
    if not ran:
        return (
            f"The raw arm -- {gloss} -- was {b}{NOT_RUN}{b} on any of the {n_unrun} "
            f"tasks: {reason}."
        )
    return (
        f"On the raw arm -- {gloss} -- it is {b}{flagged_raw} of {denom_raw}{b}; it "
        f"was {b}{NOT_RUN}{b} on the other {n_unrun}: {reason}."
    )


def _point_outside(score: Any) -> bool:
    """Does this member's point estimate fall outside its own interval?

    The point is the mean of the per-item scores, which a grader that scores on
    a scale returns as fractions. The interval is a Wilson interval on the count
    of items that scored the full 1.0. On fractional scores the two measure
    different things, and the point can sit outside the interval.
    """
    if score is None or score.ci_low is None or score.ci_high is None:
        return False
    if score.n_scored == 0:
        return False
    # A float tolerance, so 100 of 100 against an upper bound of 0.9999... is
    # not marked.
    return score.mean < score.ci_low - 1e-9 or score.mean > score.ci_high + 1e-9


def provenance_block(
    payload: dict[str, Any] | None,
    digest: str | None = None,
    extra: dict[str, Any] | None = None,
) -> list[str]:
    """The pins and fingerprint this arm ran under, as its payload recorded them.

    These used to be read from ``installed_pins()`` and ``battery_fingerprint()``
    -- the environment ``report`` runs in, not the one the sweep ran in. Any bump
    would then have stamped a regenerated file with a fingerprint its numbers
    were never measured under. Instrument defect 009.
    """
    payload = payload or {}
    pins = payload.get("pins") or {}
    fingerprint = payload.get("battery_fingerprint")
    lines = [
        "| provenance | value |",
        "|---|---|",
        f"| `inspect_ai` | {pins.get('inspect_ai') or NOT_RECORDED} |",
        f"| `inspect_evals` | {pins.get('inspect_evals') or NOT_RECORDED} |",
        "| battery fingerprint | "
        + (f"`{fingerprint}`" if fingerprint else NOT_RECORDED)
        + " |",
    ]
    # Stamped from 2026-10-10 on. A payload from before carries neither and
    # renders exactly as it did; neither is ever back-filled.
    if payload.get("run_fingerprint"):
        lines.append(f"| run fingerprint | `{payload['run_fingerprint']}` |")
    if payload.get("shuffle_seed") is not None:
        lines.append(f"| shuffle seed | {payload['shuffle_seed']} |")
    if digest:
        lines.append(f"| sweep digest | `{digest[:16]}` |")
    for k, v in (extra or {}).items():
        lines.append(f"| {k} | {v} |")
    return lines


def _measured_on(payload: dict[str, Any] | None) -> str:
    """One arm's pins and fingerprint as prose, from its payload."""
    payload = payload or {}
    pins = payload.get("pins") or {}
    fingerprint = payload.get("battery_fingerprint")
    return (
        f"`inspect_ai` {pins.get('inspect_ai') or NOT_RECORDED} and `inspect_evals` "
        f"{pins.get('inspect_evals') or NOT_RECORDED}, battery fingerprint "
        + (f"`{fingerprint}`" if fingerprint else NOT_RECORDED)
    )


def _prereg_block(payload: dict[str, Any]) -> list[str]:
    """The preregistration commit this sweep ran under, if any."""
    commit = payload.get("preregistration_commit")
    path = payload.get("preregistration_path", "PREREGISTRATION.md")
    if not commit and payload.get("smoke"):
        return [
            "> **No preregistration commit recorded.** This came from a smoke run, "
            "which is exempt from the ordering gate and is not a result.",
        ]
    if not commit:
        return [
            "> **No preregistration is committed yet, so no sweep can produce a "
            "result.** `evalfloor sweep` refuses to write anywhere but "
            "`results/smoke/` until `PREREGISTRATION.md` is in git history, and it "
            "then stamps that commit hash here.",
        ]
    lines = [
        f"Preregistration `{path}` was committed at `{commit[:12]}` **before** this "
        f"sweep ran. Anyone can check that independently: "
        f"`git log --format='%H %ad' -- {path}`.",
    ]
    addendum = payload.get("addendum_commit")
    if addendum:
        lines += [
            "",
            f"Its close-out addendum, section 11, was committed at `{addendum[:12]}` "
            "and was on `origin/master` **before** this sweep ran; the sweep refuses "
            "to run otherwise. The first hash this prints is that commit: "
            f"`git log -S'{ADDENDUM_HEADING}' --reverse --format='%H %ad' -- {path}`.",
        ]
    return lines


# --------------------------------------------------------------------------
# The matrix
# --------------------------------------------------------------------------


def render_matrix(
    floors_before: Sequence[TaskFloor],
    floors_after: Sequence[TaskFloor] | None = None,
    digest: str | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    floors_after = floors_after if floors_after is not None else floors_before
    payload = payload or {}
    flagged_before, denom = flag_rate(floors_before)
    flagged_after, _ = flag_rate(floors_after)
    threshold = negative_result_threshold(payload)

    lines: list[str] = ["# Floor matrix", "", GENERATED_BANNER, ""]

    lines.append("## Headline")
    lines.append("")
    if denom == 0:
        lines.append("No task produced a scored floor. There is no headline number.")
    else:
        lines.append(
            f"**{flagged_after} of {denom}** tasks in this sweep have at least one "
            "content-free completion that scores at or above their own majority-class "
            "baseline."
        )
        lines.append("")
        lines.append(
            f"Before rulings the count was **{flagged_before} of {denom}**. "
            f"{raw_arm_clause(floors_after)} The headline uses the rendered arm, "
            "as preregistered. `coverage.md` says what is not in this denominator."
        )
        n_collisions = collision_count(floors_after)
        if n_collisions:
            lines.append("")
            lines.append(
                f"Of those {flagged_after}, **{n_collisions} rest on the template "
                "collision**: the only flagging member is `format_only` and the string "
                "it was scored on is the string `majority` was scored on, so the flag "
                "is a tie between a member and itself. Preregistration section 8.5 "
                "keeps the tie rule and requires the flag to be marked rather than "
                "silently counted; the marked rows carry **yes** in the `collision` "
                "column below."
            )
        if payload_arm(payload) == "graded":
            # Section 8A's rule, not section 1's, and stated whichever way it falls.
            pointed = polarity_sentence(floors_after, graded_polarities(floors_after))
            lines.append("")
            lines.append(
                "> **Preregistration section 8A.** "
                + graded_verdict(flagged_after, denom, threshold)
                + (f" {pointed}" if pointed else "")
            )
        elif flagged_after < threshold:
            lines.append("")
            lines.append(
                f"> **Preregistered negative result.** Fewer than "
                f"{threshold} flagged tasks was fixed in advance as "
                f"the threshold at which the finding is that the collection is "
                f"tighter than the single known case suggested. At {flagged_after} "
                f"of {denom}, that is the finding."
            )
    lines.append("")
    lines.extend(_prereg_block(payload))
    lines.append("")
    lines.extend(provenance_block(payload, digest))
    lines.append("")

    lines.append("## What a flag means")
    lines.append("")
    lines.append(
        "A flagged task is not a worthless benchmark. A loose scorer inflates a number "
        "without saying the underlying task is easy, and nothing here claims anything "
        "about the conclusions of any paper that used one of these evals."
    )
    lines.append("")

    lines.append("## Per task, rendered arm")
    lines.append("")
    header = [
        "task",
        "scorer",
        "template",
        "n",
        "majority",
        "uniform",
        "best content-free",
        "score",
        "gap",
        "flagged",
        "collision",
    ]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    collided: list[TaskFloor] = []
    for f in floors_after:
        if f.error:
            lines.append(
                f"| `{f.task}` | - | - | - | - | - | - | - | - | error: "
                f"{_esc(f.error)[:60]} | - |"
            )
            continue
        if f.nothing_scored:
            # Not one item scored, so there is no floor here to print as 0.0%.
            lines.append(
                f"| `{f.task}` | `{_esc(f.scorer)}` | {f.answer_template} | "
                f"{f.n_samples} | {NO_RESULT} | {NO_RESULT} | - | {NO_RESULT} | - | "
                "not measured | - |"
            )
            continue
        uniform = _pct(f.uniform) if f.uniform is not None else "n/a"
        flagged = ", ".join(f.flagged_by) if f.flagged else "no"
        if f.ruling:
            flagged += f" ({f.ruling})"
        if f.collision:
            collided.append(f)
        lines.append(
            f"| `{f.task}` | `{_esc(f.scorer)}` | {f.answer_template} | {f.n_samples} | "
            f"{_pct(f.majority)} | {uniform} | {f.best_member or '-'} | "
            f"{_pct(f.best_mean)} | {f.gap_to_majority:+.3f} | {flagged} | "
            f"{'**yes**' if f.collision else 'no'} |"
        )
    lines.append("")
    lines.append(
        "`collision` marks a flag that rests **only** on `format_only` and `majority` "
        "being the same completion. `format_only` is defined as the task's answer "
        "template carrying the placeholder `A`; `majority` is the modal target written "
        "in that same template. Where the modal target *is* `A` they are one string, "
        "they score identically, and the `>=` in the flag rule fires on a tie between "
        "a member and itself. The rule is unchanged (section 8.5: a tie flags, and "
        "weakening a rule after seeing data is worse) -- the flag is marked instead."
    )
    if collided:
        lines.append("")
        for f in collided:
            lines.append(f"* `{f.task}`: {_esc(f.collision_note)}")
    lines.append("")

    lines.append("## What the rendering rule changed")
    lines.append("")
    if any(_raw_ran(f) for f in floors_after if not f.error):
        lines.append(
            "Every member is defined semantically and then written down in the task's "
            "own answer template when it declares one. Both forms are scored. On a task "
            "that declares no template the two arms are identical by construction, and "
            "the rows below show that rather than asserting it."
        )
    else:
        lines.append(
            "Every member is defined semantically and then written down in the task's "
            "own answer template when it declares one. On a task that declares no "
            "template the two arms are identical by construction. This sweep scored "
            f"only the rendered form, so every raw cell below reads `{NOT_RUN}`."
        )
    lines.append("")
    lines.append(
        "| task | template | majority raw | majority rendered | best CF raw | "
        "best CF rendered | flagged raw | flagged rendered |"
    )
    lines.append("|" + "---|" * 8)
    templated_tasks = 0
    disagreements = 0
    compared = 0
    for f in floors_after:
        if f.error:
            continue
        if f.answer_template != "bare":
            templated_tasks += 1
        if not _raw_ran(f):
            majority_raw = best_raw = flagged_raw = _pct(None)
        elif f.nothing_scored:
            compared += 1
            majority_raw = best_raw = NO_RESULT
            flagged_raw = "not measured"
        else:
            compared += 1
            if f.flagged_raw != f.flagged:
                disagreements += 1
            majority_raw = _pct(f.majority_raw)
            best_raw = f"{f.best_member_raw or '-'} {_pct(f.best_mean_raw)}"
            flagged_raw = "yes" if f.flagged_raw else "no"
        if f.nothing_scored:
            majority, best, flagged = NO_RESULT, NO_RESULT, "not measured"
        else:
            majority = _pct(f.majority)
            best = f"{f.best_member or '-'} {_pct(f.best_mean)}"
            flagged = "yes" if f.flagged else "no"
        lines.append(
            f"| `{f.task}` | {f.answer_template} | {majority_raw} | "
            f"{majority} | {best_raw} | {best} | {flagged_raw} | {flagged} |"
        )
    lines.append("")
    scored_tasks = len([f for f in floors_after if not f.error])
    if compared == scored_tasks:
        compare_line = f"The two arms disagree on {disagreements}."
    elif compared == 0:
        compare_line = (
            f"The raw arm was {NOT_RUN} on any of them, so there is no second arm "
            "to compare."
        )
    else:
        compare_line = (
            f"The two arms disagree on {disagreements} of the {compared} where both "
            f"ran; the raw arm was {NOT_RUN} on the other {scored_tasks - compared}."
        )
    lines.append(
        f"{templated_tasks} of {scored_tasks} tasks here declare an answer template. "
        + compare_line
    )
    finding = rendering_finding(floors_after)
    if finding:
        lines.append("")
        lines.append(finding)
        if re.search(r"\bdefect \d{3}\b", finding):
            # Only where the paragraph above actually named one.
            lines.append("")
            lines.append("Both defects are written up in `INSTRUMENT_LESSONS.md`.")
    lines.append("")

    members = list(CONTENT_FREE_NAMES) + list(REFERENCE_NAMES)
    for arm in ARMS:
        lines.append(f"## Every battery member, every task -- {arm} arm")
        lines.append("")
        lines.append("| task | scorer | " + " | ".join(members) + " |")
        lines.append("|" + "---|" * (len(members) + 2))
        for f in floors_after:
            if f.error:
                continue
            if arm == "raw" and not _raw_ran(f):
                lines.append(
                    f"| `{f.task}` | `{_esc(f.scorer)}` | "
                    + " | ".join([NOT_RUN] * len(members))
                    + " |"
                )
                continue
            source = f.members_raw if arm == "raw" else f.members
            cells: list[str] = []
            for name in members:
                score = source.get(name)
                if score is None:
                    cells.append("-")
                elif not score.applicable:
                    cells.append("n/a")
                elif score.n_scored == 0:
                    # Every call refused, errored or was ungradeable: no rate.
                    cells.append(NO_RESULT)
                else:
                    cells.append(_pct(score.mean))
            lines.append(
                f"| `{f.task}` | `{_esc(f.scorer)}` | " + " | ".join(cells) + " |"
            )
        lines.append("")

    lines.append("## Counts, not rates (rendered arm)")
    lines.append("")
    lines.append("| task | scorer | member | correct | scored | completion scored |")
    lines.append("|---|---|---|---|---|---|")
    for f in floors_after:
        if f.error:
            continue
        for name in members:
            score = f.members.get(name)
            if score is None or not score.applicable:
                continue
            lines.append(
                f"| `{f.task}` | `{_esc(f.scorer)}` | {name} | "
                f"{score.n_correct} | {score.n_scored} | "
                f"`{_esc(score.example_completion[:60])}` |"
            )
    lines.append("")

    if payload.get("arm") == "graded" or any(f.graded for f in floors_after):
        lines.append(render_graded_section(floors_after, payload))
        lines.append("")

    lines.append("## The battery")
    lines.append("")
    lines.append(render_battery_table())
    lines.append("")
    return "\n".join(lines)


def echo_headline(floors: Sequence[TaskFloor], generic: bool = False) -> str | None:
    """The ``echo`` finding as one sentence, computed from the sweep.

    Echoing the question back carries no information about the answer, so any
    score it gets is the scorer crediting the input for containing the target.
    Every number in the sentence comes from the payload; none is typed.

    The first sweep's wording -- the samples "already contain a label" -- is
    true of ``paws``'s ``includes()`` and of no scorer in general, so the
    close-out README asks for ``generic``: what scored, against which baseline.
    """
    scored = [
        f for f in floors if f.error is None and f.members and not f.nothing_scored
    ]
    with_echo = [
        f for f in scored if f.members.get("echo") and f.members["echo"].applicable
    ]
    if not with_echo:
        return None

    above_zero = [f for f in with_echo if f.members["echo"].mean > 0.0]
    worst = max(with_echo, key=lambda f: f.members["echo"].n_correct)
    worst_echo = worst.members["echo"]

    sentence = (
        f"Echoing the question back scores above zero on **{len(above_zero)} of "
        f"{len(with_echo)}** tasks swept."
    )
    if worst_echo.n_correct > 0 and generic:
        short = worst.task.split("/")[-1]
        sentence += (
            f" The most is on `{short}`: **{worst_echo.n_correct:,} of "
            f"{worst_echo.n_scored:,}** samples score as correct when their own input "
            f"is handed back as the answer, against a {_pct(worst.majority)} `majority` "
            "baseline. Whatever the scorer credits there was in the question."
        )
    elif worst_echo.n_correct > 0:
        short = worst.task.split("/")[-1]
        sentence += (
            f" On `{short}`, **{worst_echo.n_correct:,} of {worst_echo.n_scored:,}** "
            "samples already contain a label somewhere in their own text, so the "
            "input scores against itself."
        )
    return sentence


def rendering_finding(floors: Sequence[TaskFloor]) -> str | None:
    """The instrument finding behind the rendering rule, stated plainly.

    Generated rather than written, so it cannot drift from the table above it.
    It reads only floors the raw arm was scored on: comparing the rendered arm
    with a raw arm that never ran would be reading field defaults as a result.
    """
    all_scored = _scored(floors)
    if not all_scored:
        return None
    scored = [f for f in all_scored if _raw_ran(f)]
    unrun = [f for f in all_scored if not _raw_ran(f)]
    if not scored:
        return (
            f"**What this table is showing.** Nothing. The raw arm was {NOT_RUN} on "
            f"any of the {len(unrun)} task(s) here: {_raw_not_run_reason(unrun)}. "
            "There is no second arm to compare the rendered one with."
        )
    templated = [f for f in scored if f.answer_template != "bare"]

    collapsed = [f for f in templated if f.majority_raw == 0.0 and f.majority > 0.0]
    raw_only = [f for f in scored if f.flagged_raw and not f.flagged]
    all_labels_zero = [
        f
        for f in templated
        if f.members.get("all_labels") is not None
        and f.members["all_labels"].applicable
        and f.members["all_labels"].mean == 0.0
    ]

    parts: list[str] = ["**What this table is showing.**"]
    if collapsed:
        parts.append(
            f"On {len(collapsed)} of the {len(templated)} task(s) here that declare an "
            "answer template, the raw arm's `majority` baseline is **0.0%** while the "
            "rendered arm's is not. That is instrument defect 003 preserved as a "
            "number: a bare label such as `C` is not an answer a multiple-choice "
            "scorer can read, so the chance line collapses to zero and then anything "
            "that scores at all clears it."
        )
    if raw_only:
        parts.append(
            f"That is why {len(raw_only)} task(s) are flagged on the raw arm and not "
            "on the rendered one. The raw arm is not the stricter reading of the two; "
            "it is the broken one, kept visible on purpose."
        )
    if all_labels_zero:
        parts.append(
            "In the other direction, rendered `all_labels` scores **0.000** on "
            f"{len(all_labels_zero)} of {len(templated)} templated task(s): written "
            "properly as `ANSWER: A, B, C, D`, the multiple-choice parser rejects a "
            "multi-option answer to a single-answer question. So `choice()` is "
            "genuinely tight against naming every label, and because most reachable "
            "tasks are scored by `choice()`, that is a large part of why the headline "
            "number is small rather than large."
        )
    if len(parts) == 1:
        parts.append(
            "No task here declares an answer template, so the raw and rendered arms "
            "are identical by construction and the rendering rule changed nothing."
        )
    if unrun:
        parts.append(
            f"The raw arm was {NOT_RUN} on {len(unrun)} further task(s), which this "
            "paragraph leaves out."
        )
    return " ".join(parts)


def _first_error(floor: TaskFloor) -> str:
    return floor.first_error or floor.error or "not recorded"


def _ci(score: Any, mark: bool = False) -> str:
    if score is None or score.ci_low is None or score.ci_high is None:
        return "-"
    cell = f"[{100 * score.ci_low:.1f}, {100 * score.ci_high:.1f}]"
    if mark and _point_outside(score):
        cell += f" {POINT_OUTSIDE_MARK}"
    return cell


def render_graded_section(
    floors: Sequence[TaskFloor],
    payload: dict[str, Any],
    polarity: dict[str, str | None] | None = None,
) -> str:
    """The model-graded arm: intervals, the grader, refusals, disagreement.

    Deliberately kept separate from the deterministic tables. The two arms are
    never added together into one rate: one is exact over whole datasets and
    free, the other is a capped sample graded by a model that can be wrong and
    costs money per call.

    ``polarity`` maps task to polarity; by default it is read from the committed
    ``verdict_maps.jsonl``.
    """
    grader = payload.get("grader") or {}
    graded_floors = [f for f in floors if f.graded and not f.error]

    lines: list[str] = ["## The model-graded arm", ""]
    lines.append(
        "Rates here are over a **capped sample**, graded by a model, not over a whole "
        "dataset by a pure function. They are reported as Wilson 95% intervals, and "
        "the flag rule on this arm uses the interval's **lower bound** rather than the "
        "point estimate: a task is flagged only when its floor clears chance even at "
        "the pessimistic end. These numbers are never added to the deterministic "
        "arm's to make a combined rate."
    )
    lines.append("")
    member_rows = [
        f.members[name]
        for f in graded_floors
        for name in list(CONTENT_FREE_NAMES) + list(REFERENCE_NAMES)
        if name in f.members and f.members[name].applicable
    ]
    n_outside = sum(1 for score in member_rows if _point_outside(score))
    lines.append(
        "**The point and the interval are defined differently, and both are used "
        "below.** The **point** -- the `score` and `best content-free` columns -- is "
        "the mean of the per-item scores, and a grader that scores on a scale "
        "returns fractions between 0 and 1. The **interval** -- the `95% CI` column "
        "-- is a Wilson interval on `correct` of `scored`, where `correct` counts "
        "only the items that scored the full 1.0. Where every item scores 0 or 1 "
        "the two agree. Where items score fractions they measure different things, "
        "so a point can sit outside its own interval; such a row carries "
        f"{POINT_OUTSIDE_MARK} in its `95% CI` cell, and here that is "
        f"{n_outside} of the {len(member_rows)} member rows. The flag rule is "
        "unchanged and reads the interval's lower bound."
    )
    lines.append("")

    lines.append("| grader | value |")
    lines.append("|---|---|")
    lines.append(f"| model | `{_esc(grader.get('model', 'unknown'))}` |")
    lines.append(f"| family | {_esc(grader.get('family', 'unknown'))} |")
    lines.append(f"| cap | {payload.get('cap', '?')} samples per task per member |")
    lines.append(f"| price source | {_esc(grader.get('price_source', 'unknown'))} |")
    keys = payload.get("keys_present") or {}
    if keys:
        lines.append(
            "| API keys present | "
            + _esc(", ".join(f"{k}={'yes' if v else 'no'}" for k, v in keys.items()))
            + " |"
        )
    cost = payload.get("cost_estimate") or {}
    if cost:
        usd = cost.get("usd")
        lines.append(
            "| estimated cost of this run | "
            + (f"${usd:,.4f}" if isinstance(usd, (int, float)) else "unpriced grader")
            + " |"
        )
        lines.append(f"| grading calls made | {cost.get('n_calls', 0):,} |")
    lines.append(
        f"| cache hits / misses | {payload.get('cache_hits', 0)} / "
        f"{payload.get('cache_misses', 0)} |"
    )
    routing = [
        (f.grader_model, f.routing_note) for f in graded_floors if f.routing_note
    ]
    for model_id, note in dict(routing).items():
        lines.append(f'| routing, {_esc(model_id)} | {_esc(note)} |')
    dis_routing = (payload.get('disagreement') or {}).get('routing_note')
    if dis_routing:
        lines.append(f'| routing, second grader | {_esc(dis_routing)} |')
    lines.append("")

    if grader.get("is_mock"):
        lines.append(
            "> **This run used `mockllm/model`, which is not a grader.** No provider "
            "was called and no API key was present. The numbers below exercise the "
            "plumbing and say **nothing whatever** about any eval. They are published "
            "only so the harness can be checked before money is spent running it."
        )
        lines.append("")

    # Which way each task's score points, read from verdict_maps.jsonl. A flag
    # on an inverted task is a content-free answer scoring as the bad outcome,
    # never credit.
    polarity = graded_polarities(graded_floors) if polarity is None else polarity

    lines.append("### Per task")
    lines.append("")
    lines.append(
        "| task | scorer | n | grader | majority | best content-free | 95% CI | "
        "refusals | flagged | polarity |"
    )
    lines.append("|" + "---|" * 10)
    dead: list[TaskFloor] = []
    for f in graded_floors:
        points = polarity.get(f.task) or POLARITY_NOT_RECORDED
        if f.nothing_scored:
            dead.append(f)
            lines.append(
                f"| `{f.task}` | `{_esc(f.scorer)}` | {f.n_samples} | "
                f"`{_esc(f.grader_model)}` | NO RESULT | NO RESULT | - | "
                f"{f.n_refusals} | not measured | {points} |"  # noqa: E501
            )
            continue
        best = f.members.get(f.best_member) if f.best_member else None
        lines.append(
            f"| `{f.task}` | `{_esc(f.scorer)}` | {f.n_samples} | "
            f"`{_esc(f.grader_model)}` | {_pct(f.majority)} | "
            f"{f.best_member or '-'} {_pct(f.best_mean)} | {_ci(best, mark=True)} | "
            f"{f.n_refusals} | {', '.join(f.flagged_by) if f.flagged else 'no'} | "
            f"{points} |"
        )
    if not graded_floors:
        lines.append("| _(no graded task produced a floor)_ | | | | | | | | | |")
    lines.append("")

    if dead:
        lines.append(
            f"> **{len(dead)} task(s) produced NO RESULT**: not one grading call "
            "succeeded, so there is no floor to report. This is written as "
            "`NO RESULT`, never as 0.0%. A task where nothing scored has not been "
            "measured, and printing a zero there would be the same class of mistake "
            "this project exists to find."
        )
        lines.append("")
        lines.append(
            "| task | errors | ungradeable | first error | grader injected via |"
        )
        lines.append("|---|---|---|---|---|")
        for f in dead:
            via = f.grader_injected_via or "NOT REDIRECTABLE (task hard-codes its grader)"
            lines.append(
                f"| `{f.task}` | {f.n_errors} | {f.n_ungradeable} | "
                f"{_esc(_first_error(f))[:100]} | {_esc(via)} |"
            )
        lines.append("")

    total_unmapped = sum(f.n_unmapped for f in graded_floors)
    if total_unmapped:
        seen: dict[str, int] = {}
        for f in graded_floors:
            for verdict, n in (f.unmapped_verdicts or {}).items():
                seen[verdict] = seen.get(verdict, 0) + n
        lines.append(
            f"> **{total_unmapped} verdicts had no committed mapping.** This eval "
            "answers in its own vocabulary, and Inspect's generic `value_to_float()` "
            "returns **0.0** for any string it does not know -- which would silently "
            "discard every credit the judge gave. Unmapped verdicts are recorded "
            "verbatim and excluded from the denominator instead, and the mapping is "
            "added to `verdict_maps.jsonl` quoting the eval source line it came from. "
            "Instrument defect 007."
        )
        lines.append("")
        lines.append("| verdict returned | count |")
        lines.append("|---|---|")
        for verdict, n in sorted(seen.items(), key=lambda kv: -kv[1]):
            lines.append(f"| `{_esc(verdict)}` | {n} |")
        lines.append("")

    total_ungradeable = sum(f.n_ungradeable for f in graded_floors)
    if total_ungradeable:
        lines.append(
            f"> **{total_ungradeable} grading calls came back ungradeable**: the "
            "grader answered, but emitted nothing that parses as a grade. That is "
            "neither a score nor an error nor a refusal, and it is **not** counted "
            "as a zero -- coercing it to zero would report a floor that was never "
            "measured. Ungradeable calls are excluded from the denominator and "
            "counted here."
        )
        lines.append("")

    lines.append("### Every member, with intervals")
    lines.append("")
    lines.append(
        "| task | member | score | 95% CI | correct | scored | refused | unmapped "
        "| completion |"
    )
    lines.append("|" + "---|" * 9)
    for f in graded_floors:
        for name in list(CONTENT_FREE_NAMES) + list(REFERENCE_NAMES):
            score = f.members.get(name)
            if score is None or not score.applicable:
                continue
            cell = "NO RESULT" if score.n_scored == 0 else _pct(score.mean)
            lines.append(
                f"| `{f.task}` | {name} | {cell} | {_ci(score, mark=True)} | "
                f"{score.n_correct} | {score.n_scored} | {score.n_refusals} | "
                f"{score.n_unmapped} | `{_esc(score.example_completion[:40])}` |"
            )
    lines.append("")

    lines.append("### Refusals")
    lines.append("")
    n_refusals = payload.get("n_refusals", 0)
    lines.append(
        f"**{n_refusals}** grading calls were declined by the grader or the provider. "
        "Each is recorded verbatim in `refusals.jsonl` with a SHA-256 of the prompt "
        "that produced it, and counted in the tables above. None was reworded, and "
        "none was retried more than once with the identical request. A refusal is not "
        "scored as a zero: it is taken out of the denominator and reported separately, "
        "because counting a declined grading as a failed answer would quietly credit "
        "the battery member it was grading."
    )
    lines.append("")

    dis = payload.get("disagreement")
    if dis:
        lines.append("### Judge-disagreement control")
        lines.append("")
        if dis.get("skipped"):
            lines.append(f"Skipped: {_esc(dis['skipped'])}.")
        else:
            rate = dis.get("rate", 0.0)
            low = dis.get("ci_low") or 0.0
            high = dis.get("ci_high") or 0.0
            lines.append(
                f"On `{_esc(dis.get('task'))}`, graders `{_esc(dis.get('grader_a'))}` "
                f"and `{_esc(dis.get('grader_b'))}` were run over the same items. They "
                f"disagreed on **{dis.get('n_disagree', 0)} of "
                f"{dis.get('n_compared', 0)}** = **{100 * rate:.1f}%** "
                f"[{100 * low:.1f}%, {100 * high:.1f}%]."
            )
            lines.append("")
            lines.append(
                "That rate is how much of this arm is judge noise rather than signal. "
                "It is compared per item, not per mean: two judges can agree on every "
                "mean while disagreeing on every item."
            )
            n_uncomparable = dis.get("n_uncomparable", 0)
            if n_uncomparable:
                lines.append("")
                lines.append(
                    f"A further **{n_uncomparable}** cells were produced by both "
                    "graders but **cannot be compared**: at least one of the two rows "
                    "carries no finite value. Those are excluded from the denominator "
                    "rather than compared as zeros -- reading a refusal, an "
                    "ungradeable answer or an unmapped verdict as 0.0 would make two "
                    "graders that both declined look like two graders that agreed."
                )
                lines.append("")
                lines.append("| why it could not be compared | cells |")
                lines.append("|---|---|")
                for reason, n in sorted(
                    (dis.get("uncomparable_by_reason") or {}).items(),
                    key=lambda kv: (-kv[1], kv[0]),
                ):
                    lines.append(f"| {_esc(reason)} | {n} |")
        lines.append("")
    return "\n".join(lines)


def render_battery_table() -> str:
    lines = [
        "| member | kind | semantics | templated | completion |",
        "|---|---|---|---|---|",
    ]
    for m in BATTERY:
        lines.append(
            f"| `{m.name}` | {m.kind} | {m.semantic} | "
            f"{'yes' if m.templated else 'no'} | {_esc(m.description)} |"
        )
    lines.append("")
    lines.append("Literal strings, fixed by preregistration:")
    lines.append("")
    lines.append(f"* `refusal` = `{REFUSAL_TEXT}`")
    lines.append(f"* `format_only` = `{FORMAT_ONLY_TEXT}`")
    lines.append(
        f"* `boilerplate` = {len(BOILERPLATE_TEXT)} characters, beginning "
        f"`{BOILERPLATE_TEXT[:48]}...`"
    )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Coverage -- one row for every declared task
# --------------------------------------------------------------------------


def render_coverage(
    inventory: Sequence[dict[str, Any]],
    swept_tasks: Sequence[str],
    floors: Sequence[TaskFloor],
    digest: str | None = None,
    payload: dict[str, Any] | None = None,
    not_counted: Sequence[Ruling] = (),
) -> str:
    """``not_counted`` is the deterministic arm's ``not_counted`` rows. The graded
    arm passes none: its list is section 8A's eight, which no row touches."""
    payload = payload or {}
    listed = {r.task: r for r in not_counted}
    swept = set(swept_tasks)
    errored = {f.task: f.error for f in floors if f.error and f.task not in listed}
    scored = {f.task for f in floors if f.error is None and f.members}
    flagged = {f.task for f in floors if f.error is None and f.flagged}
    reachable = [row for row in inventory if row["reachable"]]

    lines: list[str] = ["# Coverage", "", GENERATED_BANNER, ""]
    lines.append(
        "The denominator comes before the result. **Every task declared in an "
        "`eval.yaml` has exactly one row in the table at the bottom of this file**: "
        "it was swept and produced a floor, it is reachable but not yet swept, it "
        "failed when it was run, or there is a recorded reason it cannot be run."
    )
    lines.append("")
    lines.extend(_prereg_block(payload))
    lines.append("")
    lines.extend(provenance_block(payload, digest))
    lines.append("")

    lines.append("## Totals")
    lines.append("")
    lines.append("| | count |")
    lines.append("|---|---|")
    lines.append(f"| tasks declared in `eval.yaml` files | {len(inventory)} |")
    lines.append(f"| reachable for the deterministic sweep | {len(reachable)} |")
    if listed:
        lines.append(f"| reachable, not counted, with a treatment | {len(listed)} |")
    lines.append(f"| excluded, with a reason | {len(inventory) - len(reachable)} |")
    lines.append(f"| attempted in this run | {len(swept)} |")
    lines.append(f"| produced a scored floor | {len(scored)} |")
    lines.append(f"| attempted but errored | {len(errored)} |")
    lines.append(f"| flagged | {len(flagged)} |")
    lines.append("")

    lines.append("## Exclusion reasons")
    lines.append("")
    lines.append(render_exclusion_table(inventory))
    lines.append("")

    if listed:
        lines.append("## Not counted")
        lines.append("")
        lines.append(render_treatment_table(not_counted))
        lines.append("")

    lines.append("## Run failures")
    lines.append("")
    if errored:
        lines.append("| task | error |")
        lines.append("|---|---|")
        for task, err in sorted(errored.items()):
            lines.append(f"| `{task}` | {_esc(err)[:180]} |")
    else:
        lines.append("None. Every task attempted in this run produced a scored floor.")
    lines.append("")

    excluded_at_projection = (payload.get("run_projection") or {}).get("excluded") or []
    if excluded_at_projection:
        lines.append("## Excluded before the first provider call")
        lines.append("")
        lines.append(
            "These tasks were in the run's task list and could not be loaded when the "
            "arm was projected, so no grading call was made for them. The denominator "
            "shrinks by exactly this many and says so here. **No substitution is "
            "performed**: a reserve is not silently swapped in."
        )
        lines.append("")
        lines.append("| task | reason |")
        lines.append("|---|---|")
        for row in excluded_at_projection:
            lines.append(
                f"| `{_esc(row.get('task', '?'))}` | {_esc(row.get('reason', ''))[:180]} |"
            )
        lines.append("")

    lines.append(f"## Every task ({len(inventory)} rows)")
    lines.append("")
    lines.append("| task | scorer | class | status | reason | detail |")
    lines.append("|---|---|---|---|---|---|")
    covered = 0
    for row in inventory:
        task = row["name"]
        if task in listed:
            status, reason = "not counted", "not_counted"
            detail = listed[task].treatment or ""
        elif task in errored:
            status, reason, detail = "failed", "load_error", errored[task]
        elif task in scored:
            status = "flagged" if task in flagged else "swept, clean"
            reason, detail = "", ""
        elif row["reachable"]:
            status, reason, detail = "reachable, not swept", "", ""
        else:
            status = "excluded"
            reason = row["exclusion_reason"]
            detail = row["exclusion_detail"]
        covered += 1
        lines.append(
            f"| `{task}` | `{_esc(row.get('scorer_expr') or '-')}` | "
            f"`{row.get('scorer_class', '?')}` | {status} | `{reason}` | "
            f"{_esc(detail)[:140]} |"
        )
    lines.append("")
    lines.append(
        f"{covered} rows for {len(inventory)} declared tasks. Every declared task is "
        "accounted for; none is silently dropped."
    )
    lines.append("")
    return "\n".join(lines)


def render_exclusion_table(inventory: Sequence[dict[str, Any]]) -> str:
    from collections import Counter

    reasons = Counter(
        row["exclusion_reason"] for row in inventory if not row["reachable"]
    )
    reachable = sum(1 for row in inventory if row["reachable"])
    lines = ["| reason | tasks | meaning |", "|---|---|---|"]
    for reason, count in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{reason}` | {count} | {EXCLUSION_MEANINGS.get(reason, '')} |")
    lines.append(
        f"| **reachable** | **{reachable}** | the deterministic sweep can run these |"
    )
    lines.append(f"| **declared total** | **{len(inventory)}** | |")
    return "\n".join(lines)


def render_treatment_table(not_counted: Sequence[Ruling]) -> str:
    """The ``not_counted`` rows grouped by treatment, every task named."""
    by_treatment: dict[str, list[str]] = {}
    for r in not_counted:
        by_treatment.setdefault(r.treatment or "", []).append(r.task)
    lines = [
        "Reachable, and deliberately not swept. Each task has a `not_counted` row in "
        "`rulings.jsonl` that quotes the source line its treatment rests on, so the "
        "list is data rather than code.",
        "",
        "| treatment | tasks | which |",
        "|---|---|---|",
    ]
    for treatment, tasks in sorted(by_treatment.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        names = ", ".join(f"`{t.split('/')[-1]}`" for t in sorted(tasks))
        lines.append(f"| {_esc(treatment)} | {len(tasks)} | {names} |")
    lines.append(f"| **not counted** | **{len(not_counted)}** | |")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Rulings log
# --------------------------------------------------------------------------


def render_rulings(
    applied: Sequence[AppliedRuling],
    unmatched: Sequence[Ruling],
    not_counted: Sequence[Ruling] = (),
) -> str:
    """``not_counted`` is listed on the deterministic arm only; see render_coverage."""
    lines: list[str] = ["# Rulings applied", "", GENERATED_BANNER, ""]
    lines.append(
        "Every judgement call in the sweep, applied mechanically from "
        "`rulings.jsonl`. The flag rate is reported both before and after these."
    )
    lines.append("")
    if not applied and not unmatched and not not_counted:
        lines.append("`rulings.jsonl` is empty. No judgement call has been made yet.")
        lines.append("")
        return "\n".join(lines)
    if not_counted:
        lines.append("## Not counted: listed, never swept")
        lines.append("")
        lines.append("| task | treatment | reason | source |")
        lines.append("|---|---|---|---|")
        for r in not_counted:
            lines.append(
                f"| `{r.task}` | {_esc(r.treatment)} | {_esc(r.reason)} | "
                f"`{_esc(r.source)}` |"
            )
        lines.append("")
        if applied or unmatched:
            lines.append("## Rulings applied to this sweep")
            lines.append("")
    if applied:
        lines.append("| task | action | effect | reason | source |")
        lines.append("|---|---|---|---|---|")
        for a in applied:
            lines.append(
                f"| `{a.ruling.task}` | `{a.ruling.action}` | {_esc(a.effect)} | "
                f"{_esc(a.ruling.reason)} | `{_esc(a.ruling.source)}` |"
            )
        lines.append("")
    if unmatched:
        lines.append("## Rulings that matched no task in this sweep")
        lines.append("")
        lines.append("| task | action | reason |")
        lines.append("|---|---|---|")
        for r in unmatched:
            lines.append(f"| `{r.task}` | `{r.action}` | {_esc(r.reason)} |")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# README
# --------------------------------------------------------------------------

#: The literal placeholder shown until a real sweep fills it.
README_PLACEHOLDER = "{flagged} of {reachable} tasks"

#: The README's defect table: (number, heading, what it would have invalidated).
#: The middle column is the entry's heading in ``INSTRUMENT_LESSONS.md``, copied
#: verbatim, and a test fails if the two ever drift apart -- this table went
#: three defects stale once already, which is the failure mode of any summary
#: kept by hand next to the thing it summarises.
INSTRUMENT_DEFECT_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "001",
        "`choice()` tasks were not being driven at all",
        "every multiple-choice row; 16 of the first 20 tasks use `choice()`",
    ),
    (
        "002",
        "the flag rule fired on `0 >= 0`",
        "any task the harness could not drive, turning instrument failures into "
        "findings",
    ),
    (
        "003",
        "reference baselines could not parse on multiple-choice tasks",
        "the chance line the whole flag rule rests on, on every multiple-choice "
        "task",
    ),
    (
        "004",
        "a shuffled dataset made every limited sweep non-reproducible",
        "nothing published, because the manual check happened to compare two "
        "unlimited sweeps; it would have hit the first sampled arm",
    ),
    (
        "005",
        "rendering generalised, replacing the special case in 003",
        "no number, but it left two members written in the task's answer "
        "template and six written outside it for no reason a reader could check",
    ),
    (
        "006",
        "an ungradeable grader response was about to be reported as a zero",
        "nothing published -- it was caught on a mock -- but it is the exact "
        "shape this project exists to find: a number that looks like a measured "
        "floor and is not one",
    ),
    (
        "007",
        "an eval's own grade vocabulary was being converted to zero",
        "every graded number on the first real run, in the direction that "
        "understates the floor",
    ),
    (
        "008",
        "the provider pin was requested on a channel that was overwritten",
        "the judge-disagreement figure and the pinned cost line published in "
        "255eb3a, both measured under routing that was never recorded",
    ),
    (
        "009",
        "the report applied the deterministic arm's rules to the graded arm",
        "the graded verdict sentence, and three published numbers for an arm that "
        'did not run (the raw "0 of 7", the raw "0.0%" cells, "disagree on 3"); no '
        "measured number",
    ),
    (
        "010",
        "an unseeded choice shuffle made the first sweep non-reproducible",
        "the reproducibility of the published count, and with it the section 1 "
        "verdict on 0.20.0: 4 is under five, 5 is not",
    ),
    (
        "011",
        "the flag rule assumed every task's score points the same way",
        "no count; the reading of three graded flags, all on tasks whose high score "
        "is the bad outcome, and the implied denominator of 58 readable tasks",
    ),
)


# --------------------------------------------------------------------------
# Which payload the README reads
#
# render_readme computes the headline from whatever floors it is handed, and
# `_regenerate` used to hand it the floors of whichever arm had just run. So a
# `sweep --first-sweep --graded` wrote the deterministic headline into README.md
# and then, seconds later, overwrote it with the graded arm's -- a headline whose
# denominator is 8 capped samples instead of 58 whole datasets, under a sentence
# that says "of the whole collection". Nothing failed; the file just ended up
# quoting the wrong arm, and which arm it quoted depended on command order.
#
# The README is therefore assembled from BOTH payloads on disk, whichever
# command triggered the regeneration: the deterministic sweep supplies the
# headline, the graded sweep supplies the graded section, and order stops
# mattering.
# --------------------------------------------------------------------------

DETERMINISTIC_SWEEP = "sweep.json"
GRADED_SWEEP = "graded/sweep.json"


def results_root(out_dir: pathlib.Path) -> pathlib.Path:
    """The results root for an output directory that may be an arm inside it."""
    return out_dir.parent if out_dir.name == "graded" else out_dir


def readme_arms(
    payload: dict[str, Any],
    floors_after: Sequence[TaskFloor],
    out_dir: pathlib.Path,
    rules: Sequence[Any],
) -> dict[str, Any]:
    """Both arms for the README: the one just run, plus the other one from disk.

    Returns ``{"floors", "payload", "graded_floors", "graded_payload"}`` where
    ``floors``/``payload`` are always the **deterministic** arm's.
    """
    def _load(path: pathlib.Path) -> tuple[list[TaskFloor], dict[str, Any] | None]:
        if not path.exists():
            return [], None
        loaded = read_sweep(path)
        if loaded.get("smoke"):
            # A smoke payload is a harness check, not a result, and must never
            # reach the README by the side door of the other arm's regenerate.
            return [], None
        _, after, _, _, _ = prepare_floors(loaded, rules)
        return after, loaded

    root = results_root(out_dir)
    if payload.get("arm") == "graded":
        det_floors, det_payload = _load(root / DETERMINISTIC_SWEEP)
        return {
            "floors": det_floors,
            "payload": det_payload or {},
            "graded_floors": list(floors_after),
            "graded_payload": payload,
        }
    graded_floors, graded_payload = _load(root / GRADED_SWEEP)
    return {
        "floors": list(floors_after),
        "payload": payload,
        "graded_floors": graded_floors,
        "graded_payload": graded_payload,
    }


def render_readme_graded(
    floors: Sequence[TaskFloor], payload: dict[str, Any]
) -> list[str]:
    """The README's paragraph about the graded arm, from the graded payload only.

    Never added to the deterministic rate. One arm is exact over whole datasets
    and free; the other is a capped sample graded by a model that can be wrong.
    """
    flagged, denom = flag_rate(floors)
    grader = payload.get("grader") or {}
    lines = ["## The model-graded arm", ""]
    lines.append(
        f"**{flagged} of {denom}** model-graded tasks have a content-free floor that "
        "clears their own majority baseline **at the Wilson 95% lower bound** -- a "
        "stricter rule than the deterministic arm's, because these rates are over a "
        f"capped sample of {payload.get('cap', '?')} items per task per member rather "
        "than a whole dataset. This number is **never added** to the one above: the "
        "two arms have different denominators, different rules and different costs. "
        "Full tables in [`results/graded/floor_matrix.md`]"
        "(results/graded/floor_matrix.md)."
    )
    if denom and payload_arm(payload) == "graded":
        lines.append("")
        pointed = polarity_sentence(floors, graded_polarities(floors))
        lines.append(
            graded_verdict(flagged, denom, negative_result_threshold(payload))
            + (f" {pointed}" if pointed else "")
        )
    lines.append("")
    lines.append(
        f"Judged by `{_esc(grader.get('model', 'unknown'))}`. "
        + (
            "**This run used a mock grader and says nothing about any eval.** "
            if grader.get("is_mock")
            else ""
        )
    )
    dis = payload.get("disagreement") or {}
    if dis and not dis.get("skipped"):
        lines.append("")
        lines.append(
            f"Judge-disagreement control on `{_esc(dis.get('task'))}`, against "
            f"`{_esc(dis.get('grader_b'))}`: **{dis.get('n_disagree', 0)} of "
            f"{dis.get('n_compared', 0)}** comparable cells flip on a change of judge "
            f"= {100 * dis.get('rate', 0.0):.1f}% "
            f"[{100 * (dis.get('ci_low') or 0.0):.1f}%, "
            f"{100 * (dis.get('ci_high') or 0.0):.1f}%]. That bounds the judge noise "
            "in every graded figure above; it does not remove it."
        )
    elif dis.get("skipped"):
        lines.append("")
        lines.append(f"Judge-disagreement control **skipped**: {_esc(dis['skipped'])}")
    lines.append("")
    return lines


# --------------------------------------------------------------------------
# Figures in the README
#
# The figures are drawn elsewhere (`figures.py`); the README only places them.
# Each arrives as a FigureRef carrying a digest of the data it was drawn from,
# and the README prints that digest beside the figure and the data itself as a
# table under it, so a figure can always be checked against the numbers.
# --------------------------------------------------------------------------

#: The close-out README's figures, each with a fixed place: F1 after the first
#: paragraph, G1 in "What this is", F2 in the fix paragraph, F3 by the
#: denominator, and G2 with its transcript in "Reproducing it".
README_FIGURES: tuple[str, ...] = ("F1", "G1", "F2", "F3", "G2")


@dataclass(frozen=True)
class FigureRef:
    """One figure as the README embeds it."""

    id: str
    alt: str
    caption: str
    #: sha256 of the data the figure was drawn from.
    data_digest: str
    light_svg: str
    dark_svg: str
    #: The same data as a markdown table, printed under the figure.
    table_md: str
    gif: str | None = None
    #: A text transcript, for a figure that records a terminal session.
    transcript: str | None = None


#: Builds the README's figures. Called once per close-out README, with keyword
#: arguments ``payload``, ``floors`` (after rulings), ``counts`` and ``repeat``.
FigureProvider = Callable[..., Sequence[FigureRef]]


def render_figure(fig: FigureRef) -> list[str]:
    """A figure as markdown: light and dark SVG, caption, digest, data."""
    lines = [
        '<picture><source media="(prefers-color-scheme: dark)" '
        f'srcset="{html.escape(fig.dark_svg, quote=True)}">'
        f'<img src="{html.escape(fig.light_svg, quote=True)}" '
        f'alt="{html.escape(fig.alt, quote=True)}"></picture>',
        "",
        fig.caption,
    ]
    if fig.gif:
        lines += ["", f"Animated: [{fig.id}]({fig.gif})"]
    lines += [
        "",
        f"<!-- figure {fig.id} data sha256:{fig.data_digest} -->",
        "",
        "<details><summary>Data</summary>",
        "",
        fig.table_md,
        "",
        "</details>",
    ]
    if fig.transcript:
        lines += [
            "",
            "<details><summary>Transcript</summary>",
            "",
            "```text",
            fig.transcript,
            "```",
            "",
            "</details>",
        ]
    return lines


def _figures_by_id(figures: Sequence[FigureRef]) -> dict[str, FigureRef]:
    """Exactly the README's figures, once each. A missing one is a hole in the
    README and an extra one would never be placed, so both are refused."""
    by_id: dict[str, FigureRef] = {}
    for fig in figures:
        if fig.id in by_id:
            raise ValueError(f"figure {fig.id} is given twice")
        by_id[fig.id] = fig
    missing = [i for i in README_FIGURES if i not in by_id]
    extra = sorted(set(by_id) - set(README_FIGURES))
    if missing or extra:
        raise ValueError(
            f"the close-out README places {', '.join(README_FIGURES)}; "
            f"missing {missing or 'none'}, unplaced {extra or 'none'}"
        )
    return by_id


# --------------------------------------------------------------------------
# The README's sections, shared by the first-sweep and the close-out README
# --------------------------------------------------------------------------


def _readme_header() -> list[str]:
    return [
        "# eval-floor",
        "",
        GENERATED_BANNER,
        "",
        "**What score does an answer with no content in it already get?**",
        "",
        "## The number, and its denominator",
        "",
    ]


def _readme_what_this_is() -> list[str]:
    return [
        "## What this is",
        "",
        "A scorer in Inspect is a function of a completion and a target. It does not "
        "care whether a model produced the completion. So eval-floor drives an eval's "
        "real scorer, over its real dataset, with a battery of completions that carry "
        "no information about the sample: the empty string, a refusal, every label "
        "concatenated. No model is called. The sweep costs nothing and is "
        "deterministic, which is what makes it reproducible by anyone.",
        "",
    ]


def _readme_case() -> list[str]:
    return [
        "## The case that started it",
        "",
        "Inspect Evals issue "
        "[#2331](https://github.com/UKGovernmentBEIS/inspect_evals/issues/2331) was "
        "opened on 2026-08-31 by **caiotheodoro**, who found that the constant string "
        '`"yesno"` scores 8000 of 8000 on the `paws` eval, because the eval is scored '
        "with `includes()` and both labels are substrings of that constant. **That "
        "finding is theirs, not this project's.** eval-floor generalises it, asking "
        "the same question mechanically of every task in the collection. "
        # Dated, because "the latest release" is only ever true on a day.
        "[#2334](https://github.com/UKGovernmentBEIS/inspect_evals/pull/2334) by "
        "**jkopczyn** merged 2026-09-16; the v0.21.0 release notes (2026-09-17) list "
        "the `paws` and `boolq` fix; as of 2026-10-10 the latest release is 0.24.0. "
        "The anchor stays on 0.20.0, where the behaviour is present. "
        "`tests/test_paws_regression.py` reproduces it from committed code.",
        "",
    ]


def _readme_reachability(inventory: Sequence[dict[str, Any]]) -> list[str]:
    return [
        "## Reachability",
        "",
        "The denominator comes before the result. Every declared task is either "
        "swept or excluded with a recorded reason; the full per-task table is in "
        "[`results/coverage.md`](results/coverage.md).",
        "",
        render_exclusion_table(inventory),
        "",
    ]


def _readme_battery() -> list[str]:
    return [
        "## The battery",
        "",
        "Members are defined semantically and written down in the task's own answer "
        "template when it declares one. Both arms, `raw` and `rendered`, are scored "
        "and reported, so the effect of that rendering is visible rather than assumed. "
        "The flag rule uses the rendered arm.",
        "",
        render_battery_table(),
        "",
        "> **Flag rule.** A task is flagged when at least one content-free member "
        "scores at or above that task's own `majority` baseline **and** strictly "
        "above zero. `majority` is computed per task from the dataset, never assumed: "
        "the PAWS test split is 55.8 per cent `No`, so its chance line is 0.558.",
        "",
    ]


def _readme_defects() -> list[str]:
    lines = [
        "## Instrument defects found so far",
        "",
        "Defects are logged, not quietly fixed. What the instrument got wrong is what "
        "tells a reader how far to trust what it now says. Full write-ups in "
        "[`INSTRUMENT_LESSONS.md`](INSTRUMENT_LESSONS.md).",
        "",
        "| # | defect | what it would have invalidated |",
        "|---|---|---|",
    ]
    for number, defect, invalidated in INSTRUMENT_DEFECT_ROWS:
        lines.append(f"| {number} | {defect} | {invalidated} |")
    lines.append("")
    return lines


def _readme_limitations(pin_row: str) -> list[str]:
    return [
        "## Limitations",
        "",
        "| limitation | what it means for the number |",
        "|---|---|",
        "| A flagged task is not a worthless benchmark | a loose scorer inflates a "
        "number without saying the underlying task is easy. **No claim is made about "
        "the conclusions of any published paper** that used any of these evals. |",
        pin_row,
        "| Deterministic scorers only | model-graded tasks are excluded from this "
        "number and deferred to a separate arm with its own intervals. The exclusion "
        "is counted, not hidden. |",
        "| The rendering rule is a choice | writing a member in the task's answer "
        "template changes what it scores. Both arms are published so the size of that "
        "effect is visible, but the headline depends on which arm is preregistered. |",
        "| Reachability is far below the collection size | most tasks need a "
        "container, a grader model, a gated dataset or an extra dependency. The "
        "denominator is published as prominently as the rate. |",
        "| `echo` on multimodal tasks | where inputs are images, echoing the input "
        "back is not well defined; such tasks are marked in the coverage file. |",
        "| One judge, and it can be wrong | the graded arm is scored by a single "
        "cheap model. Its id and the snapshot served are recorded in every row, and "
        "a second grader from a different family gives a measured disagreement rate "
        "-- which bounds the judge noise rather than removing it. |",
        "| Per-eval grade vocabularies | graded evals answer in their own words "
        "(ACCEPTABLE / NEITHER / COMPLIANCE and so on), and Inspect's generic "
        "converter silently returns 0.0 for any it does not know, which understates "
        "a floor. Mappings live in `verdict_maps.jsonl`, each quoting the eval "
        "source line; an unmapped verdict is excluded and reported, never zeroed. |",
        "",
    ]


_GENERATED_PARAGRAPH = (
    "Every number in `results/` and in this file is generated. None is typed by "
    "hand. Judgement calls live in `rulings.jsonl`, one row each, quoting the "
    "source line they came from, and the report applies that file mechanically. "
    "`evalfloor sweep` refuses to write a non-smoke result unless "
    "`PREREGISTRATION.md` is already committed in git history, and it records that "
    "commit hash in every file it generates."
)


def _readme_disclosure() -> list[str]:
    return [
        "## Disclosure",
        "",
        "**Built with LLM coding agents (Claude), with the author reviewing every "
        "number's source.** The harness, the battery definitions and the tests were "
        "written with Claude Code doing the typing under direction. The design, the "
        "preregistration, the measurement choices and every claim made about the "
        "results are the author's, and the anchoring result is checked in as a test "
        "anyone can run against pinned versions rather than taken on trust.",
        "",
        "## Licence",
        "",
        "MIT, (c) 2026 Ebin Babu Thomas.",
        "",
    ]


def render_readme(
    floors: Sequence[TaskFloor] | None,
    inventory: Sequence[dict[str, Any]] | None,
    payload: dict[str, Any] | None = None,
    graded_floors: Sequence[TaskFloor] | None = None,
    graded_payload: dict[str, Any] | None = None,
    closeout_inputs: CloseoutReadme | None = None,
    figures: Sequence[FigureRef] | None = None,
) -> str:
    """The README, with the number and the denominator first.

    Before a real sweep exists the headline is the literal placeholder
    ``{flagged} of {reachable} tasks``, so it is obvious that nothing is being
    claimed yet. ``evalfloor report`` fills it from ``results/sweep.json``.

    A deterministic payload that carries ``addendum_commit`` is the close-out
    sweep's, and gets the close-out README; that needs ``closeout_inputs`` and
    the figures, and refuses to render without either.
    """
    payload = payload or {}
    if payload.get("addendum_commit"):
        if closeout_inputs is None:
            raise ValueError("the close-out README needs its counts (closeout_inputs)")
        if figures is None:
            raise ValueError("the close-out README needs its figures; none were given")
        return render_closeout_readme(
            floors or [], payload, graded_floors or [], graded_payload,
            closeout_inputs, figures,
        )
    # Each arm's pins and fingerprint as its own payload recorded them, never the
    # environment this report runs in. Instrument defect 009.
    measured_on = _measured_on(payload)
    graded_measured_on = _measured_on(graded_payload) if graded_payload else None

    if floors and inventory:
        flagged, denom = flag_rate(floors)
        reachable = sum(1 for row in inventory if row["reachable"])
        headline = (
            f"**{flagged} of {denom} tasks** swept have at least one content-free "
            "completion that scores at or above their own majority-class baseline. "
            f"Of the whole collection, **{reachable} of {len(inventory)}** declared "
            "tasks are reachable for this sweep at all."
        )
        secondary = raw_arm_clause(floors, bold=False)
        n_collisions = collision_count(floors)
        if n_collisions:
            secondary += (
                f" Of the {flagged} flagged, **{n_collisions} rest on the template "
                "collision** -- the only flagging member is `format_only` and the "
                "string it was scored on is `majority`'s own string, so the flag is a "
                "tie between a member and itself. The rule is unchanged and the flags "
                "are marked; `results/floor_matrix.md` names them."
            )
        echo_line = echo_headline(floors)
    else:
        headline = (
            f"`{README_PLACEHOLDER}` -- **no sweep has run yet.** This line is a "
            "placeholder that `evalfloor report` fills from `results/sweep.json`. No "
            "number is claimed here until it does."
        )
        secondary = ""
        echo_line = None

    lines: list[str] = _readme_header()
    lines.append(headline)
    if echo_line:
        lines.append("")
        lines.append(echo_line)
    if secondary:
        lines.append("")
        lines.append(secondary)
    lines.append("")
    lines.extend(_prereg_block(payload))
    lines.append("")

    if graded_payload:
        lines.extend(render_readme_graded(graded_floors or [], graded_payload))

    lines.extend(_readme_what_this_is())
    lines.extend(_readme_case())
    if inventory:
        lines.extend(_readme_reachability(inventory))
    lines.extend(_readme_battery())
    lines.extend(_readme_defects())

    if graded_measured_on is None or graded_measured_on == measured_on:
        pinned = f"everything here is measured on {measured_on}"
    else:
        pinned = (
            f"the deterministic arm is measured on {measured_on}, and the "
            f"model-graded arm on {graded_measured_on}"
        )
    lines.extend(
        _readme_limitations(
            f"| One version pin | {pinned}, as each arm's `sweep.json` recorded it. "
            "Rows from different versions are never mixed; on any bump the whole sweep "
            "re-runs. |"
        )
    )

    lines.append("## Reproducing it")
    lines.append("")
    lines.append("```")
    lines.append('uv venv && uv pip install -e ".[dev]"')
    lines.append("pytest                                 # includes the #2331 anchor")
    lines.append("evalfloor inventory                    # regenerate the task inventory")
    lines.append("evalfloor check inspect_evals/paws     # exits non-zero")
    lines.append("evalfloor sweep --first-sweep --out results/")
    lines.append("evalfloor report                       # regenerates every number here")
    lines.append("```")
    lines.append("")
    lines.append(_GENERATED_PARAGRAPH)
    lines.append("")

    lines.extend(_readme_disclosure())
    return "\n".join(lines)


# --------------------------------------------------------------------------
# The close-out README
#
# Rendered only from a deterministic payload that carries addendum_commit, and
# only by `report --out results --repeat ...`. Every computed line comes from
# closeout.py, over counts computed once in write_all; this module places them.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CloseoutReadme:
    """What the close-out README reads beyond the two arms' floors and payloads."""

    #: ``closeout.counts(...)``, computed once.
    counts: closeout.CloseoutCounts
    rules: Sequence[Ruling]
    #: The release's own inventory, ``results/task_inventory.json``.
    release_inventory: Sequence[dict[str, Any]]
    #: The second run's sweep digest, from the ``--repeat`` payload.
    repeat_digest: str | None
    #: The tasks the two runs disagree on.
    moved: Sequence[str]


def _utc_date(generated_at: str | None) -> datetime.date:
    """The day a sweep was generated, in UTC. A naive stamp is read as UTC."""
    if not generated_at:
        raise ValueError("the payload has no generated_at to date the close-out by")
    stamp = datetime.datetime.fromisoformat(generated_at)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
    return stamp.astimezone(datetime.timezone.utc).date()


def _not_run_table(not_run: Sequence[tuple[str, str]]) -> list[str]:
    if not not_run:
        return ["Every listed task ran."]
    by_reason: dict[str, list[str]] = {}
    for task, reason in not_run:
        by_reason.setdefault(reason, []).append(task)
    lines = [
        f"Listed and not run, {len(not_run)}, by reason:",
        "",
        "| reason | tasks | which |",
        "|---|---|---|",
    ]
    for reason, tasks in sorted(by_reason.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        names = ", ".join(f"`{t.split('/')[-1]}`" for t in sorted(tasks))
        lines.append(f"| {_esc(reason)[:140]} | {len(tasks)} | {names} |")
    return lines


def _fix_rows(floors: Sequence[TaskFloor], release: str) -> list[str]:
    """``paws`` and ``boolq`` on the release, from their own floors."""
    lines = [
        f"`paws` and `boolq` on `inspect_evals` {release}, generated from this sweep:",
        "",
        "| task | scorer | majority | best content-free | flagged |",
        "|---|---|---|---|---|",
    ]
    for task in closeout.FIX_TASKS:
        short = task.split("/")[-1]
        task_floors = [f for f in floors if f.task == task]
        if not task_floors:
            lines.append(f"| `{short}` | - | {NOT_RUN} | - | - |")
            continue
        for f in task_floors:
            if f.error:
                lines.append(f"| `{short}` | - | - | - | error: {_esc(f.error)[:60]} |")
                continue
            flagged = ", ".join(f.flagged_by) if f.flagged else "no"
            lines.append(
                f"| `{short}` | `{_esc(f.scorer)}` | {_pct(f.majority)} | "
                f"{f.best_member or '-'} {_pct(f.best_mean)} | {flagged} |"
            )
    return lines


def _venv_for(release: str) -> str:
    """``.venv-024`` for 0.24.0: the environment the close-out recipe builds."""
    major, minor = (release.split(".") + ["0"])[:2]
    return f".venv-{major}{minor}"


def _reproduce_blocks(payload: dict[str, Any], release: str) -> list[str]:
    pins = payload.get("pins") or {}
    venv = _venv_for(release)
    python = f"{venv}/Scripts/python.exe"
    cli_ = f"{venv}/Scripts/evalfloor"
    anchor = closeout.ANCHOR_RELEASE
    return [
        f"The close-out, on `inspect_evals` {release}: the whole list, twice, in "
        "separate processes. The second run goes to `results/smoke/repeat`, and "
        "`report` compares the two task by task. (`Scripts/` is `bin/` off Windows.)",
        "",
        "```",
        f"uv venv {venv} --python 3.13",
        f"uv pip install --python {python} --no-deps -e .",
        f"uv pip install --python {python} inspect_ai=={pins.get('inspect_ai')} "
        f'inspect_evals=={release} "pytest>=8.0" "pytest-asyncio>=0.24"',
        f"{cli_} sweep --closeout --out results/",
        f"{cli_} sweep --closeout --out results/smoke/repeat",
        f"{cli_} report --out results --repeat results/smoke/repeat/sweep.json",
        "```",
        "",
        f"The {closeout.ISSUE} anchor, on `inspect_evals` {anchor}, where the "
        "behaviour is present:",
        "",
        "```",
        'uv venv && uv pip install -e ".[dev]"',
        "pytest                                 # includes the #2331 anchor",
        f"evalfloor check inspect_evals/paws     # exits non-zero on {anchor}",
        "```",
    ]


def render_closeout_readme(
    floors: Sequence[TaskFloor],
    payload: dict[str, Any],
    graded_floors: Sequence[TaskFloor],
    graded_payload: dict[str, Any] | None,
    inputs: CloseoutReadme,
    figures: Sequence[FigureRef],
) -> str:
    """The close-out README. ``floors`` are the deterministic floors after rulings."""
    from .rulings import not_counted

    c = inputs.counts
    fig = _figures_by_id(figures)
    rules = list(inputs.rules)

    lines: list[str] = _readme_header()
    lines.append(
        f"{closeout.first_line(c, floors, rules)} {closeout.section1_sentence(c.F, c.K)}"
    )
    lines.append("")
    lines.extend(render_figure(fig["F1"]))
    lines.append("")
    lines.append(closeout.status_line(_utc_date(payload.get("generated_at"))))
    lines.append("")
    echo_line = echo_headline(floors, generic=True)
    if echo_line:
        lines.append(echo_line)
        lines.append("")

    lines.append("## The denominator")
    lines.append("")
    lines.append(closeout.denominator_line(c))
    lines.append("")
    lines.extend(render_figure(fig["F3"]))
    lines.append("")
    lines.extend(_not_run_table(c.not_run))
    lines.append("")
    listed = not_counted(rules)
    if listed:
        lines.append("### Not counted")
        lines.append("")
        lines.append(render_treatment_table(listed))
        lines.append("")
    lines.append(f"### Reachability on `inspect_evals` {c.release}")
    lines.append("")
    lines.append(render_exclusion_table(inputs.release_inventory))
    lines.append("")

    lines.append("## Determinism")
    lines.append("")
    lines.append(
        closeout.determinism_line(payload["digest"], inputs.repeat_digest, inputs.moved)
    )
    lines.append("")

    lines.append("## Preregistration")
    lines.append("")
    lines.append(
        closeout.preregistration_line(
            payload.get("preregistration_commit"), payload.get("addendum_commit")
        )
    )
    lines.append("")

    if graded_payload:
        lines.extend(render_readme_graded(graded_floors, graded_payload))

    lines.extend(_readme_what_this_is())
    lines.extend(render_figure(fig["G1"]))
    lines.append("")

    lines.extend(_readme_case())
    lines.extend(_fix_rows(floors, c.release))
    lines.append("")
    lines.extend(render_figure(fig["F2"]))
    lines.append("")

    lines.extend(_readme_battery())
    lines.extend(_readme_defects())
    pins_line = closeout.pins_line(
        payload.get("pins") or {}, (graded_payload or {}).get("pins")
    )
    lines.extend(
        _readme_limitations(
            f"| Two arms, two pins | {pins_line} Each arm's pins and fingerprint are "
            "the ones its own `sweep.json` recorded, and no rate mixes releases. |"
        )
    )

    lines.append("## Reproducing it")
    lines.append("")
    lines.extend(_reproduce_blocks(payload, c.release))
    lines.append("")
    lines.extend(render_figure(fig["G2"]))
    lines.append("")
    lines.append(
        _GENERATED_PARAGRAPH
        + " `evalfloor sweep --closeout` also refuses until the close-out addendum, "
        "section 11, is committed and on `origin/master`."
    )
    lines.append("")

    lines.extend(_readme_disclosure())
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Payload IO
# --------------------------------------------------------------------------


def write_sweep(payload: dict[str, Any], path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_sweep(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def floors_from_payload(payload: dict[str, Any]) -> list[TaskFloor]:
    """Rebuild TaskFloor objects from a committed sweep payload."""
    from .aggregate import MemberScore

    floors: list[TaskFloor] = []
    for row in payload.get("floors", []):
        members = {
            name: MemberScore(**score)
            for name, score in (row.get("members") or {}).items()
        }
        members_raw = {
            name: MemberScore(**score)
            for name, score in (row.get("members_raw") or {}).items()
        }
        data = {k: v for k, v in row.items() if k not in ("members", "members_raw")}
        floors.append(TaskFloor(members=members, members_raw=members_raw, **data))
    floors.sort(key=lambda f: (f.task, f.scorer))
    return floors


# --------------------------------------------------------------------------
# Determinism across two runs (section 11.7)
#
# The close-out list runs twice, in separate processes, and `report --repeat`
# reads the second payload. A task whose two digests differ, or that errored in
# only one run, is "not run: non-deterministic": marked before rulings, so it
# leaves both the before and the after rate. Separate processes also catch
# set-order and hash-seed effects one process cannot.
# --------------------------------------------------------------------------


def repeat_mismatch(first: dict[str, Any], second: dict[str, Any]) -> list[str]:
    """What stops two payloads' per-task digests from being compared.

    Empty when they are comparable: the same pins, run fingerprint and task
    list, and both carry ``task_digests``. A difference in any of those means
    the second run was a different measurement, not a repeat of the first.
    """
    problems = [
        f"{key} differ: {first.get(key)!r} vs {second.get(key)!r}"
        for key in REPEAT_MUST_MATCH
        if first.get(key) != second.get(key)
    ]
    for name, payload in (("first", first), ("second", second)):
        if not payload.get("task_digests"):
            problems.append(f"the {name} payload carries no task_digests")
    return problems


def nondeterministic_tasks(first: dict[str, Any], second: dict[str, Any]) -> list[str]:
    """Tasks whose two runs differ in digest, or errored in only one of them."""
    d1 = first.get("task_digests") or {}
    d2 = second.get("task_digests") or {}

    def errored(payload: dict[str, Any]) -> set[str]:
        return {row["task"] for row in payload.get("floors", []) if row.get("error")}

    differ = {t for t in set(d1) | set(d2) if d1.get(t) != d2.get(t)}
    return sorted(differ | (errored(first) ^ errored(second)))


def apply_repeat(
    floors: Sequence[TaskFloor], payload: dict[str, Any], repeat: dict[str, Any]
) -> list[str]:
    """Mark the tasks two runs disagree on, in place. Returns them.

    Raises ValueError when the second payload is not a repeat of the first.
    """
    problems = repeat_mismatch(payload, repeat)
    if problems:
        raise ValueError("the second run is not a repeat: " + "; ".join(problems))
    moved = nondeterministic_tasks(payload, repeat)
    for f in floors:
        if f.task in moved:
            f.error = NOT_RUN_NONDETERMINISTIC
    return moved


def prepare_floors(
    payload: dict[str, Any],
    rules: Sequence[Ruling],
    repeat: dict[str, Any] | None = None,
) -> tuple[list[TaskFloor], list[TaskFloor], list[AppliedRuling], list[Ruling], list[str]]:
    """``(before, after, applied, unmatched, moved)`` for one payload.

    The one place floors are rebuilt, marked against a second run and ruled on,
    so every file and every console line reads the same floors. ``moved`` is
    the tasks the two runs disagree on, marked before rulings so they leave the
    before rate too; it is empty without ``repeat``. Everything downstream of
    the matrix -- the README and its figures -- reads ``after`` only.
    """
    from .rulings import apply_rulings

    before = floors_from_payload(payload)
    moved = apply_repeat(before, payload, repeat) if repeat is not None else []
    after, applied, unmatched = apply_rulings(before, list(rules))
    return before, after, applied, unmatched, moved


def readme_is_written_here(
    payload: dict[str, Any], arms: dict[str, Any], repeat: dict[str, Any] | None
) -> bool:
    """Whether this regeneration may write README.md.

    Once the deterministic payload carries ``addendum_commit`` the README is the
    close-out README, and only `report --out results --repeat ...` writes it:
    never a graded regenerate, which would rebuild it from one arm's side, and
    never a deterministic one without the second run to read determinism from.
    """
    if not (arms.get("payload") or {}).get("addendum_commit"):
        return True
    return payload_arm(payload) == "deterministic" and repeat is not None


def write_all(
    payload: dict[str, Any],
    out_dir: pathlib.Path,
    rulings_path: pathlib.Path,
    inventory: Sequence[dict[str, Any]] | None = None,
    readme_path: pathlib.Path | None = None,
    repeat: dict[str, Any] | None = None,
    figure_provider: FigureProvider | None = None,
) -> list[pathlib.Path]:
    """Regenerate every markdown artifact from a sweep payload. Returns paths.

    ``repeat`` is a second run's payload. Tasks the two runs disagree on are
    "not run: non-deterministic" in everything written here.

    ``figure_provider`` builds the close-out README's figures. Without one, a
    close-out README refuses to render: it never goes out with holes in it.
    """
    from .rulings import load_rulings, not_counted

    out_dir.mkdir(parents=True, exist_ok=True)
    rules = load_rulings(rulings_path)
    floors_before, floors_after, applied, unmatched, moved = prepare_floors(
        payload, rules, repeat
    )
    digest = payload.get("digest")
    # The not_counted rows shape the deterministic list only. The graded arm's
    # files never mention them, so they stay byte-identical when the rows land.
    listed = not_counted(rules) if payload_arm(payload) == "deterministic" else []

    written: list[pathlib.Path] = []

    matrix = out_dir / "floor_matrix.md"
    matrix.write_text(
        render_matrix(floors_before, floors_after, digest, payload), encoding="utf-8"
    )
    written.append(matrix)

    if inventory is not None:
        coverage = out_dir / "coverage.md"
        coverage.write_text(
            render_coverage(
                inventory, payload.get("tasks", []), floors_after, digest, payload,
                not_counted=listed,
            ),
            encoding="utf-8",
        )
        written.append(coverage)

    rulings_md = out_dir / "rulings_applied.md"
    rulings_md.write_text(
        render_rulings(applied, unmatched, not_counted=listed), encoding="utf-8"
    )
    written.append(rulings_md)

    arms = readme_arms(payload, floors_after, out_dir, rules) if readme_path else {}
    if readme_path is not None and readme_is_written_here(payload, arms, repeat):
        inputs: CloseoutReadme | None = None
        figures: list[FigureRef] | None = None
        if arms["payload"].get("addendum_commit"):
            # Only the deterministic arm, with its second run, gets here.
            root = results_root(out_dir)
            release_inventory = _required_inventory(root / "task_inventory.json")
            anchor_inventory = _required_inventory(root / "graded" / "task_inventory.json")
            counts = closeout.counts(
                floors_after, payload, rules, release_inventory, anchor_inventory,
                nondeterministic=moved,
            )
            inputs = CloseoutReadme(
                counts=counts,
                rules=rules,
                release_inventory=release_inventory,
                repeat_digest=(repeat or {}).get("digest"),
                moved=tuple(moved),
            )
            if figure_provider is not None:
                figures = list(
                    figure_provider(
                        payload=payload, floors=floors_after, counts=counts, repeat=repeat
                    )
                )
        readme_path.write_text(
            render_readme(
                arms["floors"],
                inventory,
                arms["payload"],
                graded_floors=arms["graded_floors"],
                graded_payload=arms["graded_payload"],
                closeout_inputs=inputs,
                figures=figures,
            ),
            encoding="utf-8",
        )
        written.append(readme_path)

    return written


def _required_inventory(path: pathlib.Path) -> list[dict[str, Any]]:
    """An inventory the close-out README cannot do without. Never a fallback:
    the anchor's 58 reachable are 0.20.0's, and the release's are its own."""
    if not path.exists():
        raise FileNotFoundError(
            f"the close-out README needs {path}; it is never replaced by another "
            "release's inventory"
        )
    return json.loads(path.read_text(encoding="utf-8"))
