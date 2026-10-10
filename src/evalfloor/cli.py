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
import subprocess
import sys
from typing import Any, Sequence

from . import installed_pins
from .aggregate import (
    aggregate_run,
    collision_count,
    flag_rate,
    sweep_digest,
    task_digests,
)
from .battery import BATTERY, SHUFFLE_SEED, battery_fingerprint, run_fingerprint
from .drive import TaskRun, drive_task_async
from .report import (
    ADDENDUM_HEADING,
    negative_result_threshold,
    raw_arm_clause,
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
    "inspect_evals/paws",  # includes below 0.21; pattern from 0.21 (#2334)
    "inspect_evals/drop",  # f1
)

#: The close-out list: the 45 countable tasks of the 58 reachable on 0.20.0,
#: fixed by name in PREREGISTRATION.md section 11 before any 0.24.0 result. The
#: other 13 each carry a ``not_counted`` row in ``rulings.jsonl``, and any task
#: given such a row later is dropped by ``closeout_task_list`` -- so a ruling
#: against ``lab_bench`` is data, not an edit here. No task is ever added.
CLOSEOUT_TASKS: tuple[str, ...] = (
    # The preregistered twenty (section 6), in its order.
    "inspect_evals/vstar_bench_spatial_relationship_reasoning",
    "inspect_evals/sec_qa_v2",
    "inspect_evals/sec_qa_v2_5_shot",
    "inspect_evals/vstar_bench_attribute_recognition",
    "inspect_evals/musr",
    "inspect_evals/pre_flight",
    "inspect_evals/onet_m6",
    "inspect_evals/wmdp_chem",
    "inspect_evals/pubmedqa",
    "inspect_evals/truthfulqa",
    "inspect_evals/arc_challenge",
    "inspect_evals/commonsense_qa",
    "inspect_evals/winogrande",
    "inspect_evals/wmdp_bio",
    "inspect_evals/gsm8k",
    "inspect_evals/arc_easy",
    "inspect_evals/boolq",
    "inspect_evals/race_h",
    "inspect_evals/paws",
    "inspect_evals/drop",
    # choice(), 8
    "inspect_evals/bbq",
    "inspect_evals/hellaswag",
    "inspect_evals/mmlu_0_shot",
    "inspect_evals/mmlu_5_shot",
    "inspect_evals/mmlu_pro",
    "inspect_evals/sec_qa_v1",
    "inspect_evals/sec_qa_v1_5_shot",
    "inspect_evals/wmdp_cyber",
    # other scorers, 9
    "inspect_evals/aime2024",
    "inspect_evals/aime2025",
    "inspect_evals/aime2026",
    "inspect_evals/squad",
    "inspect_evals/bbeh",
    "inspect_evals/bbeh_mini",
    "inspect_evals/bbh",
    "inspect_evals/chembench",
    "inspect_evals/macbench",
    # precision_choice(), 8: counted on the eval's own accuracy(), NOANSWER = 0
    "inspect_evals/lab_bench_cloning_scenarios",
    "inspect_evals/lab_bench_dbqa",
    "inspect_evals/lab_bench_figqa",
    "inspect_evals/lab_bench_litqa",
    "inspect_evals/lab_bench_protocolqa",
    "inspect_evals/lab_bench_seqqa",
    "inspect_evals/lab_bench_suppqa",
    "inspect_evals/lab_bench_tableqa",
)

#: The model-graded arm's first sweep, fixed by ``PREREGISTRATION.md`` section 8A.
#:
#: The generated inventory classifies **27** tasks as ``model_graded``. Eight of
#: them are runnable; the other 19 are excluded and counted -- 15 fetch their
#: dataset from a URL or a repository at run time, two are over the 1.00 GiB disk
#: cap (``mmmu_open`` at 3.41 GiB), and one (``xstest``) is gated.
#:
#: Until 2026-09-17 ``sweep --graded`` passed no task list, so the graded arm
#: defaulted to all 27: nine ``agie_*`` URL-fetching tasks, ``mmmu_open`` and
#: ``xstest`` included. The preregistered denominator is 8, so the eight are
#: named here, in the order the preregistration lists them, and passed
#: explicitly. ``--tasks`` still overrides.
GRADED_FIRST_SWEEP: tuple[str, ...] = (
    "inspect_evals/frontierscience",
    "inspect_evals/moru",
    "inspect_evals/fortress_adversarial",
    "inspect_evals/fortress_benign",
    "inspect_evals/mask",
    "inspect_evals/coconot",
    "inspect_evals/uccb",
    "inspect_evals/sosbench",
)

