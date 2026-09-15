"""Turn driven arms into per-task floors, and apply the flag rule.

The flag rule, fixed by preregistration:

    A task is **flagged** when at least one content-free battery member scores at
    or above the ``majority`` reference baseline on that task, **and** that
    member's score is greater than zero.

``majority`` is computed per task from that task's own dataset, so the rule never
depends on a global assumption about label balance. On ``paws`` the majority line
is 0.558, not 0.5.

The "greater than zero" clause is not decoration. Without it, any task where
nothing scores at all -- because the harness cannot drive that scorer, or because
every completion genuinely fails -- has ``majority == 0`` and every content-free
member trivially satisfies ``0 >= 0``, so the whole battery "flags" it. That was
observed on ``sec_qa_v2`` in the first smoke sweep before the multiple-choice
handling in ``drive.build_state`` existed, and it is a defect signature rather
than a finding. A member that scores nothing has not reached any floor.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence

from .battery import CONTENT_FREE_NAMES, REFERENCE_NAMES
from .drive import ArmResult, TaskRun

#: z for a 95 per cent Wilson interval.
Z95 = 1.959963984540054


def wilson_interval(successes: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Reported instead of a point estimate on any arm that was scored over a
    sample of the dataset rather than all of it.
    """
    if n <= 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass
class MemberScore:
    member: str
    mean: float
    n_correct: int
    n_scored: int
    applicable: bool
    arm: str = "rendered"
    example_completion: str = ""
    n_refusals: int = 0
    n_ungradeable: int = 0
    n_unmapped: int = 0
    not_applicable_reason: str | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    n_seeds: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskFloor:
    """One task, one scorer: the floor under it and whether that floor is flagged.

    ``members`` is the **rendered** arm -- the members written in the task's own
    answer template -- and it is the arm the flag rule reads. ``members_raw`` is
    the same members written plainly, kept so a reader can see exactly what the
    rendering rule changed on this task rather than taking it on trust. On a task
    that declares no answer template the two are identical by construction.
    """

    task: str
    scorer: str
    n_samples: int
    sampled: bool
    majority_label: str = ""
    majority: float = 0.0
    uniform: float | None = None
    members: dict[str, MemberScore] = field(default_factory=dict)
    members_raw: dict[str, MemberScore] = field(default_factory=dict)
    answer_template: str = "bare"
    majority_raw: float = 0.0
    best_member: str = ""
    best_mean: float = 0.0
    best_member_raw: str = ""
    best_mean_raw: float = 0.0
    gap_to_majority: float = 0.0
    flagged: bool = False
    flagged_by: list[str] = field(default_factory=list)
    flagged_raw: bool = False
    #: Graded arm only. When true the rates are over a capped sample rather than
    #: the dataset, so the report prints Wilson intervals and the flag rule uses
    #: the interval's lower bound, not the point estimate.
    graded: bool = False
    grader_model: str = ""
    grader_snapshot: str = ""
    grader_injected_via: str = ""
    capped_at: int | None = None
    n_refusals: int = 0
    n_errors: int = 0
    n_ungradeable: int = 0
    n_unmapped: int = 0
    unmapped_verdicts: dict[str, int] = field(default_factory=dict)
    first_error: str | None = None
    #: True when not one grading call succeeded. A floor of 0.0% because nothing
    #: was scored is not a floor of 0.0%, and must never print as one.
    nothing_scored: bool = False
    ruling: str | None = None
    ruling_reason: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["members"] = {k: v.to_dict() for k, v in self.members.items()}
        out["members_raw"] = {k: v.to_dict() for k, v in self.members_raw.items()}
        return out


