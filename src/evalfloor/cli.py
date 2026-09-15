"""``evalfloor`` -- inventory, sweep, report, check.

``check`` is the one that matters for CI. It exits non-zero when a content-free
completion reaches a task's own majority-class baseline. That single exit code is
what makes this a gate rather than a report.

Exit codes:

======  ==========================================================
 0      checked and clean, or a command that only produces output
 1      **flagged**: a content-free member reached majority
 2      the task could not be run at all (the reason is printed)
======  ==========================================================
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import pathlib
import sys
from typing import Any, Sequence

from . import installed_pins
from .aggregate import aggregate_run, flag_rate, sweep_digest
from .battery import BATTERY, battery_fingerprint
from .drive import TaskRun, drive_task_async
from .report import (
    NEGATIVE_RESULT_THRESHOLD,
    floors_from_payload,
    read_sweep,
    write_all,
    write_sweep,
)

#: The smoke set: five of the preregistered twenty, chosen to cover all five
#: scorer families that appear in them. Defined here so the command and the
#: determinism test sweep exactly the same thing.
SMOKE_TASKS: tuple[str, ...] = (
    "inspect_evals/sec_qa_v2",  # choice
    "inspect_evals/gsm8k",  # match(numeric=True)
    "inspect_evals/boolq",  # pattern
    "inspect_evals/paws",  # includes
    "inspect_evals/drop",  # f1
)

DEFAULT_RESULTS = pathlib.Path("results")
DEFAULT_RULINGS = pathlib.Path("rulings.jsonl")
DEFAULT_INVENTORY_JSON = DEFAULT_RESULTS / "task_inventory.json"

EXIT_OK = 0
EXIT_FLAGGED = 1
EXIT_UNRUNNABLE = 2


# --------------------------------------------------------------------------
# inventory
# --------------------------------------------------------------------------


def cmd_inventory(args: argparse.Namespace) -> int:
    from .discover import (
        discover,
        first_sweep_tasks,
        write_inventory,
        write_inventory_json,
    )

    out = pathlib.Path(args.out)
    tasks = discover(
        probe=not args.no_probe,
        cache_path=out / "hf_probe_cache.json",
    )
    md = write_inventory(tasks, out / "task_inventory.md")
    js = write_inventory_json(tasks, out / "task_inventory.json")

    reachable = [t for t in tasks if t.reachable]
    print(f"{len(tasks)} tasks declared, {len(reachable)} reachable, "
          f"{len(tasks) - len(reachable)} excluded")
    print(f"wrote {md}")
    print(f"wrote {js}")
    if args.first_sweep:
        print()
        print(f"the preregistered first {len(first_sweep_tasks(tasks))}:")
        for t in first_sweep_tasks(tasks):
            print(f"  {t.name}")
    return EXIT_OK


# --------------------------------------------------------------------------
# sweep
# --------------------------------------------------------------------------


def _resolve_task_list(args: argparse.Namespace) -> list[str]:
    if args.tasks:
        names: list[str] = []
        for item in args.tasks:
            names.extend(part for part in item.split(",") if part.strip())
        return [n.strip() for n in names]
    if getattr(args, "smoke_set", False):
        return list(SMOKE_TASKS)
    if args.first_sweep:
        from .discover import discover, first_sweep_tasks

        inv_path = pathlib.Path(args.out) / "task_inventory.json"
        if inv_path.exists():
            rows = json.loads(inv_path.read_text(encoding="utf-8"))
            from .discover import TaskInfo

            infos = [TaskInfo(**row) for row in rows]
        else:
            infos = discover(probe=True, cache_path=pathlib.Path(args.out) / "hf_probe_cache.json")
        return [t.name for t in first_sweep_tasks(infos)]
    raise SystemExit("sweep needs --tasks, --first-sweep or --smoke-set")


# --------------------------------------------------------------------------
# The ordering gate
#
# "The preregistration was committed before any result existed" is a claim, and
# a claim a stranger cannot check is worth nothing. So the sweep refuses to
# produce a result at all unless PREREGISTRATION.md is already in git history,
# and it stamps that file's commit hash into sweep.json and into every generated
# markdown header. Anyone can then run `git log -- PREREGISTRATION.md` and see
# for themselves that the commit predates the result.
#
# results/smoke/ is exempt. A smoke run is a harness check, not a result, and
# the generated files say so in place of a commit hash.
# --------------------------------------------------------------------------

PREREGISTRATION_FILENAME = "PREREGISTRATION.md"

#: The one output directory exempt from the gate.
SMOKE_DIR_NAMES = ("smoke",)


def is_smoke_output(out: pathlib.Path) -> bool:
    """True for ``results/smoke`` and anything under it."""
    parts = [p.lower() for p in out.parts]
    return any(name in parts for name in SMOKE_DIR_NAMES)


def preregistration_commit(
    repo: pathlib.Path | None = None, filename: str = PREREGISTRATION_FILENAME
) -> str | None:
    """The hash of the commit that introduced the preregistration, or None.

    Uses the *earliest* commit touching the file, because what has to predate
    the result is when the preregistration was first committed, not when it was
    last edited.
    """
    import subprocess

    repo = repo or pathlib.Path.cwd()
    try:
        proc = subprocess.run(
            ["git", "log", "--reverse", "--format=%H", "--", filename],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    hashes = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return hashes[0] if hashes else None


def check_ordering_gate(out: pathlib.Path, repo: pathlib.Path | None = None) -> str | None:
    """Return the preregistration commit, or raise SystemExit explaining why not.

    Returns None for a smoke output, which is exempt.
    """
    if is_smoke_output(out):
        return None
    commit = preregistration_commit(repo)
    if commit:
        return commit
    raise SystemExit(
        f"refusing to sweep into {out}/.\n"
        f"\n"
        f"  {PREREGISTRATION_FILENAME} is not in this repository's git history.\n"
        f"\n"
        f"The whole point of a preregistration is that it is committed BEFORE any\n"
        f"result exists, and that a stranger can check the ordering with\n"
        f"`git log -- {PREREGISTRATION_FILENAME}`. Writing the sweep first and the\n"
        f"preregistration afterwards would make the claim unverifiable, so the\n"
        f"sweep will not run.\n"
        f"\n"
        f"What to do:\n"
        f"  1. review PREREGISTRATION.draft.md and answer its open questions\n"
        f"  2. git mv PREREGISTRATION.draft.md {PREREGISTRATION_FILENAME}\n"
        f"  3. git add {PREREGISTRATION_FILENAME} && git commit\n"
        f"  4. re-run this command\n"
        f"\n"
        f"To exercise the harness without producing a result, sweep into\n"
        f"results/smoke/, which is exempt."
    )


def _sweep(tasks: Sequence[str], limit: int | None) -> tuple[list[TaskRun], list[Any]]:
    runs: list[TaskRun] = []
    floors: list[Any] = []
    for name in tasks:
        print(f"  {name} ... ", end="", flush=True)
        run = asyncio.run(drive_task_async(name, limit=limit))
        runs.append(run)
        task_floors = aggregate_run(run)
        floors.extend(task_floors)
        if run.error:
            print(f"FAILED ({run.error[:70]})")
        else:
            flagged = [f for f in task_floors if f.flagged]
            best = max((f.best_mean for f in task_floors), default=0.0)
            state = (
                "FLAGGED by " + ", ".join(sorted({m for f in flagged for m in f.flagged_by}))
                if flagged
                else "clean"
            )
            print(f"n={run.n_samples} best content-free={100 * best:.1f}% -> {state}")
    return runs, floors


def cmd_sweep(args: argparse.Namespace) -> int:
    out = pathlib.Path(args.out)
    # The gate runs BEFORE any task is loaded, so a refused sweep costs nothing
    # and cannot leave a half-written result behind.
    prereg_commit = check_ordering_gate(out)
    smoke = is_smoke_output(out)

    tasks = _resolve_task_list(args)
    if smoke:
        print(f"SMOKE run into {out}/ -- exempt from the ordering gate, not a result")
    else:
        print(f"preregistration committed at {prereg_commit[:12]}; proceeding")
    print(f"sweeping {len(tasks)} tasks into {out}/")
    runs, floors = _sweep(tasks, args.limit)

    payload: dict[str, Any] = {
        "schema": 2,
        "pins": installed_pins(),
        "battery_fingerprint": battery_fingerprint(),
        "limit": args.limit,
        "tasks": list(tasks),
        "digest": sweep_digest(runs),
        "smoke": smoke,
        "preregistration_path": PREREGISTRATION_FILENAME,
        "preregistration_commit": prereg_commit,
        # Recorded, but deliberately absent from every generated .md, so that two
        # sweeps produce byte-identical markdown.
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "runs": [r.to_dict() for r in runs],
        "floors": [f.to_dict() for f in floors],
    }
    sweep_path = write_sweep(payload, out / "sweep.json")
    print(f"\nwrote {sweep_path}")
    print(f"digest {payload['digest'][:16]}")

    flagged, denom = flag_rate(floors)
    flagged_raw, _ = flag_rate(floors, arm="raw")
    print(f"flag rate before rulings: {flagged} of {denom} rendered, {flagged_raw} of {denom} raw")

    if not args.no_report:
        written = _regenerate(
            out, pathlib.Path(args.rulings), payload, readme=not smoke
        )
        for path in written:
            print(f"wrote {path}")
    return EXIT_OK


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------


def _load_inventory(out: pathlib.Path) -> list[dict[str, Any]] | None:
    path = out / "task_inventory.json"
    if not path.exists():
        path = DEFAULT_INVENTORY_JSON
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _regenerate(
    out: pathlib.Path,
    rulings: pathlib.Path,
    payload: dict[str, Any],
    readme: bool = True,
) -> list[pathlib.Path]:
    return write_all(
        payload,
        out,
        rulings,
        inventory=_load_inventory(out),
        # A smoke run never rewrites the README. Its numbers are not results.
        readme_path=pathlib.Path("README.md") if readme else None,
    )


def cmd_report(args: argparse.Namespace) -> int:
    out = pathlib.Path(args.out)
    sweep_path = out / "sweep.json"
    if not sweep_path.exists():
        print(
            f"no sweep payload at {sweep_path}; run `evalfloor sweep` first",
            file=sys.stderr,
        )
        return EXIT_UNRUNNABLE
    payload = read_sweep(sweep_path)
    readme = not payload.get("smoke", False) and not args.no_readme
    written = _regenerate(out, pathlib.Path(args.rulings), payload, readme=readme)
    floors = floors_from_payload(payload)
    flagged, denom = flag_rate(floors)
    flagged_raw, _ = flag_rate(floors, arm="raw")
    for path in written:
        print(f"wrote {path}")
    print(f"{flagged} of {denom} flagged before rulings (rendered arm)")
    print(f"{flagged_raw} of {denom} flagged on the raw arm")
    if payload.get("smoke"):
        print("smoke payload: README.md was not rewritten")
    if denom and flagged < NEGATIVE_RESULT_THRESHOLD:
        print(
            f"note: below the preregistered negative-result threshold of "
            f"{NEGATIVE_RESULT_THRESHOLD}"
        )
    return EXIT_OK


def cmd_readme(args: argparse.Namespace) -> int:
    """Write the README placeholder version, before any sweep exists."""
    from .report import render_readme

    out = pathlib.Path(args.out)
    inventory = _load_inventory(out)
    path = pathlib.Path("README.md")
    path.write_text(render_readme(None, inventory, {}), encoding="utf-8")
    print(f"wrote {path} (placeholder headline; no sweep payload used)")
    return EXIT_OK


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    name = args.task
    run = asyncio.run(drive_task_async(name, limit=args.limit))
    if run.error:
        print(f"{name}: could not run: {run.error}", file=sys.stderr)
        return EXIT_UNRUNNABLE

    floors = aggregate_run(run)
    pins = installed_pins()
    print(f"{name}  (inspect_ai {pins['inspect_ai']}, inspect_evals {pins['inspect_evals']})")
    print(f"  {run.n_samples} samples, scorer(s): {', '.join(run.scorers)}")

    any_flagged = False
    for floor in floors:
        print(f"  scorer {floor.scorer}")
        print(f"    majority baseline  {100 * floor.majority:6.2f}%  "
              f"(modal target {floor.majority_label!r})")
        if floor.uniform is not None:
            print(f"    uniform baseline   {100 * floor.uniform:6.2f}%")
        for member in BATTERY:
            score = floor.members.get(member.name)
            if score is None:
                continue
            if not score.applicable:
                print(f"    {member.name:<14} n/a  ({score.not_applicable_reason})")
                continue
            mark = ""
            if (
                member.kind == "content_free"
                and score.mean >= floor.majority
                and score.mean > 0.0
            ):
                mark = "  <-- at or above majority"
            print(
                f"    {member.name:<14} {100 * score.mean:6.2f}%  "
                f"{score.n_correct}/{score.n_scored}{mark}"
            )
        if floor.flagged:
            any_flagged = True
            print(
                f"    FLAGGED: {', '.join(floor.flagged_by)} "
                f"score at or above the majority baseline"
            )

    if any_flagged:
        print(f"\n{name}: FLAGGED", file=sys.stderr)
        return EXIT_FLAGGED
    print(f"\n{name}: clean")
    return EXIT_OK


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evalfloor",
        description="What score does an answer with no content in it already get?",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_inv = sub.add_parser("inventory", help="enumerate tasks and classify their scorers")
    p_inv.add_argument("--out", default=str(DEFAULT_RESULTS))
    p_inv.add_argument(
        "--no-probe",
        action="store_true",
        help="skip the Hugging Face metadata lookup (offline; no size or gating data)",
    )
    p_inv.add_argument("--first-sweep", action="store_true", help="also print the chosen twenty")
    p_inv.set_defaults(func=cmd_inventory)

    p_sweep = sub.add_parser("sweep", help="drive the battery over tasks")
    p_sweep.add_argument("--tasks", nargs="*", help="task names, space or comma separated")
    p_sweep.add_argument(
        "--first-sweep", action="store_true", help="use the preregistered twenty"
    )
    p_sweep.add_argument(
        "--smoke-set",
        action="store_true",
        help="use the five-task smoke set (one per scorer family)",
    )
    p_sweep.add_argument("--out", default=str(DEFAULT_RESULTS))
    p_sweep.add_argument("--rulings", default=str(DEFAULT_RULINGS))
    p_sweep.add_argument("--limit", type=int, default=None, help="cap samples per task")
    p_sweep.add_argument("--no-report", action="store_true")
    p_sweep.set_defaults(func=cmd_sweep)

    p_report = sub.add_parser(
        "report", help="regenerate the markdown and the README from a sweep payload"
    )
    p_report.add_argument("--out", default=str(DEFAULT_RESULTS))
    p_report.add_argument("--rulings", default=str(DEFAULT_RULINGS))
    p_report.add_argument(
        "--no-readme", action="store_true", help="leave README.md alone"
    )
    p_report.set_defaults(func=cmd_report)

    p_readme = sub.add_parser(
        "readme", help="write the placeholder README, before any sweep has run"
    )
    p_readme.add_argument("--out", default=str(DEFAULT_RESULTS))
    p_readme.set_defaults(func=cmd_readme)

    p_check = sub.add_parser(
        "check", help="exit non-zero when a content-free member reaches majority"
    )
    p_check.add_argument("task")
    p_check.add_argument("--limit", type=int, default=None)
    p_check.set_defaults(func=cmd_check)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
