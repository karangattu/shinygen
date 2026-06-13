"""Tests for shinygen.pricing."""

from shinygen.pricing import (
    Timer,
    UsageStats,
    calculate_cost,
    calculate_value_score,
    get_pricing,
)


class TestGetPricing:
    def test_known_model_returns_tuple(self):
        result = get_pricing("anthropic/claude-sonnet-4-6")
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_new_claude_opus_release_returns_expected_price(self):
        result = get_pricing("anthropic/claude-opus-4-7")
        assert result == (5.00, 25.00)

    def test_claude_opus_4_8_release_returns_expected_price(self):
        result = get_pricing("anthropic/claude-opus-4-8")
        assert result == (5.00, 25.00)

    def test_gpt55_release_returns_expected_price(self):
        assert get_pricing("openai/gpt-5.5") == (5.00, 30.00)
        assert get_pricing("openai/gpt-5.5-2026-04-23") == (5.00, 30.00)

    def test_unknown_model_returns_none(self):
        result = get_pricing("unknown/mystery-model")
        assert result is None

    def test_static_table_no_network_calls(self):
        """Pricing should work without any network access."""
        result = get_pricing("claude-opus-4-6")
        assert result is not None
        assert result == (5.00, 25.00)

    def test_lmstudio_pricing(self):
        assert get_pricing("openai/gemma-4-26b-a4b") == (0.0, 0.0)
        assert get_pricing("openai/qwen3.6-27b") == (0.0, 0.0)
        assert calculate_cost("openai/gemma-4-26b-a4b", 1_000_000, 1_000_000) == 0.0


class TestCalculateCost:
    def test_known_anthropic_model(self):
        # claude-sonnet-4-6: $3/MTok input, $15/MTok output
        cost = calculate_cost("anthropic/claude-sonnet-4-6", 1_000_000, 100_000)
        assert cost is not None
        assert cost == 3.0 + 1.5  # $3 input + $1.5 output

    def test_known_openai_model(self):
        # gpt-5.4: $2.50/MTok input, $15/MTok output
        cost = calculate_cost("openai/gpt-5.4", 500_000, 50_000)
        assert cost is not None
        assert cost == 1.25 + 0.75

    def test_known_openai_gpt55_model(self):
        # gpt-5.5: $5/MTok input, $30/MTok output
        cost = calculate_cost("openai/gpt-5.5", 200_000, 50_000)
        assert cost is not None
        assert cost == 1.00 + 1.50

    def test_gpt55_long_context_surcharge(self):
        # GPT-5.5 prompts over 272K input tokens are charged 2x input and
        # 1.5x output for the session.
        cost = calculate_cost("openai/gpt-5.5", 300_000, 10_000)
        assert cost is not None
        assert cost == 3.00 + 0.45

    def test_unknown_model_returns_none(self):
        cost = calculate_cost("unknown/mystery-model", 1000, 1000)
        assert cost is None

    def test_zero_tokens(self):
        cost = calculate_cost("anthropic/claude-sonnet-4-6", 0, 0)
        assert cost == 0.0

    def test_strips_prefix(self):
        cost_with = calculate_cost("anthropic/claude-opus-4-6", 1000, 1000)
        cost_without = calculate_cost("claude-opus-4-6", 1000, 1000)
        assert cost_with == cost_without


