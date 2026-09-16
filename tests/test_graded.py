"""The model-graded arm. None of these calls a provider.

The graded arm is the part of this project that can spend money and can be
wrong, so its guards are tested harder than the deterministic arm's: the cost
guard, the cap, the cache, the three outcomes (graded / refused / ungradeable),
and the rule that an unmeasured task never reports a floor.
"""

from __future__ import annotations

import asyncio
import json
import math

import pytest
from inspect_ai import Task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import Score, Target, accuracy, scorer
from inspect_ai.solver import TaskState

from evalfloor.aggregate import aggregate_run, flag_rate, wilson_interval
from evalfloor.battery import BATTERY
from evalfloor.drive import drive_task_async
from evalfloor.graded import (
    GRADERS,
    BudgetExceeded,
    CostEstimate,
    GradedCache,
    Grader,
    RefusalLog,
    arms_for_template,
    choose_grader,
    choose_second_grader,
    detect_keys,
    enforce_budget,
    grade_task_async,
    grader_active,
    grader_task_args,
    looks_like_refusal,
)


def _samples(n: int = 12) -> list[Sample]:
    return [
        Sample(id=i, input=f"question {i}", target="yes" if i % 3 else "no")
        for i in range(n)
    ]


def _task_with(score_fn) -> Task:
    @scorer(metrics=[accuracy()], name="evalfloor/fake_judge")
    def fake():
        async def score(state: TaskState, target: Target) -> Score:
            return score_fn(state, target)

        return score

    return Task(dataset=MemoryDataset(_samples()), scorer=fake())


# --------------------------------------------------------------------------
# Keys and grader selection -- never leaks a value
# --------------------------------------------------------------------------


def test_detect_keys_returns_only_booleans() -> None:
    keys = detect_keys()
    assert set(keys) == {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"}
    assert all(isinstance(v, bool) for v in keys.values())


def _clear_judge_env(monkeypatch) -> None:
    for name in ("EVALFLOOR_JUDGE", "EVALFLOOR_JUDGE2", "EVALFLOOR_GRADER"):
        monkeypatch.delenv(name, raising=False)


def test_grader_selection_prefers_openai_then_openrouter_then_anthropic(monkeypatch) -> None:
    """Ebin's order: OpenAI first, OpenRouter second, Anthropic last."""
    _clear_judge_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "y")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "z")
    assert choose_grader().family == "openai"

    monkeypatch.delenv("OPENAI_API_KEY")
    assert choose_grader().family == "openrouter"

    monkeypatch.delenv("OPENROUTER_API_KEY")
    # Anthropic is not a judge for this arm at all, so with neither of the two
    # supported keys we fall to the stub rather than to Anthropic.
    assert choose_grader().is_mock is True


def test_the_default_judge_is_the_cheap_openai_model_from_the_snapshot() -> None:
    judge = GRADERS["openai"]
    assert judge.model == "openai/gpt-5.6-luna", (
        "default judge is luna on MEASURED cost: nano emits ~13x more output per "
        "grading call, which makes it ~3x dearer for this arm despite a lower "
        "input price"
    )
    assert (judge.price_in_per_mtok, judge.price_out_per_mtok) == (0.20, 1.20)
    assert "F-economy-plan" in judge.price_source, "the price must cite its source"

    fallback = GRADERS["openai_fallback"]
    assert fallback.model == "openai/gpt-5-nano"


def test_anthropic_is_last_and_is_not_the_default() -> None:
    from evalfloor.graded import DO_NOT_USE_AS_JUDGE, KEY_ENV_VARS, KEY_TO_FAMILY

    assert KEY_ENV_VARS[0] == "OPENAI_API_KEY"
    assert KEY_ENV_VARS[1] == "OPENROUTER_API_KEY"
    assert [f for _, f in KEY_TO_FAMILY] == ["openai", "openrouter"]
    assert "anthropic/claude-haiku-4-5-20251001" in DO_NOT_USE_AS_JUDGE


def test_judge_env_var_overrides_key_detection(monkeypatch) -> None:
    _clear_judge_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("EVALFLOOR_JUDGE", "openai/some-unlisted-model")
    grader = choose_grader()
    assert grader.model == "openai/some-unlisted-model"
    assert grader.price_in_per_mtok is None, "an unknown model must not get a made-up price"


