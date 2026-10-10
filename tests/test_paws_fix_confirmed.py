"""The other side of the anchor: from 0.21.0, ``paws`` and ``boolq`` are tight.

``test_paws_regression.py`` pins 0.20.0, where ``paws`` is scored with
``includes()`` and ``all_labels`` reaches 8000 of 8000 (issue #2331, opened by
caiotheodoro). #2334 merged on 2026-09-16 and the v0.21.0 release notes
(2026-09-17) list it: ``paws`` replaces ``includes()`` with a ``pattern()`` that
accepts only a bare Yes or No, and ``boolq`` is tightened the same way.

This file confirms the fix with the same driver and the same battery the anchor
uses: on each task, every content-free member scores strictly below
``majority``, in both arms, over the whole dataset. It is skipped below 0.21,
where the anchor covers the other side, and it is marked ``dataset`` because it
scores the PAWS test split (8000 samples) and the BoolQ validation split (3270).
"""

from __future__ import annotations

import asyncio
import importlib.metadata as md

import pytest
from packaging.version import Version

from evalfloor.aggregate import aggregate_run
from evalfloor.battery import ARMS, CONTENT_FREE_NAMES
from evalfloor.drive import drive_task_async

#: The first release with #2334 in it.
FIXED_IN = Version("0.21.0")
INSTALLED = Version(md.version("inspect_evals"))

TASKS = ("inspect_evals/paws", "inspect_evals/boolq")

pytestmark = [
    pytest.mark.dataset,
    pytest.mark.skipif(
        INSTALLED < FIXED_IN,
        reason=(
            f"inspect_evals {INSTALLED} predates the paws fix ({FIXED_IN}); "
            "test_paws_regression.py pins this version's behaviour"
        ),
    ),
]


@pytest.fixture(scope="module", params=TASKS)
def run(request):
    return asyncio.run(drive_task_async(request.param))


def test_the_scorer_is_the_anchored_pattern(run) -> None:
    """The precondition. A clean result below must be the fix holding, not a
    task that failed to load or a scorer that was never the one fixed."""
    assert run.error is None, run.error
    assert run.scorers == ["inspect_ai/pattern"]
    assert run.labels_closed is True
    assert run.n_distinct_labels == 2


def test_every_content_free_member_stays_below_majority(run) -> None:
    """THE CONFIRMATION. Strictly below, for every member, in each arm."""
    for arm in ARMS:
        cells = {a.member: a for a in run.arms if a.arm == arm}
        majority = cells["majority"]
        assert majority.n_errors == 0
        assert majority.mean > 0.0, f"{run.task}: majority scored nothing ({arm})"
        for name in CONTENT_FREE_NAMES:
            cell = cells[name]
            assert cell.applicable, f"{run.task}: {name} did not apply ({arm})"
            assert cell.n_errors == 0, f"{run.task}: {name}: {cell.first_error}"
            assert cell.n_scored == run.n_samples
            assert cell.mean < majority.mean, (
                f"{run.task}: {name} scored {cell.mean:.4f} against a majority "
                f"of {majority.mean:.4f} ({arm})"
            )


def test_neither_task_is_flagged(run) -> None:
    """The same fact through the flag rule, which is what a sweep reports."""
    floors = aggregate_run(run)
    assert floors
    assert not any(f.flagged for f in floors)
