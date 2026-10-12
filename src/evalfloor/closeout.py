"""The close-out README's computed lines (build guide B7). Pure: no I/O.

Every number in the close-out README is computed here from what the caller
hands in -- the floors after rulings, the payload, the rulings and the two
inventories -- and none is typed. ``report.render_readme`` reads the files and
places the lines; this module only decides what they say.

The definitions, all over the deterministic payload of the close-out sweep:

    N   countable tasks that ran: listed, scored, not non-deterministic
    C   the size of the list, ``len(payload["tasks"])``
    F   flagged under section 4, ties counted
    K   the template-collision ties among F (section 8.5)
    real = F - K, the flags that are not ties by construction
    R   reachable of D declared, in the release's own inventory
    R0  reachable in the anchor release's inventory, which the list was fixed from
    X   reachable on the release, neither listed nor named by a not_counted row

A listed task that did not count is "not run", with its reason, never dropped:
N plus the not-run list is always C.

Rulings are read by attribute (``task``, ``action``, ``source``, ``scorer``,
``treatment``), so ``rulings.Ruling`` rows and anything shaped like them work.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .aggregate import TaskFloor
from .battery import CONTENT_FREE_NAMES

#: The release the first sweep ran on and ``tests/test_paws_regression.py``
#: pins. A historical fact, like the three below, not a count.
ANCHOR_RELEASE = "0.20.0"

#: The commit whose ``results/task_inventory.json`` (the 0.20.0 inventory, 58
#: reachable) section 11 fixed the close-out list against. Nothing here reads
#: git: callers pass that inventory in as ``anchor_inventory``, and this names
#: where they and the tests get it (``git show 316f142:results/task_inventory.json``).
LIST_FIXED_AT = "316f142"

#: The upstream facts behind the fix clause. #2331 is caiotheodoro's report;
#: the v0.21.0 release notes list the ``paws`` and ``boolq`` fix (#2334).
ISSUE = "#2331"
REPORTER = "caiotheodoro"
FIX_RELEASE = "0.21.0"

#: The two tasks whose floors confirm the fix, or do not.
FIX_TASKS: tuple[str, ...] = ("inspect_evals/paws", "inspect_evals/boolq")

#: Preregistration section 1's threshold on the deterministic arm.
SECTION1_THRESHOLD = 5

#: The ``rulings.jsonl`` actions this module reads.
NOT_COUNTED = "not_counted"
NOTE = "note"

#: The not-run reason section 11.7 gives a task whose two runs disagree.
NON_DETERMINISTIC = "non-deterministic: the two runs disagree (section 11.7)"

#: What a real flag's cause reads when no ``note`` ruling has classified it.
UNCLASSIFIED = "unclassified"

_WORDS = (
    "zero", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten",
)


def _word(n: int) -> str:
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


def _pct(x: float) -> str:
    # The same rendering as report._pct, so a sentence and a table agree.
    return f"{100 * x:.1f}%"


def _short(task: str) -> str:
    return task.split("/", 1)[-1]


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def _scored(floor: TaskFloor) -> bool:
    """The floor ``aggregate.flag_rate`` counts in its denominator."""
    return floor.error is None and bool(floor.members) and not floor.nothing_scored


def representative_floor(floors_for_task: Sequence[TaskFloor]) -> TaskFloor:
    """The one floor that stands for a task with several scorers.

    A stable interface: :func:`counts`, :func:`first_line` and the figures all
    pick a task's floor through this, so a sentence and a figure can never
    disagree about which scorer a task was counted on. In order:

    1.  a flag that is not a tie (``flagged``, no ``error``, no ``collision``);
    2.  a tie (``flagged`` and ``collision``);
    3.  a scored floor, largest gap first (best content-free mean minus
        ``majority``, i.e. ``gap_to_majority``);
    4.  anything else: errored, or nothing scored.

    Within a class the scorer name breaks ties, so the choice never depends on
    the order the floors arrive in. Raises on no floors or on floors of more
    than one task.
    """
    if not floors_for_task:
        raise ValueError("no floors to choose from")
    tasks = {f.task for f in floors_for_task}
    if len(tasks) != 1:
        raise ValueError(f"floors of more than one task: {sorted(tasks)}")

    def rank(floor: TaskFloor) -> tuple[int, float, str]:
        flag = floor.error is None and floor.flagged
        if flag and not floor.collision:
            return (0, 0.0, floor.scorer)
        if flag:
            return (1, 0.0, floor.scorer)
        if _scored(floor):
            return (2, -floor.gap_to_majority, floor.scorer)
        return (3, 0.0, floor.scorer)

    return min(floors_for_task, key=rank)


# --------------------------------------------------------------------------
# The counts
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class CloseoutCounts:
    N: int
    C: int
    F: int
    K: int
    R: int
    D: int
    R0: int
    #: Reachable on the release, neither listed nor not_counted. Sorted names.
    X: tuple[str, ...]
    #: Every listed task that did not count, as ``(task, reason)``, sorted.
    not_run: tuple[tuple[str, str], ...]
    #: ``inspect_evals`` as the deterministic payload pinned it.
    release: str
    anchor_release: str
    #: The task names behind N, F and K.
    ran: tuple[str, ...]
    flagged: tuple[str, ...]
    ties: tuple[str, ...]

    @property
    def real(self) -> int:
        return self.F - self.K

    @property
    def real_flags(self) -> tuple[str, ...]:
        ties = set(self.ties)
        return tuple(t for t in self.flagged if t not in ties)


def counts(
    floors: Sequence[TaskFloor],
    payload: Mapping[str, Any],
    not_counted_rulings: Iterable[Any],
    release_inventory: Sequence[Mapping[str, Any]],
    anchor_inventory: Sequence[Mapping[str, Any]],
    nondeterministic: Iterable[str] = (),
    anchor_release: str = ANCHOR_RELEASE,
) -> CloseoutCounts:
    """N, C, F, K, R, D, R0, X and the not-run list, from the arguments alone.

    ``floors`` are the deterministic floors after rulings. ``not_counted_rulings``
    may be the whole rulings list: rows of any other action are ignored.
    ``nondeterministic`` names the tasks whose two runs differed or that failed
    in only one; they are not run whatever their floors say.

    F and K use aggregate's own notions: a floor is flagged when ``flagged``
    is set, and a tie when ``collision`` is. A task with several scorers is
    counted on its :func:`representative_floor`, which puts a real flag ahead
    of a tie, so a real flag on one scorer is never hidden behind a tie on
    another.
    """
    if "tasks" not in payload:
        raise ValueError("the payload has no `tasks`; C is its length")
    listed = [str(t) for t in payload["tasks"]]
    if len(set(listed)) != len(listed):
        raise ValueError("the payload lists a task twice; C would count it twice")
    release = (payload.get("pins") or {}).get("inspect_evals")
    if not release:
        raise ValueError("the payload has no `inspect_evals` pin to name its release")

    listed_set = set(listed)
    nondet = set(nondeterministic)
    by_task: dict[str, list[TaskFloor]] = {}
    for floor in floors:
        if floor.task in listed_set:
            by_task.setdefault(floor.task, []).append(floor)

    ran: list[str] = []
    not_run: list[tuple[str, str]] = []
    flagged: list[str] = []
    ties: list[str] = []
    for task in sorted(listed_set):
        if task in nondet:
            not_run.append((task, NON_DETERMINISTIC))
            continue
        if task not in by_task:
            not_run.append((task, "no result in the payload"))
            continue
        floor = representative_floor(by_task[task])
        if not _scored(floor):
            not_run.append((task, floor.error or "nothing scored"))
            continue
        ran.append(task)
        if floor.flagged:
            flagged.append(task)
            if floor.collision:
                ties.append(task)

    excluded = listed_set | {
        r.task for r in not_counted_rulings if getattr(r, "action", None) == NOT_COUNTED
    }
    unlisted = sorted(
        str(row["name"])
        for row in release_inventory
        if row.get("reachable") and row["name"] not in excluded
    )

    return CloseoutCounts(
        N=len(ran),
        C=len(listed),
        F=len(flagged),
        K=len(ties),
        R=sum(1 for row in release_inventory if row.get("reachable")),
        D=len(release_inventory),
        R0=sum(1 for row in anchor_inventory if row.get("reachable")),
        X=tuple(unlisted),
        not_run=tuple(not_run),
        release=str(release),
        anchor_release=anchor_release,
        ran=tuple(ran),
        flagged=tuple(flagged),
        ties=tuple(ties),
    )


# --------------------------------------------------------------------------
# Section 1's sentence
# --------------------------------------------------------------------------


def section1_sentence(F: int, K: int, threshold: int = SECTION1_THRESHOLD) -> str:
    """Preregistration section 1's verdict, computed, never typed.

    Ties count toward F, as section 8.5 decided; the sentence says when only
    ties carried F over the threshold.
    """
    if not 0 <= K <= F:
        raise ValueError(f"ties must be between 0 and the flags; got F={F}, K={K}")
    if F < threshold:
        return "Preregistered negative result."
    if F == K:
        return (
            f"{F} flagged under the preregistered rule, all of them ties by "
            f"construction; the threshold of {_word(threshold)} is crossed only by "
            "ties, so the negative result does not hold as written."
        )
    return (
        f"{F} flagged under the preregistered rule, {K} of them ties; the "
        "preregistered negative result does not hold."
    )


# --------------------------------------------------------------------------
# The first line
# --------------------------------------------------------------------------


def fix_confirmed(c: CloseoutCounts, floors: Sequence[TaskFloor]) -> bool:
    """True only when ``paws`` and ``boolq`` both ran clean and unflagged."""
    return not _fix_shortfalls(c, floors)


def _fix_shortfalls(c: CloseoutCounts, floors: Sequence[TaskFloor]) -> list[str]:
    """What stops this sweep confirming the fix, one phrase per task."""
    not_run = dict(c.not_run)
    shortfalls: list[str] = []
    for task in FIX_TASKS:
        name = f"`{_short(task)}`"
        task_floors = [f for f in floors if f.task == task]
        if task in not_run:
            shortfalls.append(f"{name} did not run")
        elif task not in c.ran or not task_floors:
            shortfalls.append(f"{name} has no result")
        elif any(f.error is None and f.flagged for f in task_floors):
            shortfalls.append(f"{name} is flagged")
        elif any(f.error for f in task_floors):
            shortfalls.append(f"{name} did not run cleanly")
    return shortfalls


def fix_clause(c: CloseoutCounts, floors: Sequence[TaskFloor]) -> str:
    """The ``paws`` sentence. It claims confirmation only from the floors."""
    lead = (
        f"The one loose scorer this tool found on {c.anchor_release}, `paws` "
        f"(reported first by {REPORTER}, {ISSUE}), was fixed upstream in "
        f"v{FIX_RELEASE}"
    )
    shortfalls = _fix_shortfalls(c, floors)
    if not shortfalls:
        return f"{lead}. This sweep confirms the fix."
    return f"{lead}. In this sweep {' and '.join(shortfalls)}, so it does not confirm the fix."


def _note_source(task: str, scorer: str, rulings: Sequence[Any]) -> str | None:
    """The ``source`` of the last ``note`` ruling on this task and scorer."""
    source = None
    for r in rulings:
        if getattr(r, "action", None) != NOTE or r.task != task:
            continue
        if getattr(r, "scorer", None) and r.scorer != scorer:
            continue
        source = r.source
    return source


#: A source-code citation as a ruling writes it: ``bbh.py:98-108``, ``src/r.py:41``.
_CITATION = re.compile(r"[\w./\\-]+\.py:\d+(?:-\d+)?")
#: A parenthesised aside holding at least one citation, with the space before it.
_CITED_ASIDE = re.compile(r"\s*\([^()]*?" + _CITATION.pattern + r"[^()]*\)")
#: A bare citation, with the colon that may follow it and the space around it.
_BARE_CITATION = re.compile(r"\s*" + _CITATION.pattern + r":?\s*")


def citations(source: str) -> list[str]:
    """Every file:line citation in a ruling's source, in order, once each."""
    found: list[str] = []
    for hit in _CITATION.findall(source):
        if hit not in found:
            found.append(hit)
    return found


