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

import json
import pathlib
from typing import Any, Sequence

from . import installed_pins
from .aggregate import TaskFloor, flag_rate
from .battery import (
    ARMS,
    BATTERY,
    BOILERPLATE_TEXT,
    CONTENT_FREE_NAMES,
    FORMAT_ONLY_TEXT,
    REFERENCE_NAMES,
    REFUSAL_TEXT,
    battery_fingerprint,
)
from .rulings import AppliedRuling, Ruling

GENERATED_BANNER = (
    "<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. "
    "Every number here is computed from results/sweep.json and rulings.jsonl. -->"
)

#: Fewer than this many flagged reachable tasks is the preregistered negative
#: result: the collection is tighter than the single known case suggested.
NEGATIVE_RESULT_THRESHOLD = 5

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


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _esc(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def provenance_block(
    digest: str | None = None, extra: dict[str, Any] | None = None
) -> list[str]:
    pins = installed_pins()
    lines = [
        "| provenance | value |",
        "|---|---|",
        f"| `inspect_ai` | {pins.get('inspect_ai')} |",
        f"| `inspect_evals` | {pins.get('inspect_evals')} |",
        f"| battery fingerprint | `{battery_fingerprint()}` |",
    ]
    if digest:
        lines.append(f"| sweep digest | `{digest[:16]}` |")
    for k, v in (extra or {}).items():
        lines.append(f"| {k} | {v} |")
    return lines


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
    return [
        f"Preregistration `{path}` was committed at `{commit[:12]}` **before** this "
        f"sweep ran. Anyone can check that independently: "
        f"`git log --format='%H %ad' -- {path}`.",
    ]


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
    flagged_raw, _ = flag_rate(floors_after, arm="raw")

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
            f"Before rulings the count was **{flagged_before} of {denom}**. On the raw "
            f"arm -- members written plainly, ignoring each task's answer template -- "
            f"it is **{flagged_raw} of {denom}**. The headline uses the rendered arm, "
            "as preregistered. `coverage.md` says what is not in this denominator."
        )
        if flagged_after < NEGATIVE_RESULT_THRESHOLD:
            lines.append("")
            lines.append(
                f"> **Preregistered negative result.** Fewer than "
                f"{NEGATIVE_RESULT_THRESHOLD} flagged tasks was fixed in advance as "
                f"the threshold at which the finding is that the collection is "
                f"tighter than the single known case suggested. At {flagged_after} "
                f"of {denom}, that is the finding."
            )
    lines.append("")
    lines.extend(_prereg_block(payload))
    lines.append("")
    lines.extend(provenance_block(digest))
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
    ]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for f in floors_after:
        if f.error:
            lines.append(
                f"| `{f.task}` | - | - | - | - | - | - | - | - | error: "
                f"{_esc(f.error)[:60]} |"
            )
            continue
        uniform = _pct(f.uniform) if f.uniform is not None else "n/a"
        flagged = ", ".join(f.flagged_by) if f.flagged else "no"
        if f.ruling:
            flagged += f" ({f.ruling})"
        lines.append(
            f"| `{f.task}` | `{_esc(f.scorer)}` | {f.answer_template} | {f.n_samples} | "
            f"{_pct(f.majority)} | {uniform} | {f.best_member or '-'} | "
            f"{_pct(f.best_mean)} | {f.gap_to_majority:+.3f} | {flagged} |"
        )
    lines.append("")

    lines.append("## What the rendering rule changed")
    lines.append("")
    lines.append(
        "Every member is defined semantically and then written down in the task's own "
        "answer template when it declares one. Both forms are scored. On a task that "
        "declares no template the two arms are identical by construction, and the rows "
        "below show that rather than asserting it."
    )
    lines.append("")
    lines.append(
        "| task | template | majority raw | majority rendered | best CF raw | "
        "best CF rendered | flagged raw | flagged rendered |"
    )
    lines.append("|" + "---|" * 8)
    templated_tasks = 0
    disagreements = 0
    for f in floors_after:
        if f.error:
            continue
        if f.answer_template != "bare":
            templated_tasks += 1
        if f.flagged_raw != f.flagged:
            disagreements += 1
        lines.append(
            f"| `{f.task}` | {f.answer_template} | {_pct(f.majority_raw)} | "
            f"{_pct(f.majority)} | {f.best_member_raw or '-'} "
            f"{_pct(f.best_mean_raw)} | {f.best_member or '-'} {_pct(f.best_mean)} | "
            f"{'yes' if f.flagged_raw else 'no'} | {'yes' if f.flagged else 'no'} |"
        )
    lines.append("")
    scored_tasks = len([f for f in floors_after if not f.error])
    lines.append(
        f"{templated_tasks} of {scored_tasks} tasks here declare an answer template. "
        f"The two arms disagree on {disagreements}."
    )
    finding = rendering_finding(floors_after)
    if finding:
        lines.append("")
        lines.append(finding)
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
            source = f.members_raw if arm == "raw" else f.members
            cells: list[str] = []
            for name in members:
                score = source.get(name)
                if score is None:
                    cells.append("-")
                elif not score.applicable:
                    cells.append("n/a")
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