def test_judge2_env_var_selects_the_second_grader(monkeypatch) -> None:
    _clear_judge_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("EVALFLOOR_JUDGE2", "openrouter/deepseek/deepseek-v4.1-flash")
    second = choose_second_grader(choose_grader())
    assert second is not None
    assert second.model == "openrouter/deepseek/deepseek-v4.1-flash"
    assert second.price_in_per_mtok == 0.15, "the documented alternative keeps its price"


def test_second_grader_comes_from_a_different_family(monkeypatch) -> None:
    _clear_judge_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("OPENROUTER_API_KEY", "y")
    first = choose_grader()
    second = choose_second_grader(first)
    assert second is not None
    assert second.family != first.family
    assert second.model == "openrouter/z-ai/glm-5.3-flash"
    assert second.pin_provider == "DeepInfra", "unpinned pays the canonical rate"


def test_no_second_grader_rather_than_reusing_the_first(monkeypatch) -> None:
    """Two runs of the same model is not a disagreement control."""
    _clear_judge_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert choose_second_grader(choose_grader()) is None


def test_grader_active_sets_and_restores_the_env(monkeypatch) -> None:
    import os

    monkeypatch.delenv("INSPECT_EVAL_MODEL", raising=False)
    with grader_active(GRADERS["openai"]):
        assert os.environ["INSPECT_EVAL_MODEL"] == "openai/gpt-5.6-luna"
    assert "INSPECT_EVAL_MODEL" not in os.environ


# --------------------------------------------------------------------------
# The cost guard runs before anything is called
# --------------------------------------------------------------------------


def test_budget_refuses_when_the_estimate_is_too_high() -> None:
    est = CostEstimate(n_calls=10_000, input_tokens=10_000_000, output_tokens=2_000_000)
    est.usd = 20.0
    with pytest.raises(BudgetExceeded, match="exceeds"):
        enforce_budget(est, budget_usd=5.0, grader=GRADERS["openai"])


def test_budget_refuses_when_the_grader_has_no_verified_price(monkeypatch) -> None:
    """A cost guard built on a guessed price is worse than no cost guard.

    Uses a model genuinely absent from the snapshot, so the refusal comes from
    the grader having no price rather than from a flag set by hand.
    """
    _clear_judge_env(monkeypatch)
    monkeypatch.setenv("EVALFLOOR_JUDGE", "openai/some-model-not-in-the-snapshot")
    unpriced = choose_grader()
    assert unpriced.price_in_per_mtok is None

    est = CostEstimate(n_calls=10, input_tokens=1000, output_tokens=200)
    est.priced = False
    est.usd = None
    with pytest.raises(BudgetExceeded, match="no verified price"):
        enforce_budget(est, budget_usd=1000.0, grader=unpriced)


# --------------------------------------------------------------------------
# Prompt caching
# --------------------------------------------------------------------------


def test_caching_support_is_declared_per_provider() -> None:
    from evalfloor.graded import caches_prompts

    assert caches_prompts(GRADERS["openai"]) == "automatic"
    assert caches_prompts(GRADERS["openrouter"]) == "per-model"
    assert caches_prompts(GRADERS["openai_fallback"]) == "automatic"
    assert caches_prompts(GRADERS["mock"]) == "none"


def test_the_cacheable_part_of_a_judge_prompt_comes_first() -> None:
    """Caching is prefix-matched: sample first means the cache never hits."""
    from evalfloor.graded import cacheable_prefix_first

    prompt = cacheable_prefix_first(
        "Grade the answer against the criterion.",
        "Reply ACCEPTABLE or UNACCEPTABLE.",
        "Question: what is the capital of France?",
    )
    static_end = prompt.index("---")
    assert prompt.index("Grade the answer") < static_end
    assert prompt.index("ACCEPTABLE") < static_end
    assert prompt.index("capital of France") > static_end


class _FakeSample:
    id = 1
    input = "a question " * 40
    target = "yes"
    choices = None

    @property
    def input_text(self) -> str:
        return self.input

    @property
    def target_text(self) -> str:
        return self.target


