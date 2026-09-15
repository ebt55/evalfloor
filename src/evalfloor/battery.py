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

# --------------------------------------------------------------------------
# The rendering rule
#
# Every member is defined SEMANTICALLY: all_labels is "every distinct target",
# majority is "the modal target". A semantic value then has to be written down
# in a form the task's scorer can read. Some tasks declare an answer template --
# a multiple-choice task's scorer does not read the completion text at all, it
# reads which choices the multiple_choice() solver marked, and that solver only
# marks a choice when the completion contains "ANSWER: X". A bare "C" on such a
# task is not the modal target expressed plainly; it is an unreadable answer.
#
# So a member's semantic value is RENDERED in the task's declared answer template
# when the task declares one. Both forms are scored and both are reported:
#
#   raw       the semantic value written plainly, template ignored
#   rendered  the semantic value written in the task's own answer template
#
# The flag rule uses the RENDERED arm. Reporting both is what lets a reader see
# exactly what the rendering changed, rather than taking it on trust.
#
# Rendering never adds task content. "ANSWER: A, B, C, D" names every option and
# says nothing whatever about the sample, exactly as "No Yes" does on paws.
# --------------------------------------------------------------------------

#: The two arms every member is scored under.
ARMS: tuple[str, ...] = ("raw", "rendered")


@dataclass(frozen=True)
class AnswerTemplate:
    """How a task expects an answer to be written down."""

    name: str

    def render_one(self, value: str) -> str:
        if self.name == "choice":
            return f"ANSWER: {value}"
        return value

    def render_many(self, values: Sequence[str]) -> str:
        if self.name == "choice":
            return "ANSWER: " + ", ".join(values)
        return " ".join(values)

    def render_placeholder(self, value: str = "A") -> str:
        """``format_only`` is *defined* as the answer template with a
        placeholder, so it carries the default template even on a task that
        declares none of its own."""
        return f"ANSWER: {value}"


BARE_TEMPLATE = AnswerTemplate(name="bare")
CHOICE_TEMPLATE = AnswerTemplate(name="choice")


def detect_template(sample: Any) -> AnswerTemplate:
    """A sample carrying ``choices`` is a multiple-choice sample, which is the
    one answer template Inspect declares structurally rather than only in prose."""
    return CHOICE_TEMPLATE if getattr(sample, "choices", None) else BARE_TEMPLATE


MemberKind = Literal["content_free", "reference"]

#: How a member's semantic value is turned into a completion.
#:
#: ``literal``      a fixed text; never templated, because it is not label-valued
#: ``label``        one value drawn from the label set
#: ``labels``       every value in the label set
#: ``placeholder``  the answer template itself, with a fixed placeholder
SemanticKind = Literal["literal", "label", "labels", "placeholder"]

#: Signature of every member: (sample, label set, seed) -> semantic value, or
#: None when the member does not apply to this dataset.
MemberFn = Callable[[Any, LabelSet, int], "str | list[str] | None"]


@dataclass(frozen=True)
class BatteryMember:
    name: str
    kind: MemberKind
    description: str
    fn: MemberFn
    semantic: SemanticKind = "literal"
    #: More than one seed only for ``uniform``; every other member is a pure
    #: function of (sample, label set) and ignores the seed argument.
    seeds: tuple[int, ...] = (0,)
    #: True when the member is undefined on a dataset without a closed label set.
    requires_closed_labels: bool = False

    def semantic_value(
        self, sample: Any, labels: LabelSet, seed: int = 0
    ) -> "str | list[str] | None":
        if self.requires_closed_labels and not labels.is_closed:
            return None
        return self.fn(sample, labels, seed)

    def completion(
        self, sample: Any, labels: LabelSet, seed: int = 0, arm: str = "rendered"
    ) -> str | None:
        """The member's semantic value, written down for this task and this arm."""
        value = self.semantic_value(sample, labels, seed)
        if value is None:
            return None
        template = detect_template(sample) if arm == "rendered" else BARE_TEMPLATE

        if self.semantic == "literal":
            # Not label-valued, so no template applies in either arm. echo,
            # refusal, boilerplate, all_letters, empty and whitespace are the
            # texts they are; dressing them in "ANSWER:" would be inventing a
            # different member rather than rendering this one.
            return value if isinstance(value, str) else " ".join(value)
        if self.semantic == "placeholder":
            return template.render_placeholder("A")
        if self.semantic == "labels":
            values = value if isinstance(value, list) else [value]
            return template.render_many(values)
        single = value if isinstance(value, str) else " ".join(value)
        return template.render_one(single)

    def applies_to(self, labels: LabelSet) -> bool:
        return labels.is_closed or not self.requires_closed_labels

    @property
    def templated(self) -> bool:
        """True when the rendered arm can differ from the raw arm."""
        return self.semantic in ("label", "labels", "placeholder")


