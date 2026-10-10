"""README figures and GIFs, generated from the committed results. None is drawn by hand.

Run as::

    python -m evalfloor.figures --out docs/figures [--before-ref 316f142] [--only F1,F3,G2]
    python -m evalfloor.figures --out docs/figures --capture check-paws-020 -- \\
        .venv/Scripts/evalfloor check inspect_evals/paws

The module is in two halves, and the split is the point.

**Data, pure.** :func:`figure_data` takes the floors after rulings, the
deterministic payload, :class:`closeout.CloseoutCounts`, the anchor payload and
the inventories, and returns the rows each figure plots as plain dicts. Titles,
alt text, captions and the markdown table twin are computed from those rows
(:func:`title`, :func:`alt_text`, :func:`caption`, :func:`table_twin`), so no
number in a figure is typed. :func:`data_digest` hashes the rows, not the bytes
of any file. Nothing in this half imports matplotlib or Pillow.

**Drawing.** matplotlib for the static figures and Pillow for the GIFs, each
imported inside the function that uses it. Every image a figure writes carries its
rows' digest: in the SVG's metadata Description and in a PNG ``tEXt`` chunk, and
the SVG also uses it as ``svg.hashsalt``. With ``Date=None`` and
``svg.fonttype='path'`` (glyphs as outlines, so GitHub renders them exactly), the
same rows give the same bytes.

The figures:

* **F1, the floor.** One row per task: the majority baseline (a tick) and the best
  content-free point (a dot), sorted by gap. A real flag wears the status colour
  with an icon and its numbers; a collision tie is a hollow diamond in neutral
  ink; everything else is grey. Not-run tasks are listed as text.
* **F2, paws before and after.** A dumbbell per content-free member, from the
  anchor release to the release under test. Drawn only when the payload is on a
  different release from the anchor's, i.e. after the close-out sweep.
* **F3, the denominator.** One part-to-whole bar over the anchor inventory.
* **G1.** F2's rows as a GIF: each member's completion typed in, its bar grown.
* **G2.** A terminal recording, replayed from a capture with timestamps
  (:func:`capture`), plus a plain-text transcript of the same capture.
"""

from __future__ import annotations

import argparse
import codecs
import csv
import datetime as _dt
import hashlib
import io
import json
import logging
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .aggregate import COLLISION_MEMBER, TaskFloor
from .battery import CONTENT_FREE_NAMES
from .closeout import ANCHOR_RELEASE, LIST_FIXED_AT, CloseoutCounts, representative_floor

# --------------------------------------------------------------------------
# Names, sizes, budgets
# --------------------------------------------------------------------------

#: The static figures, in README order. F2 exists only after the close-out sweep.
FIGURE_IDS: tuple[str, ...] = ("F1", "F2", "F3")
GIF_IDS: tuple[str, ...] = ("G1", "G2")

#: File stems. A static figure writes ``<stem>-{light,dark}.{svg,png}`` and
#: ``<stem>.csv``; G1 writes ``<stem>.gif``; G2 writes ``g2-<name>.{gif,txt,json}``.
FIGURE_NAMES: dict[str, str] = {
    "F1": "f1-floor",
    "F2": "f2-paws-fix",
    "F3": "f3-denominator",
    "G1": "g1-paws-battery",
    # Every g2-<name>.json capture, in release order, in one terminal.
    "G2": "g2-terminal",
}

#: The task F2 and G1 are about: the one loose scorer found on the anchor release.
FIX_TASK = "inspect_evals/paws"

#: Every PNG and GIF is this size; every SVG has this aspect.
SIZE: tuple[int, int] = (1920, 1080)
DPI = 100

#: GIF budgets (bytes) and G1's running time (seconds).
G1_MAX_BYTES = 4 * 1024 * 1024
G2_MAX_BYTES = 2 * 1024 * 1024
G1_SECONDS: tuple[float, float] = (10.0, 14.0)

#: F1 puts at most this many rows in one panel before it splits into two.
F1_ROWS_PER_PANEL = 26

FIELDS: dict[str, tuple[str, ...]] = {
    "F1": (
        "task", "scorer", "n_scorers", "state", "majority", "majority_label",
        "best_member", "best_mean", "gap", "flagged_by", "flag_member", "flag_mean",
        "collision_completion", "cause", "reason",
    ),
    "F2": (
        "task", "member", "release_before", "release_after", "scorer_before",
        "scorer_after", "majority_before", "majority_after", "completion_before",
        "completion_after", "applicable_before", "applicable_after", "score_before",
        "score_after", "reaches_before", "reaches_after",
    ),
    "F3": ("segment", "label", "kind", "count", "start", "end", "tasks", "detail"),
}

# --------------------------------------------------------------------------
# Colour. Every hex is from the dataviz skill's documented palette
# (references/palette.md), except the derivations noted. Validated with
# scripts/validate_palette.js in both modes; see PALETTES.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Theme:
    mode: str
    surface: str
    ink: str  # primary text, the majority tick
    ink2: str  # secondary text: labels, ticks, captions
    grid: str  # hairline gridlines
    connector: str  # the thin line from tick to point
    flag: str  # status "critical": a real (non-tie) flag, always with an icon
    tie: str  # neutral ink: the hollow diamond of a collision tie
    clean: str  # grey: every other point
    before: str  # F2: the anchor release (the lighter step in light mode)
    after: str  # F2: the release under test
    excluded: str  # F3: grey step for exclusion segments
    not_counted: str  # F3: grey step for the not-counted segment
    ran: str  # F3: the accent, countable and ran
    not_run: str  # F3: a lighter step of the accent, countable and not run


#: Light: the chart surface #fcfcfb and its ink. Status critical for a real flag.
LIGHT = Theme(
    mode="light",
    surface="#fcfcfb",
    ink="#0b0b0b",
    ink2="#52514e",
    grid="#e1e0d9",
    connector="#c3c2b7",
    flag="#d03b3b",
    tie="#52514e",
    clean="#898781",
    before="#6da7ec",  # blue 300
    after="#184f95",  # blue 600
    excluded="#c3c2b7",
    not_counted="#898781",
    ran="#2a78d6",  # blue 450, slot 1
    not_run="#86b6ef",  # blue 250
)

#: Dark: selected for the dark surface #1a1a19, not flipped from light. The
#: sequential anchor flips (more emphasis is lighter), so F2's release under test
#: and F3's "ran" are the lighter steps here, and the greys step up to stay
#: visible against a near-black surface.
DARK = Theme(
    mode="dark",
    surface="#1a1a19",
    ink="#ffffff",
    ink2="#c3c2b7",
    grid="#2c2c2a",
    connector="#52514e",
    flag="#d03b3b",
    tie="#c3c2b7",
    clean="#898781",
    before="#1c5cab",  # blue 550
    after="#9ec5f4",  # blue 200
    excluded="#52514e",
    not_counted="#898781",
    ran="#3987e5",  # blue 400, dark slot 1
    not_run="#1c5cab",  # blue 550
)

THEMES: tuple[Theme, ...] = (LIGHT, DARK)

#: G1 cannot follow the reader's theme, so it picks one neutral surface that
#: reads on both GitHub themes: the palette's neutral grey, framed by a muted
#: border. A mid-grey would drop the status red below 3:1.
G1_THEME: dict[str, str] = {
    "surface": "#f0efec",
    "border": "#898781",
    "ink": "#0b0b0b",
    "ink2": "#52514e",
    "chip": "#fcfcfb",
    "chip_border": "#c3c2b7",
    "track": "#e1e0d9",
    "flag": "#d03b3b",
    "clean": "#898781",
    "good": "#0ca30c",
}

#: G2 is a terminal, so dark.
G2_THEME: dict[str, str] = {
    "surface": "#1a1a19",
    "bar": "#2c2c2a",
    "border": "#52514e",
    "text": "#e1e0d9",
    "prompt": "#898781",
    "command": "#ffffff",
    "caption": "#c3c2b7",
}

#: Every palette a figure uses, for ``scripts/validate_palette.js``:
#: ``(what, mode, kind, colours, surface)``. ``kind`` "ordinal" runs the ramp
#: checks (``--ordinal``). The greys and text tokens are not identity colours, so
#: they are checked for contrast only (:data:`CONTRAST_CHECKS`).
PALETTES: tuple[tuple[str, str, str, tuple[str, ...], str], ...] = (
    ("F1 real flag (status critical)", "light", "categorical", ("#d03b3b",), LIGHT.surface),
    ("F1 real flag (status critical)", "dark", "categorical", ("#d03b3b",), DARK.surface),
    ("F2 releases, anchor -> under test", "light", "ordinal", (LIGHT.before, LIGHT.after), LIGHT.surface),
    ("F2 releases, anchor -> under test", "dark", "ordinal", (DARK.before, DARK.after), DARK.surface),
    ("F3 countable, not run -> ran", "light", "ordinal", (LIGHT.not_run, LIGHT.ran), LIGHT.surface),
    ("F3 countable, not run -> ran", "dark", "ordinal", (DARK.not_run, DARK.ran), DARK.surface),
    ("G1 reaches the line (status critical)", "light", "categorical", (G1_THEME["flag"],), G1_THEME["surface"]),
)

#: ``(what, colour, surface, minimum ratio)``: marks at 3:1, text at 4.5:1. A
#: grey below 3:1 is a context mark that every figure also labels directly.
CONTRAST_CHECKS: tuple[tuple[str, str, str, float], ...] = (
    ("light text ink2", LIGHT.ink2, LIGHT.surface, 4.5),
    ("dark text ink2", DARK.ink2, DARK.surface, 4.5),
    ("light clean point", LIGHT.clean, LIGHT.surface, 3.0),
    ("dark clean point", DARK.clean, DARK.surface, 3.0),
    ("light tie diamond", LIGHT.tie, LIGHT.surface, 3.0),
    ("dark tie diamond", DARK.tie, DARK.surface, 3.0),
    ("light F3 not counted", LIGHT.not_counted, LIGHT.surface, 3.0),
    ("dark F3 not counted", DARK.not_counted, DARK.surface, 3.0),
    ("G1 text ink2", G1_THEME["ink2"], G1_THEME["surface"], 4.5),
    ("G1 clean bar", G1_THEME["clean"], G1_THEME["surface"], 3.0),
    ("G2 output text", G2_THEME["text"], G2_THEME["surface"], 4.5),
    ("G2 prompt", G2_THEME["prompt"], G2_THEME["surface"], 4.5),
    ("G2 caption", G2_THEME["caption"], G2_THEME["surface"], 4.5),
)

# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _pct(x: float | None) -> str:
    # The rendering report._pct and closeout._pct use, so a figure and a table agree.
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _short(task: str) -> str:
    return task.split("/", 1)[-1]


def _scorer_short(scorer: str) -> str:
    return scorer.split("/", 1)[-1]


def _plural(n: int, one: str, many: str) -> str:
    return one if n == 1 else many


def _names(items: Sequence[str]) -> str:
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _literal(text: str) -> str:
    """A completion as a quoted literal: ``"No Yes"``, ``""``, ``"\\n"``."""
    return '"' + json.dumps(text, ensure_ascii=False)[1:-1] + '"'


def _clip_literal(text: str, max_chars: int) -> str:
    lit = _literal(text)
    if len(lit) <= max_chars:
        return lit
    return lit[: max(2, max_chars - 2)] + '…"'


def _release(payload: Mapping[str, Any] | None) -> str | None:
    return ((payload or {}).get("pins") or {}).get("inspect_evals")


def _scored(floor: TaskFloor) -> bool:
    return floor.error is None and bool(floor.members) and not floor.nothing_scored


def _group(floors: Iterable[TaskFloor]) -> dict[str, list[TaskFloor]]:
    by_task: dict[str, list[TaskFloor]] = {}
    for f in floors:
        by_task.setdefault(f.task, []).append(f)
    return by_task


def floors_after_rulings(
    payload: Mapping[str, Any], rulings: Sequence[Any] = ()
) -> list[TaskFloor]:
    """``report.floors_from_payload`` then ``rulings.apply_rulings``: the same two
    steps ``report.write_all`` takes, so a figure reads the floors a table reads."""
    from .report import floors_from_payload
    from .rulings import apply_rulings

    after, _, _ = apply_rulings(floors_from_payload(dict(payload)), list(rulings))
    return after


# --------------------------------------------------------------------------
# Rows: F1
# --------------------------------------------------------------------------


#: The triage classes of build guide B9. A real flag's ``cause`` is the first of
#: these that its ``note`` ruling names, so the figure never classifies a flag
#: the rulings have not.
TRIAGE_CLASSES: tuple[str, ...] = ("scorer defect", "task property", "instrument fault")

_STATE_ORDER = {"flag": 0, "tie": 1, "clean": 2}


def _note_cause(task: str, scorer: str, rulings: Sequence[Any]) -> str:
    """The triage class the last ``note`` ruling on this task and scorer names,
    the way ``closeout._note_source`` picks the ruling; "" when none does."""
    text = ""
    for r in rulings:
        if getattr(r, "action", None) != "note" or r.task != task:
            continue
        if getattr(r, "scorer", None) and r.scorer != scorer:
            continue
        text = f"{r.reason} {r.source}".lower()
    hits = [(text.find(c), c) for c in TRIAGE_CLASSES if c in text]
    return min(hits)[1] if hits else ""