def _without_citations(source: str) -> str:
    """A ruling's source with its file:line citations taken out, for the lead."""
    text = _BARE_CITATION.sub(" ", _CITED_ASIDE.sub("", source))
    return " ".join(text.split())


def _real_flag(task: str, floors: Sequence[TaskFloor], rulings: Sequence[Any]) -> str:
    """One real flag in plain sentences: the task, its best flagging member and
    both rates, then the cause. The cause's file:line citations are left out
    here; :func:`citations_line` carries them at the end of the section."""
    floor = representative_floor([f for f in floors if f.task == task])
    if floor.error is not None or not floor.flagged or floor.collision:
        raise ValueError(f"{task} is counted as a real flag, but its floors carry none")
    member = min(floor.flagged_by, key=lambda m: (-floor.members[m].mean, m))
    rates = (
        f"On `{task}`, `{member}` scores {_pct(floor.members[member].mean)} "
        f"against a {_pct(floor.majority)} baseline."
    )
    source = _note_source(task, floor.scorer, rulings)
    if not source:
        return f"{rates} The cause is {UNCLASSIFIED}."
    return f"{rates} The reason is that {_without_citations(source)}."


def _ties_sentence(K: int, more: bool) -> str:
    """The ties by construction, in plain words, with the §8.5 pointer."""
    return (
        f"On {K}{' more' if more else ''}, the placeholder answer is also the most "
        "common answer, so its score ties the baseline by construction (§8.5)."
    )


