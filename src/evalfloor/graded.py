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

#: Checked in this order: **OpenAI first, OpenRouter second, Anthropic last.**
#: Values are never read into any output -- only the name and a boolean.
KEY_ENV_VARS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
)

#: Override the judge, e.g. EVALFLOOR_JUDGE=openai/gpt-5.6-luna
JUDGE_ENV_VAR = "EVALFLOOR_JUDGE"

#: Override the second grader used by the judge-disagreement control.
JUDGE2_ENV_VAR = "EVALFLOOR_JUDGE2"

#: Accepted as a fallback for continuity with the first cut of this module.
LEGACY_GRADER_ENV_VAR = "EVALFLOOR_GRADER"
GRADER_ENV_VAR = LEGACY_GRADER_ENV_VAR


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
    #: Price of a cached input token, when the provider publishes one.
    price_cached_in_per_mtok: float | None = None
    #: OpenRouter endpoint to pin to, so the cheap provider actually serves it.
    pin_provider: str | None = None
    #: Set at construction once the model id is confirmed served.
    verified_served: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


#: Where every model id and price below came from. Not recalled, read.
#:
#: ``ai-incident-response/dosecurve/analysis/prices.json`` -- the pricing snapshot
#: Ebin already runs against ("orchestrator-supplied table, 2026-09-13"), and
#: ``dosecurve/harness/providers/openai_compat.py`` for the provider wiring, the
#: base URLs and the key env vars. ``gpt-5.6-luna`` is the model that file records
#: as "Verified live 2026-09-13" and the cheapest of the three OpenAI models in
#: the snapshot.
PRICE_SOURCE_FILE = (
    "profile-update-aug2026/decision-2026-09-15/F-economy-plan.md S1 workload 1 "
    "(verified 2026-09-15), with ids cross-checked against "
    "ai-incident-response/dosecurve/analysis/prices.json and harness/providers/"
)

#: OpenAI will not cache a prefix shorter than this many input tokens (F-economy
#: plan R4). Below it, caching is impossible -- not merely unlikely -- so the
#: cache-hit guard must not treat a zero hit rate as a fault.
OPENAI_CACHE_MIN_TOKENS = 1024

#: Batch and the "flex" service tier are both 50% off list (plan S1), but flex
#: is measurably slow: ~4 calls/minute here, which turns an 8,000-call arm into
#: a ~33-hour run for a saving of about $0.60 on luna. Standard is therefore the
#: default and flex is opt-in with `--tier flex`, for runs where time is free.
FLEX_DISCOUNT = 0.5
DEFAULT_SERVICE_TIER = "standard"
SERVICE_TIER = DEFAULT_SERVICE_TIER

#: Calls per minute measured on flex and on standard, for the wall-clock
#: projection printed before a run. Measured 2026-09-15 on coconot.
MEASURED_CALLS_PER_MIN = {"flex": 4.0, "standard": 12.7}

#: OpenRouter endpoint pinning: the same GLM weights served by DeepInfra at about
#: half the canonical rate. Unpinned, you pay canonical.
OPENROUTER_PIN_PROVIDER = "DeepInfra"

#: Cache reads are billed at this multiple of the input price. From the same
#: snapshot's ``cache_read_multiplier``.
CACHE_READ_MULTIPLIER = 0.1

