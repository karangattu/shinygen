"""Tests for shinygen.config"""

import os
from unittest.mock import patch

from shinygen.config import (
    FRAMEWORKS,
    MODEL_ALIASES,
    APIKeyMissingError,
    DockerNotAvailableError,
    check_api_key,
    check_docker,
    find_free_port,
    prepare_model_environment,
    preflight_checks,
    resolve_framework,
    resolve_model,
)

import pytest


class TestResolveModel:
    def test_known_alias(self):
        agent, model_id = resolve_model("claude-sonnet")
        assert agent == "claude_code"
        assert "claude" in model_id

    def test_claude_opus_alias_resolves_to_latest_release(self):
        agent, model_id = resolve_model("claude-opus")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-opus-4-7"

    def test_known_alias_case_insensitive(self):
        agent, _ = resolve_model("Claude-Opus")
        assert agent == "claude_code"

    def test_full_anthropic_id(self):
        agent, model_id = resolve_model("anthropic/claude-sonnet-4-6")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-sonnet-4-6"

    def test_full_openai_id(self):
        agent, model_id = resolve_model("openai/gpt-5.4")
        assert agent == "codex_cli"
        assert model_id == "openai/gpt-5.4"

    def test_exact_anthropic_model_name_without_provider(self):
        agent, model_id = resolve_model("claude-sonnet-4-5")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-sonnet-4-5"

    def test_exact_anthropic_opus_model_name_without_provider(self):
        agent, model_id = resolve_model("claude-opus-4-7")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-opus-4-7"

    def test_exact_openai_mini_model_name_without_provider(self):
        agent, model_id = resolve_model("gpt-5.4-mini")
        assert agent == "codex_cli"
        assert model_id == "openai/gpt-5.4-mini-2026-03-17"

    def test_exact_openai_nano_model_name_without_provider(self):
        agent, model_id = resolve_model("gpt-5.4-nano")
        assert agent == "codex_cli"
        assert model_id == "openai/gpt-5.4-nano"

    @pytest.mark.parametrize(
        ("alias", "expected_model_id"),
        [
            ("gpt55", "openai/gpt-5.5"),
            ("gpt-5.5", "openai/gpt-5.5"),
            ("gpt-5.5-2026-04-23", "openai/gpt-5.5-2026-04-23"),
        ],
    )
    def test_openai_gpt55_aliases_resolve_to_codex_cli(self, alias, expected_model_id):
        agent, model_id = resolve_model(alias)
        assert agent == "codex_cli"
        assert model_id == expected_model_id

    def test_exact_openai_codex_model_name_without_provider(self):
        agent, model_id = resolve_model("gpt-5.3-codex")
        assert agent == "codex_cli"
        assert model_id == "openai/gpt-5.3-codex"

    def test_opencode_go_alias_resolves_to_mini_swe_agent(self):
        agent, model_id = resolve_model("opencode-go/kimi-k2.6")
        assert agent == "mini_swe_agent"
        assert model_id == "openai-api/opencode-go/kimi-k2.6"

    def test_opencode_go_short_alias_resolves_to_openai_api_provider(self):
        agent, model_id = resolve_model("deepseek-v4-flash")
        assert agent == "mini_swe_agent"
        assert model_id == "openai-api/opencode-go/deepseek-v4-flash"

    def test_full_openai_api_id_uses_mini_swe_agent(self):
        agent, model_id = resolve_model("openai-api/opencode-go/qwen3.6-plus")
        assert agent == "mini_swe_agent"
        assert model_id == "openai-api/opencode-go/qwen3.6-plus"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            resolve_model("nonexistent-model")


class TestResolveFramework:
    def test_canonical(self):
        assert resolve_framework("shiny_python") == "shiny_python"

    def test_alias_dash(self):
        assert resolve_framework("shiny-python") == "shiny_python"

    def test_short_alias(self):
        assert resolve_framework("python") == "shiny_python"
        assert resolve_framework("r") == "shiny_r"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown framework"):
            resolve_framework("flask")


class TestFrameworks:
    def test_python_config(self):
        fw = FRAMEWORKS["shiny_python"]
        assert fw["primary_artifact"] == "app.py"
        assert fw["language"] == "Python"

    def test_r_config(self):
        fw = FRAMEWORKS["shiny_r"]
        assert fw["primary_artifact"] == "app.R"
        assert fw["language"] == "R"

    def test_r_system_prompt_lists_visual_qa_runtime_packages_as_preinstalled(self):
        from shinygen.prompts import build_system_prompt

        prompt = build_system_prompt("shiny_r")
        assert "scales" in prompt
        assert "thematic" in prompt

    def test_all_frameworks_have_required_keys(self):
        required = {
            "label",
            "language",
            "primary_artifact",
            "run_command",
            "install_command",
            "skill_dir",
        }
        for key, fw in FRAMEWORKS.items():
            missing = required - set(fw.keys())
            assert not missing, f"Framework {key} missing keys: {missing}"


class TestPortUtilities:
    def test_find_free_port_returns_bindable_port(self):
        import socket

        port = find_free_port()
        assert isinstance(port, int)
        assert port > 0

        # The selected port should be immediately bindable by caller.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", port))


class TestCheckDocker:
    def test_docker_not_installed(self):
        with patch("shinygen.config.shutil.which", return_value=None):
            with pytest.raises(DockerNotAvailableError, match="not installed"):
                check_docker()

    def test_docker_not_running(self):
        import subprocess

        with patch("shinygen.config.shutil.which", return_value="/usr/local/bin/docker"):
            with patch(
                "shinygen.config.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "docker info"),
            ):
                with pytest.raises(DockerNotAvailableError, match="not running"):
                    check_docker()

    def test_docker_timeout(self):
        import subprocess

        with patch("shinygen.config.shutil.which", return_value="/usr/local/bin/docker"):
            with patch(
                "shinygen.config.subprocess.run",
                side_effect=subprocess.TimeoutExpired("docker info", 15),
            ):
                with pytest.raises(DockerNotAvailableError, match="not running"):
                    check_docker()


class TestCheckAPIKey:
    def test_anthropic_key_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(APIKeyMissingError, match="ANTHROPIC_API_KEY"):
                check_api_key("claude_code")

    def test_anthropic_key_present(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
            check_api_key("claude_code")  # should not raise

    def test_openai_key_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(APIKeyMissingError, match="OPENAI_API_KEY"):
                check_api_key("codex_cli")

    def test_openai_key_present(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            check_api_key("codex_cli")  # should not raise

    def test_opencode_go_key_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(APIKeyMissingError, match="OPENCODE_GO_API_KEY"):
                check_api_key("mini_swe_agent", "openai-api/opencode-go/kimi-k2.6")

    def test_opencode_go_key_present(self):
        with patch.dict("os.environ", {"OPENCODE_GO_API_KEY": "sk-test"}, clear=True):
            check_api_key("mini_swe_agent", "openai-api/opencode-go/kimi-k2.6")

    def test_prepare_model_environment_sets_opencode_go_base_url(self):
        with patch.dict("os.environ", {"OPENCODE_GO_API_KEY": "sk-test"}, clear=True):
            prepare_model_environment("openai-api/opencode-go/kimi-k2.6")
            assert os.environ["OPENCODE_GO_BASE_URL"] == "https://opencode.ai/zen/go/v1"


class TestPreflightChecks:
    def test_preflight_checks_docker_first(self):
        """Docker check runs before API key check."""
        with patch("shinygen.config.shutil.which", return_value=None):
            with pytest.raises(DockerNotAvailableError):
                preflight_checks("claude_code")
