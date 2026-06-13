"""
Token pricing tables and cost calculation utilities.

Prices are per million tokens (MTok) in USD.

Prices are maintained as a static table. Update _PRICING when new models are
released or prices change. Previous versions attempted to scrape live pricing
from provider websites, but the HTML structure changed frequently and broke
silently — a static table is more reliable.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

VALUE_SCORE_ITERATION_PENALTY = 0.35
VALUE_SCORE_COST_PENALTY_PER_DOLLAR = 1.0
VALUE_SCORE_MAX_ITERATION_PENALTY = 2.0
VALUE_SCORE_MAX_COST_PENALTY = 2.5


@dataclass(frozen=True)
class ValueScore:
    """Cost- and iteration-adjusted score derived from judge quality."""

    quality_score: float
    value_score: float
    iteration_penalty: float
    cost_penalty: float
    iterations: int
    generation_cost: float | None
    cost_known: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "quality_score": self.quality_score,
            "value_score": self.value_score,
            "iteration_penalty": self.iteration_penalty,
            "cost_penalty": self.cost_penalty,
            "iterations": self.iterations,
            "generation_cost": self.generation_cost,
            "cost_known": self.cost_known,
        }


def _clamp_score(value: float) -> float:
    return max(0.0, min(10.0, value))


def calculate_value_score(
    quality_score: float,
    iterations: int,
    generation_cost: float | None,
    *,
    iteration_penalty: float = VALUE_SCORE_ITERATION_PENALTY,
    cost_penalty_per_dollar: float = VALUE_SCORE_COST_PENALTY_PER_DOLLAR,
    max_iteration_penalty: float = VALUE_SCORE_MAX_ITERATION_PENALTY,
    max_cost_penalty: float = VALUE_SCORE_MAX_COST_PENALTY,
) -> ValueScore:
    """Return a value-adjusted 1-10 score from quality, cost, and retries.

    The judge supplies the raw quality signal. This deterministic adjustment
    makes repeated expensive generations lose ground against similarly good,
    cheaper one-shot generations, which keeps benchmark rankings focused on
    value rather than quality alone.
    """
    normalized_quality = round(_clamp_score(float(quality_score)), 2)
    normalized_iterations = max(0, int(iterations or 0))
    extra_iterations = max(0, normalized_iterations - 1)
    iteration_penalty_value = min(
        max_iteration_penalty,
        extra_iterations * iteration_penalty,
    )

    cost_known = generation_cost is not None
    if generation_cost is None:
        cost_penalty_value = 0.0
        normalized_generation_cost = None
    else:
        normalized_generation_cost = max(0.0, float(generation_cost))
        cost_penalty_value = min(
            max_cost_penalty,
            normalized_generation_cost * cost_penalty_per_dollar,
        )

    value_score = _clamp_score(
        normalized_quality - iteration_penalty_value - cost_penalty_value
    )

    return ValueScore(
        quality_score=normalized_quality,
        value_score=round(value_score, 2),
        iteration_penalty=round(iteration_penalty_value, 2),
        cost_penalty=round(cost_penalty_value, 2),
        iterations=normalized_iterations,
        generation_cost=(
            round(normalized_generation_cost, 6)
            if normalized_generation_cost is not None
            else None
        ),
        cost_known=cost_known,
    )


class Timer:
    """Context-manager timer. Use as:  with Timer() as t: ..."""

    def __init__(self) -> None:
        self.elapsed: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = time.perf_counter() - self._start


# ---------------------------------------------------------------------------
# Pricing table — update when models are released or prices change
# ---------------------------------------------------------------------------

# format: model_short_name -> (input_price_per_mtok, output_price_per_mtok)
_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic models
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-opus-4-1": (15.00, 75.00),
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-sonnet-3-7": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-haiku-3-5": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-haiku": (0.25, 1.25),
    # OpenAI models
    "gpt-5.5": (5.00, 30.00),
    "gpt-5.5-2026-04-23": (5.00, 30.00),
    "gpt-5.4": (2.50, 15.00),
    "gpt-5.4-pro": (30.00, 180.00),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4-mini-2026-03-17": (0.75, 4.50),
    "gpt-5.4-nano": (0.20, 1.25),
    "gpt-5-codex": (1.25, 10.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    # OpenCode Go models — pricing per 1M tokens.
    # Source: OpenCode Go pricing dashboard (current as of 2026-05).
    "deepseek-v4-pro": (1.74, 3.48),
    "mimo-v2-pro": (1.00, 3.00),
    "mimo-v2-omni": (0.40, 2.00),
    "glm-5.1": (1.40, 4.40),
    "glm-5": (1.00, 3.20),
    "mimo-v2.5-pro": (1.74, 3.48),
    "kimi-k2.7-code": (0.95, 4.00),
    "kimi-k2.6": (0.95, 4.00),

    "minimax-m3": (0.60, 2.40),
    "minimax-m2.7": (0.30, 1.20),
    "minimax-m2.5": (0.30, 1.20),
    "qwen3.7-max": (2.50, 7.50),
    "qwen3.7-plus": (0.40, 1.60),
    "qwen3.6-plus": (0.50, 3.00),
    "deepseek-v4-flash": (0.14, 0.28),
    "mimo-v2.5": (0.14, 0.28),
    "gemma-4-26b-a4b": (0.0, 0.0),
    "qwen3.6-27b": (0.0, 0.0),
}

# Cache multipliers (write, read) relative to base input price per provider
_CACHE_MULTIPLIERS: dict[str, tuple[float, float]] = {
    "anthropic": (1.25, 0.10),
    "openai": (1.00, 0.10),
    # OpenCode Go publishes absolute cache-read prices per model (see
    # _CACHE_READ_PRICE_OVERRIDES). The multiplier here only applies when
    # an override is missing for a particular model.
    "opencode-go": (1.00, 0.10),
}

# Absolute cache-read price per million tokens for models whose cache-read
# pricing is not a clean multiple of the standard input price. Used by
# OpenCode Go where each model publishes its own cache-read rate.
_CACHE_READ_PRICE_OVERRIDES: dict[str, float] = {
    "deepseek-v4-pro": 0.0145,
    "mimo-v2-pro": 0.20,
    "mimo-v2-omni": 0.08,
    "glm-5.1": 0.26,
    "glm-5": 0.20,
    "mimo-v2.5-pro": 0.0145,
    "kimi-k2.7-code": 0.19,
    "kimi-k2.6": 0.16,

    "minimax-m3": 0.12,
    "minimax-m2.7": 0.06,
    "minimax-m2.5": 0.06,
    "qwen3.7-max": 0.50,
    "qwen3.7-plus": 0.04,
    "qwen3.6-plus": 0.05,
    "deepseek-v4-flash": 0.0028,
    "mimo-v2.5": 0.0028,
}

_CACHE_WRITE_PRICE_OVERRIDES: dict[str, float] = {
    "minimax-m3": 0.75,
    "minimax-m2.7": 0.375,
    "minimax-m2.5": 0.375,
    "qwen3.7-max": 3.125,
    "qwen3.7-plus": 0.50,
    "qwen3.6-plus": 0.625,
}

# model_short_name -> (input_token_threshold, input_multiplier, output_multiplier)
_LONG_CONTEXT_SURCHARGES: dict[str, tuple[int, float, float]] = {
    "gpt-5.5": (272_000, 2.0, 1.5),
    "gpt-5.5-2026-04-23": (272_000, 2.0, 1.5),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _normalize_model_name(model_id: str) -> str:
    """Strip provider prefix and normalise for lookup."""
    name = model_id.lower().strip()
    # OpenCode Go models reach this code as `openai-api/opencode-go/<name>`
    # or `anthropic/opencode-go/<name>`. Strip the routing prefix down to the
    # short alias so the static pricing table matches.
    for opencode_prefix in (
        "openai-api/opencode-go/",
        "anthropic/opencode-go/",
        "opencode-go/",
    ):
        if name.startswith(opencode_prefix):
            return name[len(opencode_prefix) :]
    for prefix in ("anthropic/", "openai/", "openai-api/"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    return name


def _detect_provider(model_id: str) -> str | None:
    """Detect provider from model ID or name."""
    name = model_id.lower().strip()
    if "opencode-go/" in name:
        return "opencode-go"
    if name.startswith("anthropic/") or "claude" in name:
        return "anthropic"
    if (
        name.startswith("openai/")
        or name.startswith("openai-api/")
        or name.startswith("gpt")
    ):
        return "openai"
    return None


def get_pricing(model_id: str) -> tuple[float, float] | None:
    """Return (input_price_per_mtok, output_price_per_mtok) or None if unknown."""
    return _PRICING.get(_normalize_model_name(model_id))


def calculate_cost(
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float | None:
    """Calculate cost in USD for a given model and token counts."""
    price = get_pricing(model_id)
    if price is None:
        return None
    input_price, output_price = price
    normalized_name = _normalize_model_name(model_id)

    surcharge = _LONG_CONTEXT_SURCHARGES.get(normalized_name)
    if surcharge is not None:
        threshold, input_multiplier, output_multiplier = surcharge
        if input_tokens > threshold:
            input_price *= input_multiplier
            output_price *= output_multiplier

    if cache_write_tokens > 0 or cache_read_tokens > 0:
        provider = _detect_provider(model_id)
        write_mult, read_mult = _CACHE_MULTIPLIERS.get(provider or "", (1.0, 1.0))
        cache_read_override = _CACHE_READ_PRICE_OVERRIDES.get(normalized_name)
        cache_write_override = _CACHE_WRITE_PRICE_OVERRIDES.get(normalized_name)
        regular_input = max(0, input_tokens - cache_write_tokens - cache_read_tokens)
        if cache_read_override is not None:
            cache_read_cost_component = cache_read_tokens * cache_read_override
        else:
            cache_read_cost_component = cache_read_tokens * input_price * read_mult

        if cache_write_override is not None:
            cache_write_cost_component = cache_write_tokens * cache_write_override
        else:
            cache_write_cost_component = cache_write_tokens * input_price * write_mult

        input_cost = (
            regular_input * input_price
            + cache_write_cost_component
            + cache_read_cost_component
        ) / 1_000_000
    else:
        input_cost = (input_tokens * input_price) / 1_000_000

    output_cost = (output_tokens * output_price) / 1_000_000
    return input_cost + output_cost


# ---------------------------------------------------------------------------
# Usage tracking
# ---------------------------------------------------------------------------


@dataclass
class UsageStats:
    """Accumulated usage statistics for a pipeline run."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cost: float | None = 0.0
    generation_cost: float | None = 0.0
    judge_cost: float | None = 0.0
    total_time_seconds: float = 0.0
    generation_time_seconds: float = 0.0
    judge_time_seconds: float = 0.0
    details: list[dict] = field(default_factory=list)

    def add(
        self,
        stage: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        elapsed: float,
        iteration: int = 0,
        cost_override: float | None = None,
        cache_write_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> None:
        """Record usage from a single API call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cache_write_tokens += cache_write_tokens
        self.total_cache_read_tokens += cache_read_tokens

        cost = (
            cost_override
            if cost_override is not None
            else calculate_cost(
                model,
                input_tokens,
                output_tokens,
                cache_write_tokens,
                cache_read_tokens,
            )
        )
        if cost is not None and self.total_cost is not None:
            self.total_cost += cost
        else:
            self.total_cost = None

        if stage == "generate":
            self.generation_time_seconds += elapsed
            if cost is not None and self.generation_cost is not None:
                self.generation_cost += cost
            else:
                self.generation_cost = None
        elif stage == "judge":
            self.judge_time_seconds += elapsed
            if cost is not None and self.judge_cost is not None:
                self.judge_cost += cost
            else:
                self.judge_cost = None

        self.total_time_seconds += elapsed

        self.details.append(
            {
                "stage": stage,
                "model": model,
                "iteration": iteration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_write_tokens": cache_write_tokens,
                "cache_read_tokens": cache_read_tokens,
                "elapsed": elapsed,
                "cost": cost,
            }
        )

    def add_time(
        self,
        stage: str,
        elapsed: float,
        iteration: int = 0,
        attempt: int | None = None,
    ) -> None:
        """Record wall-clock time for a pipeline stage (generate / judge)."""
        self.total_time_seconds += elapsed
        if stage == "generate":
            self.generation_time_seconds += elapsed
        elif stage == "judge":
            self.judge_time_seconds += elapsed

        self.details.append(
            {
                "stage": stage,
                "model": None,
                "iteration": iteration,
                "attempt": attempt,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_write_tokens": 0,
                "cache_read_tokens": 0,
                "elapsed": elapsed,
                "cost": 0.0,
                "timing_only": True,
            }
        )

    def iteration_rollups(self) -> list[dict[str, Any]]:
        """Summarize timing, cost, and token usage by benchmark iteration."""
        rollups: dict[int, dict[str, Any]] = {}

        for detail in self.details:
            iteration = int(detail.get("iteration", 0) or 0)
            if iteration not in rollups:
                rollups[iteration] = {
                    "iteration": iteration,
                    "generation_time_seconds": 0.0,
                    "judge_time_seconds": 0.0,
                    "total_time_seconds": 0.0,
                    "generation_cost": 0.0,
                    "judge_cost": 0.0,
                    "total_cost": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_write_tokens": 0,
                    "cache_read_tokens": 0,
                    "generation_input_tokens": 0,
                    "generation_output_tokens": 0,
                    "generation_cache_write_tokens": 0,
                    "generation_cache_read_tokens": 0,
                    "judge_input_tokens": 0,
                    "judge_output_tokens": 0,
                    "judge_cache_write_tokens": 0,
                    "judge_cache_read_tokens": 0,
                    "generation_attempts": 0,
                    "_models": set(),
                    "_cost_unknown": False,
                }

            rollup = rollups[iteration]
            stage = str(detail.get("stage") or "")
            elapsed = float(detail.get("elapsed") or 0.0)
            input_tokens = int(detail.get("input_tokens", 0) or 0)
            output_tokens = int(detail.get("output_tokens", 0) or 0)
            cache_write_tokens = int(detail.get("cache_write_tokens", 0) or 0)
            cache_read_tokens = int(detail.get("cache_read_tokens", 0) or 0)
            cost = detail.get("cost")
            timing_only = bool(detail.get("timing_only"))

            if stage == "generate":
                rollup["generation_time_seconds"] += elapsed
                if timing_only:
                    rollup["generation_attempts"] += 1
                else:
                    rollup["generation_input_tokens"] += input_tokens
                    rollup["generation_output_tokens"] += output_tokens
                    rollup["generation_cache_write_tokens"] += cache_write_tokens
                    rollup["generation_cache_read_tokens"] += cache_read_tokens
                    if cost is None:
                        rollup["_cost_unknown"] = True
                    else:
                        rollup["generation_cost"] += float(cost)
            elif stage == "judge":
                rollup["judge_time_seconds"] += elapsed
                rollup["judge_input_tokens"] += input_tokens
                rollup["judge_output_tokens"] += output_tokens
                rollup["judge_cache_write_tokens"] += cache_write_tokens
                rollup["judge_cache_read_tokens"] += cache_read_tokens
                if cost is None:
                    rollup["_cost_unknown"] = True
                else:
                    rollup["judge_cost"] += float(cost)

            if not timing_only:
                rollup["input_tokens"] += input_tokens
                rollup["output_tokens"] += output_tokens
                rollup["cache_write_tokens"] += cache_write_tokens
                rollup["cache_read_tokens"] += cache_read_tokens

            model = detail.get("model")
            if model:
                rollup["_models"].add(str(model))

        result: list[dict[str, Any]] = []
        for iteration, rollup in sorted(rollups.items()):
            rollup["total_time_seconds"] = (
                rollup["generation_time_seconds"] + rollup["judge_time_seconds"]
            )
            if rollup.pop("_cost_unknown"):
                rollup["total_cost"] = None
            else:
                rollup["total_cost"] = rollup["generation_cost"] + rollup["judge_cost"]
            rollup["models"] = sorted(rollup.pop("_models"))
            result.append(rollup)

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cache_write_tokens": self.total_cache_write_tokens,
            "total_cache_read_tokens": self.total_cache_read_tokens,
            "total_cost": self.total_cost,
            "generation_cost": self.generation_cost,
            "judge_cost": self.judge_cost,
            "total_time_seconds": self.total_time_seconds,
            "generation_time_seconds": self.generation_time_seconds,
            "judge_time_seconds": self.judge_time_seconds,
            "iterations": self.iteration_rollups(),
            "details": self.details,
        }