def f1_rows(
    after_floors: Sequence[TaskFloor], counts: CloseoutCounts, rulings: Sequence[Any] = ()
) -> list[dict[str, Any]]:
    """One row per task that ran, on its :func:`closeout.representative_floor`,
    sorted by gap (largest first; at equal gaps flags, then ties, then clean);
    then one row per not-run task, with its reason.

    ``state`` is ``flag`` (a real flag), ``tie`` (a collision tie, counted in F),
    ``clean`` or ``not_run``. It is read from the same floor ``counts`` read, and a
    disagreement with ``counts`` raises rather than drawing a second answer. A
    real flag's ``flag_member`` is picked the way the README's first line picks
    it, and its ``cause`` comes from a ``note`` ruling (:data:`TRIAGE_CLASSES`).
    """
    by_task = _group(after_floors)
    flagged, ties = set(counts.flagged), set(counts.ties)
    rows: list[dict[str, Any]] = []
    for task in counts.ran:
        floors = by_task.get(task)
        if not floors:
            raise ValueError(f"{task} is in counts.ran but has no floor")
        f = representative_floor(floors)
        if f.flagged != (task in flagged) or (f.flagged and f.collision) != (task in ties):
            raise ValueError(f"{task}: the floor and the counts disagree on its flag")
        state = "tie" if task in ties else "flag" if task in flagged else "clean"
        collided = f.members.get(COLLISION_MEMBER) if state == "tie" else None
        member = ""
        if state == "flag":
            member = min(f.flagged_by, key=lambda m: (-f.members[m].mean, m))
        rows.append(
            {
                "task": task,
                "scorer": f.scorer,
                "n_scorers": len(floors),
                "state": state,
                "majority": f.majority,
                "majority_label": f.majority_label,
                "best_member": f.best_member,
                "best_mean": f.best_mean,
                "gap": f.gap_to_majority,
                "flagged_by": list(f.flagged_by),
                "flag_member": member,
                "flag_mean": f.members[member].mean if member else None,
                "collision_completion": collided.example_completion if collided else "",
                "cause": _note_cause(task, f.scorer, rulings) if state == "flag" else "",
                "reason": "",
            }
        )
    rows.sort(key=lambda r: (-r["gap"], _STATE_ORDER[r["state"]], r["task"]))
    for task, reason in counts.not_run:
        rows.append(
            {
                "task": task,
                "scorer": "",
                "n_scorers": len(by_task.get(task, [])),
                "state": "not_run",
                "majority": None,
                "majority_label": "",
                "best_member": "",
                "best_mean": None,
                "gap": None,
                "flagged_by": [],
                "flag_member": "",
                "flag_mean": None,
                "collision_completion": "",
                "cause": "",
                "reason": reason,
            }
        )
    return rows


def _f1_tally(rows: Sequence[Mapping[str, Any]]) -> tuple[int, int, int]:
    """(N, F, K) from F1's rows: what the figure actually draws."""
    drawn = [r for r in rows if r["state"] != "not_run"]
    F = sum(1 for r in drawn if r["state"] in ("flag", "tie"))
    K = sum(1 for r in drawn if r["state"] == "tie")
    return len(drawn), F, K


# --------------------------------------------------------------------------
# Rows: F2 (and G1)
# --------------------------------------------------------------------------


def _fix_floor(payload: Mapping[str, Any], rulings: Sequence[Any], task: str) -> TaskFloor | None:
    floors = [f for f in floors_after_rulings(payload, rulings) if f.task == task]
    if not floors:
        return None
    f = representative_floor(floors)
    return f if _scored(f) else None


def f2_rows(
    anchor_payload: Mapping[str, Any],
    payload: Mapping[str, Any],
    rulings: Sequence[Any] = (),
    task: str = FIX_TASK,
) -> list[dict[str, Any]]:
    """One row per content-free member of ``task``: anchor release, then the
    release under test. Each side's majority is read from its own payload.
    Empty when either side has no scored floor for the task."""
    before = _fix_floor(anchor_payload, rulings, task)
    after = _fix_floor(payload, rulings, task)
    if before is None or after is None:
        return []
    rows: list[dict[str, Any]] = []
    for name in CONTENT_FREE_NAMES:
        b, a = before.members.get(name), after.members.get(name)
        if b is None and a is None:
            continue
        rows.append(
            {
                "task": task,
                "member": name,
                "release_before": _release(anchor_payload),
                "release_after": _release(payload),
                "scorer_before": before.scorer,
                "scorer_after": after.scorer,
                "majority_before": before.majority,
                "majority_after": after.majority,
                "completion_before": b.example_completion if b else "",
                "completion_after": a.example_completion if a else "",
                "applicable_before": bool(b and b.applicable),
                "applicable_after": bool(a and a.applicable),
                "score_before": b.mean if b and b.applicable else None,
                "score_after": a.mean if a and a.applicable else None,
                "reaches_before": name in before.flagged_by,
                "reaches_after": name in after.flagged_by,
            }
        )
    return rows


# --------------------------------------------------------------------------
# Rows: F3
# --------------------------------------------------------------------------

#: F3's exclusion segments: the inventory's reasons, grouped. A reason not
#: named here (one a newer inventory adds) gets its own segment under its key.
EXCLUSION_SEGMENTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("sandbox", "sandbox", ("sandbox_required",)),
    ("optional_dependency", "optional dependency", ("extra_dependency",)),
    ("grader", "grader", ("model_graded",)),
    (
        "network_gated_large",
        "network, gated or too large",
        ("network_required", "gated_dataset", "too_large"),
    ),
)


def default_countable(payload: Mapping[str, Any], rulings: Sequence[Any] = ()) -> list[str]:
    """The countable list: a close-out payload's own task list, else
    ``cli.closeout_task_list`` (``CLOSEOUT_TASKS`` minus ``not_counted`` rows)."""
    if payload.get("closeout"):
        return [str(t) for t in payload["tasks"]]
    from .cli import closeout_task_list

    return closeout_task_list(list(rulings))