def first_line(
    c: CloseoutCounts, floors: Sequence[TaskFloor], rulings: Iterable[Any]
) -> str:
    """The README's opening paragraph, for ``real == 0`` and for ``real >= 1``.

    Plain sentences, one idea each. A real flag's cause is the ``source`` of a
    ``note`` ruling on that task, with its file:line citations taken out, or
    "unclassified" until the triage writes one.
    """
    rulings = list(rulings)
    opening = (
        f"I fed {_word(len(CONTENT_FREE_NAMES))} answers with no content to the real "
        f"scorers of {c.N} Inspect Evals {_plural(c.N, 'task', 'tasks')} that run "
        f"without a model, on `inspect_evals` {c.release}."
    )
    if c.real == 0:
        if c.K:
            middle = (
                "None reached its majority baseline except as a tie. "
                f"{_ties_sentence(c.K, more=False)}"
            )
        else:
            middle = "None reached its majority baseline."
    else:
        reached = _plural(
            c.real,
            "reached its majority baseline outright, not as a tie",
            "reached their majority baselines outright, not as ties",
        )
        items = " ".join(_real_flag(task, floors, rulings) for task in c.real_flags)
        middle = f"{c.real} {reached}. {items}"
        if c.K:
            middle += f" {_ties_sentence(c.K, more=True)}"
    return f"{opening} {middle} {fix_clause(c, floors)}"