def test_the_estimate_promises_no_cache_saving_below_the_provider_minimum() -> None:
    """OpenAI will not cache a prefix under 1,024 tokens (plan rule R4).

    The judge prompts here are far shorter, so an estimate that banked a cache
    discount would be promising a saving it cannot get. Measured on the real
    run: 0 cached tokens across 140 calls.
    """
    from evalfloor.battery import LabelSet
    from evalfloor.graded import OPENAI_CACHE_MIN_TOKENS, TEMPLATE_TOKEN_OVERHEAD, estimate_cost

    assert TEMPLATE_TOKEN_OVERHEAD < OPENAI_CACHE_MIN_TOKENS

    samples = [_FakeSample() for _ in range(20)]
    labels = LabelSet.from_targets(["yes", "no", "no"])
    members = [m for m in BATTERY if m.name == "empty"]

    est = estimate_cost(samples, members, labels, GRADERS["openai"], "bare", cap=20)
    assert est.caching.startswith("none"), "must not bank a saving it cannot get"
    assert est.cached_input_tokens == 0
    assert any("below OpenAI" in a for a in est.assumptions)
    assert any("Not padded" in a for a in est.assumptions), (
        "the file must say it refused to pad the rubric to win the discount"
    )


def test_the_cache_guard_does_not_blame_a_prompt_that_was_too_short() -> None:
    from evalfloor.graded import OPENAI_CACHE_MIN_TOKENS, UsageMeter

    meter = UsageMeter(calls=40, input_tokens=10_000, cached_input_tokens=0)
    short = OPENAI_CACHE_MIN_TOKENS - 1
    assert meter.should_abort(GRADERS["openai"], short) is False
    assert "expected zero" in meter.cache_verdict(GRADERS["openai"], short)

    long_enough = OPENAI_CACHE_MIN_TOKENS + 1
    assert meter.should_abort(GRADERS["openai"], long_enough) is True
    assert "ZERO on a prompt that should cache" in meter.cache_verdict(
        GRADERS["openai"], long_enough
    )


def test_standard_is_the_default_tier_and_flex_is_opt_in() -> None:
    """Flex is 50% off and ~4 calls/min, which turns the 8,000-call arm into a
    ~33-hour run for about $0.60. Time is the scarcer resource this week."""
    from evalfloor.graded import DEFAULT_SERVICE_TIER, judge_model_args

    assert DEFAULT_SERVICE_TIER == "standard"

    default_args = judge_model_args(GRADERS["openai"], "inspect_evals/coconot")
    assert "service_tier" not in default_args, "standard is the API default"
    assert default_args["prompt_cache_key"].endswith("inspect_evals/coconot")

    flex_args = judge_model_args(GRADERS["openai"], "inspect_evals/coconot", "flex")
    assert flex_args["service_tier"] == "flex"


def test_the_wall_clock_projection_is_printed_before_a_run() -> None:
    from evalfloor.battery import LabelSet
    from evalfloor.graded import estimate_cost

    samples = [_FakeSample() for _ in range(100)]
    labels = LabelSet.from_targets(["yes", "no", "no"])
    members = [m for m in BATTERY if m.name == "empty"]

    fast = estimate_cost(
        samples, members, labels, GRADERS["openai"], "bare", cap=100, tier="standard"
    )
    slow = estimate_cost(
        samples, members, labels, GRADERS["openai"], "bare", cap=100, tier="flex"
    )
    assert slow.projected_minutes > fast.projected_minutes * 2, (
        "flex must be shown as materially slower, not just cheaper"
    )
    assert slow.usd is not None and fast.usd is not None
    assert slow.usd == pytest.approx(fast.usd * 0.5)
    assert "standard" in fast.describe()
    assert "projected wall clock" in fast.describe()


def test_provider_pinning_is_requested() -> None:
    from evalfloor.graded import judge_model_args

    pinned = judge_model_args(GRADERS["openrouter"], "inspect_evals/coconot")
    # Inspect's OpenRouter provider takes `provider` as a MODEL ARG and builds
    # extra_body itself; passing extra_body directly is the wrong channel.
    assert pinned["provider"]["order"] == ["DeepInfra"], "unpinned pays canonical"
    assert pinned["provider"]["allow_fallbacks"] is False
    assert "extra_body" not in pinned


