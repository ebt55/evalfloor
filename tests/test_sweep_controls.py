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
import json
import os
import pathlib
import subprocess

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

    The tasks are built straight through the registry, not ``resolve_task``.
    ``resolve_task`` seeds the shuffle now (defect 010), and two seeded loads
    agree with or without the sort, so through it this test would pin nothing.
    """
    from inspect_ai._util.registry import registry_create

    import inspect_evals._registry  # noqa: F401  (populates the registry)
    from evalfloor.drive import task_samples

    for name in ("inspect_evals/paws", "inspect_evals/boolq"):
        first_task = registry_create("task", name)
        second_task = registry_create("task", name)
        # The premise: unseeded, the two loads come back in different orders.
        assert [s.id for s in first_task.dataset] != [
            s.id for s in second_task.dataset
        ], f"{name}: two unseeded loads agree, so this test no longer tests the sort"
        first = [s.id for s in task_samples(first_task, limit=50)]
        second = [s.id for s in task_samples(second_task, limit=50)]
        assert first == second, f"{name}: limited subset is not stable across calls"


@pytest.mark.dataset
def test_the_smoke_set_covers_every_scorer_family_in_the_twenty() -> None:
    """If this fails the smoke set has stopped being representative.

    Version-aware. ``paws`` is the twenty's only ``includes()`` task up to
    0.20.0; from 0.21.0 (#2334) it is scored with an anchored ``pattern()``, so
    ``pattern`` takes its place and the twenty have one family fewer.
    """
    import importlib.metadata as md

    from packaging.version import Version

    if Version(md.version("inspect_evals")) < Version("0.21.0"):
        paws_family = "inspect_ai/includes"
    else:
        paws_family = "inspect_ai/pattern"

    families = set()
    for name in SMOKE_TASKS:
        run = _run_named(name, limit=1)
        assert run.error is None, f"{name}: {run.error}"
        if name == "inspect_evals/paws":
            assert run.scorers == [paws_family]
        families.update(run.scorers)
    assert families == {
        "inspect_ai/choice",
        "inspect_ai/match",
        "inspect_ai/pattern",
        "inspect_ai/f1",
        paws_family,
    }


def test_generated_markdown_is_byte_identical_for_the_fixture_sweep() -> None:
    """Determinism at the report level, with no network involved."""
    from evalfloor.report import render_matrix

    a = aggregate_run(_run(loose_eval.loose_refusal(), "evalfloor_fixtures/loose_refusal"))
    b = aggregate_run(_run(loose_eval.loose_refusal(), "evalfloor_fixtures/loose_refusal"))
    assert render_matrix(a) == render_matrix(b)


# --------------------------------------------------------------------------
# 4. The close-out: its list, its gate, its stamps
#
# None of these drives a dataset. Wherever a command runs, the sweep itself is
# stubbed, so these check what is decided before a task loads and what is
# written after.
# --------------------------------------------------------------------------

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The commit whose 58 reachable tasks section 11 splits into 45 and 13.
LIST_FIXED_AT = "316f142"


def _git_in(repo: pathlib.Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, encoding="utf-8"
    )
    assert proc.returncode == 0, f"git {' '.join(args)}: {proc.stderr}"
    return proc.stdout


def _inventory_at_list_commit() -> list[dict]:
    """The 0.20.0 inventory, read from git rather than from disk, so a later
    `evalfloor inventory` on 0.24.0 cannot move the check."""
    proc = subprocess.run(
        ["git", "show", f"{LIST_FIXED_AT}:results/task_inventory.json"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        pytest.skip(f"{LIST_FIXED_AT} is not in this clone's history")
    return json.loads(proc.stdout)


def _not_counted_rows() -> list:
    """The not_counted rows to check.

    A draft named by EVALFLOOR_NOT_COUNTED_ROWS first, then the committed rows
    in rulings.jsonl. The rows land in rulings.jsonl with section 11; until then
    these tests run against a draft and skip without one.
    """
    from evalfloor.rulings import load_rulings, not_counted

    draft = os.environ.get("EVALFLOOR_NOT_COUNTED_ROWS")
    if draft:
        return load_rulings(pathlib.Path(draft))
    committed = not_counted(load_rulings(ROOT / "rulings.jsonl"))
    if not committed:
        pytest.skip(
            "no not_counted rows yet: they land in rulings.jsonl with section 11 "
            "(set EVALFLOOR_NOT_COUNTED_ROWS to check a draft)"
        )
    return committed


def test_the_closeout_list_is_the_45_section_11_names() -> None:
    """Section 11 fixes the list by name: the preregistered twenty, then the 25
    further countable tasks reachable on 0.20.0. Nothing derives it at run time."""
    from evalfloor.cli import CLOSEOUT_TASKS
    from evalfloor.discover import TaskInfo, first_sweep_tasks

    assert len(CLOSEOUT_TASKS) == 45
    assert len(set(CLOSEOUT_TASKS)) == 45
    assert all(name.startswith("inspect_evals/") for name in CLOSEOUT_TASKS)

    # The first twenty are section 6's, in its order, as its rule computes them.
    infos = [TaskInfo(**row) for row in _inventory_at_list_commit()]
    assert list(CLOSEOUT_TASKS[:20]) == [t.name for t in first_sweep_tasks(infos)]

    short = [name.removeprefix("inspect_evals/") for name in CLOSEOUT_TASKS[20:]]
    assert short[:8] == [
        "bbq", "hellaswag", "mmlu_0_shot", "mmlu_5_shot", "mmlu_pro",
        "sec_qa_v1", "sec_qa_v1_5_shot", "wmdp_cyber",
    ]
    assert short[8:17] == [
        "aime2024", "aime2025", "aime2026", "squad", "bbeh", "bbeh_mini", "bbh",
        "chembench", "macbench",
    ]
    assert short[17:] == [
        f"lab_bench_{s}"
        for s in (
            "cloning_scenarios", "dbqa", "figqa", "litqa", "protocolqa", "seqqa",
            "suppqa", "tableqa",
        )
    ]


def test_closeout_drops_not_counted_tasks_and_refuses_a_limit(
    tmp_path, monkeypatch
) -> None:
    """A rejected lab_bench ruling is data: eight not_counted rows take the list
    from 45 to 37, and no code changes. The run is never capped or mixed."""
    import argparse

    import evalfloor.cli as cli
    from evalfloor.aggregate import task_digests
    from evalfloor.battery import SHUFFLE_SEED, battery_fingerprint, run_fingerprint

    def args(**over):
        base = dict(
            closeout=True, tasks=None, first_sweep=False, smoke_set=False,
            limit=None, graded=False, rulings=str(tmp_path / "none.jsonl"),
        )
        base.update(over)
        return argparse.Namespace(**base)

    assert cli._resolve_task_list(args()) == list(cli.CLOSEOUT_TASKS)

    lab = tmp_path / "lab.jsonl"
    lab.write_text(
        "".join(
            json.dumps(
                {
                    "task": name, "action": "not_counted",
                    "treatment": "precision_choice is not read on accuracy()",
                    "reason": "fixture", "source": "tests/test_sweep_controls.py",
                    "date": "2026-10-10", "author": "ebt55",
                }
            )
            + "\n"
            for name in cli.CLOSEOUT_TASKS
            if "lab_bench_" in name
        ),
        encoding="utf-8",
    )
    resolved = cli._resolve_task_list(args(rulings=str(lab)))
    assert len(resolved) == 37
    assert resolved == [n for n in cli.CLOSEOUT_TASKS if "lab_bench_" not in n]

    for bad in (
        dict(limit=100),
        dict(tasks=["inspect_evals/paws"]),
        dict(first_sweep=True),
        dict(smoke_set=True),
        dict(graded=True),
    ):
        with pytest.raises(SystemExit):
            cli._resolve_task_list(args(**bad))

    # Through the command, into smoke: no dataset is touched -- the one run
    # handed back is a control task -- and the payload says what kind of run it
    # was, under which fingerprint and seed, with one digest per task.
    control = _run_named("evalfloor/control_tight")
    seen: dict[str, list[str]] = {}

    def fake_sweep(tasks, limit):
        seen["tasks"] = list(tasks)
        return [control], aggregate_run(control)

    monkeypatch.setattr(cli, "_sweep", fake_sweep)
    out = tmp_path / "smoke"
    assert cli.main(
        ["sweep", "--closeout", "--out", str(out), "--rulings", str(lab), "--no-report"]
    ) == 0
    assert len(seen["tasks"]) == 37
    payload = json.loads((out / "sweep.json").read_text(encoding="utf-8"))
    assert payload["closeout"] is True
    assert payload["tasks"] == seen["tasks"]
    assert payload["battery_fingerprint"] == battery_fingerprint()
    assert payload["run_fingerprint"] == run_fingerprint()
    assert payload["shuffle_seed"] == SHUFFLE_SEED
    assert payload["task_digests"] == task_digests([control])
    assert set(payload["task_digests"]) == {"evalfloor/control_tight"}
    assert "addendum_commit" not in payload, "smoke is exempt, and stamps nothing"

    with pytest.raises(SystemExit):
        cli.main(["sweep", "--closeout", "--limit", "5", "--out", str(out)])


def test_the_draft_not_counted_rows_load_and_quote_their_sources() -> None:
    """The 13 rows section 11 commits: 4 need solver state, 3 need a judge and 6
    score behaviour. Each quotes an inspect_evals 0.20.0 file:line."""
    import re
    from collections import Counter

    rows = _not_counted_rows()
    assert len(rows) == 13
    assert all(r.action == "not_counted" for r in rows)
    assert Counter(r.treatment for r in rows) == {
        "needs solver state": 4,
        "needs a judge": 3,
        "scores behaviour, not answer correctness": 6,
    }
    for r in rows:
        assert r.source.startswith("inspect_evals 0.20.0, src/inspect_evals/"), r.task
        assert re.search(r"\.py:\d+", r.source), f"{r.task}: no file:line"
        assert r.reason and r.date and r.author == "ebt55"


def test_closeout_list_and_not_counted_rows_partition_the_58_reachable() -> None:
    """45 swept plus 13 listed is the 58 reachable on 0.20.0, with no task in
    both and none in neither. A drift test: it fails if either side moves."""
    from evalfloor.cli import CLOSEOUT_TASKS

    reachable = [row["name"] for row in _inventory_at_list_commit() if row["reachable"]]
    assert len(reachable) == 58
    listed = [r.task for r in _not_counted_rows()]
    assert len(set(listed)) == len(listed) == 13
    assert not set(CLOSEOUT_TASKS) & set(listed), "a task both swept and listed"
    assert set(CLOSEOUT_TASKS) | set(listed) == set(reachable)


def _isolated_git(tmp_path, monkeypatch) -> None:
    """No user or system git config reaches the test repository."""
    empty = tmp_path / "empty.gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "evalfloor test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.invalid")


def test_gate_refuses_without_the_addendum(tmp_path, monkeypatch) -> None:
    """`sweep --closeout` refuses until section 11 is committed, unmodified and
    on origin. The push time on the server is the one date its author cannot
    set, so committed alone is not enough."""
    import evalfloor.cli as cli
    from evalfloor.report import ADDENDUM_HEADING

    _isolated_git(tmp_path, monkeypatch)
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_in(tmp_path, "init", "--bare", "-b", "master", str(origin))
    _git_in(repo, "init", "-b", "master")
    _git_in(repo, "remote", "add", "origin", str(origin))
    prereg = repo / "PREREGISTRATION.md"
    prereg.write_text("# Preregistration\n\n## 1. Threshold\n", encoding="utf-8")
    _git_in(repo, "add", "PREREGISTRATION.md")
    _git_in(repo, "commit", "-m", "preregistration")
    _git_in(repo, "push", "origin", "master")

    def refusal() -> str:
        with pytest.raises(SystemExit) as caught:
            cli.check_addendum_gate(repo)
        return str(caught.value)

    def never(*_a, **_k):
        raise AssertionError("a refused close-out must not load a single task")

    # 1. No section 11 at all -- and through the command, before any task loads.
    assert ADDENDUM_HEADING in refusal()
    assert cli.addendum_commit(repo) is None
    monkeypatch.chdir(repo)
    monkeypatch.setattr(cli, "_sweep", never)
    with pytest.raises(SystemExit):
        cli.main(["sweep", "--closeout", "--out", str(repo / "results")])

    # 2. Committed, not pushed.
    with prereg.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{ADDENDUM_HEADING} -- written before any 0.24.0 result\n")
    _git_in(repo, "commit", "-am", "section 11")
    added = _git_in(repo, "rev-parse", "HEAD").strip()
    assert cli.addendum_commit(repo) == added
    assert "not on origin/master" in refusal()

    # 3. Pushed: the gate passes, and returns the commit that added the heading.
    _git_in(repo, "push", "origin", "master")
    assert cli.check_addendum_gate(repo) == added

    # And an edit after the push is refused: the file is not the one on origin.
    with prereg.open("a", encoding="utf-8") as fh:
        fh.write("an edit after the push\n")
    assert "uncommitted changes" in refusal()
    _git_in(repo, "checkout", "--", "PREREGISTRATION.md")

    # A gated run stamps the addendum, prints both hashes and writes no README.
    monkeypatch.setattr(cli, "_sweep", lambda tasks, limit: ([], []))
    assert cli.main(
        [
            "sweep", "--closeout", "--out", str(repo / "results"),
            "--rulings", str(repo / "rulings.jsonl"),
        ]
    ) == 0
    payload = json.loads((repo / "results" / "sweep.json").read_text(encoding="utf-8"))
    assert payload["addendum_commit"] == added
    assert payload["closeout"] is True
    first = _git_in(repo, "log", "--reverse", "--format=%H", "--", "PREREGISTRATION.md")
    assert payload["preregistration_commit"] == first.split()[0]
    matrix = (repo / "results" / "floor_matrix.md").read_text(encoding="utf-8")
    assert payload["preregistration_commit"][:12] in matrix
    assert added[:12] in matrix
    assert f"git log -S'{ADDENDUM_HEADING}' --reverse" in matrix
    assert not (repo / "README.md").exists(), "a close-out sweep writes no README"


def test_provenance_prints_the_run_fingerprint_and_seed_only_when_stamped() -> None:
    """The committed 0.20.0 payloads carry neither, and render as they did."""
    from evalfloor.report import _prereg_block, provenance_block, read_sweep

    for path in (ROOT / "results" / "sweep.json", ROOT / "results" / "graded" / "sweep.json"):
        old = read_sweep(path)
        if "run_fingerprint" in old:
            continue  # a payload written after the stamp
        block = "\n".join(provenance_block(old, old.get("digest")))
        assert "run fingerprint" not in block
        assert "shuffle seed" not in block
        assert "close-out addendum" not in "\n".join(_prereg_block(old))

    new = {"pins": {}, "run_fingerprint": "abcdef012345", "shuffle_seed": 42}
    block = "\n".join(provenance_block(new))
    assert "| run fingerprint | `abcdef012345` |" in block
    assert "| shuffle seed | 42 |" in block


# --------------------------------------------------------------------------
# 5. Determinism across two runs (section 11.7), read by the report
# --------------------------------------------------------------------------


def _two_task_payload(**over) -> dict:
    """A close-out-shaped payload over the two committed control tasks."""
    from evalfloor.aggregate import aggregate, task_digests

    runs = [
        _run_named("evalfloor/control_tight"),
        _run_named("evalfloor/control_loose"),
    ]
    payload = {
        "arm": "deterministic",
        "schema": 2,
        "pins": {"inspect_ai": "0.3.263", "inspect_evals": "0.24.0"},
        "battery_fingerprint": "b019ebb6ecee",
        "run_fingerprint": "f1f1f1f1f1f1",
        "shuffle_seed": 42,
        "tasks": [r.task for r in runs],
        "digest": sweep_digest(runs),
        "task_digests": task_digests(runs),
        "smoke": False,
        "runs": [],
        "floors": [f.to_dict() for f in aggregate(runs)],
    }
    payload.update(over)
    return payload


def test_a_repeat_with_other_pins_fingerprint_or_tasks_is_refused(
    tmp_path, capsys
) -> None:
    """A second run under other pins, another fingerprint or another list is a
    different measurement, not a determinism check."""
    from evalfloor.cli import main
    from evalfloor.report import repeat_mismatch, write_all, write_sweep

    first = _two_task_payload()
    assert repeat_mismatch(first, _two_task_payload()) == []
    for over in (
        {"pins": {"inspect_ai": "0.3.263", "inspect_evals": "0.20.0"}},
        {"run_fingerprint": "000000000000"},
        {"tasks": ["evalfloor/control_tight"]},
        {"task_digests": {}},
    ):
        second = _two_task_payload(**over)
        assert repeat_mismatch(first, second), over
        with pytest.raises(ValueError, match="not a repeat"):
            write_all(first, tmp_path / "w", tmp_path / "r.jsonl", repeat=second)

    out = tmp_path / "results"
    write_sweep(first, out / "sweep.json")
    write_sweep(_two_task_payload(run_fingerprint="000000000000"), tmp_path / "b.json")
    code = main(
        ["report", "--out", str(out), "--no-readme", "--rulings", str(tmp_path / "r.jsonl"),
         "--repeat", str(tmp_path / "b.json")]
    )
    assert code != 0
    assert "run_fingerprint differ" in capsys.readouterr().err
    assert not (out / "floor_matrix.md").exists(), "refused before anything is written"


def test_two_payloads_that_differ_in_one_task_render_it_not_run(tmp_path, capsys) -> None:
    """The guide's B6 test. A task whose digests differ, or that errored in only
    one run, leaves every rate as "not run: non-deterministic"; the other task
    is untouched."""
    from evalfloor.aggregate import flag_rate
    from evalfloor.cli import main
    from evalfloor.report import (
        NOT_RUN_NONDETERMINISTIC,
        floors_from_payload,
        nondeterministic_tasks,
        write_sweep,
    )

    first = _two_task_payload()
    assert flag_rate(floors_from_payload(first)) == (1, 2)
    assert nondeterministic_tasks(first, _two_task_payload()) == []

    moved = dict(first["task_digests"], **{"evalfloor/control_loose": "0" * 64})
    second = _two_task_payload(task_digests=moved)
    assert nondeterministic_tasks(first, second) == ["evalfloor/control_loose"]

    # An error in one run only also moves the task, digests aside.
    errored = _two_task_payload()
    errored["floors"][0]["error"] = "RuntimeError: boom"
    assert nondeterministic_tasks(first, errored) == [errored["floors"][0]["task"]]

    out = tmp_path / "results"
    write_sweep(first, out / "sweep.json")
    write_sweep(second, tmp_path / "b.json")
    assert main(
        ["report", "--out", str(out), "--no-readme", "--rulings", str(tmp_path / "r.jsonl"),
         "--repeat", str(tmp_path / "b.json")]
    ) == 0
    printed = capsys.readouterr().out
    assert "not run, non-deterministic across the two runs: evalfloor/control_loose" in printed
    matrix = (out / "floor_matrix.md").read_text(encoding="utf-8")
    assert f"| `evalfloor/control_loose` | - | - | - | - | - | - | - | - | error: {NOT_RUN_NONDETERMINISTIC} | - |" in matrix
    # Out of the before rate as well as the after: control_loose was the flag.
    assert "**0 of 1** tasks" in matrix
    assert "Before rulings the count was **0 of 1**" in matrix


def test_the_closeout_readme_is_written_only_with_the_second_run(tmp_path) -> None:
    """Once the deterministic payload carries addendum_commit, a graded
    regenerate never writes README.md, and neither does a deterministic one
    without --repeat. Before section 11 the README is written as it always was."""
    from evalfloor.report import write_all, write_sweep

    results = tmp_path / "results"
    readme = tmp_path / "README.md"
    rulings = tmp_path / "rulings.jsonl"
    det = _two_task_payload(addendum_commit="a" * 40, preregistration_commit="b" * 40)
    write_sweep(det, results / "sweep.json")
    graded = _two_task_payload(arm="graded", cap=4, grader={"model": "mockllm/model"})

    written = write_all(graded, results / "graded", rulings, readme_path=readme)
    assert readme not in written and not readme.exists(), "graded regenerate"

    written = write_all(det, results, rulings, readme_path=readme)
    assert readme not in written and not readme.exists(), "no second run yet"

    written = write_all(det, results, rulings, readme_path=readme, repeat=_two_task_payload())
    assert readme in written and readme.exists()

    # Without section 11 stamped, nothing changes: the README is written.
    readme.unlink()
    plain = _two_task_payload()
    write_sweep(plain, results / "sweep.json")
    assert readme in write_all(graded, results / "graded", rulings, readme_path=readme)