class TestUsageStats:
    def test_add_accumulates(self):
        usage = UsageStats()
        usage.add("judge", "anthropic/claude-sonnet-4-6", 1000, 500, 2.5, iteration=1)
        usage.add("judge", "anthropic/claude-sonnet-4-6", 2000, 300, 1.5, iteration=2)

        assert usage.total_input_tokens == 3000
        assert usage.total_output_tokens == 800
        assert usage.total_cost is not None
        assert usage.total_cost > 0
        assert usage.judge_cost is not None
        assert usage.judge_cost == usage.total_cost
        assert usage.generation_cost == 0.0
        assert usage.judge_time_seconds == 4.0
        assert len(usage.details) == 2

    def test_add_unknown_model_sets_cost_none(self):
        usage = UsageStats()
        usage.add("judge", "unknown/model", 1000, 500, 1.0)
        assert usage.total_cost is None
        assert usage.judge_cost is None

    def test_add_time_only(self):
        usage = UsageStats()
        usage.add_time("generate", 10.5, iteration=1, attempt=2)
        assert usage.generation_time_seconds == 10.5
        assert usage.total_time_seconds == 10.5
        assert usage.total_input_tokens == 0
        assert usage.generation_cost == 0.0
        assert usage.details == [
            {
                "stage": "generate",
                "model": None,
                "iteration": 1,
                "attempt": 2,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_write_tokens": 0,
                "cache_read_tokens": 0,
                "elapsed": 10.5,
                "cost": 0.0,
                "timing_only": True,
            }
        ]

    def test_to_dict_includes_iteration_rollups(self):
        usage = UsageStats()
        usage.add_time("generate", 3.0, iteration=1, attempt=1)
        usage.add(
            "generate",
            "openai/gpt-5.4-mini",
            1000,
            200,
            0.0,
            iteration=1,
            cache_read_tokens=50,
        )
        usage.add("judge", "anthropic/claude-sonnet-4-6", 500, 100, 2.0, iteration=1)

        data = usage.to_dict()

        assert data["iterations"] == [
            {
                "iteration": 1,
                "generation_time_seconds": 3.0,
                "judge_time_seconds": 2.0,
                "total_time_seconds": 5.0,
                "generation_cost": usage.details[1]["cost"],
                "judge_cost": usage.details[2]["cost"],
                "total_cost": usage.details[1]["cost"] + usage.details[2]["cost"],
                "input_tokens": 1500,
                "output_tokens": 300,
                "cache_write_tokens": 0,
                "cache_read_tokens": 50,
                "generation_input_tokens": 1000,
                "generation_output_tokens": 200,
                "generation_cache_write_tokens": 0,
                "generation_cache_read_tokens": 50,
                "judge_input_tokens": 500,
                "judge_output_tokens": 100,
                "judge_cache_write_tokens": 0,
                "judge_cache_read_tokens": 0,
                "generation_attempts": 1,
                "models": ["anthropic/claude-sonnet-4-6", "openai/gpt-5.4-mini"],
            }
        ]

    def test_generation_and_judge_costs_split(self):
        usage = UsageStats()
        usage.add("generate", "openai/gpt-5.4-mini", 5000, 2000, 5.0, iteration=1)
        usage.add("judge", "anthropic/claude-sonnet-4-6", 1000, 500, 1.0, iteration=1)

        assert usage.generation_cost is not None
        assert usage.judge_cost is not None
        assert usage.total_cost is not None
        assert usage.generation_cost > 0
        assert usage.judge_cost > 0
        assert (
            abs(usage.total_cost - (usage.generation_cost + usage.judge_cost)) < 1e-10
        )

    def test_add_uses_cost_override(self):
        usage = UsageStats()
        usage.add(
            "generate",
            "openai/gpt-5.4",
            1000,
            100,
            0.0,
            iteration=1,
            cost_override=0.1234,
        )

        assert usage.total_cost == 0.1234
        assert usage.generation_cost == 0.1234

    def test_details_recorded(self):
        usage = UsageStats()
        usage.add("judge", "anthropic/claude-sonnet-4-6", 100, 200, 0.5, iteration=1)
        assert len(usage.details) == 1
        d = usage.details[0]
        assert d["stage"] == "judge"
        assert d["iteration"] == 1
        assert d["input_tokens"] == 100
        assert d["output_tokens"] == 200
        assert d["cost"] is not None

    def test_cache_tokens_tracked(self):
        usage = UsageStats()
        usage.add(
            "generate",
            "anthropic/claude-sonnet-4-6",
            10000,
            500,
            1.0,
            iteration=1,
            cache_write_tokens=3000,
            cache_read_tokens=2000,
        )
        assert usage.total_cache_write_tokens == 3000
        assert usage.total_cache_read_tokens == 2000
        d = usage.details[0]
        assert d["cache_write_tokens"] == 3000
        assert d["cache_read_tokens"] == 2000