def test_the_serving_provider_is_recorded_not_inferred() -> None:
    """The pin is a request; which provider served it is a fact to be read."""
    from evalfloor.graded import PROVIDER_UNREPORTED, routing_note

    ok = routing_note(GRADERS["openrouter"], "DeepInfra", 140, 140)
    assert "served by DeepInfra on 140 of 140" in ok
    assert "gap in the record" not in ok

    # A row that recorded no provider is a hole in the record. It must not read
    # as though some other provider served those calls.
    partial = routing_note(GRADERS["openrouter"], "DeepInfra", 136, 140)
    assert "served by DeepInfra on 136 of 140" in partial
    assert "the other 4 recorded no provider at all" in partial

    unknown = routing_note(GRADERS["openrouter"], PROVIDER_UNREPORTED, 138, 140)
    assert "UNREPORTED" in unknown
    assert "served by" not in unknown, "must not claim a provider it was not told"

    wrong = routing_note(GRADERS["openrouter"], "Parasail", 140, 140)
    assert "did NOT take effect" in wrong

    # A direct-API judge has no routing layer to ask about, so there is no
    # measurement to report as missing.
    assert routing_note(GRADERS["openai"], PROVIDER_UNREPORTED, 140, 140) == ""


def test_the_routing_probe_retries_before_reporting_nothing(monkeypatch) -> None:
    """The pinned pool 429s intermittently; one attempt would lose the answer."""
    import evalfloor.graded as g

    monkeypatch.setenv("OPENROUTER_API_KEY", "not-a-real-key")
    monkeypatch.setattr(g.time, "sleep", lambda _s: None)

    calls = {"n": 0}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b'{"provider": "DeepInfra"}'

    def flaky(_request, timeout=0):
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("HTTP Error 429: Too Many Requests")
        return _Response()

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", flaky)
    assert g.probe_openrouter_routing(GRADERS["openrouter"], attempts=3) == "DeepInfra"
    assert calls["n"] == 3

    calls["n"] = 0
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("429"))
    )
    assert (
        g.probe_openrouter_routing(GRADERS["openrouter"], attempts=3)
        == g.PROVIDER_UNREPORTED
    ), "an exhausted probe reports nothing rather than assuming the pin held"


def test_haiku_is_refused_as_a_judge(monkeypatch) -> None:
    from evalfloor.graded import NoGraderError

    _clear_judge_env(monkeypatch)
    monkeypatch.setenv("EVALFLOOR_JUDGE", "anthropic/claude-haiku-4-5-20251001")
    with pytest.raises(NoGraderError, match="excluded as a judge"):
        choose_grader()


def test_openai_estimate_says_the_true_cost_may_be_lower_but_not_zero() -> None:
    from evalfloor.battery import LabelSet
    from evalfloor.graded import estimate_cost

    est = estimate_cost(
        [_FakeSample()],
        [m for m in BATTERY if m.name == "empty"],
        LabelSet.from_targets(["yes", "no", "no"]),
        GRADERS["openai"],
        "bare",
        cap=1,
    )
    note = " ".join(est.assumptions)
    assert "complimentary" in note
    assert "NOT assumed to be zero" in note
    assert est.usd is not None and est.usd > 0.0


def test_budget_allows_a_run_inside_it() -> None:
    est = CostEstimate(n_calls=10, input_tokens=1000, output_tokens=200)
    est.usd = 0.01
    enforce_budget(est, budget_usd=5.0, grader=GRADERS["openai"])


def test_mock_grader_is_exempt_from_the_budget() -> None:
    est = CostEstimate(n_calls=1, input_tokens=1, output_tokens=1)
    est.priced = False
    est.usd = None
    enforce_budget(est, budget_usd=0.0, grader=GRADERS["mock"])


def test_the_raw_arm_is_not_paid_for_when_it_cannot_differ() -> None:
    assert arms_for_template("bare") == ("rendered",)
    assert set(arms_for_template("choice")) == {"raw", "rendered"}


# --------------------------------------------------------------------------
# Cap, cache, and the three outcomes
# --------------------------------------------------------------------------


def test_the_cap_is_applied_after_sorting_by_id(tmp_path) -> None:
    """Instrument defect 004 applies here too: a cap over a shuffled dataset
    would mean something different on every run."""
    from evalfloor.drive import task_samples

    task = _task_with(lambda s, t: Score(value=1.0))
    first = [s.id for s in task_samples(task, limit=5)]
    second = [s.id for s in task_samples(task, limit=5)]
    assert first == second
    assert len(first) == 5