def _mean_over_seeds(arms: Sequence[ArmResult]) -> MemberScore | None:
    """Collapse a member's per-seed arms, within one arm, into one score."""
    if not arms:
        return None
    usable = [a for a in arms if a.applicable]
    if not usable:
        a = arms[0]
        return MemberScore(
            member=a.member,
            arm=a.arm,
            example_completion=a.example_completion,
            mean=0.0,
            n_correct=0,
            n_scored=0,
            applicable=False,
            not_applicable_reason=a.not_applicable_reason,
            n_seeds=len(arms),
        )
    total_scored = sum(a.n_scored for a in usable)
    total_correct = sum(a.n_correct for a in usable)
    mean = sum(a.mean for a in usable) / len(usable)
    low, high = wilson_interval(total_correct, total_scored)
    return MemberScore(
        member=usable[0].member,
        arm=usable[0].arm,
        example_completion=usable[0].example_completion,
        n_refusals=sum(a.n_refusals for a in usable),
        n_ungradeable=sum(a.n_ungradeable for a in usable),
        n_unmapped=sum(a.n_unmapped for a in usable),
        mean=mean,
        n_correct=total_correct,
        n_scored=total_scored,
        applicable=True,
        ci_low=low,
        ci_high=high,
        n_seeds=len(usable),
    )


def _clears(score: MemberScore, floor: "TaskFloor") -> bool:
    """Does this content-free member reach the task's chance line?

    On the deterministic arm every sample is scored, so the point estimate *is*
    the rate and the comparison is exact.

    On the graded arm the rate is over at most ``capped_at`` sampled items, so a
    point estimate would flag tasks on sampling noise. The preregistered rule
    there is stricter: the **Wilson lower bound** of the member must reach the
    majority baseline. A task is only flagged when the floor is above chance even
    on the pessimistic end of the interval.
    """
    if score.mean <= 0.0:
        # The zero guard. A member that scores nothing has not reached any floor,
        # and 0 >= 0 is a defect signature rather than a finding.
        return False
    if floor.graded:
        lower = score.ci_low if score.ci_low is not None else score.mean
        return lower >= floor.majority
    return score.mean >= floor.majority


def aggregate_run(run: TaskRun, full_dataset_size: int | None = None) -> list[TaskFloor]:
    """One TaskFloor per scorer the task declares."""
    if run.error:
        return [
            TaskFloor(
                task=run.task,
                scorer="-",
                n_samples=run.n_samples,
                sampled=False,
                error=run.error,
            )
        ]

    floors: list[TaskFloor] = []
    for scorer in run.scorers or ["-"]:
        buckets: dict[tuple[str, str], list[ArmResult]] = {}
        for arm in run.arms:
            if arm.scorer != scorer:
                continue
            buckets.setdefault((arm.arm, arm.member), []).append(arm)

        floor = TaskFloor(
            task=run.task,
            scorer=scorer,
            n_samples=run.n_samples,
            sampled=bool(full_dataset_size and run.n_samples < full_dataset_size),
            majority_label=run.majority_label,
            answer_template=run.answer_template,
            graded=bool(run.grader_model),
            grader_model=run.grader_model,
            grader_snapshot=run.grader_snapshot,
            grader_injected_via=run.grader_injected_via,
            capped_at=run.capped_at,
            n_refusals=run.n_refusals,
        )
        scorer_arms = [a for a in run.arms if a.scorer == scorer]
        floor.n_errors = sum(a.n_errors for a in scorer_arms)
        floor.n_ungradeable = sum(a.n_ungradeable for a in scorer_arms)
        floor.n_unmapped = sum(a.n_unmapped for a in scorer_arms)
        floor.unmapped_verdicts = dict(run.unmapped_verdicts)
        floor.first_error = next(
            (a.first_error for a in scorer_arms if a.first_error), None
        )
        floor.nothing_scored = sum(a.n_scored for a in scorer_arms) == 0
        for (arm_name, member), arms in buckets.items():
            score = _mean_over_seeds(arms)
            if score is None:
                continue
            if arm_name == "raw":
                floor.members_raw[member] = score
            else:
                floor.members[member] = score

        majority = floor.members.get("majority")
        floor.majority = majority.mean if majority else 0.0
        majority_raw = floor.members_raw.get("majority")
        floor.majority_raw = majority_raw.mean if majority_raw else 0.0
        uniform = floor.members.get("uniform")
        floor.uniform = uniform.mean if uniform and uniform.applicable else None

        # The flag rule reads the RENDERED arm. Preregistered.
        content_free = [
            s
            for name, s in floor.members.items()
            if name in CONTENT_FREE_NAMES and s.applicable
        ]
        if content_free:
            best = max(content_free, key=lambda s: s.mean)
            floor.best_member = best.member
            floor.best_mean = best.mean
            floor.gap_to_majority = best.mean - floor.majority
            floor.flagged_by = sorted(
                s.member for s in content_free if _clears(s, floor)
            )
            floor.flagged = bool(floor.flagged_by)

        # The raw arm is reported alongside, never used to flag, so that the
        # effect of the rendering rule on the headline is visible as a number.
        content_free_raw = [
            s
            for name, s in floor.members_raw.items()
            if name in CONTENT_FREE_NAMES and s.applicable
        ]
        if content_free_raw:
            best_raw = max(content_free_raw, key=lambda s: s.mean)
            floor.best_member_raw = best_raw.member
            floor.best_mean_raw = best_raw.mean
            raw_floor = TaskFloor(
                task=floor.task,
                scorer=floor.scorer,
                n_samples=floor.n_samples,
                sampled=floor.sampled,
                majority=floor.majority_raw,
                graded=floor.graded,
            )
            floor.flagged_raw = any(_clears(s, raw_floor) for s in content_free_raw)
        floors.append(floor)
    return floors