class TestCalculateValueScore:
    def test_value_score_penalizes_extra_iterations_and_generation_cost(self):
        baseline = calculate_value_score(
            quality_score=8.0,
            iterations=1,
            generation_cost=0.0,
        )
        expensive_retry = calculate_value_score(
            quality_score=8.0,
            iterations=3,
            generation_cost=1.25,
        )

        assert baseline.value_score == 8.0
        assert expensive_retry.iteration_penalty == 0.70
        assert expensive_retry.cost_penalty == 1.25
        assert expensive_retry.value_score == 6.05
        assert expensive_retry.value_score < baseline.value_score

    def test_unknown_generation_cost_is_reported_without_cost_penalty(self):
        result = calculate_value_score(
            quality_score=7.5,
            iterations=2,
            generation_cost=None,
        )

        assert result.cost_known is False
        assert result.cost_penalty == 0.0
        assert result.value_score == 7.15

    def test_value_score_is_clamped_to_zero_to_ten(self):
        high = calculate_value_score(
            quality_score=12.0,
            iterations=1,
            generation_cost=0.0,
        )
        low = calculate_value_score(
            quality_score=1.0,
            iterations=10,
            generation_cost=100.0,
        )

        assert high.value_score == 10.0
        assert low.value_score == 0.0


class TestCalculateCostWithCache:
    def test_anthropic_cache_discount(self):
        # claude-sonnet-4-6: $3/MTok input
        # 10000 total input, 3000 cache-write (1.25x), 2000 cache-read (0.1x)
        # regular = 10000 - 3000 - 2000 = 5000
        # input_cost = (5000*3 + 3000*3*1.25 + 2000*3*0.10) / 1e6
        cost = calculate_cost(
            "anthropic/claude-sonnet-4-6",
            10000,
            0,
            cache_write_tokens=3000,
            cache_read_tokens=2000,
        )
        assert cost is not None
        expected = (5000 * 3 + 3000 * 3 * 1.25 + 2000 * 3 * 0.10) / 1_000_000
        assert abs(cost - expected) < 1e-12

    def test_openai_cache_discount(self):
        # gpt-5.4: $2.50/MTok input
        # 10000 total, 0 write, 4000 read (0.1x)
        cost = calculate_cost(
            "openai/gpt-5.4",
            10000,
            0,
            cache_write_tokens=0,
            cache_read_tokens=4000,
        )
        assert cost is not None
        expected = (6000 * 2.50 + 4000 * 2.50 * 0.10) / 1_000_000
        assert abs(cost - expected) < 1e-12

    def test_no_cache_same_as_before(self):
        with_cache = calculate_cost("anthropic/claude-sonnet-4-6", 1000, 500)
        without = calculate_cost(
            "anthropic/claude-sonnet-4-6",
            1000,
            500,
            cache_write_tokens=0,
            cache_read_tokens=0,
        )
        assert with_cache == without


