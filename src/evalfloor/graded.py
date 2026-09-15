"""The model-graded arm: drive graded scorers with the same battery, one cheap judge.

Everything in the deterministic arm is free and exact. This arm is neither, and
the whole design follows from that:

*   **One cheap judge**, chosen from whichever API key exists on the machine and
    overridable with ``EVALFLOOR_GRADER``. Its model id and the snapshot the
    provider actually served are recorded in **every** row.
*   **Capped at 100 samples per task per member**, taken after sorting by sample
    id (instrument defect 004: several evals shuffle unseeded, so an uncapped
    sort is the only way a cap means the same thing twice).
*   **Wilson intervals, never bare rates.** A rate over 100 sampled items is not
    a rate over the dataset, and printing it as though it were is the exact
    mistake this project exists to find.
*   **Every result cached to disk**, keyed by everything that could change it, so
    a rerun costs nothing and an interrupted run resumes.
*   **Refusals are data.** If the grader or the provider declines, the text is
    written verbatim to ``results/refusals.jsonl`` with a hash of the prompt and
    counted in the table. Never reworded, never retried beyond one identical
    retry.
*   **A cost guard that runs first.** The estimate is printed before anything is
    called, and the run refuses if it exceeds the budget.

The judge is pointed at the tasks by setting ``INSPECT_EVAL_MODEL``, which is
what Inspect's ``get_model()`` resolves to when a scorer does not name a model.
Tasks that hard-code their own grader are recorded as such rather than silently
graded by something else.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import math
import os
import pathlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Sequence

from .battery import ARMS, BATTERY, BatteryMember, LabelSet, battery_fingerprint
from .drive import (
    MOCK_MODEL,
    ArmResult,
    SampleView,
    TaskRun,
    label_set,
    resolve_task,
    scorer_names,
    task_samples,
)

# --------------------------------------------------------------------------
# Keys and grader selection
# --------------------------------------------------------------------------

#: Checked in this order. Values are never read into any output.
KEY_ENV_VARS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)

#: Override the grader entirely, e.g. EVALFLOOR_GRADER=anthropic/claude-haiku-4-5
GRADER_ENV_VAR = "EVALFLOOR_GRADER"


def detect_keys() -> dict[str, bool]:
    """Which provider keys are present. Only ever returns booleans."""
    return {name: bool(os.environ.get(name, "").strip()) for name in KEY_ENV_VARS}


@dataclass(frozen=True)
class Grader:
    """A judge, and what it costs to ask it something."""

    model: str
    family: str
    #: USD per million tokens. None when this project has not verified a price,
    #: in which case the cost guard refuses to guess -- see estimate_cost.
    price_in_per_mtok: float | None
    price_out_per_mtok: float | None
    price_source: str
    is_mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


#: Cheapest current model per family.
#:
#: The Anthropic price is the Claude Haiku 4.5 row of Anthropic's published
#: model table ($1.00 in / $5.00 out per MTok), which is the cheapest current
#: Anthropic model. The others are deliberately left unpriced: this project has
#: not verified them, and a cost guard built on a guessed price is worse than no
#: cost guard. Supply --price-in/--price-out to run with one of those.
GRADERS: dict[str, Grader] = {
    "anthropic": Grader(
        model="anthropic/claude-haiku-4-5",
        family="anthropic",
        price_in_per_mtok=1.00,
        price_out_per_mtok=5.00,
        price_source="Anthropic published model pricing, cheapest current model",
        is_mock=False,
    ),
    "openai": Grader(
        model="openai/gpt-5.5-mini",
        family="openai",
        price_in_per_mtok=None,
        price_out_per_mtok=None,
        price_source="not verified by this project; pass --price-in/--price-out",
        is_mock=False,
    ),
    "openrouter": Grader(
        model="openrouter/anthropic/claude-haiku-4-5",
        family="openrouter",
        price_in_per_mtok=None,
        price_out_per_mtok=None,
        price_source="not verified by this project; pass --price-in/--price-out",
        is_mock=False,
    ),
    "mock": Grader(
        model=MOCK_MODEL,
        family="mock",
        price_in_per_mtok=0.0,
        price_out_per_mtok=0.0,
        price_source="no provider is called",
        is_mock=True,
    ),
}

#: Which key selects which grader, in preference order (cheapest verified first).
KEY_TO_FAMILY: tuple[tuple[str, str], ...] = (
    ("ANTHROPIC_API_KEY", "anthropic"),
    ("OPENAI_API_KEY", "openai"),
    ("OPENROUTER_API_KEY", "openrouter"),
)

#: A second grader from a different family, for the disagreement control.
DIFFERENT_FAMILY: dict[str, str] = {
    "anthropic": "openai",
    "openai": "anthropic",
    "openrouter": "anthropic",
}


class NoGraderError(RuntimeError):
    pass


def choose_grader(explicit: str | None = None, allow_mock: bool = True) -> Grader:
    """Pick the judge: explicit argument, then env var, then whichever key exists."""
    spec = explicit or os.environ.get(GRADER_ENV_VAR, "").strip() or None
    if spec:
        for grader in GRADERS.values():
            if grader.model == spec:
                return grader
        family = spec.split("/", 1)[0]
        return Grader(
            model=spec,
            family=family,
            price_in_per_mtok=None,
            price_out_per_mtok=None,
            price_source=f"explicitly requested ({GRADER_ENV_VAR} or --grader); price unverified",
            is_mock=spec.startswith("mockllm"),
        )

    keys = detect_keys()
    for env_name, family in KEY_TO_FAMILY:
        if keys.get(env_name):
            return GRADERS[family]

    if allow_mock:
        return GRADERS["mock"]
    raise NoGraderError(
        "no grader available: none of "
        + ", ".join(KEY_ENV_VARS)
        + f" is set, and no {GRADER_ENV_VAR} override was given"
    )


def choose_second_grader(first: Grader, explicit: str | None = None) -> Grader | None:
    """A grader from a different family, for the judge-disagreement control."""
    if explicit:
        return choose_grader(explicit)
    keys = detect_keys()
    wanted = DIFFERENT_FAMILY.get(first.family)
    if not wanted:
        return None
    for env_name, family in KEY_TO_FAMILY:
        if family == wanted and keys.get(env_name):
            return GRADERS[family]
    return None


#: Task parameters that name the grader. Every model-graded task in the
#: collection takes one of these and defaults it to a hard-coded provider model
#: (``coconot`` defaults to openai/gpt-3.5-turbo, ``uccb`` to openai/gpt-4o-mini,
#: and so on). Setting INSPECT_EVAL_MODEL alone does **not** redirect those --
#: the default is passed explicitly, so ``get_model()`` never sees None. The
#: judge has to be injected as a task argument, which is what this list is for.
GRADER_PARAM_NAMES: tuple[str, ...] = (
    "grader",
    "grader_model",
    "grader_models",
    "judge_model",
    "judge_llm",
    "judge_models",
    "scorer_model",
    "binary_judge_model",
    "numeric_judge_model",
    "expansion_llm",
)


def grader_task_args(task_name: str, grader: Grader) -> dict[str, Any]:
    """Task kwargs that point this task's grader at our judge.

    Introspects the registered task function and fills every grader-ish
    parameter it declares, matching list-valued defaults with a one-element
    list. Returns an empty dict for a task that exposes no such parameter --
    those are recorded as "grader not redirectable" rather than being graded by
    whatever the task hard-codes.
    """
    import inspect as pyinspect

    from inspect_ai._util.registry import registry_find, registry_info

    if task_name.startswith("evalfloor"):
        return {}
    try:
        import inspect_evals._registry  # noqa: F401

        fn = next(
            t
            for t in registry_find(lambda i: i.type == "task")
            if registry_info(t).name == task_name
        )
        sig = pyinspect.signature(fn)
    except Exception:
        return {}

    args: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name not in GRADER_PARAM_NAMES:
            continue
        default = param.default
        args[name] = [grader.model] if isinstance(default, list) else grader.model
    return args


@contextlib.contextmanager
def grader_active(grader: Grader):
    """Point Inspect's default model resolution at our judge for the duration.

    A model-graded scorer that does not name a model calls ``get_model()``, which
    resolves ``INSPECT_EVAL_MODEL``. Setting it here is what makes "one cheap
    judge" true for the tasks that allow it. Tasks that hard-code a grader are
    recorded as such; they are not silently redirected.
    """
    previous = os.environ.get("INSPECT_EVAL_MODEL")
    os.environ["INSPECT_EVAL_MODEL"] = grader.model
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("INSPECT_EVAL_MODEL", None)
        else:
            os.environ["INSPECT_EVAL_MODEL"] = previous


# --------------------------------------------------------------------------
# Cost estimation, and the guard
# --------------------------------------------------------------------------

#: Per-sample cap. Preregistered.
DEFAULT_CAP = 100

#: Characters per token. A rough but standard approximation; the estimate adds a
#: safety margin on top and the file says so rather than implying precision.
CHARS_PER_TOKEN = 4.0

#: Tokens the grading template itself contributes, beyond input/target/answer.
TEMPLATE_TOKEN_OVERHEAD = 220

#: Output tokens a grader spends on reasoning plus a GRADE line.
ASSUMED_OUTPUT_TOKENS = 200

#: Multiplier applied to the raw token estimate, so the guard errs high.
SAFETY_MARGIN = 1.25


@dataclass
class CostEstimate:
    n_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float | None = None
    priced: bool = True
    assumptions: list[str] = field(default_factory=list)
    per_task: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def describe(self) -> str:
        lines = [
            f"  grading calls      {self.n_calls:,}",
            f"  input tokens       {self.input_tokens:,} (estimated)",
            f"  output tokens      {self.output_tokens:,} (estimated)",
        ]
        if self.priced and self.usd is not None:
            lines.append(f"  estimated cost     ${self.usd:,.2f}")
        else:
            lines.append("  estimated cost     UNKNOWN (no verified price for this grader)")
        for note in self.assumptions:
            lines.append(f"  assumption: {note}")
        return "\n".join(lines)


def arms_for_template(answer_template: str) -> tuple[str, ...]:
    """Which arms are worth paying for on a task with this answer template.

    When a task declares no answer template, the raw and rendered arms are
    identical by construction -- the deterministic sweep demonstrates that on
    every such task at zero cost. Paying a grader twice to re-demonstrate it
    would double the bill of this arm for nothing, so the graded arm runs only
    the rendered arm there, and the report says the raw arm was not run and why.
    """
    if answer_template == "bare":
        return ("rendered",)
    return ARMS


def estimate_cost(
    samples: Sequence[SampleView],
    members: Sequence[BatteryMember],
    labels: LabelSet,
    grader: Grader,
    answer_template: str,
    cap: int = DEFAULT_CAP,
    already_cached: int = 0,
) -> CostEstimate:
    """Estimate before calling anything. Counts only what is not already cached."""
    est = CostEstimate()
    capped = list(samples[:cap])
    arms = arms_for_template(answer_template)

    est.assumptions.append(
        f"{CHARS_PER_TOKEN:.0f} characters per token, +{TEMPLATE_TOKEN_OVERHEAD} "
        f"template tokens, {ASSUMED_OUTPUT_TOKENS} output tokens per call"
    )
    est.assumptions.append(f"safety margin x{SAFETY_MARGIN}")
    est.assumptions.append(f"cap {cap} samples per task per member")
    est.assumptions.append(
        "arms: " + ", ".join(arms) + (
            " (raw not run: identical by construction on a task with no answer template)"
            if len(arms) == 1
            else ""
        )
    )
    if already_cached:
        est.assumptions.append(f"{already_cached:,} calls already cached and free")

    for member in members:
        for seed in member.seeds:
            for arm in arms:
                for sample in capped:
                    completion = member.completion(sample, labels, seed, arm=arm)
                    if completion is None:
                        continue
                    chars = (
                        len(sample.input_text)
                        + len(sample.target_text)
                        + len(completion)
                    )
                    est.n_calls += 1
                    est.input_tokens += int(chars / CHARS_PER_TOKEN) + TEMPLATE_TOKEN_OVERHEAD
                    est.output_tokens += ASSUMED_OUTPUT_TOKENS

    est.n_calls = max(0, est.n_calls - already_cached)
    est.input_tokens = int(est.input_tokens * SAFETY_MARGIN)
    est.output_tokens = int(est.output_tokens * SAFETY_MARGIN)

    if grader.price_in_per_mtok is None or grader.price_out_per_mtok is None:
        est.priced = False
        est.usd = None
        est.assumptions.append(f"price source: {grader.price_source}")
    else:
        est.usd = (
            est.input_tokens / 1_000_000 * grader.price_in_per_mtok
            + est.output_tokens / 1_000_000 * grader.price_out_per_mtok
        )
        est.assumptions.append(
            f"price: ${grader.price_in_per_mtok}/MTok in, "
            f"${grader.price_out_per_mtok}/MTok out ({grader.price_source})"
        )
    return est


class BudgetExceeded(RuntimeError):
    pass


def enforce_budget(estimate: CostEstimate, budget_usd: float, grader: Grader) -> None:
    """Refuse to run when the estimate exceeds the budget. Called before any call."""
    if grader.is_mock:
        return
    if not estimate.priced or estimate.usd is None:
        raise BudgetExceeded(
            f"refusing to run: no verified price for grader {grader.model}, so the "
            f"${budget_usd:.2f} budget cannot be enforced.\n"
            f"  {grader.price_source}\n"
            "Pass --price-in and --price-out to state the price explicitly, or use a "
            "grader this project has a price for."
        )
    if estimate.usd > budget_usd:
        raise BudgetExceeded(
            f"refusing to run: estimated ${estimate.usd:,.2f} exceeds the "
            f"${budget_usd:,.2f} budget.\n"
            f"{estimate.describe()}\n"
            "Raise --budget-usd deliberately, lower --cap, or sweep fewer tasks."
        )


# --------------------------------------------------------------------------
# The result cache
# --------------------------------------------------------------------------


@dataclass
class GradedCache:
    """Append-only JSONL cache so a rerun costs nothing and an interrupt resumes."""

    path: pathlib.Path
    entries: dict[str, dict[str, Any]] = field(default_factory=dict)
    hits: int = 0
    misses: int = 0

    @classmethod
    def load(cls, path: pathlib.Path) -> "GradedCache":
        cache = cls(path=path)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = row.get("key")
                if key:
                    cache.entries[key] = row
        return cache

    @staticmethod
    def key(
        task: str,
        scorer: str,
        sample_id: Any,
        member: str,
        seed: int,
        arm: str,
        grader_model: str,
    ) -> str:
        blob = "|".join(
            [
                task,
                scorer,
                str(sample_id),
                member,
                str(seed),
                arm,
                grader_model,
                battery_fingerprint(),
            ]
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        row = self.entries.get(key)
        if row is not None:
            self.hits += 1
        else:
            self.misses += 1
        return row

    def put(self, key: str, value: dict[str, Any]) -> None:
        row = {"key": key, **value}
        self.entries[key] = row
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def count_for(
        self,
        task: str,
        scorer: str,
        samples: Sequence[SampleView],
        members: Sequence[BatteryMember],
        arms: Sequence[str],
        grader_model: str,
    ) -> int:
        n = 0
        for member in members:
            for seed in member.seeds:
                for arm in arms:
                    for sample in samples:
                        if (
                            self.key(
                                task, scorer, sample.id, member.name, seed, arm, grader_model
                            )
                            in self.entries
                        ):
                            n += 1
        return n


# --------------------------------------------------------------------------
# Refusals are data
# --------------------------------------------------------------------------

#: Markers that mean the grader or the provider declined, rather than graded.
REFUSAL_MARKERS: tuple[str, ...] = (
    "i can't help",
    "i cannot help",
    "i can't assist",
    "i cannot assist",
    "i won't",
    "i will not",
    "unable to assist",
    "cannot comply",
    "content_filter",
    "content policy",
    "safety system",
    "refusal",
    "declined",
    "blocked by",
)


def looks_like_refusal(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in REFUSAL_MARKERS)


@dataclass
class RefusalLog:
    """Writes refusals verbatim. Never rewords, never summarises."""

    path: pathlib.Path
    count: int = 0

    def record(
        self,
        task: str,
        scorer: str,
        sample_id: Any,
        member: str,
        arm: str,
        grader: Grader,
        prompt_text: str,
        verbatim: str,
        kind: str,
        retried: bool,
    ) -> None:
        self.count += 1
        row = {
            "task": task,
            "scorer": scorer,
            "sample_id": str(sample_id),
            "member": member,
            "arm": arm,
            "grader_model": grader.model,
            "grader_family": grader.family,
            "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
            "prompt_chars": len(prompt_text),
            "kind": kind,
            "retried_once": retried,
            # Verbatim. Not reworded, not truncated to make it look tidier.
            "verbatim": verbatim,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


# --------------------------------------------------------------------------
# Driving one graded arm
# --------------------------------------------------------------------------


async def _score_once(scorer: Any, sample: SampleView, completion: str) -> Any:
    from inspect_ai.scorer import Target

    from .drive import build_state

    state = build_state(sample, completion)
    return await scorer(state, Target(sample.target))


async def run_graded_arm(
    task_name: str,
    scorer: Any,
    scorer_name: str,
    member: BatteryMember,
    seed: int,
    arm: str,
    samples: Sequence[SampleView],
    labels: LabelSet,
    grader: Grader,
    cache: GradedCache,
    refusals: RefusalLog,
) -> ArmResult:
    """One (member, seed, arm) over capped samples, cached, refusals recorded."""
    from inspect_ai.scorer import value_to_float

    result = ArmResult(
        task=task_name,
        scorer=scorer_name,
        member=member.name,
        seed=seed,
        arm=arm,
        n_samples=len(samples),
    )
    if not member.applies_to(labels):
        result.applicable = False
        result.not_applicable_reason = (
            "dataset has no closed label set "
            f"({labels.n_distinct} distinct targets over {labels.n_samples} samples)"
        )
        return result

    to_float = value_to_float()
    started = time.monotonic()

    for sample in samples:
        completion = member.completion(sample, labels, seed, arm=arm)
        if completion is None:
            result.applicable = False
            result.not_applicable_reason = "member returned no completion for this sample"
            break
        if not result.example_completion:
            result.example_completion = completion

        key = GradedCache.key(
            task_name, scorer_name, sample.id, member.name, seed, arm, grader.model
        )
        cached = cache.get(key)
        if cached is not None:
            if cached.get("refusal"):
                result.n_refusals += 1
                continue
            if cached.get("ungradeable"):
                result.n_ungradeable += 1
                continue
            if cached.get("error"):
                result.n_errors += 1
                if result.first_error is None:
                    result.first_error = str(cached["error"])[:300]
                continue
            result.n_scored += 1
            result.score_sum += float(cached.get("value", 0.0))
            if float(cached.get("value", 0.0)) >= 1.0:
                result.n_correct += 1
            continue

        prompt_text = f"{sample.input_text}\n{sample.target_text}\n{completion}"
        score = None
        error_text: str | None = None
        retried = False

        for attempt in (1, 2):
            try:
                score = await _score_once(scorer, sample, completion)
                error_text = None
                break
            except Exception as exc:  # a grader that declines is data, not a crash
                error_text = f"{type(exc).__name__}: {exc}"
                if attempt == 1:
                    # Exactly one identical retry. No backoff games, no rewording.
                    retried = True
                    continue

        if score is None:
            kind = "refusal" if looks_like_refusal(error_text or "") else "error"
            if kind == "refusal":
                result.n_refusals += 1
                refusals.record(
                    task_name, scorer_name, sample.id, member.name, arm, grader,
                    prompt_text, error_text or "", "provider_exception", retried,
                )
                cache.put(key, {"refusal": True, "verbatim": error_text,
                                "grader_model": grader.model})
            else:
                result.n_errors += 1
                if result.first_error is None:
                    result.first_error = (error_text or "")[:300]
                cache.put(key, {"error": error_text, "grader_model": grader.model})
            continue

        explanation = getattr(score, "explanation", "") or ""
        value = to_float(score.value)
        snapshot = _snapshot_from_score(score, grader)

        if not math.isfinite(value):
            # The grader answered, but emitted nothing that parses as a grade.
            # Not a score, not an error, and emphatically not a zero: coercing it
            # to 0.0 would report a floor that was never measured. Excluded from
            # the denominator and counted separately.
            result.n_ungradeable += 1
            cache.put(
                key,
                {
                    "ungradeable": True,
                    "grader_model": grader.model,
                    "grader_snapshot": snapshot,
                    "explanation": explanation[:2000],
                },
            )
            continue

        # A grader that answered with a refusal instead of a grade is a refusal,
        # even though the call succeeded and the scorer returned INCORRECT.
        if value == 0.0 and looks_like_refusal(explanation):
            result.n_refusals += 1
            refusals.record(
                task_name, scorer_name, sample.id, member.name, arm, grader,
                prompt_text, explanation, "grader_declined_to_grade", retried,
            )
            cache.put(key, {"refusal": True, "verbatim": explanation,
                            "grader_model": grader.model, "grader_snapshot": snapshot})
            continue

        result.n_scored += 1
        result.score_sum += value
        if value >= 1.0:
            result.n_correct += 1
        cache.put(
            key,
            {
                "value": value,
                "grader_model": grader.model,
                "grader_snapshot": snapshot,
                "explanation": explanation[:2000],
            },
        )

    result.elapsed_s = time.monotonic() - started
    return result


def _snapshot_from_score(score: Any, grader: Grader) -> str:
    """The model id the provider actually served, when it can be recovered."""
    for attr in ("metadata",):
        meta = getattr(score, attr, None)
        if isinstance(meta, dict):
            for candidate in ("model", "grader_model", "snapshot"):
                if meta.get(candidate):
                    return str(meta[candidate])
    return grader.model


async def grade_task_async(
    task_name: str,
    grader: Grader,
    cap: int = DEFAULT_CAP,
    members: Iterable[BatteryMember] = BATTERY,
    cache: GradedCache | None = None,
    refusals: RefusalLog | None = None,
    budget_usd: float | None = None,
    task: Any | None = None,
    print_estimate: bool = True,
) -> tuple[TaskRun, CostEstimate]:
    """Run the battery over one model-graded task with one judge."""
    members = list(members)
    cache = cache or GradedCache.load(pathlib.Path("results/graded_cache.jsonl"))
    refusals = refusals or RefusalLog(pathlib.Path("results/refusals.jsonl"))

    started = time.monotonic()
    run = TaskRun(task=task_name)
    run.grader_model = grader.model
    run.grader_snapshot = grader.model
    run.capped_at = cap

    with grader_active(grader):
        task_args = grader_task_args(task_name, grader)
        run.grader_injected_via = ", ".join(sorted(task_args)) if task_args else ""
        try:
            if task is None:
                task = resolve_task(task_name, **task_args)
        except TypeError:
            # The task rejected our grader kwargs. Fall back to the plain call and
            # record that the grader could not be redirected, rather than silently
            # grading with whatever the task hard-codes.
            run.grader_injected_via = ""
            try:
                task = resolve_task(task_name)
            except Exception as exc:
                run.error = f"{type(exc).__name__}: {exc}"[:500]
                run.elapsed_s = time.monotonic() - started
                return run, CostEstimate()
        except Exception as exc:
            run.error = f"{type(exc).__name__}: {exc}"[:500]
            run.elapsed_s = time.monotonic() - started
            return run, CostEstimate()

        try:
            samples = task_samples(task, limit=cap)
        except Exception as exc:
            run.error = f"dataset load failed: {type(exc).__name__}: {exc}"[:500]
            run.elapsed_s = time.monotonic() - started
            return run, CostEstimate()

        from .battery import detect_template

        labels = label_set(samples)
        run.n_samples = len(samples)
        run.n_distinct_labels = labels.n_distinct
        run.labels_closed = labels.is_closed
        run.majority_label = labels.majority_label
        run.majority_share = labels.majority_share
        run.answer_template = detect_template(samples[0]).name if samples else "bare"

        scorers = getattr(task, "scorer", None) or []
        if not isinstance(scorers, (list, tuple)):
            scorers = [scorers]
        names = scorer_names(task)
        run.scorers = names

        arms = arms_for_template(run.answer_template)
        cached_already = sum(
            cache.count_for(task_name, name, samples, members, arms, grader.model)
            for name in names
        )
        estimate = estimate_cost(
            samples, members, labels, grader, run.answer_template, cap, cached_already
        )
        if print_estimate:
            print(f"  cost estimate for {task_name} with {grader.model}:")
            print(estimate.describe())
        if budget_usd is not None:
            enforce_budget(estimate, budget_usd, grader)

        for scorer, name in zip(scorers, names):
            for member in members:
                for seed in member.seeds:
                    for arm in arms:
                        run.arms.append(
                            await run_graded_arm(
                                task_name, scorer, name, member, seed, arm,
                                samples, labels, grader, cache, refusals,
                            )
                        )

    run.n_refusals = sum(a.n_refusals for a in run.arms)
    run.elapsed_s = time.monotonic() - started
    return run, estimate


def grade_task(task_name: str, grader: Grader, **kwargs: Any) -> tuple[TaskRun, CostEstimate]:
    return asyncio.run(grade_task_async(task_name, grader, **kwargs))


# --------------------------------------------------------------------------
# Judge-disagreement control
# --------------------------------------------------------------------------


@dataclass
class Disagreement:
    task: str
    grader_a: str
    grader_b: str
    n_compared: int = 0
    n_disagree: int = 0
    ci_low: float | None = None
    ci_high: float | None = None

    @property
    def rate(self) -> float:
        return self.n_disagree / self.n_compared if self.n_compared else 0.0

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["rate"] = self.rate
        return out


def disagreement_from_cache(
    task_name: str,
    scorer_names_: Sequence[str],
    samples: Sequence[SampleView],
    members: Sequence[BatteryMember],
    arms: Sequence[str],
    grader_a: Grader,
    grader_b: Grader,
    cache: GradedCache,
) -> Disagreement:
    """Pair up every cached cell that both graders scored, and count differences."""
    from .aggregate import wilson_interval

    result = Disagreement(task=task_name, grader_a=grader_a.model, grader_b=grader_b.model)
    for name in scorer_names_:
        for member in members:
            for seed in member.seeds:
                for arm in arms:
                    for sample in samples:
                        row_a = cache.entries.get(
                            GradedCache.key(
                                task_name, name, sample.id, member.name, seed, arm,
                                grader_a.model,
                            )
                        )
                        row_b = cache.entries.get(
                            GradedCache.key(
                                task_name, name, sample.id, member.name, seed, arm,
                                grader_b.model,
                            )
                        )
                        if row_a is None or row_b is None:
                            continue
                        if row_a.get("refusal") or row_b.get("refusal"):
                            continue
                        if row_a.get("error") or row_b.get("error"):
                            continue
                        result.n_compared += 1
                        if float(row_a.get("value", 0.0)) != float(row_b.get("value", 0.0)):
                            result.n_disagree += 1
    result.ci_low, result.ci_high = wilson_interval(result.n_disagree, result.n_compared)
    return result
