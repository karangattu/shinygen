"""Tests for shinygen.iterate internal helpers."""

import base64
import json
import zipfile
from pathlib import Path

import pytest

from shinygen.iterate import (
    GenerationResult,
    _copy_agent_screenshot_artifact,
    _copy_output_screenshots,
    _extract_generation_usage_rows,
    _generation_extra_config,
    _recover_code_from_eval_logs,
    _resolve_judge_screenshot_paths,
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


class TestGenerationExtraConfig:
    def test_claude_generation_uses_medium_reasoning_effort(self):
        assert _generation_extra_config("claude_code") == {"reasoning_effort": "medium"}

    def test_codex_generation_uses_default_config(self):
        assert _generation_extra_config("codex_cli") == {}


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
            judge_models=["anthropic/claude-sonnet-4-6"],
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
        assert summary["judge_models"] == ["anthropic/claude-sonnet-4-6"]
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


class TestCopyAgentScreenshotArtifact:
    def test_prefers_full_page_screenshot_from_results_volume(self, tmp_path):
        results_dir = tmp_path / "results" / "sample"
        results_dir.mkdir(parents=True)
        (results_dir / "screenshot_bottom_final.png").write_bytes(b"crop")
        (results_dir / "screenshot.png").write_bytes(b"full-page")

        output_path = tmp_path / "output"
        output_path.mkdir()

        copied = _copy_agent_screenshot_artifact(
            output_path,
            results_dir=tmp_path / "results",
            log_path=None,
        )

        assert copied == output_path / "agent_last_screenshot.png"
        assert copied.read_bytes() == b"full-page"

    def test_accepts_legacy_agent_last_from_results_volume(self, tmp_path):
        results_dir = tmp_path / "results" / "sample"
        results_dir.mkdir(parents=True)
        (results_dir / "agent_last_screenshot.png").write_bytes(b"legacy-agent")

        output_path = tmp_path / "output"
        output_path.mkdir()

        copied = _copy_agent_screenshot_artifact(
            output_path,
            results_dir=tmp_path / "results",
            log_path=None,
        )

        assert copied == output_path / "agent_last_screenshot.png"
        assert copied.read_bytes() == b"legacy-agent"

    def test_falls_back_to_last_eval_log_image_attachment(self, tmp_path):
        log_path = tmp_path / "sample.eval"
        output_path = tmp_path / "output"
        output_path.mkdir()
        last_image = b"last-image"

        sample = {
            "id": "shinygen/generate",
            "attachments": {
                "first": "data:image/png;base64,"
                + base64.b64encode(b"first-image").decode("ascii"),
                "last": "data:image/png;base64,"
                + base64.b64encode(last_image).decode("ascii"),
            },
            "messages": [
                {
                    "content": [
                        {
                            "type": "image",
                            "image": "attachment://first",
                            "detail": "auto",
                        }
                    ]
                },
                {
                    "content": [
                        {
                            "type": "image",
                            "image": "attachment://last",
                            "detail": "auto",
                        }
                    ]
                },
            ],
            "metadata": {},
        }

        with zipfile.ZipFile(log_path, "w") as archive:
            archive.writestr(
                "samples/shinygen/generate_epoch_1.json", json.dumps(sample)
            )

        copied = _copy_agent_screenshot_artifact(
            output_path,
            results_dir=tmp_path / "missing-results",
            log_path=log_path,
        )

        assert copied == output_path / "agent_last_screenshot.png"
        assert copied.read_bytes() == last_image


class TestRecoverCodeFromEvalLogs:
    def test_recovers_code_from_latest_eval_log(self, tmp_path):
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        sample = {
            "id": "shinygen/generate",
            "metadata": {
                "framework": "shiny_r",
                "primary_artifact": "app.R",
            },
            "messages": [
                {
                    "role": "assistant",
                    "content": [],
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "function": "exec_command",
                            "arguments": {
                                "cmd": (
                                    "cat > /home/user/project/app.R <<'EOF'\n"
                                    "library(shiny)\n"
                                    "library(bslib)\n\n"
                                    "ui <- page_sidebar(sidebar = sidebar(), textOutput('result'))\n\n"
                                    "server <- function(input, output, session) {\n"
                                    "  output$result <- renderText('ok')\n"
                                    "}\n\n"
                                    "shinyApp(ui, server)\n"
                                    "EOF\n"
                                    "Rscript -e \"parse('app.R')\""
                                )
                            },
                        }
                    ],
                }
            ],
        }

        eval_path = logs_dir / "sample.eval"
        with zipfile.ZipFile(eval_path, "w") as archive:
            archive.writestr(
                "samples/shinygen/generate_epoch_1.json",
                json.dumps(sample),
            )

        code, recovered_log_path = _recover_code_from_eval_logs(logs_dir, "app.R")

        assert recovered_log_path == eval_path
        assert code is not None
        assert code.startswith("library(shiny)")
        assert "shinyApp(ui, server)" in code

    def test_returns_none_when_no_eval_log_exists(self, tmp_path):
        code, recovered_log_path = _recover_code_from_eval_logs(
            tmp_path / "missing-logs",
            "app.R",
        )

        assert code is None
        assert recovered_log_path is None


