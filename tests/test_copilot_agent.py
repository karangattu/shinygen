"""Tests for shinygen.copilot_agent"""

from pathlib import Path

import pytest

from shinygen.copilot_agent import _resolve_copilot_model


class TestResolveCopilotModel:
    def test_strips_anthropic_prefix(self):
        assert _resolve_copilot_model("anthropic/claude-opus-4-6") == "claude-opus-4-6"

    def test_strips_openai_prefix(self):
        assert _resolve_copilot_model("openai/gpt-5.4") == "gpt-5.4"

    def test_passthrough_bare_model_name(self):
        assert _resolve_copilot_model("gpt-5") == "gpt-5"

    def test_strips_only_first_slash(self):
        assert _resolve_copilot_model("openai/gpt-5.4-mini-2026-03-17") == "gpt-5.4-mini-2026-03-17"


class TestRunCopilotGeneration:
    def test_writes_data_files_to_work_dir(self, tmp_path, monkeypatch):
        """Verify data files are staged before the session runs."""
        import shinygen.copilot_agent as mod

        captured_work_dir = {}

        # Mock the async session to capture the work dir and write a fake artifact
        async def fake_session(*args, **kwargs):
            from shinygen.copilot_agent import CopilotGenerationResult

            work_dir = kwargs.get("work_dir") or args[3]
            captured_work_dir["path"] = work_dir
            # Write a fake app.py as the agent would
            (work_dir / "app.py").write_text("from shiny import App\napp = App()")
            return CopilotGenerationResult(code="from shiny import App\napp = App()")

        monkeypatch.setattr(mod, "_run_copilot_session", fake_session)

        code, usage_rows = mod.run_copilot_generation(
            prompt="Build a dashboard",
            model_id="anthropic/claude-sonnet-4-6",
            framework_key="shiny_python",
            data_files={"data.csv": "a,b\n1,2\n"},
        )

        assert code is not None
        assert "App" in code
        # Verify data file was written
        assert (captured_work_dir["path"] / "data.csv").exists()

    def test_returns_none_on_missing_artifact(self, tmp_path, monkeypatch):
        """If the agent doesn't create the artifact, returns None."""
        import shinygen.copilot_agent as mod

        async def fake_session(*args, **kwargs):
            from shinygen.copilot_agent import CopilotGenerationResult

            return CopilotGenerationResult(
                error="artifact not found"
            )

        monkeypatch.setattr(mod, "_run_copilot_session", fake_session)

        code, usage_rows = mod.run_copilot_generation(
            prompt="Build a dashboard",
            model_id="openai/gpt-5.4",
            framework_key="shiny_python",
        )

        assert code is None
        assert usage_rows == []