#: The judge-disagreement control's task. The prior published in the
#: preregistration -- 13 of 111 comparable cells -- was measured on this task and
#: on no other, so the control has to run on it or say that it did not. The arm
#: used to run the control on ``tasks[0]``, whatever happened to sort first.
DISAGREEMENT_TASK = "inspect_evals/coconot"

#: Samples per task per member on the graded arm. Preregistered.
GRADED_CAP = 100

#: Default budgets. A smoke run is exploratory and cheap; the real arm is
#: deliberately capped low enough that an accident cannot empty a grant.
GRADED_BUDGET_SMOKE = 5.0
GRADED_BUDGET_REAL = 30.0

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


def closeout_task_list(rules: Sequence[Any]) -> list[str]:
    """``CLOSEOUT_TASKS`` minus every task a ``not_counted`` row names."""
    from .rulings import not_counted

    dropped = {r.task for r in not_counted(rules)}
    return [name for name in CLOSEOUT_TASKS if name not in dropped]


def _resolve_task_list(args: argparse.Namespace) -> list[str]:
    if getattr(args, "closeout", False):
        from .rulings import load_rulings

        # The list is fixed by section 11. Nothing narrows or caps it here.
        if args.tasks or args.first_sweep or getattr(args, "smoke_set", False):
            raise SystemExit(
                "--closeout fixes its own task list; it takes no --tasks, "
                "--first-sweep or --smoke-set"
            )
        if args.limit is not None:
            raise SystemExit(
                "--closeout sweeps whole datasets; it refuses --limit, because a "
                "capped run is not the run section 11 describes"
            )
        if getattr(args, "graded", False):
            raise SystemExit(
                "--closeout does not run the graded arm: it stays on 0.20.0 and is "
                "not re-run (PREREGISTRATION.md section 11.3)"
            )
        return closeout_task_list(load_rulings(pathlib.Path(args.rulings)))
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
    raise SystemExit("sweep needs --tasks, --first-sweep, --smoke-set or --closeout")


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


# --------------------------------------------------------------------------
# The close-out gate
#
# Section 11 fixes the close-out list, the pin and the seed after the 17 Sep
# results existed and before any 0.24.0 result. A commit date is set by its
# author, so "before" has to be checked against something the author cannot
# set: the addendum has to be on origin, where the push time is the server's.
# `sweep --closeout` therefore refuses unless all three hold, and stamps the
# addendum's commit so every generated file can print it.
# --------------------------------------------------------------------------

#: Where "on origin" is checked, locally. A stale fetch can only make the gate
#: refuse, never pass something that is not there.
ADDENDUM_REMOTE_REF = "origin/master"


def _git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def addendum_commit(
    repo: pathlib.Path | None = None,
    heading: str = ADDENDUM_HEADING,
    filename: str = PREREGISTRATION_FILENAME,
) -> str | None:
    """The commit that added section 11's heading, or None.

    ``git log -S`` lists the commits that changed how often the string occurs;
    the earliest is the one that introduced it.
    """
    proc = _git(
        repo or pathlib.Path.cwd(),
        "log", f"-S{heading}", "--reverse", "--format=%H", "--", filename,
    )
    if proc is None or proc.returncode != 0:
        return None
    hashes = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return hashes[0] if hashes else None


