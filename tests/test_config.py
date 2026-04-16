"""Tests for shinygen.config"""

from unittest.mock import patch

from shinygen.config import (
    FRAMEWORKS,
    MODEL_ALIASES,
    APIKeyMissingError,
    DockerNotAvailableError,
    check_api_key,
    check_docker,
    find_free_port,
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

    def test_exact_openai_codex_model_name_without_provider(self):
        agent, model_id = resolve_model("gpt-5.3-codex")
        assert agent == "codex_cli"
        assert model_id == "openai/gpt-5.3-codex"

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

    def test_r_install_command_includes_visual_qa_runtime_packages(self):
        install_command = FRAMEWORKS["shiny_r"]["install_command"]

        assert '"scales"' in install_command
        assert '"thematic"' in install_command

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


class TestPreflightChecks:
    def test_preflight_checks_docker_first(self):
        """Docker check runs before API key check."""
        with patch("shinygen.config.shutil.which", return_value=None):
            with pytest.raises(DockerNotAvailableError):
                preflight_checks("claude_code")
