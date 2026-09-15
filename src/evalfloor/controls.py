"""Controls: tasks committed in this repository with known answers.

Two of the controls in the measurement plan need a task whose answer is known in
advance, and neither should depend on downloading anything.

``control_tight``
    The **positive control**. Numeric targets scored with ``exact()``. Every
    content-free member must score zero. If one does not, the harness is broken
    and no other number in this repository means anything.

``control_loose``
    The **synthetic negative control**. The same dataset scored with
    ``includes()`` over yes/no labels, which is deliberately loose. It must be
    flagged. A detector that cannot fail on a case built to fail is not a gate.

Both are registered Inspect tasks, so they work with the ordinary commands::

    evalfloor check evalfloor/control_tight   # exits 0
    evalfloor check evalfloor/control_loose   # exits 1
"""

from __future__ import annotations

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import exact, includes

#: Sample count for both control tasks. Small, fixed, and in this file.
CONTROL_N = 120


def _numeric_samples() -> list[Sample]:
    """Targets are numbers, and no number appears in any input."""
    return [
        Sample(
            id=i,
            input=(
                "Question: what is the sum of the two quantities described below?\n"
                "The first quantity is described in words only, and the second "
                "likewise. Answer with a number and nothing else."
            ),
            target=str(1000 + i),
        )
        for i in range(CONTROL_N)
    ]


def _yes_no_samples() -> list[Sample]:
    """Deliberately unbalanced, so the majority line is not 0.5 and the flag rule
    has to compute it rather than assume it."""
    return [
        Sample(
            id=i,
            input=(
                "Question: are the two statements below paraphrases of one "
                "another? Answer Yes or No."
            ),
            target="Yes" if i % 3 == 0 else "No",
        )
        for i in range(CONTROL_N)
    ]


@task(name="evalfloor/control_tight")
def control_tight() -> Task:
    """Positive control: exact() over numeric targets. Must score zero throughout."""
    return Task(
        dataset=MemoryDataset(_numeric_samples(), name="evalfloor_control_tight"),
        scorer=exact(),
    )


@task(name="evalfloor/control_loose")
def control_loose() -> Task:
    """Synthetic negative control: includes() over yes/no labels. Must be flagged."""
    return Task(
        dataset=MemoryDataset(_yes_no_samples(), name="evalfloor_control_loose"),
        scorer=includes(),
    )