class TestResolveJudgeScreenshotPaths:
    def test_strict_mode_uses_legacy_agent_screenshot_from_output_dir(
        self,
        tmp_path,
        monkeypatch,
    ):
        output_path = tmp_path / "output"
        output_path.mkdir()
        agent_screenshot = output_path / "agent_last_screenshot.png"
        agent_screenshot.write_bytes(b"agent")

        monkeypatch.setenv("SHINYGEN_STRICT_SANDBOX_SCREENSHOT", "1")

        screenshot_paths = _resolve_judge_screenshot_paths(
            output_path,
            tmp_path / "eval",
            "shiny_python",
            18801,
        )

        assert screenshot_paths == [agent_screenshot]

    def test_augments_legacy_agent_screenshot_with_host_multitab_capture(
        self,
        tmp_path,
        monkeypatch,
    ):
        output_path = tmp_path / "output"
        output_path.mkdir()
        agent_screenshot = output_path / "agent_last_screenshot.png"
        agent_screenshot.write_bytes(b"legacy")

        eval_dir = tmp_path / "eval"
        eval_dir.mkdir()
        landing = eval_dir / "screenshot_01_landing.png"
        details = eval_dir / "screenshot_02_details.png"
        landing.write_bytes(b"host-landing")
        details.write_bytes(b"host-details")

        monkeypatch.delenv("SHINYGEN_STRICT_SANDBOX_SCREENSHOT", raising=False)

        def fake_take_screenshots(app_dir, framework_key, port):
            assert app_dir == eval_dir
            assert framework_key == "shiny_python"
            assert port == 18801
            return [landing, details]

        monkeypatch.setattr(
            "shinygen.screenshot.take_screenshots", fake_take_screenshots
        )

        screenshot_paths = _resolve_judge_screenshot_paths(
            output_path,
            eval_dir,
            "shiny_python",
            18801,
        )

        copied_landing = output_path / "screenshot_01_landing.png"
        copied_details = output_path / "screenshot_02_details.png"
        assert screenshot_paths == [copied_landing, copied_details]
        assert copied_landing.read_bytes() == b"host-landing"
        assert copied_details.read_bytes() == b"host-details"
        assert agent_screenshot.read_bytes() == b"host-landing"

    def test_falls_back_to_host_side_capture_when_sandbox_missing(
        self,
        tmp_path,
        monkeypatch,
    ):
        output_path = tmp_path / "output"
        output_path.mkdir()
        eval_dir = tmp_path / "eval"
        eval_dir.mkdir()
        host_screenshot = eval_dir / "screenshot.png"
        host_screenshot.write_bytes(b"host")

        monkeypatch.delenv("SHINYGEN_STRICT_SANDBOX_SCREENSHOT", raising=False)

        def fake_take_screenshots(app_dir, framework_key, port):
            assert app_dir == eval_dir
            assert framework_key == "shiny_r"
            assert port == 18888
            return host_screenshot

        monkeypatch.setattr(
            "shinygen.screenshot.take_screenshots", fake_take_screenshots
        )

        screenshot_paths = _resolve_judge_screenshot_paths(
            output_path,
            eval_dir,
            "shiny_r",
            18888,
        )

        # New behavior: host-side fallback preserves the original filename
        # (so multi-tab series like ``screenshot_02_<slug>.png`` survive)
        # and additionally writes a legacy ``agent_last_screenshot.png``
        # alias pointing at the landing image.
        copied = output_path / "screenshot.png"
        legacy_alias = output_path / "agent_last_screenshot.png"
        assert screenshot_paths == [copied]
        assert copied.read_bytes() == b"host"
        assert legacy_alias.exists()
        assert legacy_alias.read_bytes() == b"host"

    def test_raises_in_strict_mode_when_sandbox_missing(
        self,
        tmp_path,
        monkeypatch,
    ):
        output_path = tmp_path / "output"
        output_path.mkdir()
        eval_dir = tmp_path / "eval"
        eval_dir.mkdir()
        host_screenshot = eval_dir / "screenshot.png"
        host_screenshot.write_bytes(b"host")

        monkeypatch.setenv("SHINYGEN_STRICT_SANDBOX_SCREENSHOT", "1")

        def fake_take_screenshots(app_dir, framework_key, port):
            return host_screenshot

        monkeypatch.setattr(
            "shinygen.screenshot.take_screenshots", fake_take_screenshots
        )

        with pytest.raises(RuntimeError, match="Missing sandbox screenshot"):
            _resolve_judge_screenshot_paths(
                output_path,
                eval_dir,
                "shiny_r",
                18888,
            )

    def test_raises_when_sandbox_missing_and_host_fallback_fails(
        self,
        tmp_path,
        monkeypatch,
    ):
        output_path = tmp_path / "output"
        output_path.mkdir()
        eval_dir = tmp_path / "eval"
        eval_dir.mkdir()

        monkeypatch.delenv("SHINYGEN_STRICT_SANDBOX_SCREENSHOT", raising=False)

        def fake_take_screenshots(app_dir, framework_key, port):
            return None

        monkeypatch.setattr(
            "shinygen.screenshot.take_screenshots", fake_take_screenshots
        )

        with pytest.raises(RuntimeError, match="Host-side fallback also failed"):
            _resolve_judge_screenshot_paths(
                output_path,
                eval_dir,
                "shiny_r",
                18888,
            )


class TestCopyOutputScreenshots:
    def test_keeps_output_resident_screenshot_without_recopied_same_file(
        self, tmp_path
    ):
        output_path = tmp_path / "output"
        output_path.mkdir()
        screenshot_path = output_path / "agent_last_screenshot.png"
        screenshot_path.write_bytes(b"agent")

        copied = _copy_output_screenshots(output_path, [screenshot_path])

        assert copied == [screenshot_path]
        assert screenshot_path.read_bytes() == b"agent"
