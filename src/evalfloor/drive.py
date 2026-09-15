"""Drive a task's own scorer with a battery completion. No model is called.

A scorer in Inspect is an async function of a ``TaskState`` and a ``Target``. It
does not care where the completion came from. So a content-free completion can
be fed straight into the eval's real scorer and the eval's real dataset, with no
model, no cost and no non-determinism.

This is the shape the reproduction in Inspect Evals issue #2331 uses (that issue
was opened by caiotheodoro on 2026-08-31; it is not ours). ``mockllm/model`` is
named as the model so that any scorer inspecting ``state.model`` sees the model
every Inspect Evals eval is already required to support in its end-to-end test.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from inspect_ai.model import ChatMessageAssistant, ChatMessageUser, ModelName, ModelOutput
from inspect_ai.scorer import Score, Target, value_to_float
from inspect_ai.solver import TaskState

from .battery import (
    BATTERY,
    BatteryMember,
    LabelSet,
    normalize_input,
    normalize_target,
)

#: The model name written into every TaskState. Never contacted.
MOCK_MODEL = "mockllm/model"


# --------------------------------------------------------------------------
# Normalised views of the things we drive
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SampleView:
    """A dataset sample reduced to what a scorer and the battery can see."""

    id: Any
    input: Any
    target: Any
    choices: list[str] | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_sample(cls, sample: Any, index: int) -> "SampleView":
        return cls(
            id=getattr(sample, "id", None) if getattr(sample, "id", None) is not None else index,
            input=getattr(sample, "input", ""),
            target=getattr(sample, "target", ""),
            choices=getattr(sample, "choices", None),
            metadata=getattr(sample, "metadata", None),
        )

    @property
    def target_text(self) -> str:
        return normalize_target(self.target)

    @property
    def input_text(self) -> str:
        return normalize_input(self.input)


@dataclass
class ArmResult:
    """One (task, scorer, battery member, seed) cell of the matrix."""

    task: str
    scorer: str
    member: str
    seed: int
    n_samples: int = 0
    n_scored: int = 0
    n_errors: int = 0
    n_correct: int = 0
    score_sum: float = 0.0
    applicable: bool = True
    not_applicable_reason: str | None = None
    first_error: str | None = None
    elapsed_s: float = 0.0

    @property
    def mean(self) -> float:
        """Mean score over the samples the scorer actually returned a score for."""
        if self.n_scored == 0:
            return 0.0
        return self.score_sum / self.n_scored

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "scorer": self.scorer,
            "member": self.member,
            "seed": self.seed,
            "n_samples": self.n_samples,
            "n_scored": self.n_scored,
            "n_errors": self.n_errors,
            "n_correct": self.n_correct,
            "mean": self.mean,
            "applicable": self.applicable,
            "not_applicable_reason": self.not_applicable_reason,
            "first_error": self.first_error,
            "elapsed_s": round(self.elapsed_s, 3),
        }


@dataclass
class TaskRun:
    """Everything one task contributed to the sweep."""

    task: str
    scorers: list[str] = field(default_factory=list)
    n_samples: int = 0
    n_distinct_labels: int = 0
    labels_closed: bool = False
    majority_label: str = ""
    majority_share: float = 0.0
    arms: list[ArmResult] = field(default_factory=list)
    error: str | None = None
    elapsed_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "scorers": self.scorers,
            "n_samples": self.n_samples,
            "n_distinct_labels": self.n_distinct_labels,
            "labels_closed": self.labels_closed,
            "majority_label": self.majority_label,
            "majority_share": self.majority_share,
            "error": self.error,
            "elapsed_s": round(self.elapsed_s, 3),
            "arms": [a.to_dict() for a in self.arms],
        }


# --------------------------------------------------------------------------
# Task resolution
# --------------------------------------------------------------------------


def resolve_task(task_name: str, **task_args: Any) -> Any:
    """Build a ``Task`` object from a registry name such as ``inspect_evals/paws``.

    Calling the task function is what downloads the dataset, so this is the
    expensive step and the one that fails for gated, sandboxed or oversized evals.
    """
    from inspect_ai._util.registry import registry_create

    if task_name.startswith("evalfloor/"):
        from . import controls  # noqa: F401  (registers the control tasks)
    else:
        import inspect_evals._registry  # noqa: F401  (populates the registry)

    return registry_create("task", task_name, **task_args)


def scorer_names(task: Any) -> list[str]:
    """Registry names of a task's scorer(s), in declaration order."""
    from inspect_ai._util.registry import registry_info

    scorers = getattr(task, "scorer", None)
    if scorers is None:
        return []
    if not isinstance(scorers, (list, tuple)):
        scorers = [scorers]
    names: list[str] = []
    for s in scorers:
        try:
            names.append(registry_info(s).name)
        except Exception:
            names.append(getattr(s, "__name__", repr(s)))
    return names