def test_cache_makes_a_rerun_free(tmp_path) -> None:
    task = _task_with(lambda s, t: Score(value=1.0))
    cache = GradedCache.load(tmp_path / "cache.jsonl")
    refusals = RefusalLog(tmp_path / "refusals.jsonl")

    run_a, est_a = asyncio.run(
        grade_task_async(
            "evalfloor/graded_probe", GRADERS["mock"], cap=4, cache=cache,
            refusals=refusals, task=task, print_estimate=False,
        )
    )
    calls_first = est_a.n_calls
    assert calls_first > 0

    cache2 = GradedCache.load(tmp_path / "cache.jsonl")
    run_b, est_b = asyncio.run(
        grade_task_async(
            "evalfloor/graded_probe", GRADERS["mock"], cap=4, cache=cache2,
            refusals=refusals, task=task, print_estimate=False,
        )
    )
    assert est_b.n_calls == 0, "a rerun must cost nothing"
    assert cache2.hits > 0 and cache2.misses == 0


def test_an_ungradeable_response_is_not_a_zero(tmp_path) -> None:
    """Defect 006. A grader that answers without emitting a grade has not
    scored anything, and must not be counted as scoring zero."""
    task = _task_with(lambda s, t: Score(value=float("nan"), explanation="no grade found"))
    run, _ = asyncio.run(
        grade_task_async(
            "evalfloor/ungradeable_probe", GRADERS["mock"], cap=6,
            cache=GradedCache.load(tmp_path / "c.jsonl"),
            refusals=RefusalLog(tmp_path / "r.jsonl"),
            task=task, print_estimate=False,
        )
    )
    floor = aggregate_run(run)[0]
    assert floor.nothing_scored is True
    assert floor.n_ungradeable > 0
    assert floor.flagged is False
    for score in floor.members.values():
        assert score.n_scored == 0
        assert math.isfinite(score.mean)


def test_a_task_where_nothing_scored_is_not_in_the_denominator(tmp_path) -> None:
    task = _task_with(lambda s, t: Score(value=float("nan")))
    run, _ = asyncio.run(
        grade_task_async(
            "evalfloor/ungradeable_probe", GRADERS["mock"], cap=4,
            cache=GradedCache.load(tmp_path / "c.jsonl"),
            refusals=RefusalLog(tmp_path / "r.jsonl"),
            task=task, print_estimate=False,
        )
    )
    flagged, denom = flag_rate(aggregate_run(run))
    assert (flagged, denom) == (0, 0), "an unmeasured task must not inflate a denominator"


def test_a_refusal_is_recorded_verbatim_and_counted(tmp_path) -> None:
    refusal_text = "I'm sorry, but I can't help with grading that content."
    task = _task_with(lambda s, t: Score(value=0.0, explanation=refusal_text))
    path = tmp_path / "refusals.jsonl"
    run, _ = asyncio.run(
        grade_task_async(
            "evalfloor/refusal_probe", GRADERS["mock"], cap=5,
            cache=GradedCache.load(tmp_path / "c.jsonl"),
            refusals=RefusalLog(path), task=task, print_estimate=False,
        )
    )
    assert run.n_refusals > 0
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    row = rows[0]
    assert row["verbatim"] == refusal_text, "a refusal must never be reworded"
    assert len(row["prompt_sha256"]) == 64
    assert row["grader_model"] == "mockllm/model"
    assert "prompt" not in row, "the prompt itself is hashed, not stored"


def test_refusal_detection_does_not_fire_on_an_ordinary_grade() -> None:
    assert looks_like_refusal("I cannot assist with that request") is True
    assert looks_like_refusal("GRADE: C") is False
    assert looks_like_refusal("The answer matches the target.") is False


# --------------------------------------------------------------------------
# Intervals, and the stricter graded flag rule
# --------------------------------------------------------------------------


def test_graded_flag_rule_uses_the_wilson_lower_bound(tmp_path) -> None:
    """A point estimate over a capped sample would flag on noise.

    Every member scores 1.0 here and the majority baseline is 1.0 too, so the
    point estimate ties and would flag. Over a small sample the lower bound of
    the interval sits below 1.0, so the graded rule does not.
    """
    task = _task_with(lambda s, t: Score(value=1.0))
    run, _ = asyncio.run(
        grade_task_async(
            "evalfloor/interval_probe", GRADERS["mock"], cap=8,
            cache=GradedCache.load(tmp_path / "c.jsonl"),
            refusals=RefusalLog(tmp_path / "r.jsonl"),
            task=task, print_estimate=False,
        )
    )
    floor = aggregate_run(run)[0]
    assert floor.graded is True
    assert floor.majority == 1.0
    best = floor.members["empty"]
    assert best.mean == 1.0
    assert best.ci_low is not None and best.ci_low < 1.0
    assert floor.flagged is False, "the lower bound does not reach majority"


