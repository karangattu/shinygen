"""Tests for shinygen.config"""

import os
from unittest.mock import patch

import pytest

from shinygen.config import (
    FRAMEWORKS,
    APIKeyMissingError,
    DockerNotAvailableError,
    check_api_key,
    check_docker,
    find_free_port,
    is_opencode_go_anthropic_model,
    opencode_go_anthropic_model_name,
    preflight_checks,
    prepare_model_environment,
    resolve_framework,
    resolve_model,
)


class TestResolveModel:
    def test_known_alias(self):
        agent, model_id = resolve_model("claude-sonnet")
        assert agent == "claude_code"
        assert "claude" in model_id

    def test_claude_opus_alias_resolves_to_latest_release(self):
        agent, model_id = resolve_model("claude-opus")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-opus-4-8"

    def test_known_alias_case_insensitive(self):
        agent, _ = resolve_model("Claude-Opus")
        assert agent == "claude_code"

    def test_full_anthropic_id(self):
        agent, model_id = resolve_model("anthropic/claude-sonnet-5")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-sonnet-5"

    def test_full_openai_id(self):
        agent, model_id = resolve_model("openai/gpt-5.6-luna")
        assert agent == "codex_cli"
        assert model_id == "openai/gpt-5.6-luna"

    def test_exact_anthropic_model_name_without_provider(self):
        agent, model_id = resolve_model("claude-sonnet-5")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-sonnet-5"

    def test_exact_anthropic_opus_model_name_without_provider(self):
        agent, model_id = resolve_model("claude-opus-4-8")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-opus-4-8"

    def test_exact_anthropic_opus_4_8_model_name_without_provider(self):
        agent, model_id = resolve_model("claude-opus-4-8")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-opus-4-8"

    @pytest.mark.parametrize(
        ("alias", "expected_model_id"),
        [
            ("sol", "openai/gpt-5.6-sol"),
            ("gpt56-sol", "openai/gpt-5.6-sol"),
            ("terra", "openai/gpt-5.6-terra"),
            ("gpt56-terra", "openai/gpt-5.6-terra"),
            ("luna", "openai/gpt-5.6-luna"),
            ("gpt56-luna", "openai/gpt-5.6-luna"),
        ],
    )
    def test_gpt56_aliases_resolve_to_codex_cli(self, alias, expected_model_id):
        agent, model_id = resolve_model(alias)
        assert agent == "codex_cli"
        assert model_id == expected_model_id

    def test_opencode_go_alias_resolves_to_opencode(self):
        agent, model_id = resolve_model("opencode-go/kimi-k3")
        assert agent == "opencode"
        assert model_id == "openai-api/opencode-go/kimi-k3"

    def test_opencode_go_short_alias_resolves_to_openai_api_provider(self):
        agent, model_id = resolve_model("deepseek-v4-flash")
        assert agent == "opencode"
        assert model_id == "openai-api/opencode-go/deepseek-v4-flash"

    def test_opencode_go_minimax_alias_resolves_to_anthropic_provider_marker(self):
        agent, model_id = resolve_model("minimax-m2.7")
        assert agent == "opencode"
        assert model_id == "anthropic/opencode-go/minimax-m2.7"
        assert is_opencode_go_anthropic_model(model_id)
        assert opencode_go_anthropic_model_name(model_id) == "minimax-m2.7"

    def test_opencode_go_qwen37_max_alias_resolves_to_anthropic_provider_marker(self):
        agent, model_id = resolve_model("qwen3.7-max")
        assert agent == "opencode"
        assert model_id == "anthropic/opencode-go/qwen3.7-max"
        assert is_opencode_go_anthropic_model(model_id)
        assert opencode_go_anthropic_model_name(model_id) == "qwen3.7-max"

    @pytest.mark.parametrize(
        "alias",
        [
            "glm-5.3",
            "glm-5.3-flash",
            "glm-5.2",
            "kimi-k3",
            "kimi-k2.7-code",
            "kimi-k2.6",
            "mimo-v2.5",
            "mimo-v2.5-pro",
            "minimax-m3",
            "minimax-m2.7",
            "qwen3.8-max",
            "qwen3.8-flash",
            "qwen3.7-max",
            "qwen3.7-plus",
            "deepseek-v4-pro",
            "deepseek-v4-flash",
            "grok-4.6",
        ],
    )
    def test_all_documented_opencode_go_aliases_resolve(self, alias):
        agent, model_id = resolve_model(alias)
        assert agent == "opencode"
        assert model_id.endswith(alias)

    def test_full_openai_api_id_uses_opencode(self):
        agent, model_id = resolve_model("openai-api/opencode-go/qwen3.7-max")
        assert agent == "opencode"
        assert model_id == "openai-api/opencode-go/qwen3.7-max"

    @pytest.mark.parametrize(
        ("alias", "expected_model_id"),
        [
            ("gemini-3.7", "google/gemini-3.7"),
            ("gemini-3.7-pro", "google/gemini-3.7-pro"),
            ("gemini-3.7-flash", "google/gemini-3.7-flash"),
        ],
    )
    def test_gemini_aliases_resolve_to_gemini_cli(self, alias, expected_model_id):
        agent, model_id = resolve_model(alias)
        assert agent == "gemini_cli"
        assert model_id == expected_model_id

    def test_full_google_id_uses_gemini_cli(self):
        agent, model_id = resolve_model("google/gemini-3.7-flash")
        assert agent == "gemini_cli"
        assert model_id == "google/gemini-3.7-flash"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            resolve_model("nonexistent-model")

    def test_lmstudio_model_resolution(self):
        from shinygen.config import is_lmstudio_model

        agent, model_id = resolve_model("gemma-4-26b-a4b")
        assert agent == "opencode"
        assert model_id == "openai/google/gemma-4-26b-a4b-qat"
        assert is_lmstudio_model(model_id)

        agent2, model_id2 = resolve_model("qwen3.6-27b")
        assert agent2 == "opencode"
        assert model_id2 == "openai/qwen/qwen3.6-27b"
        assert is_lmstudio_model(model_id2)

        assert not is_lmstudio_model("openai/gpt-5.6-luna")

    def test_any_explicit_lmstudio_model_uses_opencode(self):
        from shinygen.config import is_lmstudio_model

        agent, model_id = resolve_model("lmstudio/qwen3.5-9b")
        assert agent == "opencode"
        assert model_id == "lmstudio/qwen3.5-9b"
        assert is_lmstudio_model(model_id)


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

        with patch(
            "shinygen.config.shutil.which", return_value="/usr/local/bin/docker"
        ):
            with patch(
                "shinygen.config.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "docker info"),
            ):
                with pytest.raises(DockerNotAvailableError, match="not running"):
                    check_docker()

    def test_docker_timeout(self):
        import subprocess

        with patch(
            "shinygen.config.shutil.which", return_value="/usr/local/bin/docker"
        ):
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

    def test_gemini_key_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(APIKeyMissingError, match="GEMINI_API_KEY"):
                check_api_key("gemini_cli")

    def test_gemini_key_present(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}, clear=True):
            check_api_key("gemini_cli")
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}, clear=True):
            check_api_key("gemini_cli")

    def test_opencode_go_key_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(APIKeyMissingError, match="OPENCODE_GO_API_KEY"):
                check_api_key("opencode", "openai-api/opencode-go/kimi-k2.6")

    def test_opencode_go_key_present(self):
        with patch.dict("os.environ", {"OPENCODE_GO_API_KEY": "sk-test"}, clear=True):
            check_api_key("opencode", "openai-api/opencode-go/kimi-k2.6")

    def test_prepare_model_environment_sets_opencode_go_base_url(self):
        with patch.dict("os.environ", {"OPENCODE_GO_API_KEY": "sk-test"}, clear=True):
            prepare_model_environment("openai-api/opencode-go/kimi-k2.6")
            assert os.environ["OPENCODE_GO_BASE_URL"] == "https://opencode.ai/zen/go/v1"

    def test_lmstudio_key_not_required(self):
        with patch.dict("os.environ", {}, clear=True):
            check_api_key("opencode", "openai/google/gemma-4-26b-a4b-qat")
            check_api_key("opencode", "openai/qwen/qwen3.6-27b")

    def test_opencode_openai_model_requires_openai_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(APIKeyMissingError, match="OPENAI_API_KEY"):
                check_api_key("opencode", "openai/gpt-5.6-luna")

    def test_opencode_google_model_requires_gemini_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(APIKeyMissingError, match="GEMINI_API_KEY"):
                check_api_key("opencode", "google/gemini-3.7-flash")

    def test_build_lmstudio_model(self):
        from inspect_ai.model import GenerateConfig

        from shinygen.config import _build_lmstudio_model

        with patch("inspect_ai.model.get_model") as mock_get_model:
            _build_lmstudio_model("openai/google/gemma-4-26b-a4b-qat")
            mock_get_model.assert_called_once_with(
                "openai/google/gemma-4-26b-a4b-qat",
                base_url="http://localhost:1234/v1",
                api_key="lm-studio",
                config=GenerateConfig(reasoning_effort="none"),
                memoize=False,
            )


class TestPreflightChecks:
    def test_preflight_checks_docker_first(self):
        """Docker check runs before API key check."""
        with patch("shinygen.config.shutil.which", return_value=None):
            with pytest.raises(DockerNotAvailableError):
                preflight_checks("claude_code")

    def test_preflight_checks_skips_docker_for_lmstudio(self):
        """LM Studio models run on the host and must not require Docker."""
        with patch("shinygen.config.check_docker") as mock_docker:
            # No API key required for LM Studio, so this should pass cleanly.
            preflight_checks("opencode", "openai/google/gemma-4-26b-a4b-qat")
        mock_docker.assert_not_called()
