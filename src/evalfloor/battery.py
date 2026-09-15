"""The content-free completion battery and the reference baselines.

The measurement this project makes is the gap between two groups of completions:

*   **Content-free members** carry no information about the sample. They should
    score at or below chance. Every one of them is a pure function of the sample
    and the dataset's label set -- no model is called, ever.
*   **Reference baselines** define the line the content-free members must not
    cross. ``majority`` is the modal target of the dataset. ``uniform`` draws a
    target uniformly from the label set and is averaged over seeds.

A task is flagged when any content-free member scores at or above ``majority``.

Membership and every literal string below are fixed by ``PREREGISTRATION.md``.
Changing one after a sweep has run invalidates that sweep.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Literal, Sequence

# --------------------------------------------------------------------------
# Thresholds that decide whether a dataset has a usable label set at all.
# Preregistered; see PREREGISTRATION.md "coverage rules".
# --------------------------------------------------------------------------

#: A label set with more distinct values than this is treated as free text.
MAX_DISTINCT_LABELS = 50

#: A label longer than this many characters is treated as free text, not a label.
MAX_LABEL_CHARS = 100

#: Seeds averaged over for the ``uniform`` reference baseline.
UNIFORM_SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)


# --------------------------------------------------------------------------
# Normalisation helpers. Inspect samples carry targets as ``str | list[str]``
# and inputs as ``str | list[ChatMessage]``.
# --------------------------------------------------------------------------


def normalize_target(target: Any) -> str:
    """Render a sample target as the single string a scorer is asked to find."""
    if target is None:
        return ""
    if isinstance(target, str):
        return target
    if isinstance(target, (list, tuple)):
        return " ".join(normalize_target(t) for t in target)
    return str(target)


def normalize_input(sample_input: Any) -> str:
    """Render a sample input as plain text, for the ``echo`` member."""
    if sample_input is None:
        return ""
    if isinstance(sample_input, str):
        return sample_input
    if isinstance(sample_input, (list, tuple)):
        parts: list[str] = []
        for message in sample_input:
            content = getattr(message, "text", None)
            if content is None:
                content = getattr(message, "content", None)
            if content is None:
                content = str(message)
            parts.append(content if isinstance(content, str) else str(content))
        return "\n".join(parts)
    return str(sample_input)


# --------------------------------------------------------------------------
# The label set
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LabelSet:
    """The distinct targets of one dataset, with their counts.

    ``labels`` is ordered by descending frequency, ties broken lexicographically,
    so that ``all_labels`` and ``majority`` are byte-identical across runs.
    """

    counts: tuple[tuple[str, int], ...]
    n_samples: int

    @classmethod
    def from_targets(cls, targets: Iterable[Any]) -> "LabelSet":
        rendered = [normalize_target(t) for t in targets]
        counter = Counter(rendered)
        ordered = tuple(
            sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        )
        return cls(counts=ordered, n_samples=len(rendered))

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(label for label, _ in self.counts)

    @property
    def n_distinct(self) -> int:
        return len(self.counts)

    @property
    def majority_label(self) -> str:
        """The modal target. Empty string for an empty dataset."""
        return self.counts[0][0] if self.counts else ""

    @property
    def majority_share(self) -> float:
        """Share of samples carrying the modal target. Not a score --  a scorer
        may or may not actually credit the modal string on every such sample."""
        if not self.counts or self.n_samples == 0:
            return 0.0
        return self.counts[0][1] / self.n_samples

    @property
    def is_closed(self) -> bool:
        """True when the targets look like a label set rather than free text.

        Three conditions, all preregistered:
        at most ``MAX_DISTINCT_LABELS`` distinct values, every value at most
        ``MAX_LABEL_CHARS`` characters, and strictly fewer distinct values than
        samples (a dataset whose every target is unique has no label set).
        """
        if self.n_distinct == 0 or self.n_samples == 0:
            return False
        if self.n_distinct > MAX_DISTINCT_LABELS:
            return False
        if self.n_distinct >= self.n_samples:
            return False
        return all(len(label) <= MAX_LABEL_CHARS for label, _ in self.counts)


# --------------------------------------------------------------------------
# Member definitions
# --------------------------------------------------------------------------

#: The exact refusal sentence. Fixed by preregistration.
#:
#: Note for the reader: this phrasing contains neither "yes" nor "no" as a
#: substring. Common alternatives do -- "I don't know" contains "no" inside
#: "know", and "cannot" contains it outright -- which would make the refusal
#: member score on any yes/no task using ``includes()``. The conservative
#: phrasing was chosen deliberately, so a refusal flag means the scorer is
#: loose rather than the sentence being rigged.
REFUSAL_TEXT = "I'm sorry, but I can't help with that."

#: A long fluent paragraph carrying no task content. Fixed by preregistration.
BOILERPLATE_TEXT = (
    "Thank you for the question. This is an interesting problem and it is worth "
    "approaching it carefully and systematically. There are several considerations "
    "that are relevant here, and a complete treatment would weigh each of them in "
    "turn before arriving at a conclusion. Reasonable people can differ on questions "
    "of this kind, and the appropriate response depends a great deal on the context "
    "in which the question is being asked. Taking all of the above into account, the "
    "most sensible course of action is the one that best fits the requirements as "
    "they have been described."
)

#: The answer template with a placeholder. Fixed by preregistration.
FORMAT_ONLY_TEXT = "ANSWER: A"

#: The bare option letters. Fixed by preregistration.
ALL_LETTERS_TEXT = "A B C D E"

MemberKind = Literal["content_free", "reference"]

#: Signature of every member: (sample, label set, seed) -> completion, or None
#: when the member does not apply to this dataset.
MemberFn = Callable[[Any, LabelSet, int], "str | None"]


@dataclass(frozen=True)
class BatteryMember:
    name: str
    kind: MemberKind
    description: str
    fn: MemberFn
    #: More than one seed only for ``uniform``; every other member is a pure
    #: function of (sample, label set) and ignores the seed argument.
    seeds: tuple[int, ...] = (0,)
    #: True when the member is undefined on a dataset without a closed label set.
    requires_closed_labels: bool = False

    def completion(self, sample: Any, labels: LabelSet, seed: int = 0) -> str | None:
        if self.requires_closed_labels and not labels.is_closed:
            return None
        return self.fn(sample, labels, seed)

    def applies_to(self, labels: LabelSet) -> bool:
        return labels.is_closed or not self.requires_closed_labels


# -- content-free members ---------------------------------------------------


def _empty(sample: Any, labels: LabelSet, seed: int) -> str:
    return ""


def _whitespace(sample: Any, labels: LabelSet, seed: int) -> str:
    return "\n"


def _refusal(sample: Any, labels: LabelSet, seed: int) -> str:
    return REFUSAL_TEXT


def _all_labels(sample: Any, labels: LabelSet, seed: int) -> str:
    """Every distinct target in the dataset, concatenated, single-space joined.

    This is the member that reproduces Inspect Evals issue #2331: on ``paws``
    the distinct targets are "Yes" and "No", so this member is the constant
    string "No Yes", and an ``includes()`` scorer credits it on every sample
    because the target is a substring of it whatever the sample's target is.
    """
    return " ".join(labels.labels)


def _all_letters(sample: Any, labels: LabelSet, seed: int) -> str:
    return ALL_LETTERS_TEXT


def _echo(sample: Any, labels: LabelSet, seed: int) -> str:
    return normalize_input(getattr(sample, "input", ""))


def _boilerplate(sample: Any, labels: LabelSet, seed: int) -> str:
    return BOILERPLATE_TEXT


def _format_only(sample: Any, labels: LabelSet, seed: int) -> str:
    return FORMAT_ONLY_TEXT


# -- reference baselines ----------------------------------------------------


def _majority(sample: Any, labels: LabelSet, seed: int) -> str:
    return labels.majority_label


def _uniform(sample: Any, labels: LabelSet, seed: int) -> str:
    """A target drawn uniformly from the label set.

    Seeded by ``(seed, sample id)`` so that the draw is reproducible: two runs of
    the same sweep produce byte-identical completions, which the determinism
    control requires.
    """
    if not labels.labels:
        return ""
    sample_id = getattr(sample, "id", None)
    rng = random.Random(f"{seed}|{sample_id}")
    return rng.choice(labels.labels)


CONTENT_FREE_MEMBERS: tuple[BatteryMember, ...] = (
    BatteryMember(
        name="empty",
        kind="content_free",
        description="the empty string",
        fn=_empty,
    ),
    BatteryMember(
        name="whitespace",
        kind="content_free",
        description="a single newline",
        fn=_whitespace,
    ),
    BatteryMember(
        name="refusal",
        kind="content_free",
        description="a short refusal sentence",
        fn=_refusal,
    ),
    BatteryMember(
        name="all_labels",
        kind="content_free",
        description="every distinct target in the dataset, concatenated",
        fn=_all_labels,
        requires_closed_labels=True,
    ),
    BatteryMember(
        name="all_letters",
        kind="content_free",
        description="the option letters A B C D E",
        fn=_all_letters,
    ),
    BatteryMember(
        name="echo",
        kind="content_free",
        description="the sample input, echoed back verbatim",
        fn=_echo,
    ),
    BatteryMember(
        name="boilerplate",
        kind="content_free",
        description="a long fluent paragraph containing no task content",
        fn=_boilerplate,
    ),
    BatteryMember(
        name="format_only",
        kind="content_free",
        description="the answer template with a placeholder",
        fn=_format_only,
    ),
)

REFERENCE_MEMBERS: tuple[BatteryMember, ...] = (
    BatteryMember(
        name="majority",
        kind="reference",
        description="the modal target of the dataset",
        fn=_majority,
    ),
    BatteryMember(
        name="uniform",
        kind="reference",
        description="a target drawn uniformly from the label set, averaged over seeds",
        fn=_uniform,
        seeds=UNIFORM_SEEDS,
        requires_closed_labels=True,
    ),
)

BATTERY: tuple[BatteryMember, ...] = CONTENT_FREE_MEMBERS + REFERENCE_MEMBERS

MEMBERS_BY_NAME: dict[str, BatteryMember] = {m.name: m for m in BATTERY}

CONTENT_FREE_NAMES: tuple[str, ...] = tuple(m.name for m in CONTENT_FREE_MEMBERS)
REFERENCE_NAMES: tuple[str, ...] = tuple(m.name for m in REFERENCE_MEMBERS)


def get_member(name: str) -> BatteryMember:
    try:
        return MEMBERS_BY_NAME[name]
    except KeyError:
        raise KeyError(
            f"unknown battery member {name!r}; known members: "
            + ", ".join(MEMBERS_BY_NAME)
        ) from None


def battery_fingerprint() -> str:
    """A short stable digest of the battery definition.

    Written into every results file, so a matrix produced under one battery can
    never be silently compared with one produced under another.
    """
    import hashlib

    parts: list[str] = []
    for member in BATTERY:
        parts.append(
            f"{member.name}|{member.kind}|{member.seeds}|{member.requires_closed_labels}"
        )
    parts.extend([REFUSAL_TEXT, BOILERPLATE_TEXT, FORMAT_ONLY_TEXT, ALL_LETTERS_TEXT])
    parts.append(f"{MAX_DISTINCT_LABELS}|{MAX_LABEL_CHARS}")
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:12]
