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
    "gpt-5.4": (2.50, 15.00),
    "gpt-5.4-pro": (30.00, 180.00),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4-mini-2026-03-17": (0.75, 4.50),
    "gpt-5.4-nano": (0.20, 1.25),
    "gpt-5.3-codex": (1.75, 14.00),
    "gpt-5-codex": (1.25, 10.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}

# Cache multipliers (write, read) relative to base input price per provider
_CACHE_MULTIPLIERS: dict[str, tuple[float, float]] = {
    "anthropic": (1.25, 0.10),
    "openai": (1.00, 0.50),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _normalize_model_name(model_id: str) -> str:
    """Strip provider prefix and normalise for lookup."""
    name = model_id.lower().strip()
    for prefix in ("anthropic/", "openai/"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name


def _detect_provider(model_id: str) -> str | None:
    """Detect provider from model ID or name."""
    name = model_id.lower().strip()
    if name.startswith("anthropic/") or "claude" in name:
        return "anthropic"
    if name.startswith("openai/") or name.startswith("gpt"):
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

    if cache_write_tokens > 0 or cache_read_tokens > 0:
        provider = _detect_provider(model_id)
        write_mult, read_mult = _CACHE_MULTIPLIERS.get(provider or "", (1.0, 1.0))
        regular_input = max(0, input_tokens - cache_write_tokens - cache_read_tokens)
        input_cost = (
            regular_input * input_price
            + cache_write_tokens * input_price * write_mult
            + cache_read_tokens * input_price * read_mult
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
                model, input_tokens, output_tokens,
                cache_write_tokens, cache_read_tokens,
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

    def add_time(self, stage: str, elapsed: float) -> None:
        """Record wall-clock time for a pipeline stage (generate / judge)."""
        self.total_time_seconds += elapsed
        if stage == "generate":
            self.generation_time_seconds += elapsed
        elif stage == "judge":
            self.judge_time_seconds += elapsed

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
            "details": self.details,
        }
