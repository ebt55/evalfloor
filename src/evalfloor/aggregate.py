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
    not_applicable_reason: str | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    n_seeds: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskFloor:
    """One task, one scorer: the floor under it and whether that floor is flagged."""

    task: str
    scorer: str
    n_samples: int
    sampled: bool
    majority_label: str = ""
    majority: float = 0.0
    uniform: float | None = None
    members: dict[str, MemberScore] = field(default_factory=dict)
    best_member: str = ""
    best_mean: float = 0.0
    gap_to_majority: float = 0.0
    flagged: bool = False
    flagged_by: list[str] = field(default_factory=list)
    ruling: str | None = None
    ruling_reason: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["members"] = {k: v.to_dict() for k, v in self.members.items()}
        return out


def _mean_over_seeds(arms: Sequence[ArmResult]) -> MemberScore | None:
    """Collapse a member's per-seed arms into one score."""
    if not arms:
        return None
    usable = [a for a in arms if a.applicable]
    if not usable:
        a = arms[0]
        return MemberScore(
            member=a.member,
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
        mean=mean,
        n_correct=total_correct,
        n_scored=total_scored,
        applicable=True,
        ci_low=low,
        ci_high=high,
        n_seeds=len(usable),
    )


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
        by_member: dict[str, list[ArmResult]] = {}
        for arm in run.arms:
            if arm.scorer != scorer:
                continue
            by_member.setdefault(arm.member, []).append(arm)

        floor = TaskFloor(
            task=run.task,
            scorer=scorer,
            n_samples=run.n_samples,
            sampled=bool(full_dataset_size and run.n_samples < full_dataset_size),
            majority_label=run.majority_label,
        )
        for member, arms in by_member.items():
            score = _mean_over_seeds(arms)
            if score is not None:
                floor.members[member] = score

        majority = floor.members.get("majority")
        floor.majority = majority.mean if majority else 0.0
        uniform = floor.members.get("uniform")
        floor.uniform = uniform.mean if uniform and uniform.applicable else None

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
                s.member
                for s in content_free
                if s.mean >= floor.majority and s.mean > 0.0
            )
            floor.flagged = bool(floor.flagged_by)
        floors.append(floor)
    return floors


def aggregate(runs: Iterable[TaskRun]) -> list[TaskFloor]:
    floors: list[TaskFloor] = []
    for run in runs:
        floors.extend(aggregate_run(run))
    floors.sort(key=lambda f: (f.task, f.scorer))
    return floors


def flag_rate(floors: Sequence[TaskFloor]) -> tuple[int, int]:
    """``(flagged, denominator)`` over tasks that actually produced a result.

    The denominator is the count of distinct tasks with at least one scored
    floor, not the count of floors: a task with two scorers is one task.
    """
    scored = {f.task for f in floors if f.error is None and f.members}
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
                run.error,
                [
                    [
                        a.scorer,
                        a.member,
                        a.seed,
                        a.n_scored,
                        a.n_correct,
                        a.n_errors,
                        round(a.score_sum, 9),
                        a.applicable,
                    ]
                    for a in sorted(run.arms, key=lambda a: (a.scorer, a.member, a.seed))
                ],
            ]
        )
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