def check_addendum_gate(
    repo: pathlib.Path | None = None,
    heading: str = ADDENDUM_HEADING,
    filename: str = PREREGISTRATION_FILENAME,
    remote_ref: str = ADDENDUM_REMOTE_REF,
) -> str:
    """Return the addendum commit, or raise SystemExit naming what is missing."""
    repo = repo or pathlib.Path.cwd()

    def refuse(why: str) -> SystemExit:
        return SystemExit(
            f"refusing to run the close-out sweep.\n\n  {why}\n\n"
            f"Section 11 has to be committed, unmodified in the working tree, and on\n"
            f"{remote_ref} before any close-out result exists, so that the push time\n"
            f"on the server dates it. Commit it, `git push`, then re-run this command."
        )

    shown = _git(repo, "show", f"HEAD:{filename}")
    if shown is None or shown.returncode != 0 or heading not in shown.stdout:
        raise refuse(f"{filename} at HEAD has no {heading!r}.")
    diff = _git(repo, "diff", "--quiet", "HEAD", "--", filename)
    if diff is None or diff.returncode != 0:
        raise refuse(f"{filename} has uncommitted changes.")
    commit = addendum_commit(repo, heading, filename)
    if not commit:
        raise refuse(f"no commit in history adds {heading!r}.")
    on_origin = _git(repo, "merge-base", "--is-ancestor", commit, remote_ref)
    if on_origin is None or on_origin.returncode != 0:
        raise refuse(f"the addendum commit {commit[:12]} is not on {remote_ref}.")
    return commit


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
    closeout = bool(getattr(args, "closeout", False))
    # Section 11 has to be on origin before a close-out result exists. A smoke
    # run is not a result, and is exempt here exactly as from the gate above.
    addendum = check_addendum_gate() if closeout and not smoke else None

    tasks = _resolve_task_list(args)
    if smoke:
        print(f"SMOKE run into {out}/ -- exempt from the ordering gate, not a result")
    else:
        print(f"preregistration committed at {prereg_commit[:12]}; proceeding")
    if addendum:
        print(f"close-out addendum committed at {addendum[:12]} and on {ADDENDUM_REMOTE_REF}")
    print(f"sweeping {len(tasks)} tasks into {out}/")
    runs, floors = _sweep(tasks, args.limit)

    payload: dict[str, Any] = {
        "schema": 2,
        # Selects the arm's own preregistered threshold in `report`. Payloads
        # written before 2026-10-10 carry no key and are read as deterministic.
        "arm": "deterministic",
        "pins": installed_pins(),
        "battery_fingerprint": battery_fingerprint(),
        # The battery plus the load's shuffle seed. Kept apart from
        # battery_fingerprint, which every graded cache key hashes.
        "run_fingerprint": run_fingerprint(),
        "shuffle_seed": SHUFFLE_SEED,
        "limit": args.limit,
        "tasks": list(tasks),
        "closeout": closeout,
        "digest": sweep_digest(runs),
        # One per task, at the top level: `report --repeat` compares these to
        # name the tasks two runs disagree on. A key on each floor would not
        # load back, since TaskFloor(**row) takes no unknown field.
        "task_digests": task_digests(runs),
        "smoke": smoke,
        "preregistration_path": PREREGISTRATION_FILENAME,
        "preregistration_commit": prereg_commit,
        # Recorded, but deliberately absent from every generated .md, so that two
        # sweeps produce byte-identical markdown.
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "runs": [r.to_dict() for r in runs],
        "floors": [f.to_dict() for f in floors],
    }
    if addendum:
        # Present only on a gated close-out run; its presence is what tells the
        # report that section 11 was on origin first.
        payload["addendum_commit"] = addendum
    sweep_path = write_sweep(payload, out / "sweep.json")
    print(f"\nwrote {sweep_path}")
    print(f"digest {payload['digest'][:16]}")

    flagged, denom = flag_rate(floors)
    flagged_raw, _ = flag_rate(floors, arm="raw")
    print(f"flag rate before rulings: {flagged} of {denom} rendered, {flagged_raw} of {denom} raw")
    n_collisions = collision_count(floors)
    if n_collisions:
        print(
            f"  of which {n_collisions} rest on the format_only/majority template "
            "collision (marked, not removed)"
        )

    if not args.no_report:
        # A close-out sweep writes no README. The close-out README is written
        # only by `report --out results --repeat ...`, once both runs exist.
        written = _regenerate(
            out, pathlib.Path(args.rulings), payload, readme=not smoke and not closeout
        )
        for path in written:
            print(f"wrote {path}")

    # The graded arm, when asked for, runs after the deterministic one and writes
    # its own payload beside it. Two arms, two files, never mixed into one rate.
    if getattr(args, "graded", False):
        print("\n" + "=" * 62)
        print("graded arm")
        print("=" * 62)
        graded_out = out / "graded"
        graded_args = argparse.Namespace(
            tier=getattr(args, "tier", "standard"),
            tasks=None,
            # A first sweep of the deterministic arm means a first sweep of the
            # graded one: the preregistered eight, not every task the inventory
            # marks model_graded.
            first_sweep=bool(getattr(args, "first_sweep", False)),
            limit_tasks=args.graded_limit_tasks,
            out=str(graded_out),
            rulings=args.rulings,
            no_report=args.no_report,
            grader=args.grader,
            second_grader=args.second_grader,
            disagreement=args.disagreement,
            disagreement_task=getattr(args, "disagreement_task", None),
            cap=args.cap,
            budget_usd=args.budget_usd,
            price_in=args.price_in,
            price_out=args.price_out,
        )
        cmd_graded(graded_args)
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
    repeat: dict[str, Any] | None = None,
) -> list[pathlib.Path]:
    return write_all(
        payload,
        out,
        rulings,
        inventory=_load_inventory(out),
        # A smoke run never rewrites the README. Its numbers are not results.
        readme_path=pathlib.Path("README.md") if readme else None,
        repeat=repeat,
    )


# --------------------------------------------------------------------------
# graded arm
# --------------------------------------------------------------------------


def graded_task_names(out: pathlib.Path) -> list[str]:
    """The tasks the generated inventory classified as model-graded."""
    rows = _load_inventory(out) or []
    return sorted(
        row["name"] for row in rows if row.get("exclusion_reason") == "model_graded"
    )


