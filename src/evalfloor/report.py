"""Write ``results/*.md``. No number in any generated file is typed by hand.

Every figure that appears in the matrix, the coverage file or the controls file
is computed here from a committed sweep payload plus ``rulings.jsonl``. The files
carry a "GENERATED" banner and the pins the measurement was taken under, so a row
produced under one version pair can never be silently read next to another.

Generated markdown deliberately contains **no timestamps and no wall-clock
timings**, so two sweeps of the deterministic arms produce byte-identical output
and the determinism control is a plain file comparison.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Iterable, Sequence

from . import installed_pins
from .aggregate import TaskFloor, flag_rate
from .battery import (
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


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _esc(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def provenance_block(digest: str | None = None, extra: dict[str, Any] | None = None) -> list[str]:
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


# --------------------------------------------------------------------------
# The matrix
# --------------------------------------------------------------------------


def render_matrix(
    floors_before: Sequence[TaskFloor],
    floors_after: Sequence[TaskFloor] | None = None,
    digest: str | None = None,
) -> str:
    floors_after = floors_after if floors_after is not None else floors_before
    flagged_before, denom = flag_rate(floors_before)
    flagged_after, _ = flag_rate(floors_after)

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
            f"The denominator is the number of tasks that produced a scored floor in "
            f"this sweep; `results/coverage.md` says what is not in it and why."
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

    lines.append("## Per task")
    lines.append("")
    header = ["task", "scorer", "n", "majority", "uniform", "best content-free", "score", "gap", "flagged"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for f in floors_after:
        if f.error:
            lines.append(
                f"| `{f.task}` | - | - | - | - | - | - | - | error: {_esc(f.error)[:60]} |"
            )
            continue
        uniform = _pct(f.uniform) if f.uniform is not None else "n/a"
        flagged = ", ".join(f.flagged_by) if f.flagged else "no"
        if f.ruling:
            flagged += f" ({f.ruling})"
        lines.append(
            f"| `{f.task}` | `{_esc(f.scorer)}` | {f.n_samples} | {_pct(f.majority)} | "
            f"{uniform} | {f.best_member or '-'} | {_pct(f.best_mean)} | "
            f"{f.gap_to_majority:+.3f} | {flagged} |"
        )
    lines.append("")

    lines.append("## Every battery member, every task")
    lines.append("")
    members = [m for m in CONTENT_FREE_NAMES] + [m for m in REFERENCE_NAMES]
    lines.append("| task | scorer | " + " | ".join(members) + " |")
    lines.append("|" + "---|" * (len(members) + 2))
    for f in floors_after:
        if f.error:
            continue
        cells: list[str] = []
        for name in members:
            score = f.members.get(name)
            if score is None:
                cells.append("-")
            elif not score.applicable:
                cells.append("n/a")
            else:
                cells.append(_pct(score.mean))
        lines.append(f"| `{f.task}` | `{_esc(f.scorer)}` | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## Counts, not rates")
    lines.append("")
    lines.append("| task | scorer | member | correct | scored |")
    lines.append("|---|---|---|---|---|")
    for f in floors_after:
        if f.error:
            continue
        for name in members:
            score = f.members.get(name)
            if score is None or not score.applicable:
                continue
            lines.append(
                f"| `{f.task}` | `{_esc(f.scorer)}` | {name} | "
                f"{score.n_correct} | {score.n_scored} |"
            )
    lines.append("")

    lines.append("## The battery")
    lines.append("")
    lines.append("| member | kind | completion |")
    lines.append("|---|---|---|")
    for m in BATTERY:
        lines.append(f"| `{m.name}` | {m.kind} | {_esc(m.description)} |")
    lines.append("")
    lines.append("Literal strings, fixed by preregistration:")
    lines.append("")
    lines.append(f"* `refusal` = `{REFUSAL_TEXT}`")
    lines.append(f"* `format_only` = `{FORMAT_ONLY_TEXT}`")
    lines.append(f"* `boilerplate` = {len(BOILERPLATE_TEXT)} characters, beginning "
                 f"`{BOILERPLATE_TEXT[:48]}...`")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------


def render_coverage(
    inventory: Sequence[dict[str, Any]],
    swept_tasks: Sequence[str],
    floors: Sequence[TaskFloor],
    digest: str | None = None,
) -> str:
    from collections import Counter

    swept = set(swept_tasks)
    errored = {f.task: f.error for f in floors if f.error}
    scored = {f.task for f in floors if f.error is None and f.members}

    reasons = Counter(
        row["exclusion_reason"] for row in inventory if not row["reachable"]
    )
    reachable = [row for row in inventory if row["reachable"]]

    lines: list[str] = ["# Coverage", "", GENERATED_BANNER, ""]
    lines.append(
        "The denominator comes before the result. Every task declared in an "
        "`eval.yaml` gets exactly one row here: it was swept, it is reachable but "
        "not yet swept, or there is a recorded reason it cannot be."
    )
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
    lines.append(f"| swept in this run | {len(swept)} |")
    lines.append(f"| produced a scored floor | {len(scored)} |")
    lines.append(f"| swept but errored | {len(errored)} |")
    lines.append("")

    lines.append("## Exclusion reasons")
    lines.append("")
    lines.append("| reason | tasks | meaning |")
    lines.append("|---|---|---|")
    meanings = {
        "sandbox_required": "the task or its scorer needs a container",
        "extra_dependency": "needs an optional dependency group that is not installed",
        "model_graded": "the scorer needs a grader model; not part of the deterministic arm",
        "network_required": "fetches from a URL or clones a repository at run time",
        "gated_dataset": "the Hugging Face dataset requires accepting terms or an access grant",
        "too_large": "the dataset exceeds the disk cap recorded in PREREGISTRATION.md",
        "unclassified_scorer": "the scorer could not be resolved statically",
        "not_registered": "no entry in inspect_evals._registry",
    }
    for reason, count in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{reason}` | {count} | {meanings.get(reason, '')} |")
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

    lines.append("## Every task")
    lines.append("")
    lines.append("| task | status | reason | detail |")
    lines.append("|---|---|---|---|")
    for row in inventory:
        task = row["name"]
        if task in errored:
            status, reason, detail = "failed", "load_error", errored[task]
        elif task in scored:
            status, reason, detail = "swept", "", ""
        elif row["reachable"]:
            status, reason, detail = "reachable, not swept", "", ""
        else:
            status = "excluded"
            reason = row["exclusion_reason"]
            detail = row["exclusion_detail"]
        lines.append(
            f"| `{task}` | {status} | `{reason}` | {_esc(detail)[:140]} |"
        )
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Rulings log
# --------------------------------------------------------------------------


def render_rulings(
    applied: Sequence[AppliedRuling], unmatched: Sequence[Ruling]
) -> str:
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
            name: MemberScore(**score) for name, score in (row.get("members") or {}).items()
        }
        data = {k: v for k, v in row.items() if k != "members"}
        floors.append(TaskFloor(members=members, **data))
    floors.sort(key=lambda f: (f.task, f.scorer))
    return floors


def write_all(
    payload: dict[str, Any],
    out_dir: pathlib.Path,
    rulings_path: pathlib.Path,
    inventory: Sequence[dict[str, Any]] | None = None,
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
    matrix.write_text(render_matrix(floors_before, floors_after, digest), encoding="utf-8")
    written.append(matrix)

    if inventory is not None:
        coverage = out_dir / "coverage.md"
        coverage.write_text(
            render_coverage(inventory, payload.get("tasks", []), floors_after, digest),
            encoding="utf-8",
        )
        written.append(coverage)

    rulings_md = out_dir / "rulings_applied.md"
    rulings_md.write_text(render_rulings(applied, unmatched), encoding="utf-8")
    written.append(rulings_md)

    return written
