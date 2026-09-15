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
import math
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from inspect_ai.model import ChatMessageAssistant, ChatMessageUser, ModelName, ModelOutput
from inspect_ai.scorer import Score, Target, value_to_float
from inspect_ai.solver import TaskState

from .battery import (
    ARMS,
    BATTERY,
    BatteryMember,
    LabelSet,
    detect_template,
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
    """One (task, scorer, battery member, seed, arm) cell of the matrix."""

    task: str
    scorer: str
    member: str
    seed: int
    #: "raw" (the member's semantic value written plainly) or "rendered" (the
    #: same value written in the task's own answer template). The flag rule uses
    #: the rendered arm; both are recorded so the effect of rendering is visible.
    arm: str = "rendered"
    #: The exact completion handed to the scorer, from the first sample. Recorded
    #: so a reader can see what was actually scored rather than inferring it.
    example_completion: str = ""
    n_samples: int = 0
    n_scored: int = 0
    n_errors: int = 0
    n_correct: int = 0
    #: Graded arm only: times the grader or the provider declined rather than
    #: graded. Recorded, counted and published -- never retried away.
    n_refusals: int = 0
    #: Times the scorer returned a non-finite value -- the grader answered, but
    #: emitted nothing that parses as a grade. Neither a score nor an error, and
    #: excluded from the denominator rather than coerced to zero.
    n_ungradeable: int = 0
    #: Verdicts in an eval's own vocabulary with no committed mapping. Never
    #: coerced to 0.0; recorded verbatim and excluded. Instrument defect 007.
    n_unmapped: int = 0
    unmapped_verdicts: dict[str, int] = field(default_factory=dict)
    score_sum: float = 0.0
    applicable: bool = True
    not_applicable_reason: str | None = None
    first_error: str | None = None
    elapsed_s: float = 0.0

    @property
    def mean(self) -> float:
        """Mean score over the samples the scorer actually returned a score for.

        Never returns a non-finite value: a NaN here would compare False against
        every threshold in the flag rule and silently disappear into a report.
        """
        import math

        if self.n_scored == 0:
            return 0.0
        value = self.score_sum / self.n_scored
        return value if math.isfinite(value) else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "scorer": self.scorer,
            "member": self.member,
            "seed": self.seed,
            "arm": self.arm,
            "example_completion": self.example_completion[:200],
            "n_samples": self.n_samples,
            "n_scored": self.n_scored,
            "n_errors": self.n_errors,
            "n_correct": self.n_correct,
            "n_refusals": self.n_refusals,
            "n_ungradeable": self.n_ungradeable,
            "n_unmapped": self.n_unmapped,
            "unmapped_verdicts": self.unmapped_verdicts,
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
    #: "choice" when the task's samples carry choices, else "bare". Decides how
    #: the rendered arm writes label-valued members down.
    answer_template: str = "bare"
    majority_label: str = ""
    majority_share: float = 0.0
    arms: list[ArmResult] = field(default_factory=list)
    error: str | None = None
    elapsed_s: float = 0.0
    #: Graded arm only. Empty string on the deterministic arm, where no model is
    #: called at all and there is nothing to attribute a result to.
    grader_model: str = ""
    grader_snapshot: str = ""
    #: Which task parameters the judge was injected through. Empty when the task
    #: exposes none, which means it graded with whatever it hard-codes -- a fact
    #: that has to be visible, not assumed away.
    grader_injected_via: str = ""
    capped_at: int | None = None
    n_refusals: int = 0
    #: Real token usage read back from the provider, never assumed.
    measured_usage: dict[str, Any] = field(default_factory=dict)
    n_unmapped: int = 0
    unmapped_verdicts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "scorers": self.scorers,
            "n_samples": self.n_samples,
            "n_distinct_labels": self.n_distinct_labels,
            "labels_closed": self.labels_closed,
            "answer_template": self.answer_template,
            "majority_label": self.majority_label,
            "majority_share": self.majority_share,
            "error": self.error,
            "elapsed_s": round(self.elapsed_s, 3),
            "grader_model": self.grader_model,
            "grader_snapshot": self.grader_snapshot,
            "grader_injected_via": self.grader_injected_via,
            "capped_at": self.capped_at,
            "n_refusals": self.n_refusals,
            "measured_usage": self.measured_usage,
            "n_unmapped": self.n_unmapped,
            "unmapped_verdicts": self.unmapped_verdicts,
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
    """The task's samples, in a deterministic order.

    Several evals shuffle their dataset by default and do not seed the shuffle
    (``paws`` and ``boolq`` both take ``shuffle: bool = True``). Two calls to the
    same task function therefore return the same samples in a different order,
    and any ``--limit`` then takes a *different subset* each run. That breaks the
    determinism control for reasons that have nothing to do with this harness.

    So the samples are sorted by sample id before the limit is applied. Sorting
    changes nothing about a full sweep -- every sample is scored either way --
    and it makes a limited sweep reproducible, which is what the control needs.
    """
    dataset = getattr(task, "dataset", None)
    if dataset is None:
        return []
    samples = list(dataset)
    views = [SampleView.from_sample(s, i) for i, s in enumerate(samples)]
    views.sort(key=lambda v: (str(type(v.id).__name__), str(v.id)))
    if limit is not None:
        views = views[:limit]
    return views


def label_set(samples: Sequence[SampleView]) -> LabelSet:
    return LabelSet.from_targets([s.target for s in samples])


# --------------------------------------------------------------------------
# The driver itself
# --------------------------------------------------------------------------


def build_state(sample: SampleView, completion: str) -> TaskState:
    """A TaskState whose model output is the battery completion.

    For a multiple-choice sample the scorer is not a function of the completion
    text alone. ``choice()`` reads which entries of ``state.choices`` are marked
    correct, and those marks are set by the ``multiple_choice()`` solver *after*
    generation, by parsing "ANSWER: X" out of the completion. Drive the scorer
    without that step and every completion scores zero, including the reference
    baselines -- which is an instrument defect, not a finding. So the same
    parse-and-mark step Inspect's own solver performs is applied here.
    """
    user = ChatMessageUser(content=sample.input_text)
    assistant = ChatMessageAssistant(content=completion, model=MOCK_MODEL)
    state = TaskState(
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
    if sample.choices:
        _mark_multiple_choice_answers(state)
    return state


def _mark_multiple_choice_answers(state: TaskState) -> None:
    """Replicate what ``multiple_choice()`` does to the state after generate."""
    from inspect_ai.solver._multiple_choice import (
        parse_answers,
        set_choices_based_on_generated_response,
    )

    try:
        answers = parse_answers(state, multiple_correct=False)
    except Exception:
        return
    if answers:
        set_choices_based_on_generated_response(state, answers)


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
    arm: str = "rendered",
) -> ArmResult:
    """Score every sample with one battery member, in one arm, against one scorer."""
    result = ArmResult(
        task=task_name,
        scorer=scorer_name,
        member=member.name,
        seed=seed,
        arm=arm,
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
        completion = member.completion(sample, labels, seed, arm=arm)
        if completion is None:
            result.applicable = False
            result.not_applicable_reason = "member returned no completion for this sample"
            break
        if not result.example_completion:
            result.example_completion = completion
        try:
            score = await score_one(scorer, sample, completion)
            value = to_float(score.value)
        except Exception as exc:  # a scorer that cannot run is data, not a crash
            result.n_errors += 1
            if result.first_error is None:
                result.first_error = f"{type(exc).__name__}: {exc}"[:300]
            continue
        if not math.isfinite(value):
            # The scorer ran but returned nothing gradeable. Not a zero.
            result.n_ungradeable += 1
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
    run.answer_template = detect_template(samples[0]).name if samples else "bare"

    scorers = getattr(task, "scorer", None) or []
    if not isinstance(scorers, (list, tuple)):
        scorers = [scorers]
    names = scorer_names(task)
    run.scorers = names

    for scorer, name in zip(scorers, names):
        for member in members:
            for seed in member.seeds:
                for arm in ARMS:
                    run.arms.append(
                        await run_arm(
                            task_name, scorer, name, member, seed, samples, labels, arm
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