def f3_rows(
    anchor_inventory: Sequence[Mapping[str, Any]],
    countable: Sequence[str],
    counts: CloseoutCounts,
    rulings: Sequence[Any] = (),
) -> list[dict[str, Any]]:
    """The bar's segments, left to right, over the anchor inventory alone:
    exclusions, not counted, then the countable list split into ran and not run.

    The release inventory is never a segment; its R of D is caption text.
    """
    from collections import Counter

    excluded = [r for r in anchor_inventory if not r.get("reachable")]
    reachable = {str(r["name"]) for r in anchor_inventory if r.get("reachable")}
    countable_set = set(countable)
    stray = sorted(countable_set - reachable)
    if stray:
        raise ValueError(f"countable tasks not reachable in the anchor inventory: {stray}")

    reasons = Counter(str(r.get("exclusion_reason") or "unclassified") for r in excluded)
    by_reason: dict[str, list[str]] = {}
    for r in excluded:
        by_reason.setdefault(str(r.get("exclusion_reason") or "unclassified"), []).append(
            str(r["name"])
        )

    segments: list[dict[str, Any]] = []
    cursor = 0

    def add(segment: str, label: str, kind: str, tasks: Sequence[str], detail: str) -> None:
        nonlocal cursor
        if not tasks:
            return
        segments.append(
            {
                "segment": segment,
                "label": label,
                "kind": kind,
                "count": len(tasks),
                "start": cursor,
                "end": cursor + len(tasks),
                "tasks": sorted(tasks),
                "detail": detail,
            }
        )
        cursor += len(tasks)

    named = set()
    for key, label, keys in EXCLUSION_SEGMENTS:
        named.update(keys)
        tasks = [t for k in keys for t in by_reason.get(k, [])]
        detail = "; ".join(f"{k} {reasons[k]}" for k in keys if reasons.get(k))
        add(key, label, "excluded", tasks, detail)
    for k in sorted(set(reasons) - named):
        add(k, k.replace("_", " "), "excluded", by_reason[k], f"{k} {reasons[k]}")

    not_counted_rows = {
        r.task: r for r in rulings if getattr(r, "action", None) == "not_counted"
    }
    off_list = sorted(reachable - countable_set)
    groups: dict[str, list[str]] = {}
    for t in off_list:
        row = not_counted_rows.get(t)
        treatment = (getattr(row, "treatment", None) or "") if row else ""
        groups.setdefault(treatment or "no not_counted row in rulings.jsonl yet", []).append(t)
    detail = "; ".join(
        f"{treatment}: {', '.join(_short(t) for t in sorted(ts))}"
        for treatment, ts in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    )
    add("not_counted", "not counted", "not_counted", off_list, detail)

    ran = sorted(t for t in counts.ran if t in countable_set)
    reasons_by_task = dict(counts.not_run)
    not_run = sorted(countable_set - set(ran))
    nr_groups: dict[str, list[str]] = {}
    for t in not_run:
        nr_groups.setdefault(reasons_by_task.get(t, "not in this payload"), []).append(t)
    add("ran", "ran", "ran", ran, f"inspect_evals {counts.release}")
    add(
        "not_run",
        "not run",
        "not_run",
        not_run,
        "; ".join(
            f"{reason}: {', '.join(_short(t) for t in sorted(ts))}"
            for reason, ts in sorted(nr_groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        ),
    )
    return segments


def _f3_totals(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    def total(*kinds: str) -> int:
        return sum(r["count"] for r in rows if r["kind"] in kinds)

    return {
        "declared": rows[-1]["end"] if rows else 0,
        "reachable": total("not_counted", "ran", "not_run"),
        "not_counted": total("not_counted"),
        "countable": total("ran", "not_run"),
        "ran": total("ran"),
        "not_run": total("not_run"),
    }


# --------------------------------------------------------------------------
# The data API
# --------------------------------------------------------------------------


def figure_data(
    after_floors: Sequence[TaskFloor],
    payload: Mapping[str, Any],
    counts: CloseoutCounts,
    anchor_payload: Mapping[str, Any] | None = None,
    inventories: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    *,
    rulings: Sequence[Any] = (),
    countable: Sequence[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Every figure's rows, keyed by figure id. Pure; draws nothing.

    ``after_floors`` are the deterministic floors after rulings (and after
    ``report.apply_repeat`` when there was a second run); ``counts`` is
    ``closeout.counts`` over those floors. ``inventories`` maps ``"anchor"`` to
    the inventory the countable list was fixed from (the 0.20.0 one) and,
    optionally, ``"release"`` to the payload release's own; only ``"anchor"`` is
    drawn. ``rulings`` supplies ``not_counted`` treatments and is applied to the
    anchor payload for F2. ``countable`` defaults to :func:`default_countable`.

    F1 is always present. F3 needs ``inventories["anchor"]``. F2 needs an
    ``anchor_payload`` on a different release from ``payload``'s, with a scored
    ``paws`` floor on both, so it appears only after the close-out sweep. G1 is
    drawn from F2's rows.
    """
    data: dict[str, list[dict[str, Any]]] = {"F1": f1_rows(after_floors, counts, rulings)}
    anchor_inventory = (inventories or {}).get("anchor")
    if anchor_inventory is not None:
        listed = list(countable) if countable is not None else default_countable(payload, rulings)
        data["F3"] = f3_rows(anchor_inventory, listed, counts, rulings)
    if anchor_payload is not None and _release(anchor_payload) != _release(payload):
        rows = f2_rows(anchor_payload, payload, rulings)
        if rows:
            data["F2"] = rows
    return data


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


def data_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    """sha256 over canonical JSON of the rows: same rows, same digest, whatever
    the file bytes. Floats are written by ``json`` (shortest round-trip repr)."""
    blob = json.dumps(
        _canonical(list(rows)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def cell(value: Any) -> str:
    """How one value is written in a CSV cell. Floats keep full precision."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return ";".join(cell(v) for v in value)
    return str(value)


def write_data(
    rows: Sequence[Mapping[str, Any]], path: pathlib.Path, fields: Sequence[str] | None = None
) -> pathlib.Path:
    """The plotted rows as CSV, LF line ends, one header row."""
    fields = list(fields or (rows[0].keys() if rows else ()))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(fields)
        for row in rows:
            writer.writerow([cell(row.get(k)) for k in fields])
    return path


def read_data(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def members_above_zero_rows(after_floors: Sequence[TaskFloor]) -> dict[str, list[str]]:
    """Per content-free member, the tasks on which it ever scores above zero."""
    out: dict[str, set[str]] = {name: set() for name in CONTENT_FREE_NAMES}
    for f in after_floors:
        if not _scored(f):
            continue
        for name in CONTENT_FREE_NAMES:
            s = f.members.get(name)
            if s is not None and s.applicable and s.mean > 0.0:
                out[name].add(f.task)
    return {name: sorted(tasks) for name, tasks in out.items()}


def members_above_zero(after_floors: Sequence[TaskFloor], max_names: int = 6) -> str:
    """One computed sentence: which members ever score above zero, and where."""
    rows = members_above_zero_rows(after_floors)
    n_tasks = len({f.task for f in after_floors if _scored(f)})
    some = [(m, ts) for m, ts in rows.items() if ts]
    none = [m for m, ts in rows.items() if not ts]
    some.sort(key=lambda kv: (-len(kv[1]), kv[0]))
    parts = []
    for member, tasks in some:
        where = (
            f"{len(tasks)} of {n_tasks} tasks"
            if len(tasks) > max_names
            else f"{len(tasks)} ({_names([_short(t) for t in tasks])})"
        )
        parts.append(f"`{member}` on {where}")
    total = len(CONTENT_FREE_NAMES)
    if not some:
        return f"None of the {total} content-free members scores above zero on any of {n_tasks} tasks."
    head = (
        f"{len(some)} of the {total} content-free members score above zero somewhere: "
        if len(some) > 1
        else f"1 of the {total} content-free members scores above zero somewhere: "
    )
    tail = ""
    if none:
        tail = (
            f"; {_names([f'`{m}`' for m in none])} "
            + _plural(len(none), "scores", "score")
            + " zero on every task"
        )
    return head + "; ".join(parts) + tail + "."


# --------------------------------------------------------------------------
# Computed text: title, subtitle, alt text, caption, table twin
# --------------------------------------------------------------------------


def _reachers(rows: Sequence[Mapping[str, Any]], side: str) -> list[str]:
    return [r["member"] for r in rows if r[f"reaches_{side}"]]


def _who_reaches(names: Sequence[str]) -> str:
    if not names:
        return "no content-free member reaches"
    return f"{_names(list(names))} {_plural(len(names), 'reaches', 'reach')}"


def _f2_majorities(rows: Sequence[Mapping[str, Any]]) -> tuple[float, float]:
    return rows[0]["majority_before"], rows[0]["majority_after"]


def _tie_completions(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return sorted({r["collision_completion"] for r in rows if r["state"] == "tie"})


def tie_sentence(rows: Sequence[Mapping[str, Any]]) -> str:
    """F1's label for a collision tie, with the completion read from the rows."""
    comps = _tie_completions(rows)
    shown = " or ".join(_literal(c) for c in comps) if comps else "the placeholder"
    return f"{shown} is also the majority answer: a tie by construction (§8.5)"


def title(fig_id: str, rows: Sequence[Mapping[str, Any]], counts: CloseoutCounts | None = None) -> str:
    """The figure's title, computed. F2 needs no counts; F1 and F3 do."""
    if fig_id == "F1":
        N, F, K = _f1_tally(rows)
        return f"{F - K} of {N} beyond {K} {_plural(K, 'tie', 'ties')}, inspect_evals {counts.release}"
    if fig_id == "F2":
        rb, ra = rows[0]["release_before"], rows[0]["release_after"]
        b, a = _reachers(rows, "before"), _reachers(rows, "after")
        after = "none does" if not a else _who_reaches(a)
        return f"{_short(rows[0]['task'])}: {_who_reaches(b)} the majority on {rb}; {after} on {ra}"
    if fig_id == "F3":
        t = _f3_totals(rows)
        return (
            f"{t['countable']} of {t['declared']} declared tasks are countable; "
            f"{t['ran']} ran on inspect_evals {counts.release}"
        )
    raise KeyError(fig_id)


def subtitle(fig_id: str, rows: Sequence[Mapping[str, Any]], counts: CloseoutCounts) -> str:
    if fig_id == "F1":
        N, F, K = _f1_tally(rows)
        return (
            "Per task, after rulings: the majority baseline (tick) and the best "
            "content-free answer (point). §4 flags a task when the point reaches the "
            f"tick; {F} {_plural(F, 'does', 'do')}, and {K} of those "
            f"{_plural(K, 'is a tie', 'are ties')} by construction."
        )
    if fig_id == "F2":
        mb, ma = _f2_majorities(rows)
        rb, ra = rows[0]["release_before"], rows[0]["release_after"]
        line = (
            f"majority {_pct(mb)} on both"
            if mb == ma
            else f"majority {_pct(mb)} on {rb}, {_pct(ma)} on {ra}"
        )
        return (
            f"Each content-free member's score on {rb} ({_scorer_short(rows[0]['scorer_before'])}) "
            f"and {ra} ({_scorer_short(rows[0]['scorer_after'])}), {line}, "
            "each read from its own payload."
        )
    if fig_id == "F3":
        t = _f3_totals(rows)
        return (
            f"Every task declared in the {counts.anchor_release} inventory, once: "
            f"{t['declared'] - t['reachable']} excluded with a reason, "
            f"{t['not_counted']} reachable but not counted, {t['countable']} countable."
        )
    raise KeyError(fig_id)


def alt_text(fig_id: str, rows: Sequence[Mapping[str, Any]], counts: CloseoutCounts) -> str:
    """The image's alt text, computed from the rows the image draws."""
    if fig_id == "F1":
        N, F, K = _f1_tally(rows)
        drawn = [r for r in rows if r["state"] != "not_run"]
        real = [r for r in drawn if r["state"] == "flag"]
        ties = [r for r in drawn if r["state"] == "tie"]
        clean = [r for r in drawn if r["state"] == "clean"]
        parts = [
            f"Dot plot of {N} tasks on inspect_evals {counts.release}, one row per task, "
            "sorted by gap: a tick at each task's majority baseline and a point at its "
            "best content-free score."
        ]
        if real:
            parts.append(
                f"{len(real)} {_plural(len(real), 'task is', 'tasks are')} flagged beyond the ties: "
                + "; ".join(
                    f"{_short(r['task'])}, where {r['flag_member']} scores "
                    f"{_pct(r['flag_mean'])} against a {_pct(r['majority'])} majority"
                    + (f" ({r['cause']}, per its note ruling)" if r["cause"] else "")
                    for r in real
                )
                + "."
            )
        else:
            parts.append("No task is flagged beyond the ties.")
        if ties:
            parts.append(
                f"{len(ties)} {_plural(len(ties), 'task ties', 'tasks tie')} the majority exactly "
                f"({_names([_short(r['task']) for r in ties])}), because "
                f"{tie_sentence(rows)}; "
                f"{_plural(len(ties), 'it is', 'they are')} counted in the {F} flags."
            )
        zeros = [r for r in clean if r["majority"] == 0.0 and r["best_mean"] == 0.0]
        below = [r for r in clean if r not in zeros]
        if zeros:
            parts.append(
                f"On {_names([_short(r['task']) for r in zeros])} the majority answer itself "
                "scores 0.0%, and a zero never flags."
            )
        if below:
            gaps = [100 * r["gap"] for r in below]
            parts.append(
                f"The other {len(below)} sit below their baseline, by "
                f"{min(-g for g in gaps):.1f} to {max(-g for g in gaps):.1f} points."
            )
        not_run = [r for r in rows if r["state"] == "not_run"]
        if not_run:
            listed = "; ".join(_short(r["task"]) + " (" + r["reason"] + ")" for r in not_run)
            parts.append(f"Not run: {listed}.")
        return " ".join(parts)
    if fig_id == "F2":
        rb, ra = rows[0]["release_before"], rows[0]["release_after"]
        mb, ma = _f2_majorities(rows)
        each = "; ".join(
            f"{r['member']} {_pct(r['score_before'])} then {_pct(r['score_after'])}"
            for r in rows
        )
        maj = (
            f"the {_pct(mb)} majority line"
            if mb == ma
            else f"majority lines at {_pct(mb)} ({rb}) and {_pct(ma)} ({ra})"
        )
        return (
            f"Dumbbell chart of {_short(rows[0]['task'])}'s content-free members on "
            f"inspect_evals {rb} and {ra}, against {maj}: {each}. {title('F2', rows, counts)}."
        )
    if fig_id == "F3":
        t = _f3_totals(rows)
        segs = "; ".join(f"{r['label']} {r['count']}" for r in rows)
        return (
            f"One horizontal bar of the {t['declared']} tasks declared in the "
            f"{counts.anchor_release} inventory, split into {segs}. The countable "
            f"{t['countable']} are highlighted; {t['ran']} of them ran on inspect_evals "
            f"{counts.release}."
        )
    raise KeyError(fig_id)


def caption(fig_id: str, rows: Sequence[Mapping[str, Any]], counts: CloseoutCounts) -> str:
    """The line printed under the figure."""
    name = FIGURE_NAMES[fig_id]
    if fig_id == "F1":
        N, F, K = _f1_tally(rows)
        return (
            f"{F} of {N} tasks flagged under §4, {K} of them ties by construction (§8.5), "
            f"on inspect_evals {counts.release}. Data: `{name}.csv`."
        )
    if fig_id == "F2":
        return f"{title('F2', rows, counts)}. Data: `{name}.csv`."
    if fig_id == "F3":
        t = _f3_totals(rows)
        text = (
            f"{t['declared']} declared in the {counts.anchor_release} inventory, "
            f"{t['reachable']} reachable, {t['not_counted']} not counted, "
            f"{t['countable']} countable, {t['ran']} ran."
        )
        if counts.release != counts.anchor_release:
            text += (
                f" inspect_evals {counts.release}'s own inventory reaches {counts.R} of "
                f"{counts.D} declared; it is not part of the bar."
            )
        return text + f" Data: `{name}.csv`."
    raise KeyError(fig_id)


def _md(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def table_twin(fig_id: str, rows: Sequence[Mapping[str, Any]]) -> str:
    """The figure's rows as a markdown table, for a ``<details>`` block."""
    lines: list[str] = []
    if fig_id == "F1":
        lines += [
            "| task | scorer | majority | best content-free | score | gap | §4 |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in rows:
            if r["state"] == "not_run":
                lines.append(f"| `{_short(r['task'])}` | - | - | - | - | - | not run: {_md(r['reason'])} |")
                continue
            mark = {"flag": "**flagged**", "tie": "flagged, tie (§8.5)", "clean": "clean"}[r["state"]]
            if r["cause"]:
                mark += f" ({r['cause']})"
            lines.append(
                f"| `{_short(r['task'])}` | `{_md(r['scorer'])}` | {_pct(r['majority'])} | "
                f"{r['best_member']} | {_pct(r['best_mean'])} | {100 * r['gap']:+.1f} pts | {mark} |"
            )
    elif fig_id == "F2":
        rb, ra = rows[0]["release_before"], rows[0]["release_after"]
        mb, ma = _f2_majorities(rows)
        lines += [
            f"| member | completion | {rb} | {ra} |",
            "|---|---|---|---|",
            f"| *majority* | | {_pct(mb)} | {_pct(ma)} |",
        ]
        for r in rows:
            comp = _clip_literal(r["completion_before"], 40)
            if r["completion_after"] != r["completion_before"]:
                comp += " / " + _clip_literal(r["completion_after"], 40)
            b = _pct(r["score_before"]) + (" **reaches**" if r["reaches_before"] else "")
            a = _pct(r["score_after"]) + (" **reaches**" if r["reaches_after"] else "")
            lines.append(f"| {r['member']} | `{_md(comp)}` | {b} | {a} |")
    elif fig_id == "F3":
        lines += ["| segment | tasks | detail |", "|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['label']} | {r['count']} | {_md(r['detail'])} |")
        lines.append(f"| **declared** | **{_f3_totals(rows)['declared']}** | |")
    else:
        raise KeyError(fig_id)
    return "\n".join(lines)


def figure_texts(
    fig_id: str,
    rows: Sequence[Mapping[str, Any]],
    counts: CloseoutCounts,
    source: str = "",
) -> dict[str, str]:
    digest = data_digest(rows)
    return {
        "title": title(fig_id, rows, counts),
        "subtitle": subtitle(fig_id, rows, counts),
        "alt": alt_text(fig_id, rows, counts),
        "caption": caption(fig_id, rows, counts),
        "footer": (
            (f"Data: {source}. " if source else "")
            + f"Rows sha256 {digest[:12]}, in {FIGURE_NAMES[fig_id]}.csv. "
            "Generated by python -m evalfloor.figures."
        ),
        "digest": digest,
    }


def readme_figures(
    data: Mapping[str, Sequence[Mapping[str, Any]]], counts: CloseoutCounts
) -> list[tuple[str, str, str]]:
    """``(file stem, alt text, caption)`` per static figure present, README order."""
    return [
        (FIGURE_NAMES[i], alt_text(i, data[i], counts), caption(i, data[i], counts))
        for i in FIGURE_IDS
        if i in data
    ]


# --------------------------------------------------------------------------
# Loading the committed inputs (the CLI's half; the data API takes objects)
# --------------------------------------------------------------------------


def git_show(ref: str, path: str, cwd: pathlib.Path | None = None) -> str:
    out = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return out.stdout


def _display_path(path: pathlib.Path) -> str:
    """A path as a figure footer prints it: relative to the working directory,
    else from its ``results`` part on, so no machine's layout is drawn."""
    try:
        return path.resolve().relative_to(pathlib.Path.cwd().resolve()).as_posix()
    except ValueError:
        parts = path.parts
        k = max((i for i, p in enumerate(parts) if p == "results"), default=max(0, len(parts) - 2))
        return pathlib.PurePosixPath(*parts[k:]).as_posix()


@dataclass
class Inputs:
    payload: dict[str, Any]
    after_floors: list[TaskFloor]
    counts: CloseoutCounts
    rulings: list[Any]
    anchor_payload: dict[str, Any] | None
    inventories: dict[str, list[dict[str, Any]]]
    sources: dict[str, str]


def load_inputs(
    results: pathlib.Path = pathlib.Path("results"),
    rulings_path: pathlib.Path = pathlib.Path("rulings.jsonl"),
    before_ref: str = LIST_FIXED_AT,
    after: pathlib.Path | None = None,
    repeat: pathlib.Path | None = None,
) -> Inputs:
    """Read the committed results the way ``report`` does, and compute counts."""
    from . import closeout
    from .report import apply_repeat, floors_from_payload, read_sweep
    from .rulings import apply_rulings, load_rulings

    payload_path = after or results / "sweep.json"
    payload = read_sweep(payload_path)
    rules = load_rulings(rulings_path)
    before = floors_from_payload(payload)
    moved: list[str] = []
    if repeat is not None:
        moved = apply_repeat(before, payload, read_sweep(repeat))
    after_floors, _, _ = apply_rulings(before, rules)

    sources = {"payload": f"{_display_path(payload_path)} (sweep digest {str(payload.get('digest', ''))[:12]})"}
    anchor_inv_path = results / "graded" / "task_inventory.json"
    if anchor_inv_path.exists():
        anchor_inventory = json.loads(anchor_inv_path.read_text(encoding="utf-8"))
        sources["anchor_inventory"] = _display_path(anchor_inv_path)
    else:
        anchor_inventory = json.loads(git_show(before_ref, "results/task_inventory.json"))
        sources["anchor_inventory"] = f"{before_ref}:results/task_inventory.json"
    release_inv_path = results / "task_inventory.json"
    release_inventory = json.loads(release_inv_path.read_text(encoding="utf-8"))

    try:
        anchor_payload = json.loads(git_show(before_ref, "results/sweep.json"))
        sources["anchor_payload"] = f"{before_ref}:results/sweep.json"
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        anchor_payload = None

    counts = closeout.counts(
        after_floors,
        payload,
        rules,
        release_inventory,
        anchor_inventory,
        nondeterministic=moved,
        anchor_release=_release(anchor_payload) or ANCHOR_RELEASE,
    )
    return Inputs(
        payload=payload,
        after_floors=after_floors,
        counts=counts,
        rulings=rules,
        anchor_payload=anchor_payload,
        inventories={"anchor": anchor_inventory, "release": release_inventory},
        sources=sources,
    )


def g1_alt_text(rows: Sequence[Mapping[str, Any]]) -> str:
    rb, ra = rows[0]["release_before"], rows[0]["release_after"]
    mb, ma = _f2_majorities(rows)
    maj = _pct(mb) if mb == ma else f"{_pct(mb)} and {_pct(ma)}"
    return (
        f"Animation in two panels, inspect_evals {rb} on the left and {ra} on the right: "
        f"each of {_short(rows[0]['task'])}'s {len(rows)} content-free completions is typed in, "
        f"then its score bar grows against the {maj} majority line. "
        + "; ".join(f"{r['member']} {_pct(r['score_before'])} then {_pct(r['score_after'])}" for r in rows)
        + f". {title('F2', rows, None)}."
    )


def g1_caption(rows: Sequence[Mapping[str, Any]]) -> str:
    return (
        f"{title('F2', rows, None)}. `echo` varies per sample; one example is shown. "
        f"Data: `{FIGURE_NAMES['F2']}.csv`."
    )


def load_captures(out_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Every ``g2-<name>.json`` capture in ``out_dir``, in release order."""
    caps = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out_dir.glob("g2-*.json"))]

    def key(cap: Mapping[str, Any]) -> tuple[Any, ...]:
        rel = capture_release(cap) or ""
        return (tuple(int(x) for x in rel.split(".") if x.isdigit()), cap.get("started_at", ""))

    return sorted(caps, key=key)


def g2_rows(caps: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """One row per capture: what it ran, on which release, and what it said."""
    return [
        {
            "command": c["display"],
            "release": capture_release(c),
            "returncode": c["returncode"],
            "elapsed_s": c["elapsed_s"],
            "recorded": str(c.get("started_at", ""))[:10],
            "verdicts": [f"{t}: {v}" for t, v in sorted(capture_verdicts(c).items())],
        }
        for c in caps
    ]


def g2_alt_text(caps: Sequence[Mapping[str, Any]]) -> str:
    runs = "; then ".join(
        f"`{r['command']}` on inspect_evals {r['release']} prints "
        + (", ".join(r["verdicts"]) or "no verdict")
        + f" and exits {r['returncode']} after {r['elapsed_s']:.1f} s"
        for r in g2_rows(caps)
    )
    return f"Terminal recording, real output with long waits compressed: {runs}."


def g2_caption(caps: Sequence[Mapping[str, Any]]) -> str:
    rows = g2_rows(caps)
    dates = sorted({r["recorded"] for r in rows})
    each = "; ".join(f"inspect_evals {r['release']}, exit {r['returncode']}" for r in rows)
    return f"Recorded {' and '.join(dates)}, real output; waits compressed. {each}."


def g2_table(caps: Sequence[Mapping[str, Any]]) -> str:
    lines = ["| command | release | verdict | exit | real time |", "|---|---|---|---|---|"]
    for r in g2_rows(caps):
        lines.append(
            f"| `{_md(r['command'])}` | {r['release']} | {_md(', '.join(r['verdicts']))} | "
            f"{r['returncode']} | {r['elapsed_s']:.1f} s |"
        )
    return "\n".join(lines)


def write_g2(caps: Sequence[Mapping[str, Any]], out_dir: pathlib.Path) -> list[pathlib.Path]:
    """``g2-terminal.{gif,txt}``: every capture, in order, in one terminal."""
    stem = FIGURE_NAMES["G2"]
    txt = out_dir / f"{stem}.txt"
    txt.write_bytes(g2_transcript(caps).encode("utf-8"))
    return [render_g2(caps, out_dir / f"{stem}.gif"), txt]


class FiguresStale(ValueError):
    """A committed figure no longer carries the rows the results give today."""


#: What to run when a committed figure is stale.
STALE_HINT = "figures are stale: run python -m evalfloor.figures --out docs/figures"


def _stale(why: str) -> FiguresStale:
    return FiguresStale(f"{STALE_HINT} ({why})")


def check_committed(
    data: Mapping[str, Sequence[Mapping[str, Any]]],
    caps: Sequence[Mapping[str, Any]],
    out_dir: pathlib.Path,
) -> None:
    """Refuse unless the images in ``out_dir`` are the ones these rows draw.

    Imports neither matplotlib nor Pillow. Each static figure's two SVGs must
    carry its rows' digest (G1 is drawn from F2's rows, so F2's SVGs stand for
    it); G2's transcript must be the one its captures give.
    """
    for fig_id in FIGURE_IDS:
        digest = data_digest(data[fig_id])
        for mode in ("light", "dark"):
            path = out_dir / f"{FIGURE_NAMES[fig_id]}-{mode}.svg"
            found = embedded_digest(path) if path.exists() else None
            if found != digest:
                state = f"carries rows sha256 {found[:12]}" if found else "is missing"
                raise _stale(f"{path.as_posix()} {state}; the results give {digest[:12]}")
    for fig_id in GIF_IDS:
        path = out_dir / f"{FIGURE_NAMES[fig_id]}.gif"
        if not path.exists():
            raise _stale(f"{path.as_posix()} is missing")
    txt = out_dir / f"{FIGURE_NAMES['G2']}.txt"
    if not txt.exists() or txt.read_bytes() != g2_transcript(caps).encode("utf-8"):
        raise _stale(f"{txt.as_posix()} is not the transcript of the g2-*.json captures")


def make_figure_provider(
    out_dir: pathlib.Path = pathlib.Path("docs/figures"),
    *,
    results: pathlib.Path = pathlib.Path("results"),
    rulings_path: pathlib.Path = pathlib.Path("rulings.jsonl"),
    before_ref: str = LIST_FIXED_AT,
    root: pathlib.Path = pathlib.Path("."),
    draw: bool = True,
) -> Any:
    """A ``report.FigureProvider``: called with ``payload``, ``floors`` (after
    rulings and the repeat), ``counts`` and ``repeat``, it draws F1, F2, F3 and
    G1 into ``out_dir``, replays the G2 captures already there, and returns one
    ``report.FigureRef`` per figure, paths relative to ``root`` (the README's
    directory). It refuses rather than return a figure with no data.

    With ``draw=False`` -- what ``evalfloor report`` uses -- nothing is drawn and
    neither drawing library is imported: :func:`check_committed` checks the
    committed images against the rows, raising :class:`FiguresStale` on any
    difference, then the CSVs are rewritten from the rows and the refs point at
    the committed files."""

    def rel(path: pathlib.Path) -> str:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def provider(*, payload: Mapping[str, Any], floors: Sequence[TaskFloor],
                 counts: CloseoutCounts, repeat: Any = None, **_: Any) -> list[Any]:
        from .report import FigureRef
        from .rulings import load_rulings

        rules = load_rulings(rulings_path)
        anchor_payload = json.loads(git_show(before_ref, "results/sweep.json"))
        inventories = {
            "anchor": json.loads((results / "graded" / "task_inventory.json").read_text(encoding="utf-8")),
            "release": json.loads((results / "task_inventory.json").read_text(encoding="utf-8")),
        }
        data = figure_data(floors, payload, counts, anchor_payload, inventories, rulings=rules)
        missing = [i for i in FIGURE_IDS if i not in data]
        if missing:
            raise ValueError(
                f"no data for {', '.join(missing)}: F2 needs the payload on a release other than "
                f"{_release(anchor_payload)} with a scored paws floor on both"
            )
        payload_src = f"results/sweep.json (sweep digest {str(payload.get('digest', ''))[:12]})"
        sources = {
            "F1": payload_src,
            "F2": f"{before_ref}:results/sweep.json and {payload_src}",
            "F3": "results/graded/task_inventory.json",
        }
        caps = load_captures(out_dir)
        if not caps:
            raise ValueError("G2 needs a capture: python -m evalfloor.figures --capture NAME -- <command>")
        if not draw:
            # Every check before any write, so a stale figure changes nothing.
            check_committed(data, caps, out_dir)
        refs: list[Any] = []
        svgs: dict[str, tuple[str, str]] = {}
        for fig_id in FIGURE_IDS:
            if draw:
                render_static(fig_id, data[fig_id], counts, out_dir, sources[fig_id])
            else:
                write_data(data[fig_id], out_dir / f"{FIGURE_NAMES[fig_id]}.csv", FIELDS[fig_id])
            stem = out_dir / FIGURE_NAMES[fig_id]
            svgs[fig_id] = (rel(stem.parent / f"{stem.name}-light.svg"), rel(stem.parent / f"{stem.name}-dark.svg"))
            refs.append(FigureRef(
                id=fig_id, alt=alt_text(fig_id, data[fig_id], counts),
                caption=caption(fig_id, data[fig_id], counts), data_digest=data_digest(data[fig_id]),
                light_svg=svgs[fig_id][0], dark_svg=svgs[fig_id][1], table_md=table_twin(fig_id, data[fig_id]),
            ))
        g1 = out_dir / f"{FIGURE_NAMES['G1']}.gif"
        if draw:
            g1 = render_g1(data["F2"], g1, sources=[f"{before_ref}:results/sweep.json", payload_src])
        refs.append(FigureRef(
            id="G1", alt=g1_alt_text(data["F2"]), caption=g1_caption(data["F2"]),
            # The GIF is the picture: report embeds it as a plain image. Its rows
            # are F2's, so F2's SVG digests are what stand for it when checked.
            data_digest=data_digest(data["F2"]), light_svg=rel(g1), dark_svg=rel(g1),
            table_md=table_twin("F2", data["F2"]), gif=rel(g1),
        ))
        gif = out_dir / f"{FIGURE_NAMES['G2']}.gif"
        if draw:
            gif, _txt = write_g2(caps, out_dir)
        refs.append(FigureRef(
            id="G2", alt=g2_alt_text(caps), caption=g2_caption(caps), data_digest=data_digest(caps),
            light_svg=rel(gif), dark_svg=rel(gif), table_md=g2_table(caps), gif=rel(gif),
            transcript=g2_transcript(caps).rstrip("\n"),
        ))
        return refs

    return provider


def _readme_figures_default() -> list[tuple[str, str, str]]:
    inputs = load_inputs()
    data = figure_data(
        inputs.after_floors,
        inputs.payload,
        inputs.counts,
        inputs.anchor_payload,
        inputs.inventories,
        rulings=inputs.rulings,
    )
    return readme_figures(data, inputs.counts)


def __getattr__(name: str) -> Any:
    # README_FIGURES is computed from the committed results on first access, so
    # importing this module reads nothing.
    if name == "README_FIGURES":
        return _readme_figures_default()
    raise AttributeError(name)


# --------------------------------------------------------------------------
# Drawing: shared matplotlib scaffolding (imported lazily)
# --------------------------------------------------------------------------

_SANS = ["Segoe UI", "DejaVu Sans"]
_MONO = ["Cascadia Mono", "Consolas", "DejaVu Sans Mono"]


def _pt(px: float) -> float:
    return px * 72.0 / DPI


def _rc(digest: str) -> dict[str, Any]:
    return {
        "font.family": _SANS,
        "svg.fonttype": "path",
        "svg.hashsalt": digest,
        "path.simplify": False,
        "axes.unicode_minus": True,
    }


class _Canvas:
    """A 1920x1080 figure with an overlay axes whose data units are pixels,
    y down from the top, for every mark that is not on a plot axis."""

    def __init__(self, theme: Theme) -> None:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure

        self.theme = theme
        self.fig = Figure(figsize=(SIZE[0] / DPI, SIZE[1] / DPI), dpi=DPI, facecolor=theme.surface)
        FigureCanvasAgg(self.fig)
        self.renderer = self.fig.canvas.get_renderer()
        ov = self.fig.add_axes((0, 0, 1, 1), zorder=5)
        ov.set_xlim(0, SIZE[0])
        ov.set_ylim(SIZE[1], 0)
        ov.axis("off")
        ov.patch.set_alpha(0.0)
        self.ov = ov
        self._widths: dict[tuple[Any, ...], float] = {}

    def text(self, x: float, y: float, s: str, px: float, color: str | None = None, **kw: Any) -> Any:
        kw.setdefault("va", "baseline")
        kw.setdefault("ha", "left")
        return self.ov.text(x, y, s, fontsize=_pt(px), color=color or self.theme.ink, **kw)

    def width(self, s: str, px: float, weight: str = "normal", mono: bool = False) -> float:
        key = (s, px, weight, mono)
        if key not in self._widths:
            t = self.ov.text(0, 0, s, fontsize=_pt(px), fontweight=weight, family=_MONO if mono else _SANS)
            self._widths[key] = t.get_window_extent(self.renderer).width
            t.remove()
        return self._widths[key]

    def plot_axes(self, x: float, y: float, w: float, h: float) -> Any:
        ax = self.fig.add_axes((x / SIZE[0], 1 - (y + h) / SIZE[1], w / SIZE[0], h / SIZE[1]), zorder=2)
        ax.set_facecolor("none")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0, colors=self.theme.ink2, labelsize=_pt(20))
        return ax

    def wrap(self, text: str, width_px: float, px: float) -> list[str]:
        words, lines, line = text.split(" "), [], ""
        for w in words:
            trial = f"{line} {w}" if line else w
            if line and self.width(trial, px) > width_px:
                lines.append(line)
                line = w
            else:
                line = trial
        if line:
            lines.append(line)
        return lines

    def header(self, title_text: str, subtitle_text: str) -> None:
        t = self.theme
        self.text(64, 76, title_text, 40, t.ink, fontweight="semibold")
        for i, line in enumerate(self.wrap(subtitle_text, 1792, 24)[:2]):
            self.text(64, 120 + 32 * i, line, 24, t.ink2)

    def footer(self, text: str) -> None:
        # Wrapped, never clipped: at most two lines, the last one at the bottom.
        lines = self.wrap(text, 1792, 18)[:2]
        for k, line in enumerate(reversed(lines)):
            self.text(64, SIZE[1] - 30 - 24 * k, line, 18, self.theme.ink2)

    def marker(self, x: float, y: float, kind: str, color: str, size_px: float = 16, hollow: bool = False) -> None:
        self.ov.plot(
            [x], [y], marker=kind, markersize=_pt(size_px),
            markerfacecolor=self.theme.surface if hollow else color,
            markeredgecolor=color if hollow else self.theme.surface,
            markeredgewidth=_pt(2.5 if hollow else 2), linestyle="none", zorder=6,
        )

    def tick(self, x: float, y: float, h: float, color: str) -> None:
        self.ov.plot([x, x], [y - h / 2, y + h / 2], color=color, lw=_pt(3), solid_capstyle="butt", zorder=6)

    def legend(self, items: Sequence[tuple[str, str, str, bool]], y: float) -> None:
        """``(kind, colour, label, hollow)`` in one row; ``kind`` "tick" or a marker."""
        x = 64.0
        for kind, color, label, hollow in items:
            if kind == "tick":
                self.tick(x + 8, y - 8, 22, color)
            else:
                self.marker(x + 8, y - 8, kind, color, 16, hollow)
            self.text(x + 26, y, label, 22, self.theme.ink2)
            x += 26 + self.width(label, 22) + 40

    def save(self, base: pathlib.Path, fig_id: str, digest: str, title_text: str) -> list[pathlib.Path]:
        import matplotlib

        desc = f"evalfloor.figures {fig_id} rows sha256 {digest}"
        svg = base.parent / f"{base.name}-{self.theme.mode}.svg"
        png = base.parent / f"{base.name}-{self.theme.mode}.png"
        buf = io.StringIO()
        self.fig.savefig(
            buf, format="svg", facecolor=self.theme.surface,
            metadata={"Date": None, "Description": desc, "Title": title_text,
                      "Creator": f"evalfloor.figures, matplotlib {matplotlib.__version__}"},
        )
        # LF on every platform, so the committed bytes equal the generated ones.
        svg.write_bytes(buf.getvalue().encode("utf-8"))
        self.fig.savefig(
            png, format="png", dpi=DPI, facecolor=self.theme.surface,
            metadata={"Description": desc, "Software": f"evalfloor.figures, matplotlib {matplotlib.__version__}"},
        )
        return [svg, png]


def _xaxis_percent(ax: Any, theme: Theme) -> None:
    ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
    ax.set_xticks(ticks)
    ax.set_xticklabels([f"{int(100 * t)}%" for t in ticks], color=theme.ink2, fontsize=_pt(20))
    for t in ticks:
        ax.axvline(t, color=theme.grid, lw=_pt(1), zorder=0)
    ax.set_yticks([])


# --------------------------------------------------------------------------
# F1
# --------------------------------------------------------------------------


def _draw_f1(rows: Sequence[Mapping[str, Any]], texts: Mapping[str, str], theme: Theme) -> _Canvas:
    cv = _Canvas(theme)
    cv.header(texts["title"], texts["subtitle"])
    drawn = [r for r in rows if r["state"] != "not_run"]
    not_run = [r for r in rows if r["state"] == "not_run"]
    states = {r["state"] for r in drawn}

    nr_lines: list[str] = []
    if not_run:
        nr_text = f"Not run ({len(not_run)}): " + "; ".join(
            f"{_short(r['task'])} ({r['reason']})" for r in not_run
        )
        nr_lines = cv.wrap(nr_text, 1792, 20)[:4]
    bottom = SIZE[1] - 64 - 30 * len(nr_lines) - 70
    top = 246.0
    panels = 1 if len(drawn) <= F1_ROWS_PER_PANEL else 2
    per = max(1, math.ceil(len(drawn) / panels))
    row_h = (bottom - top) / per
    label_px = 22.0 if row_h >= 34 else max(15.0, math.floor(row_h * 0.62))
    ann_px = max(15.0, label_px - 2)
    gutter = 56.0

    def row_label(r: Mapping[str, Any]) -> str:
        lab = _short(r["task"])
        if r["n_scorers"] > 1:
            lab += f" · {_scorer_short(r['scorer'])}"
        return lab

    full_tie = tie_sentence(rows)

    def zero(r: Mapping[str, Any]) -> bool:
        # The point sits on the tick but cannot flag: §4's zero guard. Said in
        # words, so it is never read as a tie.
        return r["state"] == "clean" and r["majority"] == 0.0 and r["best_mean"] == 0.0

    def annotation(r: Mapping[str, Any], compact: bool) -> str:
        if r["state"] == "flag":
            vs = "vs" if compact else "vs majority"
            text = f"{r['flag_member']} {_pct(r['flag_mean'])} {vs} {_pct(r['majority'])}"
            return text + (f" · {r['cause']}" if r["cause"] else "")
        if r["state"] == "tie":
            return f"{_pct(r['best_mean'])} · " + ("tie (§8.5)" if compact else full_tie)
        if zero(r):
            return "0.0% = majority: a zero never flags" if not compact else "zero: never flags"
        return ""

    chunks = [drawn[p * per : (p + 1) * per] for p in range(panels)]
    chunks = [c for c in chunks if c]
    label_ws = [max(cv.width(row_label(r), label_px) for r in c) + 20 for c in chunks]

    def ann_widths(compact: bool) -> list[float]:
        out = []
        for c in chunks:
            w = max([cv.width(annotation(r, compact), ann_px) for r in c if annotation(r, compact)] or [0])
            out.append(w + 56 if w else 0.0)
        return out

    def plot_width(anns: Sequence[float]) -> float:
        # One width for every panel, so the panels share one x scale.
        return (1792 - gutter * (len(chunks) - 1) - sum(label_ws) - sum(anns)) / len(chunks)

    compact = False
    ann_ws = ann_widths(False)
    # One panel keeps the full tie sentence on every tie row down to a plot
    # 28% of the width; two panels go compact sooner.
    min_plot = 0.28 * 1792 if len(chunks) == 1 else 0.36 * 1792 / len(chunks)
    if plot_width(ann_ws) < min_plot:
        compact = True
        ann_ws = ann_widths(True)
    plot_w = plot_width(ann_ws)

    legend: list[tuple[str, str, str, bool]] = [
        ("tick", theme.ink, "majority baseline", False),
        ("o", theme.clean, "best content-free answer", False),
    ]
    if "flag" in states:
        legend.append(("^", theme.flag, "flagged", False))
    if "tie" in states:
        # Full rows carry the sentence and the legend names it; compact rows say
        # only "tie (§8.5)", so then the legend carries the whole sentence.
        legend.append(("D", theme.tie, full_tie if compact else "tie by construction (§8.5)", True))
    cv.legend(legend, 206)

    x0 = 64.0
    for p, chunk in enumerate(chunks):
        label_w, ann_w = label_ws[p], ann_ws[p]
        anns = [annotation(r, compact) for r in chunk]
        plot_x = x0 + label_w
        x0 = plot_x + plot_w + ann_w + gutter
        ax = cv.plot_axes(plot_x, top, plot_w, bottom - top)
        ax.set_xlim(-0.025, 1.025)
        ax.set_ylim(per, 0)
        _xaxis_percent(ax, theme)
        for i, r in enumerate(chunk):
            yd = i + 0.5
            ypx = top + yd * row_h
            m, b = r["majority"], r["best_mean"]
            ax.plot([m, b], [yd, yd], color=theme.connector, lw=_pt(2), solid_capstyle="round", zorder=1)
            # Over the point: on a tie the tick runs through the hollow diamond.
            ax.plot([m, m], [yd - 0.32, yd + 0.32], color=theme.ink, lw=_pt(3), solid_capstyle="butt", zorder=5)
            if r["state"] == "tie":
                ax.plot([b], [yd], marker="D", markersize=_pt(15), markerfacecolor=theme.surface,
                        markeredgecolor=theme.tie, markeredgewidth=_pt(2.5), linestyle="none", zorder=4)
            else:
                color = theme.flag if r["state"] == "flag" else theme.clean
                ax.plot([b], [yd], marker="o", markersize=_pt(15), markerfacecolor=color,
                        markeredgecolor=theme.surface, markeredgewidth=_pt(2), linestyle="none", zorder=4)
            emphasis = r["state"] in ("flag", "tie")
            cv.text(plot_x - 16, ypx, row_label(r), label_px, theme.ink if emphasis else theme.ink2,
                    ha="right", va="center_baseline", fontweight="semibold" if r["state"] == "flag" else "normal")
            ann = anns[i]
            if ann:
                ax_x = plot_x + plot_w + 16
                if r["state"] == "flag":
                    cv.marker(ax_x + 8, ypx, "^", theme.flag, 14)
                    cv.text(ax_x + 24, ypx, ann, ann_px, theme.ink, va="center_baseline", fontweight="semibold")
                elif r["state"] == "clean":
                    cv.text(ax_x + 24, ypx, ann, ann_px, theme.ink2, va="center_baseline")
                else:
                    cv.marker(ax_x + 8, ypx, "D", theme.tie, 12, hollow=True)
                    cv.text(ax_x + 24, ypx, ann, ann_px, theme.ink2, va="center_baseline")
        cv.text(plot_x, bottom + 62, "score under the task's own scorer", 20, theme.ink2)
    for i, line in enumerate(nr_lines):
        cv.text(64, bottom + 100 + 30 * i, line, 20, theme.ink2)
    cv.footer(texts["footer"])
    return cv


# --------------------------------------------------------------------------
# F2
# --------------------------------------------------------------------------


def _draw_f2(rows: Sequence[Mapping[str, Any]], texts: Mapping[str, str], theme: Theme) -> _Canvas:
    cv = _Canvas(theme)
    cv.header(texts["title"], texts["subtitle"])
    rb, ra = rows[0]["release_before"], rows[0]["release_after"]
    mb, ma = _f2_majorities(rows)
    cv.legend(
        [
            ("o", theme.before, f"inspect_evals {rb}", False),
            ("o", theme.after, f"inspect_evals {ra}", False),
            ("tick", theme.ink, "majority baseline, from each release's payload", False),
        ],
        206,
    )
    top, bottom = 300.0, SIZE[1] - 176.0
    n = len(rows)
    row_h = (bottom - top) / n
    name_w = max(cv.width(r["member"], 22) for r in rows) + 24

    def comp_text(r: Mapping[str, Any]) -> str:
        b = _clip_literal(r["completion_before"], 26)
        if r["completion_after"] != r["completion_before"]:
            return f"{b} → {_clip_literal(r['completion_after'], 26)}"
        return b

    comp_w = max(cv.width(comp_text(r), 20, mono=True) for r in rows) + 32

    def value_text(r: Mapping[str, Any]) -> str:
        b, a = r["score_before"], r["score_after"]
        if not r["applicable_before"] and not r["applicable_after"]:
            return ""
        if (b or 0.0) == 0.0 and (a or 0.0) == 0.0:
            return ""
        return f"{_pct(b)} → {_pct(a)}"

    vals = [value_text(r) for r in rows]
    val_w = max([cv.width(v, 22) for v in vals if v] or [0]) + 48
    plot_x = 64 + name_w + comp_w
    plot_w = 1792 - name_w - comp_w - val_w
    ax = cv.plot_axes(plot_x, top, plot_w, bottom - top)
    ax.set_xlim(-0.025, 1.025)
    ax.set_ylim(n, 0)
    _xaxis_percent(ax, theme)

    def x_px(v: float) -> float:
        return plot_x + plot_w * (v + 0.025) / 1.05

    ticks = [(mb, f"majority {_pct(mb)}, both releases")] if mb == ma else [
        (mb, f"majority {_pct(mb)} on {rb}"), (ma, f"majority {_pct(ma)} on {ra}")
    ]
    for k, (m, label) in enumerate(sorted(ticks)):
        ax.plot([m, m], [0.05, n - 0.05], color=theme.ink, lw=_pt(2), zorder=3)
        ly = top - 18 - 30 * k
        cv.text(x_px(m), ly, label, 20, theme.ink2, ha="center")

    for i, r in enumerate(rows):
        yd = i + 0.5
        ypx = top + yd * row_h
        cv.text(64, ypx, r["member"] + ("*" if r["member"] == "echo" else ""), 22, theme.ink, va="center_baseline")
        cv.text(64 + name_w, ypx, comp_text(r), 20, theme.ink2, va="center_baseline", family=_MONO)
        b, a = r["score_before"], r["score_after"]
        if not r["applicable_before"] and not r["applicable_after"]:
            cv.text(x_px(0.0), ypx, "n/a", 20, theme.ink2, va="center_baseline")
            continue
        if b is not None and a is not None:
            ax.plot([b, a], [yd, yd], color=theme.connector, lw=_pt(2), solid_capstyle="round", zorder=1)
        for v, color in ((b, theme.before), (a, theme.after)):
            if v is None:
                continue
            ax.plot([v], [yd], marker="o", markersize=_pt(15), markerfacecolor=color,
                    markeredgecolor=theme.surface, markeredgewidth=_pt(2), linestyle="none", zorder=4)
        if not r["applicable_before"] or not r["applicable_after"]:
            side = rb if not r["applicable_before"] else ra
            cv.text(x_px(max(v for v in (b, a) if v is not None)) + 20, ypx, f"n/a on {side}", 20,
                    theme.ink2, va="center_baseline")
        if vals[i]:
            reaches = r["reaches_before"] or r["reaches_after"]
            cv.text(plot_x + plot_w + 24, ypx, vals[i], 22, theme.ink if reaches else theme.ink2,
                    va="center_baseline", fontweight="semibold" if reaches else "normal")
    cv.text(plot_x, bottom + 62, "score under each release's own scorer", 20, theme.ink2)
    if any(vals):
        cv.text(plot_x + plot_w + 24, top - 18, f"{rb} → {ra}", 20, theme.ink2)
    if any(r["member"] == "echo" for r in rows):
        cv.text(64, SIZE[1] - 64, "* echo returns each sample's own input, so its completion varies per "
                "sample; the one shown is the payload's example.", 20, theme.ink2)
    cv.footer(texts["footer"])
    return cv


# --------------------------------------------------------------------------
# F3
# --------------------------------------------------------------------------


def _draw_f3(rows: Sequence[Mapping[str, Any]], texts: Mapping[str, str], theme: Theme,
             counts: CloseoutCounts) -> _Canvas:
    cv = _Canvas(theme)
    cv.header(texts["title"], texts["subtitle"])
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    t = _f3_totals(rows)
    x0, x1 = 64.0, 1856.0
    bar_top, bar_h = 440.0, 24.0
    scale = (x1 - x0) / max(1, t["declared"])
    colour = {"excluded": theme.excluded, "not_counted": theme.not_counted,
              "ran": theme.ran, "not_run": theme.not_run}
    geo = []
    for k, r in enumerate(rows):
        a = x0 + r["start"] * scale + (1 if k else 0)
        b = x0 + r["end"] * scale - (1 if k < len(rows) - 1 else 0)
        geo.append((a, b))
        last = k == len(rows) - 1
        rad = 4.0 if last else 0.0
        verts = [(a, bar_top), (b - rad, bar_top)]
        codes = [Path.MOVETO, Path.LINETO]
        if rad:
            verts += [(b, bar_top), (b, bar_top + rad), (b, bar_top + bar_h - rad), (b, bar_top + bar_h),
                      (b - rad, bar_top + bar_h)]
            codes += [Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CURVE3, Path.CURVE3]
        else:
            verts += [(b, bar_top + bar_h)]
            codes += [Path.LINETO]
        verts += [(a, bar_top + bar_h), (a, bar_top)]
        codes += [Path.LINETO, Path.CLOSEPOLY]
        cv.ov.add_patch(PathPatch(Path(verts, codes), facecolor=colour[r["kind"]], edgecolor="none", zorder=3))

    # Direct labels, left-aligned at their segment with a hairline leader. A name
    # wraps onto two lines when one would run into the next label; a label that
    # still collides moves up a tier. The countable list gets one label, centred
    # over a bracket that spans ran and not run.
    def name_lines(name: str, room: float) -> list[str]:
        if cv.width(name, 22) <= room or " " not in name:
            return [name]
        words = name.split(" ")
        best = min(
            ([" ".join(words[:k]), " ".join(words[k:])] for k in range(1, len(words))),
            key=lambda pair: max(cv.width(x, 22) for x in pair),
        )
        return best

    def place(items: list[tuple[float, float, str, str, float, str]], above: bool) -> None:
        ends: list[float] = []
        for n, (xa, xb, big, name, big_px, align) in enumerate(items):
            nxt = items[n + 1][0] if n + 1 < len(items) else x1
            lines = name_lines(name, nxt - xa - 28)
            w = max([cv.width(big, big_px, "semibold")] + [cv.width(x, 22) for x in lines])
            left = (xa + xb) / 2 - w / 2 if align == "center" else xa
            tier = 0
            while tier < len(ends) and left < ends[tier]:
                tier += 1
            if tier == len(ends):
                ends.append(0.0)
            ends[tier] = left + w + 28
            extra = 28 * (len(lines) - 1)
            if above:
                base = bar_top - 26 - extra - (100 + extra) * tier
                if align != "center":
                    cv.ov.plot([xa + 1, xa + 1], [bar_top - 4, base + 12 + extra], color=theme.ink2,
                               lw=_pt(1), zorder=4)
                cv.text(left, base - 32, big, big_px, theme.ink, fontweight="semibold")
                for j, line in enumerate(lines):
                    cv.text(left, base + 28 * j, line, 22, theme.ink2)
            else:
                base = bar_top + bar_h + 56 + 100 * tier
                cv.ov.plot([xa + 1, xa + 1], [bar_top + bar_h + 4, base - 36], color=theme.ink2, lw=_pt(1), zorder=4)
                cv.text(left, base, big, big_px, theme.ink, fontweight="semibold")
                for j, line in enumerate(lines):
                    cv.text(left, base + 30 + 28 * j, line, 22, theme.ink2)

    above = [(geo[k][0], geo[k][1], str(r["count"]), r["label"], 40.0, "left")
             for k, r in enumerate(rows) if r["kind"] in ("excluded", "not_counted")]
    cidx = [k for k, r in enumerate(rows) if r["kind"] in ("ran", "not_run")]
    if cidx:
        ca, cb = geo[cidx[0]][0], geo[cidx[-1]][1]
        yb = bar_top - 12
        cv.ov.plot([ca + 1, ca + 1, cb - 1, cb - 1], [bar_top - 4, yb, yb, bar_top - 4],
                   color=theme.ink2, lw=_pt(1.5), solid_joinstyle="miter", zorder=4)
        above.append((ca, cb, str(t["countable"]), "countable", 48.0, "center"))
    place(above, True)
    below = [(geo[k][0], geo[k][1], str(rows[k]["count"]), rows[k]["label"], 40.0, "left") for k in cidx]
    place(below, False)

    # The detail, computed from the rows.
    lines: list[str] = []
    excl = [r for r in rows if r["kind"] == "excluded"]
    lines.append(
        f"Excluded ({t['declared'] - t['reachable']}): "
        # A segment that groups several inventory reasons names them.
        + "; ".join(f"{r['label']} {r['count']}" + (f" ({r['detail']})" if ";" in r["detail"] else "")
                    for r in excl)
        + "."
    )
    for r in rows:
        if r["kind"] == "not_counted":
            lines.append(f"Not counted ({r['count']}): {r['detail']}.")
        if r["kind"] == "not_run":
            lines.append(f"Countable, not run ({r['count']}): {r['detail']}.")
    if counts.release != counts.anchor_release:
        lines.append(
            f"inspect_evals {counts.release}'s own inventory reaches {counts.R} of {counts.D} "
            "declared; it is not part of the bar."
        )
    y = 700.0
    for para in lines:
        for line in cv.wrap(para, 1792, 22):
            if y > SIZE[1] - 70:
                break
            cv.text(64, y, line, 22, theme.ink2)
            y += 32
        y += 10
    cv.footer(texts["footer"])
    return cv


_DRAW = {"F1": _draw_f1, "F2": _draw_f2, "F3": _draw_f3}


def render_static(
    fig_id: str,
    rows: Sequence[Mapping[str, Any]],
    counts: CloseoutCounts,
    out_dir: pathlib.Path,
    source: str = "",
) -> list[pathlib.Path]:
    """Write ``<stem>-{light,dark}.{svg,png}`` and ``<stem>.csv``. Returns paths."""
    import matplotlib

    out_dir.mkdir(parents=True, exist_ok=True)
    texts = figure_texts(fig_id, rows, counts, source)
    digest = texts["digest"]
    base = out_dir / FIGURE_NAMES[fig_id]
    written = [write_data(rows, out_dir / f"{FIGURE_NAMES[fig_id]}.csv", FIELDS[fig_id])]
    # The DejaVu fallback (kept for glyphs Segoe UI lacks) has no semibold, and
    # font_manager says so once per text. Quiet that one logger while drawing.
    fm_log = logging.getLogger("matplotlib.font_manager")
    level = fm_log.level
    fm_log.setLevel(logging.ERROR)
    try:
        with matplotlib.rc_context(_rc(digest)):
            for theme in THEMES:
                if fig_id == "F3":
                    cv = _draw_f3(rows, texts, theme, counts)
                else:
                    cv = _DRAW[fig_id](rows, texts, theme)
                written += cv.save(base, fig_id, digest, texts["title"])
    finally:
        fm_log.setLevel(level)
    return written


def embedded_digest(path: pathlib.Path) -> str | None:
    """The rows digest a written SVG or PNG carries, or None."""
    if path.suffix == ".svg":
        m = re.search(r"rows sha256 ([0-9a-f]{64})", path.read_text(encoding="utf-8"))
        return m.group(1) if m else None
    if path.suffix == ".png":
        from PIL import Image

        with Image.open(path) as im:
            desc = (getattr(im, "text", None) or im.info).get("Description", "")
        m = re.search(r"rows sha256 ([0-9a-f]{64})", desc)
        return m.group(1) if m else None
    return None


# --------------------------------------------------------------------------
# GIFs: shared Pillow helpers
# --------------------------------------------------------------------------

_PIL_FONTS = {
    "sans": ("segoeui.ttf", "DejaVuSans.ttf"),
    "semibold": ("seguisb.ttf", "DejaVuSans-Bold.ttf"),
    "mono": ("CascadiaMono.ttf", "consola.ttf", "DejaVuSansMono.ttf"),
}


def _pil_font(kind: str, size: int) -> Any:
    from PIL import ImageFont

    for name in _PIL_FONTS[kind]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    try:
        import matplotlib

        ttf = pathlib.Path(matplotlib.get_data_path()) / "fonts" / "ttf" / _PIL_FONTS[kind][-1]
        return ImageFont.truetype(str(ttf), size)
    except (ImportError, OSError):
        return ImageFont.load_default(size=size)


def _rgb(hexcolor: str) -> tuple[int, int, int]:
    h = hexcolor.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _save_gif(frames: Sequence[Any], durations: Sequence[int], path: pathlib.Path, colors: int = 64) -> pathlib.Path:
    """One global palette from the last frame (which holds every colour), no
    dither, so the frames differ only where something moved."""
    from PIL import Image

    palette = frames[-1].quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    path.parent.mkdir(parents=True, exist_ok=True)
    q[0].save(path, save_all=True, append_images=q[1:], duration=list(durations), loop=0,
              optimize=False, disposal=1)
    return path


# --------------------------------------------------------------------------
# G1: the battery on paws, before and after
# --------------------------------------------------------------------------

_G1_TYPE_FRAMES, _G1_TYPE_MS = 6, 70
_G1_GROW_FRAMES, _G1_GROW_MS = 6, 60
_G1_SETTLE_MS = 180
_G1_INTRO_MS = 800
_G1_HOLD_MS = 3000


def _ease(x: float) -> float:
    return x * x * (3 - 2 * x)


def g1_timeline(rows: Sequence[Mapping[str, Any]]) -> list[tuple[int, float, float, bool, int]]:
    """``(member index, typed fraction, bar fraction, verdict shown, ms)`` per
    frame. Pure, so its length and running time are testable without drawing."""
    frames: list[tuple[int, float, float, bool, int]] = [(-1, 0.0, 0.0, False, _G1_INTRO_MS)]
    for i in range(len(rows)):
        for k in range(1, _G1_TYPE_FRAMES + 1):
            frames.append((i, k / _G1_TYPE_FRAMES, 0.0, False, _G1_TYPE_MS))
        for k in range(1, _G1_GROW_FRAMES + 1):
            frames.append((i, 1.0, _ease(k / _G1_GROW_FRAMES), False, _G1_GROW_MS))
        frames.append((i, 1.0, 1.0, False, _G1_SETTLE_MS))
    frames.append((len(rows) - 1, 1.0, 1.0, True, _G1_HOLD_MS))
    return frames


def g1_texts(rows: Sequence[Mapping[str, Any]], sources: Sequence[str] = ()) -> dict[str, str]:
    rb, ra = rows[0]["release_before"], rows[0]["release_after"]
    return {
        "title": f"{_short(rows[0]['task'])}: the content-free battery on inspect_evals {rb} and {ra}",
        "subtitle": (
            "Each member's literal completion is typed in, then its score under that "
            "release's own scorer grows against the majority line."
        ),
        "echo": (
            "* echo returns each sample's own input, so its completion varies per sample; "
            "only one example, the payload's, is shown."
        ),
        "source": (" · ".join(sources) + " · " if sources else "")
        + f"rows sha256 {data_digest(rows)[:12]}",
    }


def render_g1(
    rows: Sequence[Mapping[str, Any]],
    out_path: pathlib.Path,
    sources: Sequence[str] = (),
    size: tuple[int, int] = SIZE,
) -> pathlib.Path:
    """G1 as a GIF. ``size`` other than :data:`SIZE` scales the whole layout,
    which the tests use to stay fast."""
    from PIL import Image, ImageDraw

    W, H = size
    s = W / SIZE[0]
    th = G1_THEME
    tx = g1_texts(rows, sources)

    def S(v: float) -> int:
        return int(round(v * s))

    f_title, f_sub = _pil_font("semibold", S(40)), _pil_font("sans", S(24))
    f_head, f_label = _pil_font("semibold", S(28)), _pil_font("sans", S(22))
    f_small, f_mono = _pil_font("sans", S(20)), _pil_font("mono", S(22))
    f_value = _pil_font("semibold", S(22))

    panels = []
    for p, side in enumerate(("before", "after")):
        px0 = S(64 + p * 920)
        px1 = px0 + S(872)
        panels.append({"side": side, "x0": px0, "x1": px1})
    name_w, rows_top, rows_bottom = S(176), S(262), S(902)
    row_h = (rows_bottom - rows_top) / max(1, len(rows))

    def geometry(panel: Mapping[str, Any]) -> dict[str, int]:
        chip_x0 = panel["x0"] + name_w
        track_x0, track_x1 = chip_x0, panel["x1"] - S(118)
        return {"chip_x0": chip_x0, "chip_x1": panel["x1"], "track_x0": track_x0, "track_x1": track_x1}

    mono_w = f_mono.getlength("M") or 1
    max_chars = int((geometry(panels[0])["chip_x1"] - geometry(panels[0])["chip_x0"] - S(24)) / mono_w)

    base = Image.new("RGB", (W, H), _rgb(th["surface"]))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((S(10), S(10), W - S(10), H - S(10)), radius=S(14), outline=_rgb(th["border"]), width=max(1, S(3)))
    d.text((S(64), S(44)), tx["title"], font=f_title, fill=_rgb(th["ink"]))
    d.text((S(64), S(100)), tx["subtitle"], font=f_sub, fill=_rgb(th["ink2"]))
    for panel in panels:
        side = panel["side"]
        g = geometry(panel)
        rel, scorer = rows[0][f"release_{side}"], rows[0][f"scorer_{side}"]
        maj = rows[0][f"majority_{side}"]
        d.text((panel["x0"], S(160)), f"inspect_evals {rel}", font=f_head, fill=_rgb(th["ink"]))
        hx = panel["x0"] + f_head.getlength(f"inspect_evals {rel}") + S(16)
        d.text((hx, S(166)), f"scorer {scorer}", font=f_small, fill=_rgb(th["ink2"]))
        mx = g["track_x0"] + (g["track_x1"] - g["track_x0"]) * maj
        d.line((mx, S(240), mx, rows_bottom), fill=_rgb(th["ink"]), width=max(1, S(2)))
        lab = f"majority {_pct(maj)}"
        d.text((mx - f_small.getlength(lab) / 2, S(208)), lab, font=f_small, fill=_rgb(th["ink"]))
        panel["mx"] = mx
        for i, r in enumerate(rows):
            y = rows_top + i * row_h
            name = r["member"] + ("*" if r["member"] == "echo" else "")
            d.text((panel["x0"], y + S(6)), name, font=f_label, fill=_rgb(th["ink"]))
            d.rounded_rectangle((g["chip_x0"], y, g["chip_x1"], y + S(38)), radius=S(6),
                                fill=_rgb(th["chip"]), outline=_rgb(th["chip_border"]), width=1)
            d.rounded_rectangle((g["track_x0"], y + S(50), g["track_x1"], y + S(66)), radius=S(4),
                                fill=_rgb(th["track"]))
    d.text((S(64), S(950)), tx["echo"], font=f_small, fill=_rgb(th["ink2"]))
    d.text((S(64), S(990)), tx["source"], font=f_small, fill=_rgb(th["ink2"]))

    def draw_state(img: Any, idx: int, typed: float, grown: float, verdict: bool) -> None:
        dd = ImageDraw.Draw(img)
        for panel in panels:
            side = panel["side"]
            g = geometry(panel)
            for i, r in enumerate(rows):
                if i > idx:
                    break
                y = rows_top + i * row_h
                frac_t = typed if i == idx else 1.0
                frac_b = grown if i == idx else 1.0
                applicable = r[f"applicable_{side}"]
                lit = _clip_literal(r[f"completion_{side}"], max_chars) if applicable else "n/a"
                shown = lit[: math.ceil(len(lit) * frac_t)]
                tx0 = g["chip_x0"] + S(12)
                dd.text((tx0, y + S(6)), shown, font=f_mono, fill=_rgb(th["ink"]))
                if i == idx and frac_t < 1.0:
                    cx = tx0 + f_mono.getlength(shown) + S(2)
                    dd.rectangle((cx, y + S(8), cx + S(11), y + S(32)), fill=_rgb(th["ink"]))
                score = r[f"score_{side}"]
                if not applicable or score is None or frac_t < 1.0:
                    continue
                reaches = r[f"reaches_{side}"]
                colour = _rgb(th["flag"] if reaches else th["clean"])
                tw = g["track_x1"] - g["track_x0"]
                bx1 = g["track_x0"] + tw * score * frac_b
                if score * frac_b > 0 and bx1 - g["track_x0"] >= S(8):
                    dd.rounded_rectangle((g["track_x0"], y + S(48), bx1, y + S(68)), radius=S(4), fill=colour)
                    dd.rectangle((g["track_x0"], y + S(48), g["track_x0"] + S(6), y + S(68)), fill=colour)
                else:
                    dd.ellipse((g["track_x0"] - S(1), y + S(52), g["track_x0"] + S(11), y + S(64)), fill=colour)
                if frac_b >= 1.0:
                    val = _pct(score)
                    dd.text((g["track_x1"] + S(14), y + S(44)), val, font=f_value if reaches else f_label,
                            fill=_rgb(th["ink"] if reaches else th["ink2"]))
                    # The majority line is drawn over the bar, so the comparison stays visible.
                    dd.line((panel["mx"], y + S(44), panel["mx"], y + S(72)), fill=_rgb(th["ink"]), width=max(1, S(2)))
            if verdict:
                names = _reachers(rows, side)
                y = S(912)
                if names:
                    dd.ellipse((panel["x0"], y + S(6), panel["x0"] + S(20), y + S(26)), fill=_rgb(th["flag"]))
                    text = f"FLAGGED: {_names(names)} {_plural(len(names), 'reaches', 'reach')} the majority line"
                else:
                    pts = [(panel["x0"] + S(2), y + S(16)), (panel["x0"] + S(8), y + S(24)), (panel["x0"] + S(20), y + S(6))]
                    dd.line(pts, fill=_rgb(th["good"]), width=max(1, S(4)))
                    text = "clean: no content-free member reaches the majority line"
                dd.text((panel["x0"] + S(30), y), text, font=f_value, fill=_rgb(th["ink"]))

    frames, durations = [], []
    for idx, typed, grown, verdict, ms in g1_timeline(rows):
        img = base.copy()
        draw_state(img, idx, typed, grown, verdict)
        frames.append(img)
        durations.append(ms)
    return _save_gif(frames, durations, out_path)


# --------------------------------------------------------------------------
# G2: a terminal recording
# --------------------------------------------------------------------------

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")


class _LineSplitter:
    """Splits a stream into ``("line", text)`` at ``\\n`` and ``("cr", text)`` at a
    bare ``\\r`` (a progress bar redrawing its line). ``\\r\\n`` is one newline."""

    def __init__(self) -> None:
        self.buf = ""
        self.pending_cr = False

    def feed(self, text: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for ch in text:
            if self.pending_cr:
                self.pending_cr = False
                if ch == "\n":
                    out.append(("line", self.buf))
                    self.buf = ""
                    continue
                out.append(("cr", self.buf))
                self.buf = ""
            if ch == "\r":
                self.pending_cr = True
            elif ch == "\n":
                out.append(("line", self.buf))
                self.buf = ""
            else:
                self.buf += ch
        return out

    def close(self) -> list[tuple[str, str]]:
        out = []
        if self.pending_cr or self.buf:
            out.append(("line", self.buf))
        self.buf, self.pending_cr = "", False
        return out


def capture(
    cmd: Sequence[str],
    display: str | None = None,
    cwd: pathlib.Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = 1800,
) -> dict[str, Any]:
    """Run ``cmd`` and record every stdout and stderr line with its time.

    Lines are recorded verbatim, minus ANSI escapes; a bare carriage return is
    kept as a ``cr`` event, so a progress bar replays as one redrawn line. Only
    ``PYTHONUNBUFFERED`` is set, so lines arrive when they are written.
    """
    run_env = dict(os.environ if env is None else env)
    run_env.setdefault("PYTHONUNBUFFERED", "1")
    run_env.setdefault("PYTHONIOENCODING", "utf-8")
    argv = list(cmd)
    # CreateProcess does not try PATHEXT, so `.venv/Scripts/evalfloor` needs
    # its `.exe` found for it; which() does that, and is a no-op elsewhere.
    argv[0] = shutil.which(argv[0]) or argv[0]
    started = _dt.datetime.now(_dt.timezone.utc)
    t0 = time.monotonic()
    proc = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=run_env
    )
    events: list[dict[str, Any]] = []
    lock = threading.Lock()

    def pump(stream: Any, name: str) -> None:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        splitter = _LineSplitter()

        def emit(pairs: list[tuple[str, str]], t: float) -> None:
            with lock:
                for kind, text in pairs:
                    events.append({"t": round(t, 3), "stream": name, "kind": kind,
                                   "text": _ANSI.sub("", text)})

        while True:
            chunk = stream.read1(4096)
            t = time.monotonic() - t0
            if not chunk:
                break
            emit(splitter.feed(decoder.decode(chunk)), t)
        emit(splitter.feed(decoder.decode(b"", final=True)) + splitter.close(), time.monotonic() - t0)

    threads = [threading.Thread(target=pump, args=(proc.stdout, "stdout")),
               threading.Thread(target=pump, args=(proc.stderr, "stderr"))]
    for th in threads:
        th.start()
    rc = proc.wait(timeout=timeout)
    for th in threads:
        th.join()
    events.sort(key=lambda e: e["t"])
    return {
        "command": list(cmd),
        "display": display or " ".join(cmd),
        "started_at": started.isoformat(timespec="seconds"),
        "elapsed_s": round(time.monotonic() - t0, 3),
        "returncode": rc,
        "events": events,
    }


def screen_lines(events: Iterable[Mapping[str, Any]]) -> list[str]:
    """The terminal's lines after ``events``, with ``cr`` redraws applied."""
    lines: list[str] = []
    open_line: dict[str, int] = {}
    for e in events:
        stream, text = e["stream"], e["text"]
        if e["kind"] == "cr":
            if stream in open_line:
                lines[open_line[stream]] = text
            else:
                lines.append(text)
                open_line[stream] = len(lines) - 1
        else:
            if stream in open_line:
                lines[open_line.pop(stream)] = text
            else:
                lines.append(text)
    return lines


def transcript(cap: Mapping[str, Any]) -> str:
    """The capture as copyable plain text: the command, then what it printed."""
    return "\n".join([f"$ {cap['display']}"] + screen_lines(cap["events"])) + "\n"


_G2_WAIT_MS = 700  # a real wait longer than this is compressed to it
_G2_GROUP_S = 0.12  # events closer than this share a frame
_G2_HOLD_MS = 3500


def _sessions(caps: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [caps] if isinstance(caps, Mapping) else list(caps)


def g2_timeline(caps: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Frames as ``{session, typed, upto, clock, exit, ms}``: which capture, how
    much of its command is typed, how many of its events are shown, the real
    elapsed time to print, whether its exit code shows, and the frame's
    duration. One or several captures play in one terminal, in order. A real
    wait longer than ``_G2_WAIT_MS`` is compressed to it; the clock keeps the
    real time."""
    frames: list[dict[str, Any]] = []
    sessions = _sessions(caps)
    for n, cap in enumerate(sessions):
        display = cap["display"]

        def frame(**kw: Any) -> dict[str, Any]:
            f = {"session": n, "typed": len(display), "upto": 0, "clock": 0.0, "exit": False, "ms": 0}
            f.update(kw)
            return f

        frames.append(frame(typed=0, ms=500))
        step = max(1, math.ceil(len(display) / 14))
        for k in range(step, len(display) + step, step):
            frames.append(frame(typed=min(k, len(display)), ms=60))
        events = list(cap["events"])
        first = len(frames)
        i = 0
        while i < len(events):
            j = i + 1
            while j < len(events) and events[j]["t"] - events[i]["t"] < _G2_GROUP_S:
                j += 1
            frames.append(frame(upto=j, clock=events[j - 1]["t"]))
            i = j
        end = frame(upto=len(events), clock=cap["elapsed_s"], exit=True,
                    ms=_G2_HOLD_MS if n == len(sessions) - 1 else 1800)
        # Each frame shows until the next: the real gap, compressed. The last
        # typed frame waits for the first line the way the terminal did.
        nxt = frames[first:] + [end]
        frames[first - 1]["ms"] = int(min(max(1000 * nxt[0]["clock"], 80), _G2_WAIT_MS))
        for k in range(first, len(frames)):
            gap = 1000 * (nxt[k - first + 1]["clock"] - frames[k]["clock"])
            frames[k]["ms"] = int(min(max(gap, 80), _G2_WAIT_MS))
        frames.append(end)
    return frames


def render_g2(
    caps: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    out_path: pathlib.Path,
    size: tuple[int, int] = SIZE,
) -> pathlib.Path:
    """One or several captures replayed in one terminal, in order, with the real
    clock in the title bar and a corner caption saying the waits are compressed.
    The exit code is printed in the status bar, never in the terminal body,
    which shows only what the command printed."""
    from PIL import Image, ImageDraw

    sessions = _sessions(caps)
    W, H = size
    s = W / SIZE[0]

    def S(v: float) -> int:
        return int(round(v * s))

    th = G2_THEME
    f_mono = _pil_font("mono", S(25))
    f_bar = _pil_font("sans", S(22))
    f_cap = _pil_font("sans", S(20))
    char_w = f_mono.getlength("M") or 1
    line_h = S(36)
    body_x, body_y = S(48), S(104)
    cols = max(20, int((W - 2 * body_x) / char_w))
    max_rows = int((H - body_y - S(84)) / line_h)
    dates = sorted({str(c.get("started_at", ""))[:10] for c in sessions})
    caption_text = f"recorded {' and '.join(dates)}, real output; waits compressed"

    base = Image.new("RGB", (W, H), _rgb(th["surface"]))
    d = ImageDraw.Draw(base)
    d.rectangle((0, 0, W, S(64)), fill=_rgb(th["bar"]))
    d.line((0, S(64), W, S(64)), fill=_rgb(th["border"]), width=max(1, S(2)))
    d.rectangle((0, H - S(56), W, H), fill=_rgb(th["bar"]))
    d.line((0, H - S(56), W, H - S(56)), fill=_rgb(th["border"]), width=max(1, S(2)))
    d.text((W - S(48) - f_cap.getlength(caption_text), H - S(42)), caption_text, font=f_cap,
           fill=_rgb(th["caption"]))

    def wrap(text: str) -> list[str]:
        text = text.expandtabs(8)
        return [text[k : k + cols] for k in range(0, max(1, len(text)), cols)] or [""]

    def session_lines(cap: Mapping[str, Any], typed: int, upto: int) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for k, ln in enumerate(wrap(f"$ {cap['display'][:typed]}")):
            out.append(("cmd" if k else "prompt", ln))
        for ln in screen_lines(cap["events"][:upto]):
            out.extend(("out", w) for w in wrap(ln))
        return out

    frames, durations = [], []
    for fr in g2_timeline(sessions):
        cap = sessions[fr["session"]]
        img = base.copy()
        dd = ImageDraw.Draw(img)
        dd.text((S(48), S(18)), f"$ {cap['display']}", font=f_bar, fill=_rgb(th["caption"]))
        clock = f"real time {fr['clock']:.1f} s"
        dd.text((W - S(48) - f_bar.getlength(clock), S(18)), clock, font=f_bar, fill=_rgb(th["caption"]))
        shown: list[tuple[str, str]] = []
        for earlier in sessions[: fr["session"]]:
            shown += session_lines(earlier, len(earlier["display"]), len(earlier["events"])) + [("out", "")]
        shown += session_lines(cap, fr["typed"], fr["upto"])
        shown = shown[-max_rows:]
        for k, (kind, ln) in enumerate(shown):
            y = body_y + k * line_h
            if kind == "prompt":
                dd.text((body_x, y), ln[:2], font=f_mono, fill=_rgb(th["prompt"]))
                dd.text((body_x + f_mono.getlength(ln[:2]), y), ln[2:], font=f_mono, fill=_rgb(th["command"]))
            elif kind == "cmd":
                dd.text((body_x, y), ln, font=f_mono, fill=_rgb(th["command"]))
            else:
                dd.text((body_x, y), ln, font=f_mono, fill=_rgb(th["text"]))
        if fr["upto"] == 0 and not fr["exit"]:
            # The cursor, after the typed command.
            last = shown[-1][1] if shown else ""
            cy = body_y + (len(shown) - 1) * line_h
            cx = body_x + f_mono.getlength(last) + S(2)
            dd.rectangle((cx, cy + S(4), cx + S(12), cy + S(30)), fill=_rgb(th["command"]))
        if fr["exit"]:
            dd.text((S(48), H - S(42)), f"exit {cap['returncode']}", font=f_cap, fill=_rgb(th["caption"]))
        frames.append(img)
        durations.append(fr["ms"])
    return _save_gif(frames, durations, out_path, colors=32)


def g2_transcript(caps: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> str:
    """Every capture's transcript, in order, a blank line between them."""
    return "\n".join(transcript(c) for c in _sessions(caps))


def capture_release(cap: Mapping[str, Any]) -> str | None:
    """The ``inspect_evals`` release a ``check`` run printed in its header line."""
    m = re.search(r"inspect_evals (\d+(?:\.\d+)+)\)", "\n".join(screen_lines(cap["events"])))
    return m.group(1) if m else None


def capture_verdicts(cap: Mapping[str, Any]) -> dict[str, str]:
    """``{task: "FLAGGED" | "clean"}`` from a ``check`` run's last lines."""
    out: dict[str, str] = {}
    for line in screen_lines(cap["events"]):
        m = re.fullmatch(r"(\S+/\S+): (FLAGGED|clean)", line.strip())
        if m:
            out[m.group(1)] = m.group(2)
    return out


def write_capture(cap: Mapping[str, Any], out_dir: pathlib.Path, name: str) -> list[pathlib.Path]:
    """``g2-<name>.json`` (the capture), ``.txt`` (its transcript) and ``.gif``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    js = out_dir / f"g2-{name}.json"
    js.write_bytes((json.dumps(cap, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    txt = out_dir / f"g2-{name}.txt"
    txt.write_bytes(transcript(cap).encode("utf-8"))
    gif = render_g2(cap, out_dir / f"g2-{name}.gif")
    return [js, txt, gif]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _sizes(paths: Iterable[pathlib.Path]) -> None:
    for p in paths:
        print(f"  {p.as_posix()}  {p.stat().st_size} bytes")


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command: list[str] = []
    if "--" in argv:
        k = argv.index("--")
        argv, command = argv[:k], argv[k + 1 :]
    p = argparse.ArgumentParser(
        prog="python -m evalfloor.figures",
        description="Write the README figures and GIFs from the committed results.",
    )
    p.add_argument("--out", default="docs/figures")
    p.add_argument("--results", default="results")
    p.add_argument("--rulings", default="rulings.jsonl")
    p.add_argument("--before-ref", default=LIST_FIXED_AT,
                   help=f"commit holding the anchor payload and inventory (default {LIST_FIXED_AT})")
    p.add_argument("--after", default=None, help="deterministic payload to draw (default <results>/sweep.json)")
    p.add_argument("--repeat", default=None, help="the second run's payload, as for `report --repeat`")
    p.add_argument("--only", default=None, help="comma-separated: F1,F2,F3,G1,G2 (default: every one available)")
    p.add_argument("--capture", metavar="NAME", default=None,
                   help="run the command after `--`, record it as g2-NAME.{json,txt,gif}")
    args = p.parse_args(argv)
    out = pathlib.Path(args.out)

    if args.capture:
        if not command:
            p.error("--capture needs a command after `--`")
        cap = capture(command, display=" ".join(command))
        print(f"captured `{cap['display']}`: exit {cap['returncode']}, {cap['elapsed_s']} s, "
              f"{len(cap['events'])} events")
        _sizes(write_capture(cap, out, args.capture))
        return 0

    wanted = [x.strip().upper() for x in (args.only or "F1,F2,F3,G1,G2").split(",") if x.strip()]
    explicit = args.only is not None
    unknown = sorted(set(wanted) - set(FIGURE_IDS) - set(GIF_IDS))
    if unknown:
        p.error(f"unknown figure ids: {', '.join(unknown)}")

    inputs = load_inputs(
        pathlib.Path(args.results), pathlib.Path(args.rulings), args.before_ref,
        pathlib.Path(args.after) if args.after else None,
        pathlib.Path(args.repeat) if args.repeat else None,
    )
    data = figure_data(
        inputs.after_floors, inputs.payload, inputs.counts, inputs.anchor_payload,
        inputs.inventories, rulings=inputs.rulings,
    )
    status = 0
    for fig_id in wanted:
        if fig_id in FIGURE_IDS or fig_id == "G1":
            key = "F2" if fig_id == "G1" else fig_id
            if key not in data:
                why = (
                    f"{fig_id} needs a payload on a release other than the anchor's "
                    f"({_release(inputs.anchor_payload)}); this one is on {inputs.counts.release}"
                )
                print(f"{fig_id}: skipped: {why}", file=sys.stderr)
                status = 2 if explicit else status
                continue
            if fig_id == "G1":
                path = render_g1(data["F2"], out / f"{FIGURE_NAMES['G1']}.gif",
                                 sources=[inputs.sources.get("anchor_payload", ""), inputs.sources["payload"]])
                print(f"G1: {title('F2', data['F2'], inputs.counts)}")
                _sizes([path])
                continue
            source = inputs.sources["payload"] if fig_id != "F3" else inputs.sources["anchor_inventory"]
            if fig_id == "F2":
                source = f"{inputs.sources.get('anchor_payload', '')} and {inputs.sources['payload']}"
            paths = render_static(fig_id, data[fig_id], inputs.counts, out, source)
            print(f"{fig_id}: {title(fig_id, data[fig_id], inputs.counts)}")
            _sizes(paths)
        elif fig_id == "G2":
            caps = sorted(out.glob("g2-*.json"))
            if not caps:
                print("G2: skipped: no g2-*.json capture; record one with --capture NAME -- <command>",
                      file=sys.stderr)
                status = 2 if explicit else status
            for cap_path in caps:
                cap = json.loads(cap_path.read_text(encoding="utf-8"))
                txt = cap_path.with_suffix(".txt")
                txt.write_bytes(transcript(cap).encode("utf-8"))
                gif = render_g2(cap, cap_path.with_suffix(".gif"))
                print(f"G2: {cap['display']} (exit {cap['returncode']}, inspect_evals {capture_release(cap)})")
                _sizes([txt, gif])
            if caps:
                print(f"G2: {len(caps)} {_plural(len(caps), 'capture', 'captures')} in one terminal")
                _sizes(write_g2(load_captures(out), out))
    return status


if __name__ == "__main__":
    sys.exit(main())