def resolve_graded_task_list(args: argparse.Namespace) -> tuple[list[str], str]:
    """``(tasks, where the list came from)`` for the graded arm.

    Three sources, in precedence order: an explicit ``--tasks``, the
    preregistered eight under ``--first-sweep``, and -- only when neither is
    given -- every task the inventory marks ``model_graded``. That last one is
    the 27, which is not the preregistered denominator and is announced as such.
    """
    if args.tasks:
        tasks: list[str] = []
        for item in args.tasks:
            tasks.extend(p.strip() for p in item.split(",") if p.strip())
        return tasks, "--tasks, stated on the command line"

    if getattr(args, "first_sweep", False):
        tasks = list(GRADED_FIRST_SWEEP)
        source = "GRADED_FIRST_SWEEP, the preregistered eight"
    else:
        tasks = graded_task_names(DEFAULT_RESULTS)
        source = "the inventory's model_graded class"
    if getattr(args, "limit_tasks", None):
        tasks = tasks[: args.limit_tasks]
    return tasks, source


def _apply_price_overrides(grader: Any, args: argparse.Namespace) -> Any:
    from dataclasses import replace

    price_in = getattr(args, "price_in", None)
    price_out = getattr(args, "price_out", None)
    if price_in is None and price_out is None:
        return grader
    if price_in is None or price_out is None:
        raise SystemExit("--price-in and --price-out must be given together")
    return replace(
        grader,
        price_in_per_mtok=price_in,
        price_out_per_mtok=price_out,
        price_source=f"stated on the command line: ${price_in} in / ${price_out} out per MTok",
    )


def _print_keys() -> dict[str, bool]:
    from .graded import detect_keys

    keys = detect_keys()
    print(
        "api keys present: "
        + ", ".join(f"{name}={'yes' if present else 'no'}" for name, present in keys.items())
    )
    return keys


