"""Tests for shinygen.pricing."""

from shinygen.pricing import Timer, UsageStats, calculate_cost, get_pricing


class TestGetPricing:
    def test_known_model_returns_tuple(self):
        result = get_pricing("anthropic/claude-sonnet-4-6")
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_new_claude_opus_release_returns_expected_price(self):
        result = get_pricing("anthropic/claude-opus-4-7")
        assert result == (5.00, 25.00)

    def test_unknown_model_returns_none(self):
        result = get_pricing("unknown/mystery-model")
        assert result is None

    def test_static_table_no_network_calls(self):
        """Pricing should work without any network access."""
        result = get_pricing("claude-opus-4-6")
        assert result is not None
        assert result == (5.00, 25.00)


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
        usage.add_time("generate", 10.5)
        assert usage.generation_time_seconds == 10.5
        assert usage.total_time_seconds == 10.5
        assert usage.total_input_tokens == 0
        assert usage.generation_cost == 0.0

    def test_generation_and_judge_costs_split(self):
        usage = UsageStats()
        usage.add("generate", "openai/gpt-5.4-mini", 5000, 2000, 5.0, iteration=1)
        usage.add("judge", "anthropic/claude-sonnet-4-6", 1000, 500, 1.0, iteration=1)

        assert usage.generation_cost is not None
        assert usage.judge_cost is not None
        assert usage.total_cost is not None
        assert usage.generation_cost > 0
        assert usage.judge_cost > 0
        assert abs(usage.total_cost - (usage.generation_cost + usage.judge_cost)) < 1e-10

    def test_add_uses_cost_override(self):
        usage = UsageStats()
        usage.add(
            "generate",
            "openai/gpt-5.3-codex",
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
            "generate", "anthropic/claude-sonnet-4-6",
            10000, 500, 1.0, iteration=1,
            cache_write_tokens=3000, cache_read_tokens=2000,
        )
        assert usage.total_cache_write_tokens == 3000
        assert usage.total_cache_read_tokens == 2000
        d = usage.details[0]
        assert d["cache_write_tokens"] == 3000
        assert d["cache_read_tokens"] == 2000


class TestCalculateCostWithCache:
    def test_anthropic_cache_discount(self):
        # claude-sonnet-4-6: $3/MTok input
        # 10000 total input, 3000 cache-write (1.25x), 2000 cache-read (0.1x)
        # regular = 10000 - 3000 - 2000 = 5000
        # input_cost = (5000*3 + 3000*3*1.25 + 2000*3*0.10) / 1e6
        cost = calculate_cost(
            "anthropic/claude-sonnet-4-6", 10000, 0,
            cache_write_tokens=3000, cache_read_tokens=2000,
        )
        assert cost is not None
        expected = (5000 * 3 + 3000 * 3 * 1.25 + 2000 * 3 * 0.10) / 1_000_000
        assert abs(cost - expected) < 1e-12

    def test_openai_cache_discount(self):
        # gpt-5.4: $2.50/MTok input
        # 10000 total, 0 write, 4000 read (0.5x)
        cost = calculate_cost(
            "openai/gpt-5.4", 10000, 0,
            cache_write_tokens=0, cache_read_tokens=4000,
        )
        assert cost is not None
        expected = (6000 * 2.50 + 4000 * 2.50 * 0.50) / 1_000_000
        assert abs(cost - expected) < 1e-12

    def test_no_cache_same_as_before(self):
        with_cache = calculate_cost("anthropic/claude-sonnet-4-6", 1000, 500)
        without = calculate_cost(
            "anthropic/claude-sonnet-4-6", 1000, 500,
            cache_write_tokens=0, cache_read_tokens=0,
        )
        assert with_cache == without


class TestTimer:
    def test_timer_measures_time(self):
        import time as _time

        with Timer() as t:
            _time.sleep(0.05)
        assert t.elapsed >= 0.04