def test_the_deterministic_arm_still_uses_the_point_estimate() -> None:
    """The stricter graded rule must not leak into the free, exact arm."""
    task = _task_with(lambda s, t: Score(value=1.0))
    run = asyncio.run(drive_task_async("evalfloor/det_probe", task=task))
    floor = aggregate_run(run)[0]
    assert floor.graded is False
    assert floor.flagged is True


def test_every_graded_row_records_the_grader(tmp_path) -> None:
    task = _task_with(lambda s, t: Score(value=1.0))
    run, _ = asyncio.run(
        grade_task_async(
            "evalfloor/attrib_probe", GRADERS["mock"], cap=3,
            cache=GradedCache.load(tmp_path / "c.jsonl"),
            refusals=RefusalLog(tmp_path / "r.jsonl"),
            task=task, print_estimate=False,
        )
    )
    assert run.grader_model == "mockllm/model"
    assert run.capped_at == 3
    floor = aggregate_run(run)[0]
    assert floor.grader_model == "mockllm/model"
    payload = run.to_dict()
    assert payload["grader_model"] == "mockllm/model"
    assert payload["capped_at"] == 3


# --------------------------------------------------------------------------
# Grader injection
# --------------------------------------------------------------------------


@pytest.mark.dataset
def test_the_judge_is_injected_through_each_task_s_own_parameter() -> None:
    """Every model-graded task takes its judge as a task parameter defaulting to
    a hard-coded provider model, so INSPECT_EVAL_MODEL alone does not redirect
    it. Defect 006, first half."""
    cases = {
        "inspect_evals/coconot": "grader",
        "inspect_evals/uccb": "scorer_model",
        "inspect_evals/fortress_benign": "grader_model",
    }
    for task_name, expected_param in cases.items():
        args = grader_task_args(task_name, GRADERS["openai"])
        assert expected_param in args, f"{task_name}: {expected_param} not injected"
        value = args[expected_param]
        flat = value[0] if isinstance(value, list) else value
        assert flat == "openai/gpt-5.6-luna"


def test_a_task_with_no_grader_parameter_reports_it_rather_than_pretending() -> None:
    assert grader_task_args("evalfloor/control_loose", GRADERS["openai"]) == {}


# --------------------------------------------------------------------------
# Disagreement control
# --------------------------------------------------------------------------


def test_disagreement_counts_per_item_not_per_mean(tmp_path) -> None:
    """Two judges can agree on every mean while disagreeing on every item."""
    from evalfloor.drive import task_samples
    from evalfloor.graded import disagreement_from_cache

    grader_a = Grader("mock/a", "a", 0.0, 0.0, "test", True)
    grader_b = Grader("mock/b", "b", 0.0, 0.0, "test", True)
    cache = GradedCache.load(tmp_path / "c.jsonl")
    task = _task_with(lambda s, t: Score(value=1.0))
    samples = task_samples(task, limit=4)
    members = [m for m in BATTERY if m.name == "empty"]

    # Same mean (0.5 each), opposite on every item.
    for i, sample in enumerate(samples):
        for grader, values in ((grader_a, [1.0, 0.0]), (grader_b, [0.0, 1.0])):
            cache.put(
                GradedCache.key(
                    "t", "s", sample.id, "empty", 0, "rendered", grader.model
                ),
                {"value": values[i % 2], "grader_model": grader.model},
            )

    dis = disagreement_from_cache(
        "t", ["s"], samples, members, ["rendered"], grader_a, grader_b, cache
    )
    assert dis.n_compared == 4
    assert dis.n_disagree == 4
    assert dis.rate == 1.0
    assert dis.ci_low is not None and dis.ci_high is not None


def test_wilson_interval_is_reported_not_a_bare_rate() -> None:
    low, high = wilson_interval(3, 10)
    assert low < 0.3 < high
    assert high - low > 0.2, "a 10-sample interval must be visibly wide"