def run_graded(
    tasks: Sequence[str], out: pathlib.Path, args: argparse.Namespace
) -> tuple[list[TaskRun], list[Any], dict[str, Any]]:
    """Drive the graded arm over the given tasks. Returns (runs, floors, metadata)."""
    from .battery import BATTERY
    from .drive import resolve_task, task_samples
    from .graded import (
        BudgetExceeded,
        CostEstimate,
        GradedCache,
        RefusalLog,
        arms_for_template,
        choose_grader,
        choose_second_grader,
        disagreement_from_cache,
        enforce_run_budget,
        grade_task_async,
        project_run,
    )

    keys = _print_keys()
    grader = _apply_price_overrides(choose_grader(args.grader), args)
    print(f"grader: {grader.model} (family {grader.family})")
    if grader.is_mock:
        print(
            "  WARNING: no API key was found, so the grader is mockllm/model.\n"
            "  This exercises the plumbing ONLY. A mock grader is not evidence about\n"
            "  any eval. Every row it writes carries its model id so the distinction\n"
            "  survives into the results files."
        )

    cache = GradedCache.load(out / "graded_cache.jsonl")
    refusals = RefusalLog(out / "refusals.jsonl")

    # The whole arm's estimate, summed BEFORE the first provider call. The
    # per-task guard inside grade_task_async stays: it is the one that stops a
    # single task running away mid-arm. This one stops eight tasks each under
    # the budget from costing eight times it. Loading the datasets to get here
    # costs time and disk, never money.
    print("\n  projecting the whole arm before any provider call:")
    projection = project_run(
        tasks, grader, cap=args.cap, cache=cache,
        tier=getattr(args, "tier", "standard"),
    )
    print(projection.describe())
    for name, reason in projection.excluded:
        print(f"    excluded: {name}: {reason}")
    if args.budget_usd is not None:
        try:
            enforce_run_budget(projection, args.budget_usd, grader)
        except BudgetExceeded as exc:
            print(f"\n{exc}", file=sys.stderr)
            raise SystemExit(EXIT_UNRUNNABLE) from None

    runs: list[TaskRun] = []
    floors: list[Any] = []
    estimates: list[CostEstimate] = []

    for name in tasks:
        print(f"\n  {name}")
        try:
            run, estimate = asyncio.run(
                grade_task_async(
                    name, grader, cap=args.cap, cache=cache,
                    refusals=refusals, budget_usd=args.budget_usd,
                    tier=getattr(args, "tier", "standard"),
                )
            )
        except BudgetExceeded as exc:
            print(f"\n{exc}", file=sys.stderr)
            raise SystemExit(EXIT_UNRUNNABLE) from None
        runs.append(run)
        estimates.append(estimate)
        if run.error:
            print(f"    FAILED: {run.error[:110]}")
            floors.extend(aggregate_run(run))
            continue
        task_floors = aggregate_run(run)
        floors.extend(task_floors)
        for floor in task_floors:
            state = (
                "FLAGGED by " + ", ".join(floor.flagged_by) if floor.flagged else "clean"
            )
            if run.routing_note:
                print(f"    routing: {run.routing_note}")
            print(
                f"    n={run.n_samples} refusals={run.n_refusals} "
                f"majority={100 * floor.majority:.1f}% "
                f"best={floor.best_member or '-'} {100 * floor.best_mean:.1f}% -> {state}"
            )

    meta: dict[str, Any] = {
        "graded": True,
        "service_tier": getattr(args, "tier", "standard"),
        "keys_present": keys,
        # What the arm was projected to cost and which tasks could not be loaded,
        # recorded whether or not they later failed for some other reason.
        "run_projection": projection.to_dict(),
        "grader": grader.to_dict(),
        "cap": args.cap,
        "budget_usd": args.budget_usd,
        "cache_hits": cache.hits,
        "cache_misses": cache.misses,
        "n_refusals": sum(r.n_refusals for r in runs),
        "refusals_path": str(out / "refusals.jsonl"),
        "cost_estimate": {
            "n_calls": sum(e.n_calls for e in estimates),
            "input_tokens": sum(e.input_tokens for e in estimates),
            "output_tokens": sum(e.output_tokens for e in estimates),
            "usd": (
                round(sum(e.usd for e in estimates if e.usd is not None), 4)
                if estimates and all(e.priced for e in estimates)
                else None
            ),
        },
    }

    # Judge-disagreement control: one named task, a grader from a different
    # family. The task is named rather than taken as tasks[0]: the prior this
    # control replaces was measured on coconot, and a control run on some other
    # task answers a different question while printing the same field name.
    if args.second_grader or args.disagreement:
        second_spec = args.second_grader
        second = choose_second_grader(grader, second_spec)
        if second is not None:
            second = _apply_price_overrides(second, args)
        target = getattr(args, "disagreement_task", None) or DISAGREEMENT_TASK
        if second is None or not tasks:
            print("\n  judge-disagreement control skipped: no second grader available")
            meta["disagreement"] = {
                "skipped": "no grader from a different family is available"
            }
        elif target not in tasks:
            why = (
                f"the control task {target} is not in this run's task list "
                f"({', '.join(tasks) or 'empty'}). The control is not silently "
                "moved to another task: the published prior was measured on "
                f"{DISAGREEMENT_TASK} and a rate measured elsewhere is not "
                "comparable with it. Add it to --tasks, or name a different "
                "control task with --disagreement-task."
            )
            print(f"\n  judge-disagreement control SKIPPED: {why}")
            meta["disagreement"] = {"skipped": why, "task": target}
        else:
            print(f"\n  judge-disagreement control: {target} with {second.model}")
            run_b, _ = asyncio.run(
                grade_task_async(
                    target, second, cap=args.cap, cache=cache,
                    refusals=refusals, budget_usd=args.budget_usd,
                    tier=getattr(args, "tier", "standard"),
                )
            )
            samples = task_samples(resolve_task(target), limit=args.cap)
            dis = disagreement_from_cache(
                target, run_b.scorers, samples, list(BATTERY),
                arms_for_template(run_b.answer_template), grader, second, cache,
            )
            print(
                f"    disagreement {dis.n_disagree}/{dis.n_compared} "
                f"= {100 * dis.rate:.1f}% "
                f"[{100 * (dis.ci_low or 0):.1f}%, {100 * (dis.ci_high or 0):.1f}%]"
            )
            if dis.n_uncomparable:
                by_reason = ", ".join(
                    f"{reason} {n}"
                    for reason, n in sorted(
                        dis.uncomparable_by_reason.items(), key=lambda kv: -kv[1]
                    )
                )
                print(
                    f"    uncomparable {dis.n_uncomparable} cells "
                    f"(not compared as zeros): {by_reason}"
                )
            d = dis.to_dict()
            d["routing_note"] = run_b.routing_note
            d["served_provider"] = run_b.served_provider
            d["served_counts"] = run_b.served_counts
            # The second grader's own spend, kept rather than discarded. It is
            # what THIS run paid: a fully cached re-run reports 0 calls and $0,
            # which is a fact about the run and not the arm's lifetime cost.
            # Cells answered from cache were paid for by an earlier run, and
            # that payment is recorded nowhere.
            usage = run_b.measured_usage or {}
            d["measured_usage"] = usage
            print(
                f"    measured this run: {usage.get('calls', 0)} provider calls, "
                f"${usage.get('measured_usd', 0.0):.4f}"
            )
            if run_b.routing_note:
                print(f"    routing: {run_b.routing_note}")
            meta["disagreement"] = d

    return runs, floors, meta