def task_samples(task: Any, limit: int | None = None) -> list[SampleView]:
    dataset = getattr(task, "dataset", None)
    if dataset is None:
        return []
    samples = list(dataset)
    if limit is not None:
        samples = samples[:limit]
    return [SampleView.from_sample(s, i) for i, s in enumerate(samples)]


def label_set(samples: Sequence[SampleView]) -> LabelSet:
    return LabelSet.from_targets([s.target for s in samples])


# --------------------------------------------------------------------------
# The driver itself
# --------------------------------------------------------------------------


def build_state(sample: SampleView, completion: str) -> TaskState:
    """A TaskState whose model output is the battery completion."""
    user = ChatMessageUser(content=sample.input_text)
    assistant = ChatMessageAssistant(content=completion, model=MOCK_MODEL)
    return TaskState(
        model=ModelName(MOCK_MODEL),
        sample_id=sample.id,
        epoch=1,
        input=sample.input,
        messages=[user, assistant],
        target=Target(sample.target),
        choices=list(sample.choices) if sample.choices else None,
        output=ModelOutput.from_content(model=MOCK_MODEL, content=completion),
        metadata=dict(sample.metadata) if sample.metadata else {},
        completed=True,
    )


async def score_one(scorer: Any, sample: SampleView, completion: str) -> Score:
    state = build_state(sample, completion)
    return await scorer(state, Target(sample.target))


async def run_arm(
    task_name: str,
    scorer: Any,
    scorer_name: str,
    member: BatteryMember,
    seed: int,
    samples: Sequence[SampleView],
    labels: LabelSet,
) -> ArmResult:
    """Score every sample with one battery member against one scorer."""
    result = ArmResult(
        task=task_name,
        scorer=scorer_name,
        member=member.name,
        seed=seed,
        n_samples=len(samples),
    )
    if not member.applies_to(labels):
        result.applicable = False
        result.not_applicable_reason = (
            "dataset has no closed label set "
            f"({labels.n_distinct} distinct targets over {labels.n_samples} samples)"
        )
        return result

    to_float = value_to_float()
    started = time.monotonic()
    for sample in samples:
        completion = member.completion(sample, labels, seed)
        if completion is None:
            result.applicable = False
            result.not_applicable_reason = "member returned no completion for this sample"
            break
        try:
            score = await score_one(scorer, sample, completion)
            value = to_float(score.value)
        except Exception as exc:  # a scorer that cannot run is data, not a crash
            result.n_errors += 1
            if result.first_error is None:
                result.first_error = f"{type(exc).__name__}: {exc}"[:300]
            continue
        result.n_scored += 1
        result.score_sum += value
        if value >= 1.0:
            result.n_correct += 1
    result.elapsed_s = time.monotonic() - started
    return result


async def drive_task_async(
    task_name: str,
    members: Iterable[BatteryMember] = BATTERY,
    limit: int | None = None,
    task: Any | None = None,
    **task_args: Any,
) -> TaskRun:
    """Run the whole battery over one task. Never calls a model."""
    started = time.monotonic()
    run = TaskRun(task=task_name)
    try:
        if task is None:
            task = resolve_task(task_name, **task_args)
    except Exception as exc:
        run.error = f"{type(exc).__name__}: {exc}"[:500]
        run.elapsed_s = time.monotonic() - started
        return run

    try:
        samples = task_samples(task, limit=limit)
    except Exception as exc:
        run.error = f"dataset load failed: {type(exc).__name__}: {exc}"[:500]
        run.elapsed_s = time.monotonic() - started
        return run

    labels = label_set(samples)
    run.n_samples = len(samples)
    run.n_distinct_labels = labels.n_distinct
    run.labels_closed = labels.is_closed
    run.majority_label = labels.majority_label
    run.majority_share = labels.majority_share

    scorers = getattr(task, "scorer", None) or []
    if not isinstance(scorers, (list, tuple)):
        scorers = [scorers]
    names = scorer_names(task)
    run.scorers = names

    for scorer, name in zip(scorers, names):
        for member in members:
            for seed in member.seeds:
                run.arms.append(
                    await run_arm(
                        task_name, scorer, name, member, seed, samples, labels
                    )
                )

    run.elapsed_s = time.monotonic() - started
    return run


def drive_task(
    task_name: str,
    members: Iterable[BatteryMember] = BATTERY,
    limit: int | None = None,
    task: Any | None = None,
    **task_args: Any,
) -> TaskRun:
    """Blocking wrapper around :func:`drive_task_async`."""
    return asyncio.run(
        drive_task_async(
            task_name, members=members, limit=limit, task=task, **task_args
        )
    )