class TestOpenCodeGoPricing:
    """OpenCode Go models reach pricing as `openai-api/opencode-go/<name>`
    or `anthropic/opencode-go/<name>` after Inspect routes them. Pricing
    must resolve from any of these forms to the short alias."""

    def test_kimi_k26_known_input_output(self):
        assert get_pricing("kimi-k2.6") == (0.95, 4.00)

    def test_resolves_through_inspect_openai_api_prefix(self):
        assert get_pricing("openai-api/opencode-go/kimi-k2.6") == (0.95, 4.00)
        assert get_pricing("opencode-go/kimi-k2.6") == (0.95, 4.00)

    def test_resolves_through_inspect_anthropic_prefix(self):
        # MiniMax is routed via the Anthropic-compatible OpenCode Go endpoint.
        assert get_pricing("anthropic/opencode-go/minimax-m2.7") == (0.30, 1.20)

    def test_calculate_cost_for_kimi_k26(self):
        # 1M input + 500k output = $0.95 + $2.00 = $2.95
        cost = calculate_cost("openai-api/opencode-go/kimi-k2.6", 1_000_000, 500_000)
        assert cost is not None
        assert abs(cost - (0.95 + 2.00)) < 1e-12

    def test_calculate_cost_for_minimax_m27_anthropic_route(self):
        # 200k input + 100k output = $0.06 + $0.12 = $0.18
        cost = calculate_cost("anthropic/opencode-go/minimax-m2.7", 200_000, 100_000)
        assert cost is not None
        assert abs(cost - (0.06 + 0.12)) < 1e-12

    def test_qwen37_max_known_input_output(self):
        assert get_pricing("qwen3.7-max") == (2.50, 7.50)
        cost = calculate_cost("anthropic/opencode-go/qwen3.7-max", 1_000_000, 100_000)
        assert cost is not None
        assert abs(cost - (2.50 + 0.75)) < 1e-12

    def test_qwen37_plus_known_input_output(self):
        assert get_pricing("qwen3.7-plus") == (0.40, 1.60)
        cost = calculate_cost(
            "anthropic/opencode-go/qwen3.7-plus",
            1_000_000,
            100_000,
            cache_write_tokens=100_000,
            cache_read_tokens=200_000,
        )
        assert cost is not None
        assert abs(cost - 0.498) < 1e-12

    def test_qwen35_plus_returns_none(self):
        assert get_pricing("qwen3.5-plus") is None

    def test_cache_read_uses_per_model_override(self):
        # kimi-k2.6 cache-read price is $0.16/MTok.
        # 10k input split into 6k regular + 4k cache-read.
        cost = calculate_cost(
            "openai-api/opencode-go/kimi-k2.6",
            10_000,
            0,
            cache_write_tokens=0,
            cache_read_tokens=4_000,
        )
        assert cost is not None
        expected = (6_000 * 0.95 + 4_000 * 0.16) / 1_000_000
        assert abs(cost - expected) < 1e-12

    def test_cache_write_uses_per_model_override(self):
        # minimax-m3 cache-write price is $0.75/MTok.
        # 10k input split into 6k regular + 4k cache-write.
        cost = calculate_cost(
            "anthropic/opencode-go/minimax-m3",
            10_000,
            0,
            cache_write_tokens=4_000,
            cache_read_tokens=0,
        )
        assert cost is not None
        expected = (6_000 * 0.60 + 4_000 * 0.75) / 1_000_000
        assert abs(cost - expected) < 1e-12

    def test_all_documented_opencode_go_models_have_pricing(self):
        from shinygen.config import (
            OPENCODE_GO_ANTHROPIC_COMPATIBLE_MODELS,
            OPENCODE_GO_OPENAI_COMPATIBLE_MODELS,
        )

        # Models advertised in config that the smoke test can actually reach
        # (mimo-v2-pro / mimo-v2-omni are advertised but not in the public
        # OpenCode Go pricing table, so they are excluded here).
        priced_models = {
            "glm-5.1",
            "glm-5",

            "kimi-k2.6",
            "kimi-k2.7-code",
            "deepseek-v4-pro",
            "deepseek-v4-flash",
            "mimo-v2.5-pro",
            "mimo-v2.5",
            "qwen3.6-plus",
            "minimax-m2.5",
            "minimax-m2.7",
            "minimax-m3",
            "qwen3.7-max",
        }
        for model in OPENCODE_GO_OPENAI_COMPATIBLE_MODELS:
            if model in priced_models:
                assert get_pricing(model) is not None, model
        for model in OPENCODE_GO_ANTHROPIC_COMPATIBLE_MODELS:
            assert get_pricing(model) is not None, model


class TestTimer:
    def test_timer_measures_time(self):
        import time as _time

        with Timer() as t:
            _time.sleep(0.05)
        assert t.elapsed >= 0.04