def citations_line(
    c: CloseoutCounts, floors: Sequence[TaskFloor], rulings: Iterable[Any]
) -> str:
    """The file:line citations behind each real flag's cause, one sentence per
    task, for the end of section 1. "" when no ruling cites a line."""
    rulings = list(rulings)
    sentences: list[str] = []
    for task in c.real_flags:
        floor = representative_floor([f for f in floors if f.task == task])
        source = _note_source(task, floor.scorer, rulings)
        cited = citations(source) if source else []
        if cited:
            sentences.append(f"Lines cited in the `{task}` ruling: {', '.join(cited)}.")
    return " ".join(sentences)


# --------------------------------------------------------------------------
# The other lines
# --------------------------------------------------------------------------


def status_line(date: str | datetime.date) -> str:
    day = date if isinstance(date, datetime.date) else datetime.date.fromisoformat(date)
    return f"Status: closed {day.isoformat()}; no further sweeps."


def denominator_line(c: CloseoutCounts) -> str:
    """N of C, where the list came from, and what the release reaches beside it."""
    n_x = len(c.X)
    if n_x == 0:
        beside = "no reachable task is left off the list."
    else:
        names = ", ".join(f"`{t}`" for t in c.X)
        beside = (
            f"the {n_x} reachable {_plural(n_x, 'task', 'tasks')} not on the list "
            f"{_plural(n_x, 'is', 'are')} named, not run: {names}."
        )
    return (
        f"{c.N} of {c.C} countable on {c.release}. The list was fixed in §11 from the "
        f"{c.R0} tasks reachable on {c.anchor_release}; {c.release} reaches {c.R} of "
        f"{c.D} declared, and {beside}"
    )