GRADERS: dict[str, Grader] = {
    # Default judge, chosen on MEASURED cost rather than list price. gpt-5-nano
    # is 4x cheaper per input token, but emits ~13x more output per grading call
    # (277 in / 1,157 out, measured) because it reasons before answering, and
    # output is the expensive side. luna measures 273 in / 87 out, which makes it
    # about 3x cheaper for this arm. luna is also the model named in the
    # complimentary daily-token group for tiers 1-2 (F-economy-plan S2A);
    # nano's inclusion there is unverified.
    "openai": Grader(
        model="openai/gpt-5.6-luna",
        family="openai",
        price_in_per_mtok=0.20,
        price_out_per_mtok=1.20,
        price_cached_in_per_mtok=0.02,
        price_source=PRICE_SOURCE_FILE,
        is_mock=False,
    ),
    # Second grader: cross-lineage by design. Pinned to DeepInfra, which serves
    # the same weights at about half the canonical Z.ai rate.
    "openrouter": Grader(
        model="openrouter/z-ai/glm-5.3-flash",
        family="openrouter",
        price_in_per_mtok=0.075,
        price_out_per_mtok=0.25,
        price_source=PRICE_SOURCE_FILE,
        is_mock=False,
        pin_provider=OPENROUTER_PIN_PROVIDER,
    ),
    # Fallback, used only when luna is not served by the account. Still
    # selectable deliberately with EVALFLOOR_JUDGE=openai/gpt-5-nano.
    "openai_fallback": Grader(
        model="openai/gpt-5-nano",
        family="openai",
        price_in_per_mtok=0.05,
        price_out_per_mtok=0.40,
        price_cached_in_per_mtok=0.005,
        price_source=PRICE_SOURCE_FILE,
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

#: The documented alternative second grader, same class, different lineage again.
ALTERNATIVE_SECOND_GRADER = Grader(
    model="openrouter/deepseek/deepseek-v4.1-flash",
    family="openrouter",
    price_in_per_mtok=0.15,
    price_out_per_mtok=0.60,
    price_source=PRICE_SOURCE_FILE,
    is_mock=False,
)

#: claude-haiku-4-5 is explicitly NOT a judge for this arm: 14x the nano arm,
#: and at these prompt lengths nothing caches (4,096-token minimum).
DO_NOT_USE_AS_JUDGE: frozenset[str] = frozenset(
    {"anthropic/claude-haiku-4-5", "anthropic/claude-haiku-4-5-20251001"}
)

#: Which key selects which judge, in preference order.
#: **OpenAI first, OpenRouter second, Anthropic last.**
KEY_TO_FAMILY: tuple[tuple[str, str], ...] = (
    ("OPENAI_API_KEY", "openai"),
    ("OPENROUTER_API_KEY", "openrouter"),
)

#: A second grader from a different family, for the disagreement control.
DIFFERENT_FAMILY: dict[str, str] = {
    "openai": "openrouter",
    "openrouter": "openai",
}

#: Providers whose prompt caching is automatic -- no request field to set, the
#: provider matches on the prefix and bills the hit at CACHE_READ_MULTIPLIER.
#: Recorded per call from the response, never assumed: dosecurve's
#: openai_compat.py already reads ``prompt_tokens_details.cached_tokens`` into
#: ``cache_read_input_tokens``, and this arm reads the same field.
AUTOMATIC_CACHE_FAMILIES: frozenset[str] = frozenset({"openai"})

#: Providers where caching is per-model rather than a property of the provider.
#: Reported through the same field when the routed model supports it, so the
#: honest thing is to measure it rather than promise it.
PER_MODEL_CACHE_FAMILIES: frozenset[str] = frozenset({"openrouter"})


class NoGraderError(RuntimeError):
    pass


def openai_serves(model_id: str, timeout: int = 20) -> bool | None:
    """Is this model id actually served? ``GET /v1/models``, same check Ebin's
    harness does at construction (``openai_compat.py:_verify_model``).

    Returns None when the list could not be fetched -- a flaky endpoint must not
    decide a judge, and the request itself would report a bad id anyway.
    """
    import urllib.request

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    bare = model_id.split("/", 1)[-1]
    request = urllib.request.Request(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    served = {str(m.get("id")) for m in (payload.get("data") or [])}
    return bare in served if served else None


def resolve_openai_judge(preferred: Grader, fallback: Grader) -> tuple[Grader, str]:
    """``(grader, note)``. Falls back when the preferred id is not served.

    Which one was used is recorded rather than inferred: a silent fallback would
    put a different model's numbers under the preferred model's name.
    """
    from dataclasses import replace

    served = openai_serves(preferred.model)
    if served is True:
        return replace(preferred, verified_served=True), f"{preferred.model} served"
    if served is False:
        return (
            replace(fallback, verified_served=True),
            f"{preferred.model} NOT served by this account; fell back to {fallback.model}",
        )
    return (
        replace(preferred, verified_served=None),
        f"could not reach GET /v1/models; using {preferred.model} unverified",
    )


def judge_model_args(
    grader: Grader, task_name: str = "", tier: str = DEFAULT_SERVICE_TIER
) -> dict[str, Any]:
    """Provider-specific request arguments for this judge.

    OpenAI: ``service_tier="flex"`` is 50% off list and the graded arm is not
    latency-sensitive, so it is the default. ``prompt_cache_key`` is set per task
    (plan R5) so that per-task cache accounting is observable at all.

    OpenRouter: pin the endpoint, because unpinned you pay the canonical rate for
    the same weights.
    """
    args: dict[str, Any] = {}
    if grader.family == "openai" and not grader.is_mock:
        if tier and tier != "standard":
            args["service_tier"] = tier
        if task_name:
            args["prompt_cache_key"] = f"evalfloor::{task_name}"
    if grader.pin_provider:
        args["extra_body"] = {
            "provider": {
                "order": [grader.pin_provider],
                "allow_fallbacks": False,
            }
        }
    return args


def _env_spec(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def choose_grader(explicit: str | None = None, allow_mock: bool = True) -> Grader:
    """Pick the judge: explicit argument, then ``EVALFLOOR_JUDGE``, then keys.

    Key preference is OpenAI, then OpenRouter, then Anthropic.
    """
    spec = explicit or _env_spec(JUDGE_ENV_VAR, LEGACY_GRADER_ENV_VAR)
    if spec and spec in DO_NOT_USE_AS_JUDGE:
        raise NoGraderError(
            f"{spec} is excluded as a judge for this arm: about 14x the cost of the "
            "nano arm, and at these prompt lengths nothing caches (4,096-token "
            "minimum). See F-economy-plan.md S1 workload 1, row 'do not use'."
        )
    if spec:
        if spec == STUB_MODEL:
            return GRADERS_STUB
        for grader in GRADERS.values():
            if grader.model == spec:
                return grader
        if spec == ALTERNATIVE_SECOND_GRADER.model:
            return ALTERNATIVE_SECOND_GRADER
        family = spec.split("/", 1)[0]
        return Grader(
            model=spec,
            family=family,
            price_in_per_mtok=None,
            price_out_per_mtok=None,
            price_source=(
                f"explicitly requested ({JUDGE_ENV_VAR} / {JUDGE2_ENV_VAR} or "
                "--grader); price not in the snapshot, so it must be stated with "
                "--price-in/--price-out"
            ),
            is_mock=spec.startswith("mockllm"),
        )

    keys = detect_keys()
    for env_name, family in KEY_TO_FAMILY:
        if keys.get(env_name):
            if family == "openai":
                grader, note = resolve_openai_judge(
                    GRADERS["openai"], GRADERS["openai_fallback"]
                )
                print(f"  judge verification: {note}")
                return grader
            return GRADERS[family]

    if allow_mock:
        return GRADERS["mock"]
    raise NoGraderError(
        "no judge available.\n"
        "\n"
        "  Checked, in order: "
        + ", ".join(KEY_ENV_VARS)
        + " -- none is set.\n"
        "\n"
        f"  Set one of those, or name a judge with {JUDGE_ENV_VAR} (and a second\n"
        f"  grader for the disagreement control with {JUDGE2_ENV_VAR}).\n"
        "\n"
        f"  Defaults when a key is present: {GRADERS['openai'].model} on OpenAI,\n"
        f"  {GRADERS['openrouter'].model} on OpenRouter,\n"
        f"  {GRADERS['anthropic'].model} on Anthropic (last resort).\n"
        "\n"
        "  To exercise the harness without any provider, use\n"
        f"  --grader {STUB_MODEL}, which emits a fixed parseable grade and\n"
        "  is labelled as a non-result everywhere it appears."
    )


def choose_second_grader(first: Grader, explicit: str | None = None) -> Grader | None:
    """A grader from a different family, for the judge-disagreement control.

    Explicit argument, then ``EVALFLOOR_JUDGE2``, then the preferred different
    family if its key is present. Returns None rather than silently reusing the
    first judge -- two runs of the same model is not a disagreement control.
    """
    spec = explicit or _env_spec(JUDGE2_ENV_VAR)
    if spec:
        return choose_grader(spec)
    keys = detect_keys()
    wanted = DIFFERENT_FAMILY.get(first.family)
    if not wanted:
        return None
    for env_name, family in KEY_TO_FAMILY:
        if family == wanted and keys.get(env_name):
            candidate = GRADERS[family]
            if candidate.family != first.family:
                return candidate
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


def grader_task_args(
    task_name: str, grader: Grader, model: Any | None = None
) -> dict[str, Any]:
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

    # Hand the task a Model object rather than a spec string, so the same object
    # can be metered: that is how call counts and cached tokens get measured
    # instead of assumed. (The stub has no provider to resolve its name anyway.)
    value: Any = model if model is not None else (
        stub_grader_model() if grader.model == STUB_MODEL else grader.model
    )

    args: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name not in GRADER_PARAM_NAMES:
            continue
        default = param.default
        args[name] = [value] if isinstance(default, list) else value
    return args


#: The grade a stub grader emits. "I" = incorrect, so the stub credits nothing
#: and the resulting floor is a real zero rather than an unparseable NaN.
STUB_GRADE = "I"

#: Grader spec that selects the stub below instead of a provider.
STUB_MODEL = "mockllm/graded-stub"

GRADERS_STUB = Grader(
    model=STUB_MODEL,
    family="mock",
    price_in_per_mtok=0.0,
    price_out_per_mtok=0.0,
    price_source="no provider is called; emits a fixed, parseable grade",
    is_mock=True,
)


def stub_grader_model(grade: str = STUB_GRADE) -> Any:
    """A mock model that emits a **parseable** grade.

    The bare ``mockllm/model`` answers "Default output from mockllm/model", which
    carries no ``GRADE:`` line, so every grading call comes back *ungradeable*
    and the arm has no floor at all. That is the correct thing to report, and the
    harness does report it -- but it exercises only half the path: the grader is
    called and nothing is ever parsed back out of it.

    This stub closes the loop with no provider and no key. It answers every
    grading request with a well-formed grade, so the scorer parses it, the value
    flows into the arm, intervals are computed over real counts, and the cache
    stores real values.

    It is still **not evidence about any eval.** It grades nothing; it only
    proves the pipeline carries a grade from the judge through to the matrix.
    Note the vocabulary problem it has to work around. Inspect's default grade
    pattern looks for ``GRADE: C|P|I``, but graded evals routinely define their
    own: ``coconot`` parses ``ACCEPTABLE|UNACCEPTABLE|NEITHER``, its contrast
    subset ``NONCOMPLIANCE|COMPLIANCE|NEITHER``. There is no single token that
    satisfies all of them, so the stub emits the "did not meet the criterion"
    verdict in each vocabulary it knows, one per line. That is honest for a test
    double whose whole job is to answer "no" in whatever language it is asked --
    and it is also the reason a real judge has to be prompted per eval rather
    than dropped in generically.
    """
    from inspect_ai.model import ModelOutput, get_model

    body = "\n".join(
        [
            "The answer does not meet the criterion.",
            f"GRADE: {grade}",
            "UNACCEPTABLE",
            "NONCOMPLIANCE",
        ]
    )

    def always_grade(*args: Any, **kwargs: Any) -> Any:
        return ModelOutput.from_content(model=STUB_MODEL, content=body)

    return get_model("mockllm/model", custom_outputs=always_grade, memoize=False)


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
#: This is the **static prefix**: the grading instructions and the eval's own
#: grade vocabulary. It is identical for every sample of a task, which is exactly
#: what makes it cacheable -- see `cacheable_prefix_first`.
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
    #: Input tokens expected to be served from the provider's prompt cache.
    cached_input_tokens: int = 0
    #: "automatic", "per-model" or "none" for this grader's provider.
    caching: str = "none"
    tier: str = DEFAULT_SERVICE_TIER
    #: Projected wall-clock minutes, from the measured call rate for this tier.
    projected_minutes: float = 0.0
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
            f"  service tier       {self.tier}"
            + (
                f", projected wall clock {self.projected_minutes / 60:.1f} h"
                if self.projected_minutes >= 90
                else f", projected wall clock {self.projected_minutes:.0f} min"
            ),
            f"  prompt caching     {self.caching}"
            + (
                f", {self.cached_input_tokens:,} input tokens from cache"
                if self.cached_input_tokens
                else ""
            ),
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
    tier: str = DEFAULT_SERVICE_TIER,
) -> CostEstimate:
    """Estimate before calling anything. Counts only what is not already cached."""
    est = CostEstimate()
    est.tier = tier
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

    # Prompt caching. The static prefix is the same for every call on a task, so
    # on a caching provider all but the first call read it from cache at
    # CACHE_READ_MULTIPLIER of the input price. Only the prefix is cacheable; the
    # sample text after it is billed in full every time.
    caching = caches_prompts(grader)
    est.caching = caching
    prefix_tokens = int(TEMPLATE_TOKEN_OVERHEAD * SAFETY_MARGIN)
    if (
        caching == "automatic"
        and grader.family == "openai"
        and prefix_tokens < OPENAI_CACHE_MIN_TOKENS
    ):
        # Below OpenAI's minimum nothing caches, so promising a saving here would
        # be an estimate that cannot come true. Plan rule R4.
        est.caching = "none (prefix below the provider minimum)"
        est.assumptions.append(
            f"no caching assumed: the static prefix is about {prefix_tokens:,} tokens, "
            f"below OpenAI's {OPENAI_CACHE_MIN_TOKENS:,}-token minimum. Not padded to "
            "cross it -- filler to win a discount would change what the judge is asked"
        )
        caching = "none"
    if caching != "none" and est.n_calls > 1:
        prefix = prefix_tokens
        est.cached_input_tokens = min(est.input_tokens, prefix * (est.n_calls - 1))
        est.assumptions.append(
            f"prompt caching {caching}: {est.cached_input_tokens:,} input tokens "
            f"assumed served from cache at {CACHE_READ_MULTIPLIER:g}x input price"
            + (
                " (per-model on this provider, so treat as an upper bound on the saving)"
                if caching == "per-model"
                else ""
            )
        )

    # Wall clock, from the rate measured for this tier. Printed before anything
    # runs, because "50% off" and "finishes on Thursday" can be incompatible.
    rate = MEASURED_CALLS_PER_MIN.get(tier, MEASURED_CALLS_PER_MIN["standard"])
    est.projected_minutes = est.n_calls / rate if rate else 0.0
    if est.projected_minutes >= 90:
        est.assumptions.append(
            f"projected wall clock {est.projected_minutes / 60:.1f} hours at the "
            f"measured {rate:g} calls/min for tier '{tier}'"
        )

    if grader.price_in_per_mtok is None or grader.price_out_per_mtok is None:
        est.priced = False
        est.usd = None
        est.assumptions.append(f"price source: {grader.price_source}")
    else:
        full_input = max(0, est.input_tokens - est.cached_input_tokens)
        est.usd = (
            full_input / 1_000_000 * grader.price_in_per_mtok
            + est.cached_input_tokens
            / 1_000_000
            * grader.price_in_per_mtok
            * CACHE_READ_MULTIPLIER
            + est.output_tokens / 1_000_000 * grader.price_out_per_mtok
        )
        est.assumptions.append(
            f"price: ${grader.price_in_per_mtok}/MTok in, "
            f"${grader.price_out_per_mtok}/MTok out ({grader.price_source})"
        )
        if grader.family == "openai" and not grader.is_mock and tier == "flex":
            est.usd *= FLEX_DISCOUNT
            est.assumptions.append(
                f"flex tier: 50% off list, at the cost of {rate:g} calls/min -- "
                f"{est.projected_minutes / 60:.1f} hours for this run"
            )
        if grader.family == "openai":
            est.assumptions.append(
                "OpenAI usage may be complimentary under a data-sharing setting, so "
                "the true cost may be lower than this -- but it is NOT assumed to be "
                "zero, and this estimate is list price"
            )
    return est


def caches_prompts(grader: Grader) -> str:
    """How this grader's provider handles prompt caching.

    Returns "automatic", "per-model" or "none". Never claims a cache *hit* --
    hits are read back from the response and reported as measured, because a
    promised cache and an observed one are different things.
    """
    if grader.is_mock:
        return "none"
    if grader.family in AUTOMATIC_CACHE_FAMILIES:
        return "automatic"
    if grader.family in PER_MODEL_CACHE_FAMILIES:
        return "per-model"
    return "none"


def cacheable_prefix_first(instructions: str, vocabulary: str, sample_text: str) -> str:
    """Order a judge prompt so the cacheable part comes first.

    Prompt caching is prefix-matched: everything before the first byte that
    varies is reusable, and everything after it is not. So the two parts that are
    identical for every sample of a task -- the grading instructions and that
    eval's own grade vocabulary -- go at the front, and the sample goes last.
    Put the sample first and the cache never hits, however much of the prompt is
    static.

    Applies only where eval-floor supplies the template. Where an eval brings its
    own grading template, the prefix is whatever that eval built, and the cache
    hit rate is reported from the response rather than designed for.
    """
    static = "\n\n".join(part for part in (instructions.strip(), vocabulary.strip()) if part)
    return f"{static}\n\n---\n\n{sample_text.strip()}"


# --------------------------------------------------------------------------
# Verdict vocabularies
#
# Instrument defect 007. Graded evals define their own grade vocabularies, and
# Inspect's generic `value_to_float()` knows only C / P / I / N. Handed anything
# else it logs "Unable to convert value to float" and returns **0.0** -- so on
# `coconot` it mapped ACCEPTABLE, UNACCEPTABLE and NEITHER all to zero, silently
# discarding every credit the judge gave. In an audit whose entire purpose is to
# find floors that are higher than they look, quietly zeroing positive verdicts
# is the worst available failure direction.
#
# The eval's own converter is not reachable from the built Task (Inspect flattens
# `epochs` to an int and drops the reducer), so the mapping cannot be read off
# the object at run time. It is therefore a judgement call, and judgement calls
# in this project live in a committed file that quotes the source line it came
# from -- the same pattern as rulings.jsonl.
#
# A verdict with no mapping is NEVER coerced to 0.0. It is recorded verbatim as
# an `unmapped_verdict`, excluded from the denominator, and reported.
# --------------------------------------------------------------------------

#: Value strings Inspect itself defines, which need no per-eval mapping.
KNOWN_VALUE_STRINGS: frozenset[str] = frozenset({"C", "P", "I", "N"})

DEFAULT_VERDICT_MAPS_PATH = pathlib.Path("verdict_maps.jsonl")


def load_verdict_maps(path: pathlib.Path | None = None) -> dict[str, dict[str, float]]:
    """Read the committed per-eval verdict vocabulary map."""
    path = path or DEFAULT_VERDICT_MAPS_PATH
    maps: dict[str, dict[str, float]] = {}
    if not path.exists():
        return maps
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        task = row.get("task")
        mapping = row.get("map")
        if not task or not isinstance(mapping, dict):
            continue
        if not row.get("source"):
            raise ValueError(
                f"{path}: verdict map for {task} has no `source`. Every mapping must "
                "quote the eval source line it was read from."
            )
        maps[task] = {str(k).strip().lower(): float(v) for k, v in mapping.items()}
    return maps


def map_verdict(
    value: Any, task_name: str, maps: dict[str, dict[str, float]]
) -> tuple[float | None, str]:
    """``(score, raw)``. ``None`` means unmapped -- never silently zero."""
    raw = "" if value is None else str(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), raw
    if raw in KNOWN_VALUE_STRINGS:
        from inspect_ai.scorer import value_to_float

        return value_to_float()(value), raw
    mapping = maps.get(task_name) or {}
    key = raw.strip().lower()
    if key in mapping:
        return mapping[key], raw
    return None, raw


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
    verdict_maps: dict[str, dict[str, float]] | None = None,
) -> ArmResult:
    """One (member, seed, arm) over capped samples, cached, refusals recorded."""
    from inspect_ai.scorer import value_to_float

    verdict_maps = verdict_maps if verdict_maps is not None else {}

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
            if cached.get("unmapped_verdict") is not None:
                verdict = str(cached["unmapped_verdict"])
                result.n_unmapped += 1
                result.unmapped_verdicts.setdefault(verdict, 0)
                result.unmapped_verdicts[verdict] += 1
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
        snapshot = _snapshot_from_score(score, grader)

        mapped, raw_verdict = map_verdict(score.value, task_name, verdict_maps)
        if mapped is None:
            # Defect 007: an eval-specific verdict with no committed mapping.
            # Recorded verbatim and excluded, never coerced to 0.0.
            result.n_unmapped += 1
            result.unmapped_verdicts.setdefault(raw_verdict, 0)
            result.unmapped_verdicts[raw_verdict] += 1
            cache.put(
                key,
                {
                    "unmapped_verdict": raw_verdict,
                    "grader_model": grader.model,
                    "grader_snapshot": snapshot,
                    "explanation": explanation[:2000],
                },
            )
            continue
        value = mapped

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
                "raw_verdict": raw_verdict,
                "grader_model": grader.model,
                "grader_snapshot": snapshot,
                "explanation": explanation[:2000],
            },
        )

    result.elapsed_s = time.monotonic() - started
    return result