# -- content-free members ---------------------------------------------------


def _empty(sample: Any, labels: LabelSet, seed: int) -> str:
    return ""


def _whitespace(sample: Any, labels: LabelSet, seed: int) -> str:
    return "\n"


def _refusal(sample: Any, labels: LabelSet, seed: int) -> str:
    return REFUSAL_TEXT


def _all_labels(sample: Any, labels: LabelSet, seed: int) -> list[str]:
    """Every distinct target in the dataset.

    This is the member that reproduces Inspect Evals issue #2331. On ``paws``
    the distinct targets are "Yes" and "No" and the task declares no answer
    template, so both arms are the constant string "No Yes" -- and an
    ``includes()`` scorer credits it on every sample, because whatever the
    sample's target is, it is a substring of that constant.

    On a multiple-choice task the distinct targets are option letters, so the
    rendered arm is "ANSWER: A, B, C, D": the same idea, name every label,
    written in the form that task's scorer can actually read.
    """
    return list(labels.labels)


def _all_letters(sample: Any, labels: LabelSet, seed: int) -> str:
    return ALL_LETTERS_TEXT


def _echo(sample: Any, labels: LabelSet, seed: int) -> str:
    return normalize_input(getattr(sample, "input", ""))


def _boilerplate(sample: Any, labels: LabelSet, seed: int) -> str:
    return BOILERPLATE_TEXT


def _format_only(sample: Any, labels: LabelSet, seed: int) -> str:
    """The placeholder the answer template is filled with. See
    ``AnswerTemplate.render_placeholder``: this member is the template itself."""
    return "A"


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
        semantic="literal",
    ),
    BatteryMember(
        name="whitespace",
        kind="content_free",
        description="a single newline",
        fn=_whitespace,
        semantic="literal",
    ),
    BatteryMember(
        name="refusal",
        kind="content_free",
        description="a short refusal sentence",
        fn=_refusal,
        semantic="literal",
    ),
    BatteryMember(
        name="all_labels",
        kind="content_free",
        description="every distinct target in the dataset",
        fn=_all_labels,
        semantic="labels",
        requires_closed_labels=True,
    ),
    BatteryMember(
        name="all_letters",
        kind="content_free",
        description="the option letters A B C D E, bare",
        fn=_all_letters,
        semantic="literal",
    ),
    BatteryMember(
        name="echo",
        kind="content_free",
        description="the sample input, echoed back verbatim",
        fn=_echo,
        semantic="literal",
    ),
    BatteryMember(
        name="boilerplate",
        kind="content_free",
        description="a long fluent paragraph containing no task content",
        fn=_boilerplate,
        semantic="literal",
    ),
    BatteryMember(
        name="format_only",
        kind="content_free",
        description="the answer template with a placeholder",
        fn=_format_only,
        semantic="placeholder",
    ),
)

REFERENCE_MEMBERS: tuple[BatteryMember, ...] = (
    BatteryMember(
        name="majority",
        kind="reference",
        description="the modal target of the dataset",
        fn=_majority,
        semantic="label",
    ),
    BatteryMember(
        name="uniform",
        kind="reference",
        description="a target drawn uniformly from the label set, averaged over seeds",
        fn=_uniform,
        semantic="label",
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

    parts: list[str] = ["arms=" + ",".join(ARMS)]
    for member in BATTERY:
        parts.append(
            f"{member.name}|{member.kind}|{member.semantic}|{member.seeds}"
            f"|{member.requires_closed_labels}"
        )
    parts.extend([REFUSAL_TEXT, BOILERPLATE_TEXT, FORMAT_ONLY_TEXT, ALL_LETTERS_TEXT])
    parts.append(f"{MAX_DISTINCT_LABELS}|{MAX_LABEL_CHARS}")
    parts.append(
        "render: choice one->ANSWER: v; choice many->ANSWER: comma-joined; bare->identity"
    )
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return digest[:12]