def aggregate(runs: Iterable[TaskRun]) -> list[TaskFloor]:
    floors: list[TaskFloor] = []
    for run in runs:
        floors.extend(aggregate_run(run))
    floors.sort(key=lambda f: (f.task, f.scorer))
    return floors


def flag_rate(floors: Sequence[TaskFloor], arm: str = "rendered") -> tuple[int, int]:
    """``(flagged, denominator)`` over tasks that actually produced a result.

    The denominator is the count of distinct tasks with at least one scored
    floor, not the count of floors: a task with two scorers is one task.

    ``arm`` selects which arm's flags are counted. "rendered" is the
    preregistered headline; "raw" is reported beside it so the effect of the
    rendering rule on the number is itself a published figure.
    """
    # A task where not one call scored has not been measured. It belongs in the
    # coverage file as a failure, never in the denominator of a rate.
    scored = {
        f.task for f in floors if f.error is None and f.members and not f.nothing_scored
    }
    if arm == "raw":
        flagged = {f.task for f in floors if f.error is None and f.flagged_raw}
    else:
        flagged = {f.task for f in floors if f.error is None and f.flagged}
    return len(flagged & scored), len(scored)


def sweep_digest(runs: Sequence[TaskRun]) -> str:
    """A digest over only the parts of a sweep that must be reproducible.

    Excludes wall-clock timings, which vary between runs by design. Two sweeps of
    the deterministic arms must produce the same digest; if they do not, that is
    an instrument defect and gets logged rather than smoothed.
    """
    payload: list[Any] = []
    for run in sorted(runs, key=lambda r: r.task):
        payload.append(
            [
                run.task,
                run.scorers,
                run.n_samples,
                run.n_distinct_labels,
                run.majority_label,
                round(run.majority_share, 12),
                run.answer_template,
                run.error,
                [
                    [
                        a.scorer,
                        a.member,
                        a.seed,
                        a.arm,
                        a.example_completion[:200],
                        a.n_scored,
                        a.n_correct,
                        a.n_errors,
                        round(a.score_sum, 9),
                        a.applicable,
                    ]
                    for a in sorted(
                        run.arms, key=lambda a: (a.scorer, a.member, a.arm, a.seed)
                    )
                ],
            ]
        )
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
