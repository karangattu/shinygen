"""Tests for shinygen.iterate internal helpers."""

import json
from pathlib import Path

from shinygen.iterate import (
    GenerationResult,
    _extract_generation_usage_rows,
    _write_run_summary,
)


class TestExtractGenerationUsageRows:
    def test_extracts_usage(self):
        """Usage rows should be extracted from a mock log object."""

        class MockUsage:
            input_tokens = 1000
            output_tokens = 500
            input_tokens_cache_write = 200
            input_tokens_cache_read = 100
            total_cost = 0.05

        class MockStats:
            model_usage = {"anthropic/claude-sonnet-4-6": MockUsage()}

        class MockLog:
            stats = MockStats()

        rows = _extract_generation_usage_rows(MockLog())
        assert len(rows) == 1
        assert rows[0]["model"] == "anthropic/claude-sonnet-4-6"
        assert rows[0]["input_tokens"] == 1000
        assert rows[0]["output_tokens"] == 500
        assert rows[0]["cache_write_tokens"] == 200
        assert rows[0]["cache_read_tokens"] == 100
        assert rows[0]["cost_override"] == 0.05

    def test_empty_usage(self):
        class MockStats:
            model_usage = {}

        class MockLog:
            stats = MockStats()

        rows = _extract_generation_usage_rows(MockLog())
        assert rows == []

    def test_none_stats(self):
        class MockLog:
            stats = None

        rows = _extract_generation_usage_rows(MockLog())
        assert rows == []

    def test_none_cost(self):
        class MockUsage:
            input_tokens = 500
            output_tokens = 200
            input_tokens_cache_write = 0
            input_tokens_cache_read = 0
            total_cost = None

        class MockStats:
            model_usage = {"openai/gpt-5.4": MockUsage()}

        class MockLog:
            stats = MockStats()

        rows = _extract_generation_usage_rows(MockLog())
        assert len(rows) == 1
        assert rows[0]["cost_override"] is None


class TestWriteRunSummary:
    def test_persists_structured_usage_metadata(self, tmp_path):
        screenshot_path = tmp_path / "overview.png"
        screenshot_path.write_text("fake image", encoding="utf-8")

        result = GenerationResult(
            app_dir=tmp_path,
            source_code="print('hello')\n",
            score=8.7,
            iterations=2,
            passed=True,
            judge_feedback={"summary": "Strong dashboard structure."},
            screenshot_paths=[screenshot_path],
        )
        result.usage.add(
            stage="generate",
            model="openai/gpt-5.3-codex",
            input_tokens=2_000,
            output_tokens=500,
            elapsed=1.2,
            iteration=1,
        )
        result.usage.add(
            stage="judge",
            model="anthropic/claude-sonnet-4-6",
            input_tokens=600,
            output_tokens=200,
            elapsed=0.4,
            iteration=1,
        )

        summary_path = _write_run_summary(
            output_path=tmp_path,
            result=result,
            prompt="Build an Asheville Airbnb dashboard",
            requested_model="gpt-5.3-codex",
            resolved_model_id="openai/gpt-5.3-codex",
            agent="codex_cli",
            framework_key="shiny_python",
            artifact_name="app.py",
            judge_model="anthropic/claude-sonnet-4-6",
            data_file_names=["airbnb-asheville-short.csv"],
        )

        assert summary_path == tmp_path / "run_summary.json"

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["prompt"] == "Build an Asheville Airbnb dashboard"
        assert summary["model"]["requested"] == "gpt-5.3-codex"
        assert summary["model"]["resolved_id"] == "openai/gpt-5.3-codex"
        assert summary["model"]["agent"] == "codex_cli"
        assert summary["framework"] == "shiny_python"
        assert summary["artifact_name"] == "app.py"
        assert summary["judge_model"] == "anthropic/claude-sonnet-4-6"
        assert summary["passed"] is True
        assert summary["score"] == 8.7
        assert summary["iterations"] == 2
        assert summary["data_files"] == ["airbnb-asheville-short.csv"]
        assert summary["screenshots"] == ["overview.png"]
        assert summary["usage"]["generation_cost"] == result.usage.generation_cost
        assert summary["usage"]["judge_cost"] == result.usage.judge_cost
        assert summary["usage"]["total_cost"] == result.usage.total_cost
        assert summary["usage"]["total_input_tokens"] == 2_600
        assert summary["usage"]["total_output_tokens"] == 700
