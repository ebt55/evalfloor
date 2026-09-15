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
      "action": "unflag",                  # unflag | drop_member | note
      "reason": "target is a CTF flag ...",# required; why
      "source": "src/inspect_evals/x.py:41: scorer=includes()",  # required
      "date": "2026-09-15",
      "author": "ebt55"
    }
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

from .aggregate import TaskFloor

VALID_ACTIONS = frozenset({"unflag", "drop_member", "note"})


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
            )
        )
    return rulings


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
            unmatched.append(ruling)
            continue
        for floor in targets:
            if ruling.action == "note":
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
    floor.flagged_by = sorted(s.member for s in content_free if s.mean >= floor.majority)
    floor.flagged = bool(floor.flagged_by)
