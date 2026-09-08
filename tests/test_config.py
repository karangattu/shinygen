"""Tests for shinygen.config"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from shinygen.config import (
    FRAMEWORKS,
    OPENCODE_GO_SESSION_HEADER,
    OPENCODE_GO_SESSION_ID_ENV,
    APIKeyMissingError,
    DockerNotAvailableError,
    check_api_key,
    check_docker,
    find_free_port,
    get_opencode_go_session_id,
    is_opencode_go_anthropic_model,
    normalize_opencode_go_session_id,
    opencode_go_anthropic_model_name,
    preflight_checks,
    prepare_model_environment,
    reset_opencode_go_session_id,
    resolve_framework,
    resolve_model,
    set_opencode_go_session_id,
)


class TestResolveModel:
    def test_known_alias(self):
        agent, model_id = resolve_model("claude-sonnet")
        assert agent == "claude_code"
        assert "claude" in model_id

    def test_claude_opus_alias_resolves_to_latest_release(self):
        agent, model_id = resolve_model("claude-opus")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-opus-5"

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
        agent, model_id = resolve_model("claude-opus-5")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-opus-5"

    def test_exact_anthropic_haiku_model_name_without_provider(self):
        agent, model_id = resolve_model("claude-haiku-4-5")
        assert agent == "claude_code"
        assert model_id == "anthropic/claude-haiku-4-5"

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
        agent, model_id = resolve_model("minimax-m3")
        assert agent == "opencode"
        assert model_id == "anthropic/opencode-go/minimax-m3"
        assert is_opencode_go_anthropic_model(model_id)
        assert opencode_go_anthropic_model_name(model_id) == "minimax-m3"

    def test_opencode_go_qwen38_max_alias_resolves_to_anthropic_provider_marker(self):
        agent, model_id = resolve_model("qwen3.8-max")
        assert agent == "opencode"
        assert model_id == "anthropic/opencode-go/qwen3.8-max"
        assert is_opencode_go_anthropic_model(model_id)
        assert opencode_go_anthropic_model_name(model_id) == "qwen3.8-max"

    @pytest.mark.parametrize(
        "alias",
        [
            "glm-5.3",
            "glm-5.3-flash",
            "glm-5.2",
            "glm-5.1",
            "glm-5",
            "kimi-k3",
            "kimi-k2.7-code",
            "kimi-k2.6",
            "kimi-k2.5",
            "mimo-v2.5",
            "mimo-v2.5-pro",
            "mimo-v2-pro",
            "mimo-v2-omni",
            "minimax-m3",
            "minimax-m2.7",
            "minimax-m2.5",
            "qwen3.8-max",
            "qwen3.8-flash",
            "qwen3.7-max",
            "qwen3.7-plus",
            "qwen3.6-plus",
            "qwen3.5-plus",
            "deepseek-v4-pro",
            "deepseek-v4-flash",
            "deepseek-v4-flash-vision-exp",
            "grok-4.6",
            "grok-4.5",
            "hy4-preview",
            "hy3",
            "longcat-2.0",
            "muse-spark-1.3-contributor",
            "muse-spark-1.2-contributor",
        ],
    )
    def test_all_documented_opencode_go_aliases_resolve(self, alias):
        agent, model_id = resolve_model(alias)
        assert agent == "opencode"
        assert model_id.endswith(alias)

    @pytest.mark.parametrize(
        ("alias", "expected_target"),
        [
            ("muse-contributor-1.3", "openai-api/opencode-go/muse-spark-1.3-contributor"),
            ("muse-spark-1.3", "openai-api/opencode-go/muse-spark-1.3-contributor"),
            ("muse-1.3-contributor", "openai-api/opencode-go/muse-spark-1.3-contributor"),
            ("muse-contributor-1.2", "openai-api/opencode-go/muse-spark-1.2-contributor"),
            ("muse-spark-1.2", "openai-api/opencode-go/muse-spark-1.2-contributor"),
            ("muse-1.2-contributor", "openai-api/opencode-go/muse-spark-1.2-contributor"),
        ],
    )
    def test_muse_convenience_aliases_resolve(self, alias, expected_target):
        agent, model_id = resolve_model(alias)
        assert agent == "opencode"
        assert model_id == expected_target

    def test_full_anthropic_opencode_id_uses_opencode(self):
        agent, model_id = resolve_model("anthropic/opencode-go/qwen3.8-max")
        assert agent == "opencode"
        assert model_id == "anthropic/opencode-go/qwen3.8-max"

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
            assert os.environ.get("GOOGLE_API_KEY") == "test-key"
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key-2"}, clear=True):
            check_api_key("gemini_cli")
            assert os.environ.get("GEMINI_API_KEY") == "test-key-2"

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
            assert os.environ[OPENCODE_GO_SESSION_ID_ENV].startswith("ses_")

    def test_normalize_opencode_go_session_id(self):
        assert normalize_opencode_go_session_id(None).startswith("ses_")
        assert normalize_opencode_go_session_id("").startswith("ses_")
        assert normalize_opencode_go_session_id("ses_12345") == "ses_12345"
        assert normalize_opencode_go_session_id("run-34186935196-skills") == "ses_run34186935196skills"

    def test_get_set_reset_opencode_go_session_id(self):
        with patch.dict("os.environ", {}, clear=True):
            set_opencode_go_session_id("ses_custom123")
            assert get_opencode_go_session_id() == "ses_custom123"
            assert os.environ[OPENCODE_GO_SESSION_ID_ENV] == "ses_custom123"

            new_id = reset_opencode_go_session_id()
            assert new_id.startswith("ses_")
            assert new_id != "ses_custom123"
            assert get_opencode_go_session_id() == new_id

            set_opencode_go_session_id(None)
            assert OPENCODE_GO_SESSION_ID_ENV not in os.environ

    def test_httpx_async_client_injects_opencode_session_header(self):
        import asyncio
        import httpx

        received_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received_headers.update(dict(request.headers))
            return httpx.Response(200, json={"ok": True})

        async def _run():
            transport = httpx.MockTransport(handler)
            with patch.dict("os.environ", {OPENCODE_GO_SESSION_ID_ENV: "ses_test999"}):
                async with httpx.AsyncClient(transport=transport) as client:
                    await client.post("https://opencode.ai/zen/go/v1/chat/completions", json={})

        asyncio.run(_run())
        assert received_headers.get(OPENCODE_GO_SESSION_HEADER) == "ses_test999"

    def test_httpx_async_client_preserves_existing_opencode_session_header(self):
        import asyncio
        import httpx

        received_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received_headers.update(dict(request.headers))
            return httpx.Response(200, json={"ok": True})

        async def _run():
            transport = httpx.MockTransport(handler)
            with patch.dict("os.environ", {OPENCODE_GO_SESSION_ID_ENV: "ses_default"}):
                async with httpx.AsyncClient(transport=transport) as client:
                    await client.post(
                        "https://opencode.ai/zen/go/v1/chat/completions",
                        headers={OPENCODE_GO_SESSION_HEADER: "ses_explicit"},
                        json={},
                    )

        asyncio.run(_run())
        assert received_headers.get(OPENCODE_GO_SESSION_HEADER) == "ses_explicit"

    def test_httpx_async_client_skips_non_opencode_urls(self):
        import asyncio
        import httpx

        received_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received_headers.update(dict(request.headers))
            return httpx.Response(200, json={"ok": True})

        async def _run():
            transport = httpx.MockTransport(handler)
            with patch.dict("os.environ", {OPENCODE_GO_SESSION_ID_ENV: "ses_test999"}):
                async with httpx.AsyncClient(transport=transport) as client:
                    await client.post("https://api.openai.com/v1/chat/completions", json={})

        asyncio.run(_run())
        assert OPENCODE_GO_SESSION_HEADER not in received_headers

    def test_httpx_sync_client_injects_opencode_session_header(self):
        import httpx

        received_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received_headers.update(dict(request.headers))
            return httpx.Response(200, json={"ok": True})

        transport = httpx.MockTransport(handler)
        with patch.dict("os.environ", {OPENCODE_GO_SESSION_ID_ENV: "ses_sync123"}):
            with httpx.Client(transport=transport) as client:
                client.post("https://opencode.ai/zen/go/v1/chat/completions", json={})

        assert received_headers.get(OPENCODE_GO_SESSION_HEADER) == "ses_sync123"

    def test_httpx2_clients_inject_opencode_session_header(self):
        try:
            import httpx2
        except ImportError:
            return

        import asyncio

        received_headers: dict[str, str] = {}

        def handler(request):
            received_headers.update(dict(request.headers))
            return httpx2.Response(200, json={"ok": True})

        transport = httpx2.MockTransport(handler)
        with patch.dict("os.environ", {OPENCODE_GO_SESSION_ID_ENV: "ses_httpx2_val"}):
            with httpx2.Client(transport=transport) as client:
                client.post("https://opencode.ai/zen/go/v1/responses", json={})
            assert received_headers.get(OPENCODE_GO_SESSION_HEADER) == "ses_httpx2_val"

            received_headers.clear()

            async def _run():
                async with httpx2.AsyncClient(transport=transport) as client:
                    await client.post("https://opencode.ai/zen/go/v1/responses", json={})

            asyncio.run(_run())
            assert received_headers.get(OPENCODE_GO_SESSION_HEADER) == "ses_httpx2_val"

    def test_opencode_go_responses_models_auto_enable_responses_api(self):
        from inspect_ai.model._providers.openai_compatible import OpenAICompatibleAPI

        from shinygen.config import OPENCODE_GO_RESPONSES_MODELS

        assert "muse-spark-1.3-contributor" in OPENCODE_GO_RESPONSES_MODELS

        with patch.dict(
            "os.environ",
            {
                "OPENCODE_GO_BASE_URL": "https://opencode.ai/zen/go/v1",
                "OPENCODE_GO_API_KEY": "sk-test",
            },
        ):
            api_muse = OpenAICompatibleAPI(
                model_name="opencode-go/muse-spark-1.3-contributor",
            )
            assert api_muse.responses_api is True

            api_glm = OpenAICompatibleAPI(
                model_name="opencode-go/glm-5.3-flash",
            )
            assert api_glm.responses_api is None or api_glm.responses_api is False

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


def test_pyproject_contains_google_genai_dependency():
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    assert "google-genai" in content