def cmd_graded(args: argparse.Namespace) -> int:
    out = pathlib.Path(args.out)
    prereg_commit = check_ordering_gate(out)
    smoke = is_smoke_output(out)

    tasks, source = resolve_graded_task_list(args)

    # Printed before the first provider call, so the operator sees what is about
    # to be driven rather than finding out from the bill.
    print(f"graded task list ({source}): {len(tasks)} task(s)")
    for name in tasks:
        print(f"  {name}")
    if source == "the inventory's model_graded class":
        print(
            "  WARNING: this is every task the inventory marks model_graded, not "
            "the preregistered eight.\n"
            "  It includes URL-fetching tasks, a dataset over the disk cap and a "
            "gated one.\n"
            f"  Use --first-sweep for the {len(GRADED_FIRST_SWEEP)} the "
            "preregistration names, or --tasks to state a list."
        )

    if smoke:
        print(f"SMOKE graded run into {out}/ -- exempt from the ordering gate, not a result")
    else:
        print(f"preregistration committed at {prereg_commit[:12]}; proceeding")

    runs, floors, meta = run_graded(tasks, out, args)

    payload: dict[str, Any] = {
        "schema": 2,
        "arm": "graded",
        "pins": installed_pins(),
        "battery_fingerprint": battery_fingerprint(),
        "limit": args.cap,
        "tasks": list(tasks),
        "digest": sweep_digest(runs),
        "smoke": smoke,
        "preregistration_path": PREREGISTRATION_FILENAME,
        "preregistration_commit": prereg_commit,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "runs": [r.to_dict() for r in runs],
        "floors": [f.to_dict() for f in floors],
        **meta,
    }
    sweep_path = write_sweep(payload, out / "sweep.json")
    print(f"\nwrote {sweep_path}")
    flagged, denom = flag_rate(floors)
    print(f"graded flag rate before rulings: {flagged} of {denom}")
    print(f"refusals recorded: {meta['n_refusals']} -> {meta['refusals_path']}")

    if not args.no_report:
        written = _regenerate(out, pathlib.Path(args.rulings), payload, readme=not smoke)
        for path in written:
            print(f"wrote {path}")
    return EXIT_OK


def cmd_estimate(args: argparse.Namespace) -> int:
    """Print the graded arm's cost estimate without calling anything."""
    from .battery import BATTERY, detect_template
    from .drive import label_set, resolve_task, task_samples
    from .graded import choose_grader, estimate_cost, grader_active

    _print_keys()
    grader = _apply_price_overrides(choose_grader(args.grader), args)
    print(f"grader for the estimate: {grader.model}")
    print(f"price source: {grader.price_source}")
    print()

    tasks, source = resolve_graded_task_list(args)
    print(f"task list ({source}): {len(tasks)} task(s)")
    print()
    total_calls = total_in = total_out = 0
    total_usd = 0.0
    priced = True
    failed: list[tuple[str, str]] = []
    loaded = 0

    with grader_active(grader):
        for name in tasks:
            try:
                samples = task_samples(resolve_task(name), limit=args.cap)
            except Exception as exc:
                failed.append((name, f"{type(exc).__name__}: {exc}"[:90]))
                print(f"  {name:<46} could not load")
                continue
            loaded += 1
            labels = label_set(samples)
            template = detect_template(samples[0]).name if samples else "bare"
            est = estimate_cost(
                samples, list(BATTERY), labels, grader, template, args.cap,
                tier=getattr(args, "tier", "standard"),
            )
            total_calls += est.n_calls
            total_in += est.input_tokens
            total_out += est.output_tokens
            if est.priced and est.usd is not None:
                total_usd += est.usd
            else:
                priced = False
            print(
                f"  {name:<46} n={len(samples):<4} calls={est.n_calls:>6,}  "
                + (f"${est.usd:,.2f}" if est.usd is not None else "$?")
            )

    print()
    print(f"tasks loaded    : {loaded} of {len(tasks)}")
    print(f"grading calls   : {total_calls:,}")
    print(f"input tokens    : {total_in:,}")
    print(f"output tokens   : {total_out:,}")
    print(
        "estimated total : "
        + (f"${total_usd:,.2f}" if priced else "UNKNOWN (grader has no verified price)")
    )
    if failed:
        print(f"could not load  : {len(failed)}")
        for name, why in failed:
            print(f"    {name}: {why}")
    return EXIT_OK