def determinism_line(
    digest: str, digest_repeat: str | None, differing: Iterable[str] = ()
) -> str:
    """Two runs' sweep digests and the tasks whose own digests differed.

    Refuses inputs that contradict each other, so it can never print "both
    times" over two runs that disagreed.
    """
    names = sorted(set(differing))
    if digest_repeat is None:
        if names:
            raise ValueError("tasks are named as differing, but no second run was read")
        return (
            f"One run, digest `{digest[:16]}`. No second run was read, so this does "
            "not show the sweep is deterministic."
        )
    if digest == digest_repeat and names:
        raise ValueError("the sweep digests agree, but tasks are named as differing")
    if digest != digest_repeat and not names:
        raise ValueError("the sweep digests differ, but no task is named as differing")
    if not names:
        return f"Two runs in separate processes, digest `{digest[:16]}` both times."
    n = len(names)
    listed = ", ".join(f"`{t}`" for t in names)
    return (
        f"Two runs in separate processes, digests `{digest[:16]}` and "
        f"`{digest_repeat[:16]}`. {n} {_plural(n, 'task differs', 'tasks differ')} "
        f"between them and {_plural(n, 'is', 'are')} not run under §11.7: {listed}."
    )


def pins_line(
    det_pins: Mapping[str, Any], graded_pins: Mapping[str, Any] | None
) -> str:
    """Each arm's release, as its own payload recorded it."""
    release = det_pins.get("inspect_evals")
    if not release:
        raise ValueError("the deterministic pins name no `inspect_evals` release")
    line = f"Deterministic arm: `inspect_evals` {release}."
    graded = (graded_pins or {}).get("inspect_evals")
    if not graded:
        line += " Graded arm: none recorded."
    elif graded == release:
        line += f" Graded arm: {graded}."
    else:
        line += f" Graded arm: {graded}, not re-run."
    return line + " Arms are never added."


def preregistration_line(prereg_commit: str | None, addendum_commit: str | None) -> str:
    """Both preregistration hashes, and how to check them."""
    if not prereg_commit:
        return "No preregistration commit is recorded."
    line = f"Preregistration committed at `{prereg_commit[:12]}`"
    if not addendum_commit:
        return line + "; no close-out addendum is recorded."
    return (
        f"{line}; its close-out addendum, §11, at `{addendum_commit[:12]}`. "
        "`git log --format='%H %ad' -- PREREGISTRATION.md` lists both."
    )