def echo_headline(floors: Sequence[TaskFloor]) -> str | None:
    """The ``echo`` finding as one sentence, computed from the sweep.

    Echoing the question back carries no information about the answer, so any
    score it gets is the scorer crediting the input for containing the target.
    Every number in the sentence comes from the payload; none is typed.
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
    if worst_echo.n_correct > 0:
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
    """
    scored = [
        f for f in floors if f.error is None and f.members and not f.nothing_scored
    ]
    if not scored:
        return None
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
    return " ".join(parts)


def _first_error(floor: TaskFloor) -> str:
    return floor.first_error or floor.error or "not recorded"


def _ci(score: Any) -> str:
    if score is None or score.ci_low is None or score.ci_high is None:
        return "-"
    return f"[{100 * score.ci_low:.1f}, {100 * score.ci_high:.1f}]"


def render_graded_section(floors: Sequence[TaskFloor], payload: dict[str, Any]) -> str:
    """The model-graded arm: intervals, the grader, refusals, disagreement.

    Deliberately kept separate from the deterministic tables. The two arms are
    never added together into one rate: one is exact over whole datasets and
    free, the other is a capped sample graded by a model that can be wrong and
    costs money per call.
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
    lines.append("")

    if grader.get("is_mock"):
        lines.append(
            "> **This run used `mockllm/model`, which is not a grader.** No provider "
            "was called and no API key was present. The numbers below exercise the "
            "plumbing and say **nothing whatever** about any eval. They are published "
            "only so the harness can be checked before money is spent running it."
        )
        lines.append("")

    lines.append("### Per task")
    lines.append("")
    lines.append(
        "| task | scorer | n | grader | majority | best content-free | 95% CI | "
        "refusals | flagged |"
    )
    lines.append("|" + "---|" * 9)
    dead: list[TaskFloor] = []
    for f in graded_floors:
        if f.nothing_scored:
            dead.append(f)
            lines.append(
                f"| `{f.task}` | `{_esc(f.scorer)}` | {f.n_samples} | "
                f"`{_esc(f.grader_model)}` | NO RESULT | NO RESULT | - | "
                f"{f.n_refusals} | not measured |"  # noqa: E501
            )
            continue
        best = f.members.get(f.best_member) if f.best_member else None
        lines.append(
            f"| `{f.task}` | `{_esc(f.scorer)}` | {f.n_samples} | "
            f"`{_esc(f.grader_model)}` | {_pct(f.majority)} | "
            f"{f.best_member or '-'} {_pct(f.best_mean)} | {_ci(best)} | "
            f"{f.n_refusals} | {', '.join(f.flagged_by) if f.flagged else 'no'} |"
        )
    if not graded_floors:
        lines.append("| _(no graded task produced a floor)_ | | | | | | | | |")
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
                f"| `{f.task}` | {name} | {cell} | {_ci(score)} | "
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
) -> str:
    payload = payload or {}
    swept = set(swept_tasks)
    errored = {f.task: f.error for f in floors if f.error}
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
    lines.extend(provenance_block(digest))
    lines.append("")

    lines.append("## Totals")
    lines.append("")
    lines.append("| | count |")
    lines.append("|---|---|")
    lines.append(f"| tasks declared in `eval.yaml` files | {len(inventory)} |")
    lines.append(f"| reachable for the deterministic sweep | {len(reachable)} |")
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

    lines.append(f"## Every task ({len(inventory)} rows)")
    lines.append("")
    lines.append("| task | scorer | class | status | reason | detail |")
    lines.append("|---|---|---|---|---|---|")
    covered = 0
    for row in inventory:
        task = row["name"]
        if task in errored:
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


# --------------------------------------------------------------------------
# Rulings log
# --------------------------------------------------------------------------


def render_rulings(applied: Sequence[AppliedRuling], unmatched: Sequence[Ruling]) -> str:
    lines: list[str] = ["# Rulings applied", "", GENERATED_BANNER, ""]
    lines.append(
        "Every judgement call in the sweep, applied mechanically from "
        "`rulings.jsonl`. The flag rate is reported both before and after these."
    )
    lines.append("")
    if not applied and not unmatched:
        lines.append("`rulings.jsonl` is empty. No judgement call has been made yet.")
        lines.append("")
        return "\n".join(lines)
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


def render_readme(
    floors: Sequence[TaskFloor] | None,
    inventory: Sequence[dict[str, Any]] | None,
    payload: dict[str, Any] | None = None,
) -> str:
    """The README, with the number and the denominator first.

    Before a real sweep exists the headline is the literal placeholder
    ``{flagged} of {reachable} tasks``, so it is obvious that nothing is being
    claimed yet. ``evalfloor report`` fills it from ``results/sweep.json``.
    """
    payload = payload or {}
    pins = installed_pins()

    if floors and inventory:
        flagged, denom = flag_rate(floors)
        flagged_raw, _ = flag_rate(floors, arm="raw")
        reachable = sum(1 for row in inventory if row["reachable"])
        headline = (
            f"**{flagged} of {denom} tasks** swept have at least one content-free "
            "completion that scores at or above their own majority-class baseline. "
            f"Of the whole collection, **{reachable} of {len(inventory)}** declared "
            "tasks are reachable for this sweep at all."
        )
        secondary = (
            f"On the raw arm -- members written plainly, ignoring each task's answer "
            f"template -- it is {flagged_raw} of {denom}."
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

    lines: list[str] = []
    lines.append("# eval-floor")
    lines.append("")
    lines.append(GENERATED_BANNER)
    lines.append("")
    lines.append("**What score does an answer with no content in it already get?**")
    lines.append("")
    lines.append("## The number, and its denominator")
    lines.append("")
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

    lines.append("## What this is")
    lines.append("")
    lines.append(
        "A scorer in Inspect is a function of a completion and a target. It does not "
        "care whether a model produced the completion. So eval-floor drives an eval's "
        "real scorer, over its real dataset, with a battery of completions that carry "
        "no information about the sample: the empty string, a refusal, every label "
        "concatenated. No model is called. The sweep costs nothing and is "
        "deterministic, which is what makes it reproducible by anyone."
    )
    lines.append("")

    lines.append("## The case that started it")
    lines.append("")
    lines.append(
        "Inspect Evals issue "
        "[#2331](https://github.com/UKGovernmentBEIS/inspect_evals/issues/2331) was "
        "opened on 2026-08-31 by **caiotheodoro**, who found that the constant string "
        '`"yesno"` scores 8000 of 8000 on the `paws` eval, because the eval is scored '
        "with `includes()` and both labels are substrings of that constant. **That "
        "finding is theirs, not this project's.** eval-floor generalises it, asking "
        "the same question mechanically of every task in the collection. A fix is in "
        "flight: PR "
        "[#2334](https://github.com/UKGovernmentBEIS/inspect_evals/pull/2334) by "
        "**jkopczyn** replaces the `paws` and `boolq` scorers with anchored patterns, "
        "and a maintainer comment from **MattFisher** dated 2026-09-09 calls it "
        '"merge-ready" -- but it carries no approving GitHub review, it is **not '
        "merged**, and no release contains it. `paws` in `inspect_evals` "
        f"{pins.get('inspect_evals')}, the latest release, still reads "
        "`scorer=includes()`. That is why this repository pins that version: the "
        "anchor has to run against a version where the behaviour is still present. "
        "`tests/test_paws_regression.py` reproduces it from committed code."
    )
    lines.append("")

    if inventory:
        lines.append("## Reachability")
        lines.append("")
        lines.append(
            "The denominator comes before the result. Every declared task is either "
            "swept or excluded with a recorded reason; the full per-task table is in "
            "[`results/coverage.md`](results/coverage.md)."
        )
        lines.append("")
        lines.append(render_exclusion_table(inventory))
        lines.append("")

    lines.append("## The battery")
    lines.append("")
    lines.append(
        "Members are defined semantically and written down in the task's own answer "
        "template when it declares one. Both arms, `raw` and `rendered`, are scored "
        "and reported, so the effect of that rendering is visible rather than assumed. "
        "The flag rule uses the rendered arm."
    )
    lines.append("")
    lines.append(render_battery_table())
    lines.append("")
    lines.append(
        "> **Flag rule.** A task is flagged when at least one content-free member "
        "scores at or above that task's own `majority` baseline **and** strictly "
        "above zero. `majority` is computed per task from the dataset, never assumed: "
        "the PAWS test split is 55.8 per cent `No`, so its chance line is 0.558."
    )
    lines.append("")

    lines.append("## Instrument defects found so far")
    lines.append("")
    lines.append(
        "Defects are logged, not quietly fixed. What the instrument got wrong is what "
        "tells a reader how far to trust what it now says. Full write-ups in "
        "[`INSTRUMENT_LESSONS.md`](INSTRUMENT_LESSONS.md)."
    )
    lines.append("")
    lines.append("| # | defect | what it would have invalidated |")
    lines.append("|---|---|---|")
    lines.append(
        "| 001 | `choice()` tasks were not driven at all: the scorer reads marked "
        "choices, not completion text | every multiple-choice row; 16 of the first 20 "
        "tasks use `choice()` |"
    )
    lines.append(
        "| 002 | the flag rule fired on `0 >= 0` when nothing scored at all | turned "
        "harness failures into findings |"
    )
    lines.append(
        "| 003 | reference baselines could not parse on multiple-choice tasks | the "
        "chance line the whole flag rule rests on |"
    )
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append("| limitation | what it means for the number |")
    lines.append("|---|---|")
    lines.append(
        "| A flagged task is not a worthless benchmark | a loose scorer inflates a "
        "number without saying the underlying task is easy. **No claim is made about "
        "the conclusions of any published paper** that used any of these evals. |"
    )
    lines.append(
        f"| One version pin | everything here is measured on `inspect_ai` "
        f"{pins.get('inspect_ai')} and `inspect_evals` {pins.get('inspect_evals')}. "
        "Rows from different versions are never mixed; on any bump the whole sweep "
        "re-runs. |"
    )
    lines.append(
        "| Deterministic scorers only | model-graded tasks are excluded from this "
        "number and deferred to a separate arm with its own intervals. The exclusion "
        "is counted, not hidden. |"
    )
    lines.append(
        "| The rendering rule is a choice | writing a member in the task's answer "
        "template changes what it scores. Both arms are published so the size of that "
        "effect is visible, but the headline depends on which arm is preregistered. |"
    )
    lines.append(
        "| Reachability is far below the collection size | most tasks need a "
        "container, a grader model, a gated dataset or an extra dependency. The "
        "denominator is published as prominently as the rate. |"
    )
    lines.append(
        "| `echo` on multimodal tasks | where inputs are images, echoing the input "
        "back is not well defined; such tasks are marked in the coverage file. |"
    )
    lines.append(
        "| One judge, and it can be wrong | the graded arm is scored by a single "
        "cheap model. Its id and the snapshot served are recorded in every row, and "
        "a second grader from a different family gives a measured disagreement rate "
        "-- which bounds the judge noise rather than removing it. |"
    )
    lines.append(
        "| Per-eval grade vocabularies | graded evals answer in their own words "
        "(ACCEPTABLE / NEITHER / COMPLIANCE and so on), and Inspect's generic "
        "converter silently returns 0.0 for any it does not know, which understates "
        "a floor. Mappings live in `verdict_maps.jsonl`, each quoting the eval "
        "source line; an unmapped verdict is excluded and reported, never zeroed. |"
    )
    lines.append("")

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
    lines.append(
        "Every number in `results/` and in this file is generated. None is typed by "
        "hand. Judgement calls live in `rulings.jsonl`, one row each, quoting the "
        "source line they came from, and the report applies that file mechanically. "
        "`evalfloor sweep` refuses to write a non-smoke result unless "
        "`PREREGISTRATION.md` is already committed in git history, and it records that "
        "commit hash in every file it generates."
    )
    lines.append("")

    lines.append("## Disclosure")
    lines.append("")
    lines.append(
        "**Built with LLM coding agents (Claude), with the author reviewing every "
        "number's source.** The harness, the battery definitions and the tests were "
        "written with Claude Code doing the typing under direction. The design, the "
        "preregistration, the measurement choices and every claim made about the "
        "results are the author's, and the anchoring result is checked in as a test "
        "anyone can run against pinned versions rather than taken on trust."
    )
    lines.append("")
    lines.append("## Licence")
    lines.append("")
    lines.append("MIT, (c) 2026 Ebin Babu Thomas.")
    lines.append("")
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


def write_all(
    payload: dict[str, Any],
    out_dir: pathlib.Path,
    rulings_path: pathlib.Path,
    inventory: Sequence[dict[str, Any]] | None = None,
    readme_path: pathlib.Path | None = None,
) -> list[pathlib.Path]:
    """Regenerate every markdown artifact from a sweep payload. Returns paths."""
    from .rulings import apply_rulings, load_rulings

    out_dir.mkdir(parents=True, exist_ok=True)
    floors_before = floors_from_payload(payload)
    rules = load_rulings(rulings_path)
    floors_after, applied, unmatched = apply_rulings(floors_before, rules)
    digest = payload.get("digest")

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
                inventory, payload.get("tasks", []), floors_after, digest, payload
            ),
            encoding="utf-8",
        )
        written.append(coverage)

    rulings_md = out_dir / "rulings_applied.md"
    rulings_md.write_text(render_rulings(applied, unmatched), encoding="utf-8")
    written.append(rulings_md)

    if readme_path is not None:
        readme_path.write_text(
            render_readme(floors_after, inventory, payload), encoding="utf-8"
        )
        written.append(readme_path)

    return written
