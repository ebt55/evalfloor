"""B6, the aggregate half: one digest per task, beside the sweep digest.

Two sweeps of the list run in separate processes, and a task whose digests
differ is "not run: non-deterministic" under PREREGISTRATION section 11.7. That
needs a digest per task, computed from exactly what ``sweep_digest`` already
covers, so that a sweep digest which moved can be traced to the tasks that
moved it.

``sweep_digest`` is quoted in published results, so it must not change by one
byte when it is refactored to share that record. The golden test below was
written and passing against the code before the refactor.

No network: every run is driven from the committed fixture tasks, from a
multiple-choice task built here, or built by hand.
"""

from __future__ import annotations

import asyncio
import copy

from inspect_ai import Task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import choice

from evalfloor.aggregate import sweep_digest, task_digests
from evalfloor.drive import ArmResult, TaskRun, drive_task_async
from fixtures import loose_eval

#: ``sweep_digest(_runs())`` before the per-task refactor. Never update it to
#: make a test pass: a change here is a change to every published digest.
GOLDEN_SWEEP_DIGEST = "3fa97ae3e699c63047ec1c17067a148d0c56e21edab333e5ae05020c3fed3f85"


def _choice_task() -> Task:
    """Twelve three-way samples, so the rendered arm writes "ANSWER: X"."""
    return Task(
        dataset=MemoryDataset(
            [
                Sample(
                    id=i,
                    input=f"Which option is listed {['first', 'second', 'third'][i % 3]}?",
                    choices=["red", "green", "blue"],
                    target="ABC"[i % 3] if i % 4 else "A",
                )
                for i in range(12)
            ]
        ),
        scorer=choice(),
    )


def _hand_built() -> list[TaskRun]:
    """Values the fixtures never produce: fractional sums that need rounding, a
    completion past the 200-character cut, and a task that failed to load."""
    scored = TaskRun(
        task="evalfloor_fixtures/hand_built",
        scorers=["inspect_ai/model_graded_qa"],
        n_samples=3,
        n_distinct_labels=2,
        labels_closed=True,
        answer_template="bare",
        majority_label="Yes",
        majority_share=2 / 3,
        arms=[
            ArmResult(
                task="evalfloor_fixtures/hand_built",
                scorer="inspect_ai/model_graded_qa",
                member=member,
                seed=0,
                arm=arm,
                example_completion="lorem ipsum " * 25,
                n_samples=3,
                n_scored=3,
                n_correct=correct,
                score_sum=correct + 1 / 7,
                elapsed_s=0.25,
            )
            for member, correct in (("echo", 1), ("majority", 2))
            for arm in ("raw", "rendered")
        ],
        elapsed_s=1.5,
    )
    failed = TaskRun(
        task="evalfloor_fixtures/failed_load",
        error="dataset load failed: RuntimeError: the dataset could not be read",
        elapsed_s=0.01,
    )
    return [scored, failed]


def _runs() -> list[TaskRun]:
    driven = [
        (loose_eval.loose_refusal(), "evalfloor_fixtures/loose_refusal"),
        (loose_eval.tight_flags(), "evalfloor_fixtures/tight_flags"),
        (loose_eval.template_collision(), "evalfloor_fixtures/template_collision"),
        (loose_eval.exact_numeric(), "evalfloor_fixtures/exact_numeric"),
        (_choice_task(), "evalfloor_fixtures/choice_built_here"),
    ]
    runs = [asyncio.run(drive_task_async(name, task=task)) for task, name in driven]
    return runs + _hand_built()


def test_the_sweep_digest_is_byte_identical_to_before_the_refactor() -> None:
    assert sweep_digest(_runs()) == GOLDEN_SWEEP_DIGEST


def test_there_is_one_digest_per_task_and_it_is_that_tasks_sweep_digest() -> None:
    runs = _runs()
    digests = task_digests(runs)
    assert list(digests) == sorted(r.task for r in runs)
    for run in runs:
        assert digests[run.task] == sweep_digest([run])


def test_one_changed_member_score_moves_exactly_that_tasks_digest() -> None:
    runs = _runs()
    before = task_digests(runs)

    changed = copy.deepcopy(runs)
    target = next(r for r in changed if r.task == "evalfloor_fixtures/tight_flags")
    cell = next(a for a in target.arms if a.member == "echo" and a.arm == "rendered")
    cell.n_correct += 1
    cell.score_sum += 1.0
    after = task_digests(changed)

    moved = sorted(task for task in before if before[task] != after[task])
    assert moved == ["evalfloor_fixtures/tight_flags"]
    assert sweep_digest(changed) != sweep_digest(runs)


def test_timings_and_run_order_move_no_digest() -> None:
    runs = _runs()
    before = task_digests(runs)

    shuffled = copy.deepcopy(runs)[::-1]
    for run in shuffled:
        run.elapsed_s += 99.0
        run.arms.reverse()
        for arm in run.arms:
            arm.elapsed_s += 7.0

    assert task_digests(shuffled) == before
    assert sweep_digest(shuffled) == GOLDEN_SWEEP_DIGEST


def test_an_error_in_one_run_only_moves_that_tasks_digest() -> None:
    """Section 11.7's other case: a task that fails in only one of the two runs."""
    runs = _runs()
    before = task_digests(runs)

    failed = copy.deepcopy(runs)
    target = next(r for r in failed if r.task == "evalfloor_fixtures/exact_numeric")
    target.error = "dataset load failed: TimeoutError: the Hub did not answer"
    target.arms = []

    after = task_digests(failed)
    assert sorted(t for t in before if before[t] != after[t]) == [
        "evalfloor_fixtures/exact_numeric"
    ]