@dataclass
class UsageMeter:
    """Real token usage, read back from the provider rather than assumed.

    Wraps the judge's ``generate`` so every call is counted along with the
    cached-input tokens the provider reports. That is the only honest way to say
    whether prompt caching actually happened: a provider that documents caching
    and a provider that served a cache hit are different claims.
    """

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    first_output: str = ""
    tier: str = DEFAULT_SERVICE_TIER

    def record(self, output: Any) -> None:
        self.calls += 1
        if not self.first_output:
            self.first_output = (getattr(output, "completion", "") or "")[:300]
        usage = getattr(output, "usage", None)
        if usage is None:
            return
        self.input_tokens += int(getattr(usage, "input_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "output_tokens", 0) or 0)
        # Inspect surfaces the provider's cache-read count here when it has one.
        for attr in ("input_tokens_cache_read", "cache_read_input_tokens"):
            value = getattr(usage, attr, None)
            if value:
                self.cached_input_tokens += int(value)
                break

    @property
    def cache_hit_share(self) -> float:
        """Share of input tokens served from cache. 0.0 when nothing cached."""
        if self.input_tokens <= 0:
            return 0.0
        return self.cached_input_tokens / self.input_tokens

    def cache_verdict(self, grader: Grader, prefix_tokens: int) -> str:
        """Why the cache hit rate is what it is. Never blames a provider for a
        prompt that was always too short to cache."""
        if grader.is_mock or caches_prompts(grader) == "none":
            return "not applicable: this provider does not cache at this tier"
        if grader.family == "openai" and prefix_tokens < OPENAI_CACHE_MIN_TOKENS:
            return (
                f"expected zero: the static prefix is about {prefix_tokens:,} tokens, "
                f"below OpenAI's {OPENAI_CACHE_MIN_TOKENS:,}-token minimum. Not padded "
                "to cross it -- padding a rubric with filler to win a discount would "
                "change what the judge is asked"
            )
        if self.cached_input_tokens == 0:
            return (
                "ZERO on a prompt that should cache -- investigate before a full run"
            )
        return f"{100 * self.cache_hit_share:.1f}% of input tokens served from cache"

    def should_abort(self, grader: Grader, prefix_tokens: int, first_n: int = 20) -> bool:
        """Abort a real run when a prompt that *should* cache is not caching.

        Only fires where caching was actually possible: below the provider
        minimum a zero hit rate is arithmetic, not a fault.
        """
        if grader.is_mock or caches_prompts(grader) != "automatic":
            return False
        if prefix_tokens < OPENAI_CACHE_MIN_TOKENS:
            return False
        return self.calls >= first_n and self.cached_input_tokens == 0

    def cost(self, grader: Grader) -> float | None:
        if grader.price_in_per_mtok is None or grader.price_out_per_mtok is None:
            return None
        full_in = max(0, self.input_tokens - self.cached_input_tokens)
        cached_rate = (
            grader.price_cached_in_per_mtok
            if grader.price_cached_in_per_mtok is not None
            else grader.price_in_per_mtok * CACHE_READ_MULTIPLIER
        )
        gross = (
            full_in / 1_000_000 * grader.price_in_per_mtok
            + self.cached_input_tokens / 1_000_000 * cached_rate
            + self.output_tokens / 1_000_000 * grader.price_out_per_mtok
        )
        # Flex / Batch are 50% off list on OpenAI, and this arm uses flex.
        if grader.family == "openai" and not grader.is_mock and self.tier == "flex":
            gross *= FLEX_DISCOUNT
        return gross

    def to_dict(self, grader: Grader | None = None) -> dict[str, Any]:
        out = {
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "cache_hit_share": round(self.cache_hit_share, 4),
        }
        if grader is not None:
            out["measured_usd"] = self.cost(grader)
            out["caching"] = caches_prompts(grader)
            out["service_tier"] = (
                self.tier if grader.family == "openai" and not grader.is_mock else None
            )
            out["pinned_provider"] = grader.pin_provider
            prefix = int(self.input_tokens / self.calls) if self.calls else 0
            out["mean_input_tokens_per_call"] = prefix
            out["cache_verdict"] = self.cache_verdict(grader, prefix)
        return out


@contextlib.contextmanager
def metered(model: Any, meter: UsageMeter):
    """Count real generate() calls on a Model object for the duration."""
    original = getattr(model, "generate", None)
    if original is None:
        yield
        return

    async def counting(*args: Any, **kwargs: Any) -> Any:
        output = await original(*args, **kwargs)
        try:
            meter.record(output)
        except Exception:
            meter.calls += 1
        return output

    model.generate = counting
    try:
        yield
    finally:
        model.generate = original


def judge_model(
    grader: Grader, task_name: str = "", tier: str = DEFAULT_SERVICE_TIER
) -> Any:
    """The judge as a Model object, so its calls can be counted and metered."""
    from inspect_ai.model import get_model

    if grader.model == STUB_MODEL:
        return stub_grader_model()
    args = judge_model_args(grader, task_name, tier)
    try:
        return get_model(grader.model, **args)
    except TypeError:
        # A provider that will not take one of these arguments still grades; it
        # just grades at list price, and the results file says which.
        return get_model(grader.model)


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
    meter: "UsageMeter | None" = None,
    tier: str = DEFAULT_SERVICE_TIER,
) -> tuple[TaskRun, CostEstimate]:
    """Run the battery over one model-graded task with one judge."""
    members = list(members)
    cache = cache or GradedCache.load(pathlib.Path("results/graded_cache.jsonl"))
    refusals = refusals or RefusalLog(pathlib.Path("results/refusals.jsonl"))
    verdict_maps = load_verdict_maps()

    started = time.monotonic()
    run = TaskRun(task=task_name)
    run.grader_model = grader.model
    run.grader_snapshot = grader.model
    run.capped_at = cap

    meter = meter if meter is not None else UsageMeter()
    meter.tier = tier
    with grader_active(grader):
        model = judge_model(grader, task_name, tier)
        task_args = grader_task_args(task_name, grader, model=model)
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
            samples, members, labels, grader, run.answer_template, cap,
            cached_already, tier,
        )
        if print_estimate:
            print(f"  cost estimate for {task_name} with {grader.model}:")
            print(estimate.describe())
        if budget_usd is not None:
            enforce_budget(estimate, budget_usd, grader)

        with metered(model, meter):
            for scorer, name in zip(scorers, names):
                for member in members:
                    for seed in member.seeds:
                        for arm in arms:
                            run.arms.append(
                                await run_graded_arm(
                                    task_name, scorer, name, member, seed, arm,
                                    samples, labels, grader, cache, refusals,
                                    verdict_maps,
                                )
                            )

    run.n_refusals = sum(a.n_refusals for a in run.arms)
    run.n_unmapped = sum(a.n_unmapped for a in run.arms)
    unmapped: dict[str, int] = {}
    for a in run.arms:
        for verdict, n in a.unmapped_verdicts.items():
            unmapped[verdict] = unmapped.get(verdict, 0) + n
    run.unmapped_verdicts = unmapped
    run.measured_usage = meter.to_dict(grader)
    run.grader_snapshot = meter.first_output[:0] or grader.model
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
