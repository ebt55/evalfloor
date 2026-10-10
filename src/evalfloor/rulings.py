"""Apply ``rulings.jsonl`` mechanically, the way odd-number-forensics does.

Some flags need a judgement call. A task whose target is a CTF flag is a
legitimate use of substring matching. A task with free-text targets has no label
set, so ``all_labels`` never applied to it in the first place. Those decisions
are not made in prose in a write-up; each one is a row in ``rulings.jsonl`` that
quotes the source line it came from, and this module applies the file to the
results so that every published number regenerates from committed inputs.

The flag rate is always reported **both before and after** rulings, so a reader
can see exactly how much of the headline is a judgement call.

Row schema, one JSON object per line::

    {
      "task": "inspect_evals/example",     # required; registry task name
      "scorer": "inspect_ai/includes",     # optional; all scorers if omitted
      "member": "all_labels",              # optional; all members if omitted
      "action": "unflag",                  # unflag | drop_member | note | not_counted
      "treatment": "needs a judge",        # required for not_counted, only there
      "reason": "target is a CTF flag ...",# required; why
      "source": "src/inspect_evals/x.py:41: scorer=includes()",  # required
      "date": "2026-09-15",
      "author": "ebt55"
    }

``not_counted`` is the one action that acts before a sweep rather than after
it: the task is left off the close-out list (``cli.closeout_task_list``), so it
is never swept and the flag rate needs no adjustment. Its ``treatment`` is the
reason class the coverage file groups it under, and its ``reason`` and
``source`` say why that class applies to this task.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

from .aggregate import TaskFloor

VALID_ACTIONS = frozenset({"unflag", "drop_member", "note", "not_counted"})

#: The action whose rows name tasks that are listed, never swept.
NOT_COUNTED = "not_counted"


@dataclass(frozen=True)
class Ruling:
    task: str
    action: str
    reason: str
    source: str
    scorer: str | None = None
    member: str | None = None
    date: str = ""
    author: str = ""
    treatment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def matches(self, floor: TaskFloor) -> bool:
        if self.task != floor.task:
            return False
        if self.scorer and self.scorer != floor.scorer:
            return False
        return True


class RulingError(ValueError):
    pass


def load_rulings(path: pathlib.Path) -> list[Ruling]:
    """Read and validate ``rulings.jsonl``. A malformed row is an error, not a
    warning -- a silently dropped ruling would change a published number."""
    if not path.exists():
        return []
    rulings: list[Ruling] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RulingError(f"{path}:{lineno}: not valid JSON: {exc}") from None
        for required in ("task", "action", "reason", "source"):
            if not row.get(required):
                raise RulingError(f"{path}:{lineno}: missing required field {required!r}")
        if row["action"] not in VALID_ACTIONS:
            raise RulingError(
                f"{path}:{lineno}: action {row['action']!r} not one of "
                + ", ".join(sorted(VALID_ACTIONS))
            )
        treatment = row.get("treatment")
        if row["action"] == NOT_COUNTED:
            if not isinstance(treatment, str) or not treatment.strip():
                raise RulingError(
                    f"{path}:{lineno}: a {NOT_COUNTED} row needs a non-empty "
                    "'treatment'"
                )
            if row.get("scorer") or row.get("member"):
                # A task is listed or swept whole; there is no half-counted task.
                raise RulingError(
                    f"{path}:{lineno}: a {NOT_COUNTED} row names a whole task, "
                    "not a scorer or a member"
                )
        elif treatment is not None:
            raise RulingError(
                f"{path}:{lineno}: 'treatment' belongs only to a {NOT_COUNTED} row"
            )
        rulings.append(
            Ruling(
                task=row["task"],
                action=row["action"],
                reason=row["reason"],
                source=row["source"],
                scorer=row.get("scorer"),
                member=row.get("member"),
                date=row.get("date", ""),
                author=row.get("author", ""),
                treatment=treatment,
            )
        )
    return rulings


def not_counted(rulings: Iterable[Ruling]) -> list[Ruling]:
    """The ``not_counted`` rows, in file order."""
    return [r for r in rulings if r.action == NOT_COUNTED]


@dataclass
class AppliedRuling:
    ruling: Ruling
    effect: str


def apply_rulings(
    floors: Sequence[TaskFloor], rulings: Iterable[Ruling]
) -> tuple[list[TaskFloor], list[AppliedRuling], list[Ruling]]:
    """Return ``(floors after rulings, what each one did, rulings that matched nothing)``.

    The input floors are not mutated; the caller keeps the before-rulings numbers.
    """
    import copy

    after = copy.deepcopy(list(floors))
    applied: list[AppliedRuling] = []
    unmatched: list[Ruling] = []

    for ruling in rulings:
        targets = [f for f in after if ruling.matches(f)]
        if not targets:
            # A not_counted task is never swept, so matching nothing is what it
            # is for. It is listed with its treatment, never as "matched no task".
            if ruling.action != NOT_COUNTED:
                unmatched.append(ruling)
            continue
        for floor in targets:
            if ruling.action == NOT_COUNTED:
                # Swept anyway (a --tasks run, say): the floor leaves every
                # rate the way an errored task does, and says why.
                floor.error = f"not counted: {ruling.treatment}"
                floor.ruling = NOT_COUNTED
                floor.ruling_reason = ruling.reason
                applied.append(
                    AppliedRuling(ruling, f"{floor.task}: not counted ({ruling.treatment})")
                )
            elif ruling.action == "note":
                floor.ruling = "note"
                floor.ruling_reason = ruling.reason
                applied.append(AppliedRuling(ruling, f"{floor.task}: note recorded"))
            elif ruling.action == "drop_member":
                if not ruling.member:
                    raise RulingError("drop_member requires a member")
                removed = floor.members.pop(ruling.member, None)
                floor.flagged_by = [m for m in floor.flagged_by if m != ruling.member]
                _recompute(floor)
                floor.ruling = "drop_member"
                floor.ruling_reason = ruling.reason
                applied.append(
                    AppliedRuling(
                        ruling,
                        f"{floor.task}: dropped member {ruling.member}"
                        + ("" if removed else " (was not present)"),
                    )
                )
            elif ruling.action == "unflag":
                was = floor.flagged
                floor.flagged = False
                floor.flagged_by = []
                floor.ruling = "unflag"
                floor.ruling_reason = ruling.reason
                applied.append(
                    AppliedRuling(
                        ruling,
                        f"{floor.task}: unflagged" + ("" if was else " (was not flagged)"),
                    )
                )
    return after, applied, unmatched


def _recompute(floor: TaskFloor) -> None:
    from .battery import CONTENT_FREE_NAMES

    content_free = [
        s for name, s in floor.members.items() if name in CONTENT_FREE_NAMES and s.applicable
    ]
    if not content_free:
        floor.best_member = ""
        floor.best_mean = 0.0
        floor.gap_to_majority = 0.0
        floor.flagged = False
        floor.flagged_by = []
        return
    best = max(content_free, key=lambda s: s.mean)
    floor.best_member = best.member
    floor.best_mean = best.mean
    floor.gap_to_majority = best.mean - floor.majority
    floor.flagged_by = sorted(
        s.member for s in content_free if s.mean >= floor.majority and s.mean > 0.0
    )
    floor.flagged = bool(floor.flagged_by)