def cmd_report(args: argparse.Namespace) -> int:
    out = pathlib.Path(args.out)
    sweep_path = out / "sweep.json"
    if not sweep_path.exists():
        print(
            f"no sweep payload at {sweep_path}; run `evalfloor sweep` first",
            file=sys.stderr,
        )
        return EXIT_UNRUNNABLE
    from .report import prepare_floors, repeat_mismatch
    from .rulings import load_rulings

    payload = read_sweep(sweep_path)
    repeat = None
    if getattr(args, "repeat", None):
        repeat_path = pathlib.Path(args.repeat)
        if not repeat_path.exists():
            print(f"no second payload at {repeat_path}", file=sys.stderr)
            return EXIT_UNRUNNABLE
        repeat = read_sweep(repeat_path)
        problems = repeat_mismatch(payload, repeat)
        if problems:
            # Refused before anything is written: a second run under other pins,
            # another fingerprint or another list is not a determinism check.
            print(f"refusing --repeat {repeat_path}:", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return EXIT_UNRUNNABLE
    readme = not payload.get("smoke", False) and not args.no_readme
    written = _regenerate(
        out, pathlib.Path(args.rulings), payload, readme=readme, repeat=repeat
    )
    # The same floors write_all read: one preparation, never a second recipe.
    floors, after, _, _, moved = prepare_floors(
        payload, load_rulings(pathlib.Path(args.rulings)), repeat
    )
    if repeat is not None:
        if moved:
            print(f"not run, non-deterministic across the two runs: {', '.join(moved)}")
        else:
            print(f"two runs, every task digest identical ({len(payload['task_digests'])} tasks)")
    if readme and pathlib.Path("README.md") not in written:
        print(
            "README.md not rewritten: once section 11 is stamped, only "
            "`report --out results --repeat <second sweep.json>` writes it"
        )
    flagged, denom = flag_rate(floors)
    flagged_after, _ = flag_rate(after)
    for path in written:
        print(f"wrote {path}")
    print(f"{flagged} of {denom} flagged before rulings (rendered arm)")
    n_collisions = collision_count(floors)
    if n_collisions:
        print(
            f"{n_collisions} of those rest on the format_only/majority template "
            "collision (marked, not removed)"
        )
    print(f"{flagged_after} of {denom} flagged after rulings (rendered arm)")
    # The matrix's own sentence, so an arm that never ran prints "not run".
    print(raw_arm_clause(after, bold=False))
    if payload.get("smoke"):
        print("smoke payload: README.md was not rewritten")
    # Per arm, and against the count the headline reports: after rulings.
    threshold = negative_result_threshold(payload)
    if denom and flagged_after < threshold:
        print(
            f"note: below the preregistered negative-result threshold of "
            f"{threshold}"
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


def add_grader_args(parser: argparse.ArgumentParser, default_budget: float) -> None:
    """Grader selection, the sample cap and the cost guard, shared by subcommands."""
    parser.add_argument(
        "--grader",
        default=None,
        help="grader model spec; overrides EVALFLOOR_GRADER and key detection",
    )
    parser.add_argument(
        "--second-grader",
        default=None,
        help="grader from a different family, for the judge-disagreement control",
    )
    parser.add_argument(
        "--disagreement",
        action="store_true",
        help=f"run the judge-disagreement control on {DISAGREEMENT_TASK}",
    )
    parser.add_argument(
        "--disagreement-task",
        default=None,
        help=(
            f"task the judge-disagreement control runs on (default "
            f"{DISAGREEMENT_TASK}, the task the published prior was measured on). "
            "The control is skipped, with the reason printed, when this task is "
            "not in the run's task list."
        ),
    )
    parser.add_argument(
        "--cap",
        type=int,
        default=GRADED_CAP,
        help=f"samples per task per member (default {GRADED_CAP})",
    )
    parser.add_argument(
        "--budget-usd",
        type=float,
        default=default_budget,
        help=f"refuse to run when the estimate exceeds this (default {default_budget})",
    )
    parser.add_argument(
        "--price-in",
        type=float,
        default=None,
        help="USD per MTok input, for a grader this project has no verified price for",
    )
    parser.add_argument(
        "--price-out", type=float, default=None, help="USD per MTok output"
    )
    parser.add_argument(
        "--tier",
        choices=("standard", "flex"),
        default="standard",
        help=(
            "OpenAI service tier. standard (default) is full price and about "
            "12.7 calls/min; flex is 50%% off and about 4 calls/min, which turns "
            "the 8,000-call arm into a ~33-hour run"
        ),
    )


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
    p_sweep.add_argument(
        "--closeout",
        action="store_true",
        help=(
            f"sweep the {len(CLOSEOUT_TASKS)} close-out tasks, minus any with a "
            "not_counted ruling; outside results/smoke/ it refuses unless "
            "PREREGISTRATION.md section 11 is committed and on origin. No --limit."
        ),
    )
    p_sweep.add_argument("--out", default=str(DEFAULT_RESULTS))
    p_sweep.add_argument("--rulings", default=str(DEFAULT_RULINGS))
    p_sweep.add_argument("--limit", type=int, default=None, help="cap samples per task")
    p_sweep.add_argument("--no-report", action="store_true")
    p_sweep.add_argument(
        "--graded",
        action="store_true",
        help="also run the model-graded arm into <out>/graded/ after the deterministic one",
    )
    p_sweep.add_argument(
        "--graded-limit-tasks", type=int, default=None,
        help="with --graded, use only the first N model-graded tasks",
    )
    add_grader_args(p_sweep, GRADED_BUDGET_REAL)
    p_sweep.set_defaults(func=cmd_sweep)

    p_report = sub.add_parser(
        "report", help="regenerate the markdown and the README from a sweep payload"
    )
    p_report.add_argument("--out", default=str(DEFAULT_RESULTS))
    p_report.add_argument("--rulings", default=str(DEFAULT_RULINGS))
    p_report.add_argument(
        "--no-readme", action="store_true", help="leave README.md alone"
    )
    p_report.add_argument(
        "--repeat",
        default=None,
        help=(
            "a second run's sweep.json, from a separate process; tasks the two "
            "runs disagree on are reported as not run: non-deterministic. Refused "
            "if its pins, run fingerprint or task list differ"
        ),
    )
    p_report.set_defaults(func=cmd_report)

    p_readme = sub.add_parser(
        "readme", help="write the placeholder README, before any sweep has run"
    )
    p_readme.add_argument("--out", default=str(DEFAULT_RESULTS))
    p_readme.set_defaults(func=cmd_readme)

    p_graded = sub.add_parser(
        "graded", help="drive the model-graded tasks with one cheap judge"
    )
    p_graded.add_argument("--tasks", nargs="*", help="task names; default is all model-graded")
    p_graded.add_argument(
        "--first-sweep",
        action="store_true",
        help=(
            f"use the preregistered {len(GRADED_FIRST_SWEEP)} runnable "
            "model-graded tasks rather than every task the inventory marks "
            "model_graded"
        ),
    )
    p_graded.add_argument(
        "--limit-tasks", type=int, default=None, help="use only the first N tasks"
    )
    p_graded.add_argument("--out", default=str(DEFAULT_RESULTS / "graded"))
    p_graded.add_argument("--rulings", default=str(DEFAULT_RULINGS))
    p_graded.add_argument("--no-report", action="store_true")
    add_grader_args(p_graded, GRADED_BUDGET_REAL)
    p_graded.set_defaults(func=cmd_graded)

    p_est = sub.add_parser(
        "estimate", help="print the graded arm's cost estimate without calling anything"
    )
    p_est.add_argument("--tasks", nargs="*")
    p_est.add_argument(
        "--first-sweep",
        action="store_true",
        help=f"price the preregistered {len(GRADED_FIRST_SWEEP)} rather than all 27",
    )
    p_est.add_argument(
        "--limit-tasks", type=int, default=None, help="use only the first N tasks"
    )
    p_est.add_argument("--out", default=str(DEFAULT_RESULTS))
    add_grader_args(p_est, GRADED_BUDGET_REAL)
    p_est.set_defaults(func=cmd_estimate)

    p_check = sub.add_parser(
        "check", help="exit non-zero when a content-free member reaches majority"
    )
    p_check.add_argument("task")
    p_check.add_argument("--limit", type=int, default=None)
    p_check.set_defaults(func=cmd_check)

    return parser


def load_local_env(path: pathlib.Path | None = None) -> list[str]:
    """Load ``.env`` from the working directory, without overriding the environment.

    Returns the **names** of the variables it set. Values are never returned,
    logged or printed anywhere in this project, and ``.env`` is in ``.gitignore``.

    ``python-dotenv`` is already present as a transitive dependency of
    ``inspect_ai``; the small fallback parser exists only so that a missing
    optional package can never stop the CLI from starting.

    ``override=False`` is deliberate: a variable already exported in the shell
    wins over the file, so a one-off export is never silently overwritten by a
    stale file.
    """
    import os

    path = path or pathlib.Path(".env")
    if not path.exists():
        return []

    before = set(os.environ)
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=path, override=False)
    except Exception:
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            return []
    return sorted(set(os.environ) - before)


def main(argv: Sequence[str] | None = None) -> int:
    loaded = load_local_env()
    if loaded:
        # Names only. Never values.
        print(f"loaded from .env: {', '.join(loaded)}")
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
