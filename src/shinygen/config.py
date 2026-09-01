"""
Model mappings, framework definitions, and default constants.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from inspect_ai.model import Model

PACKAGE_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Model aliases → (agent, full model ID)
# ---------------------------------------------------------------------------

MODEL_ALIASES: dict[str, tuple[str, str]] = {
    "claude-opus": ("claude_code", "anthropic/claude-opus-4-8"),
    "claude-opus-4-8": ("claude_code", "anthropic/claude-opus-4-8"),
    "claude-3-opus": ("claude_code", "anthropic/claude-3-opus-20240229"),
    "claude-sonnet": ("claude_code", "anthropic/claude-sonnet-5"),
    "claude-sonnet-5": ("claude_code", "anthropic/claude-sonnet-5"),
    "claude-3-7-sonnet": ("claude_code", "anthropic/claude-3-7-sonnet-20250219"),
    "claude-3.7-sonnet": ("claude_code", "anthropic/claude-3-7-sonnet-20250219"),
    "claude-3-5-sonnet": ("claude_code", "anthropic/claude-3-5-sonnet-20241022"),
    "claude-3.5-sonnet": ("claude_code", "anthropic/claude-3-5-sonnet-20241022"),
    "claude-haiku": ("claude_code", "anthropic/claude-haiku-4-5"),
    "claude-haiku-4-5": ("claude_code", "anthropic/claude-haiku-4-5"),
    "claude-3-5-haiku": ("claude_code", "anthropic/claude-3-5-haiku-20241022"),
    "claude-3.5-haiku": ("claude_code", "anthropic/claude-3-5-haiku-20241022"),
    "sol": ("codex_cli", "openai/gpt-5.6-sol"),
    "gpt56-sol": ("codex_cli", "openai/gpt-5.6-sol"),
    "gpt-5.6-sol": ("codex_cli", "openai/gpt-5.6-sol"),
    "terra": ("codex_cli", "openai/gpt-5.6-terra"),
    "gpt56-terra": ("codex_cli", "openai/gpt-5.6-terra"),
    "gpt-5.6-terra": ("codex_cli", "openai/gpt-5.6-terra"),
    "luna": ("codex_cli", "openai/gpt-5.6-luna"),
    "gpt56-luna": ("codex_cli", "openai/gpt-5.6-luna"),
    "gpt-5.6-luna": ("codex_cli", "openai/gpt-5.6-luna"),
    "gemma-4-26b-a4b": ("opencode", "openai/google/gemma-4-26b-a4b-qat"),
    "openai/gemma-4-26b-a4b": (
        "opencode",
        "openai/google/gemma-4-26b-a4b-qat",
    ),
    "gemma-4-26b-a4b-qat": ("opencode", "openai/google/gemma-4-26b-a4b-qat"),
    "google/gemma-4-26b-a4b-qat": (
        "opencode",
        "openai/google/gemma-4-26b-a4b-qat",
    ),
    "openai/google/gemma-4-26b-a4b-qat": (
        "opencode",
        "openai/google/gemma-4-26b-a4b-qat",
    ),
    "qwen3.6-27b": ("opencode", "openai/qwen/qwen3.6-27b"),
    "openai/qwen3.6-27b": ("opencode", "openai/qwen/qwen3.6-27b"),
    "qwen/qwen3.6-27b": ("opencode", "openai/qwen/qwen3.6-27b"),
    "openai/qwen/qwen3.6-27b": ("opencode", "openai/qwen/qwen3.6-27b"),
    "gemma-4-e4b": ("opencode", "openai/google/gemma-4-e4b"),
    "google/gemma-4-e4b": ("opencode", "openai/google/gemma-4-e4b"),
    "openai/google/gemma-4-e4b": ("opencode", "openai/google/gemma-4-e4b"),
    "qwen3.6-35b-a3b": ("opencode", "openai/qwen/qwen3.6-35b-a3b"),
    "qwen/qwen3.6-35b-a3b": ("opencode", "openai/qwen/qwen3.6-35b-a3b"),
    "openai/qwen/qwen3.6-35b-a3b": (
        "opencode",
        "openai/qwen/qwen3.6-35b-a3b",
    ),
    "gemma-4-12b-it-qat": ("opencode", "openai/gemma-4-12b-it-qat"),
    "openai/gemma-4-12b-it-qat": ("opencode", "openai/gemma-4-12b-it-qat"),
    "gemini-3.7": ("gemini_cli", "google/gemini-3.7"),
    "gemini-3.7-pro": ("gemini_cli", "google/gemini-3.7-pro"),
    "gemini-3.7-flash": ("gemini_cli", "google/gemini-3.7-flash"),
    "google/gemini-3.7": ("gemini_cli", "google/gemini-3.7"),
    "google/gemini-3.7-pro": ("gemini_cli", "google/gemini-3.7-pro"),
    "google/gemini-3.7-flash": ("gemini_cli", "google/gemini-3.7-flash"),
}

OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"

# OpenCode Go models that expose OpenAI-compatible chat completions endpoints.
OPENCODE_GO_OPENAI_COMPATIBLE_MODELS = (
    "glm-5.3",
    "glm-5.3-flash",
    "glm-5.2",
    "kimi-k3",
    "kimi-k2.7-code",
    "kimi-k2.6",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "deepseek-v4-flash-vision-exp",
    "mimo-v2.5-pro",
    "mimo-v2.5",
    "qwen3.8-flash",
    "grok-4.6",
    "grok-4.5",
    "hy4-preview",
    "hy3",
    "longcat-2.0",
)

# OpenCode Go MiniMax & Qwen Max/Plus models that expose Anthropic-compatible messages endpoint.
OPENCODE_GO_ANTHROPIC_COMPATIBLE_MODELS = (
    "minimax-m3",
    "minimax-m2.7",
    "qwen3.8-max",
    "qwen3.7-max",
    "qwen3.7-plus",
)


def _register_opencode_go_aliases() -> None:
    for model_name in OPENCODE_GO_OPENAI_COMPATIBLE_MODELS:
        inspect_model_id = f"openai-api/opencode-go/{model_name}"
        for alias in (
            model_name,
            f"opencode-go/{model_name}",
            f"opencode-go-{model_name}",
        ):
            MODEL_ALIASES.setdefault(alias, ("opencode", inspect_model_id))

    for model_name in OPENCODE_GO_ANTHROPIC_COMPATIBLE_MODELS:
        inspect_model_id = f"anthropic/opencode-go/{model_name}"
        for alias in (
            model_name,
            f"opencode-go/{model_name}",
            f"opencode-go-{model_name}",
        ):
            MODEL_ALIASES.setdefault(alias, ("opencode", inspect_model_id))


_register_opencode_go_aliases()

# ---------------------------------------------------------------------------
# Framework configuration
# ---------------------------------------------------------------------------

FRAMEWORKS: dict[str, dict[str, str]] = {
    "shiny_python": {
        "label": "Shiny for Python",
        "language": "Python",
        "primary_artifact": "app.py",
        "run_command": "shiny run app.py --port {port}",
        "install_command": (
            "pip install shiny shinywidgets plotly faicons pandas " "matplotlib seaborn"
        ),
        "skill_dir": "shiny-for-python",
    },
    "shiny_r": {
        "label": "Shiny for R",
        "language": "R",
        "primary_artifact": "app.R",
        "run_command": (
            "Rscript -e \"shiny::runApp('app.R', port = {port}, "
            'launch.browser = FALSE)"'
        ),
        "install_command": (
            'Rscript -e \'install.packages(c("package_name"), '
            'repos = "https://cloud.r-project.org")\''
        ),
        "skill_dir": "shiny-for-r",
    },
}

# Normalize CLI framework names
FRAMEWORK_ALIASES: dict[str, str] = {
    "shiny-python": "shiny_python",
    "shiny-r": "shiny_r",
    "shiny_python": "shiny_python",
    "shiny_r": "shiny_r",
    "python": "shiny_python",
    "r": "shiny_r",
}

# ---------------------------------------------------------------------------
# Agent ↔ tool/path mappings
# ---------------------------------------------------------------------------

# Web search tool name per agent
WEB_SEARCH_TOOL_NAME: dict[str, str] = {
    "claude_code": "WebSearch",
    "codex_cli": "web_search",
    "gemini_cli": "google_web_search",
    "opencode": "web_search",
}

# Agent → skill directory path inside sandbox
AGENT_SKILLS_DIR: dict[str, str] = {
    "claude_code": ".claude/skills",
    "codex_cli": ".agents/skills",
    "gemini_cli": ".gemini/skills",
    "opencode": ".config/opencode/skills",
}

# Framework → compose file
FRAMEWORK_COMPOSE: dict[str, str] = {
    "shiny_r": "compose.yaml",
    "shiny_python": "compose-python.yaml",
}

# Image name env vars and defaults used for both Inspect sandboxes and
# post-generation runtime validation.
SANDBOX_IMAGE_ENV_DEFAULTS: dict[str, tuple[str, str]] = {
    "shiny_r": (
        "SHINYGEN_SANDBOX_R_IMAGE",
        "ghcr.io/karangattu/shinygen-sandbox-r:latest",
    ),
    "shiny_python": (
        "SHINYGEN_SANDBOX_PYTHON_IMAGE",
        "ghcr.io/karangattu/shinygen-sandbox-python:latest",
    ),
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_FRAMEWORK = "shiny_python"
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_QUALITY_THRESHOLD = 7.0
SANDBOX_WORK_DIR = "/home/user/project"
SANDBOX_TIME_LIMIT = 10 * 60  # 10 minutes
# Shiny for R generations are generally slower due heavier startup and
# package/runtime validation, so give them a larger execution budget.
# 25 min for R lets Claude Opus complete with --screenshot enabled in 3
# iterations within a 120 min GHA job budget.
SANDBOX_TIME_LIMIT_BY_FRAMEWORK: dict[str, int] = {
    "shiny_python": SANDBOX_TIME_LIMIT,
    "shiny_r": 25 * 60,
}
# Hard ceiling for the OpenCode Go (open-weights) tier. Empirical evidence
# from May-13 showed runs hitting the 25-min framework ceiling without
# producing better apps because the upstream proxy was stalling. Failing
# fast at 10 minutes preserves benchmark budget.
OPENCODE_GO_TIME_LIMIT = 10 * 60
BASE_PORT = 18801
STARTUP_TIMEOUT = 25
PAGE_LOAD_WAIT = 7
POST_INTERACT_WAIT = 5
SCREENSHOT_VIEWPORT = (1920, 2200)


def find_free_port() -> int:
    """Find and return a free TCP port on localhost."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def sandbox_time_limit_for_framework(framework_key: str) -> int:
    """Return sandbox time limit (seconds) for a framework."""
    return SANDBOX_TIME_LIMIT_BY_FRAMEWORK.get(framework_key, SANDBOX_TIME_LIMIT)


def resolve_model(alias: str) -> tuple[str, str]:
    """Resolve a model alias to (agent, model_id).

    Raises ValueError if unknown alias.
    """
    key = alias.lower().strip()
    if key in MODEL_ALIASES:
        return MODEL_ALIASES[key]
    if key.startswith("lmstudio/") and key != "lmstudio/":
        return ("opencode", key)
    # Allow passing a full model ID directly — infer agent from prefix
    if key.startswith("anthropic/"):
        return ("claude_code", alias)
    if key.startswith("openai/"):
        return ("codex_cli", alias)
    if key.startswith("google/") or key.startswith("gemini/"):
        return ("gemini_cli", alias)
    if key.startswith("openai-api/") or key.startswith("opencode/"):
        return ("opencode", alias)
    raise ValueError(
        f"Unknown model '{alias}'. Choose from: "
        f"{', '.join(sorted(MODEL_ALIASES.keys()))}"
    )


def is_opencode_go_model(model_id: str) -> bool:
    """Return True when a resolved Inspect model points at OpenCode Go."""
    model = model_id.lower().strip()
    return model.startswith("openai-api/opencode-go/") or model.startswith(
        "anthropic/opencode-go/"
    )


def is_lmstudio_model(model_id: str) -> bool:
    """Return True when a resolved Inspect model points to LM Studio."""
    model = model_id.lower().strip()
    # Provider-qualified OpenCode Go IDs can contain the same model names as
    # local LM Studio aliases; the provider prefix must take precedence.
    if is_opencode_go_model(model):
        return False
    return (
        model.startswith("lmstudio/")
        or "gemma-4-26b-a4b" in model
        or "qwen3.6-27b" in model
        or "gemma-4-e4b" in model
        or "qwen3.6-35b-a3b" in model
        or "gemma-4-12b-it-qat" in model
    )


def _build_lmstudio_model(model_id: str) -> "Model":
    """Construct an Inspect ``Model`` for a local LM Studio model."""
    from inspect_ai.model import GenerateConfig, get_model

    base_url = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    api_key = os.environ.get("LMSTUDIO_API_KEY", "lm-studio")
    inspect_model_id = (
        f"openai/{model_id.split('/', 1)[1]}"
        if model_id.lower().startswith("lmstudio/")
        else model_id
    )
    return get_model(
        inspect_model_id,
        base_url=base_url,
        api_key=api_key,
        config=GenerateConfig(reasoning_effort="none"),
        memoize=False,
    )


def is_opencode_go_anthropic_model(model_id: str) -> bool:
    """Return True for OpenCode Go models served via Anthropic messages."""
    return model_id.lower().strip().startswith("anthropic/opencode-go/")


def opencode_go_anthropic_model_name(model_id: str) -> str:
    """Return the API model name for an Anthropic-compatible OpenCode Go ID."""
    if not is_opencode_go_anthropic_model(model_id):
        raise ValueError(f"Not an OpenCode Go Anthropic-compatible model: {model_id}")
    return model_id.split("/", 2)[2]


def prepare_model_environment(model_id: str) -> None:
    """Set provider defaults needed by resolved model IDs.

    Inspect's `openai-api/<provider>/<model>` provider reads
    `<PROVIDER>_API_KEY` and `<PROVIDER>_BASE_URL`. OpenCode Go's base URL is
    stable, so shinygen supplies it automatically while leaving the API key to
    the caller's environment or CI secret.
    """
    if is_opencode_go_model(model_id):
        os.environ.setdefault("OPENCODE_GO_BASE_URL", OPENCODE_GO_BASE_URL)


def resolve_framework(alias: str) -> str:
    """Resolve a framework alias to the canonical key.

    Raises ValueError if unknown alias.
    """
    key = alias.lower().strip().replace(" ", "_")
    if key in FRAMEWORK_ALIASES:
        return FRAMEWORK_ALIASES[key]
    raise ValueError(
        f"Unknown framework '{alias}'. Choose from: "
        f"{', '.join(sorted(FRAMEWORK_ALIASES.keys()))}"
    )


# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------


class DockerNotAvailableError(RuntimeError):
    """Raised when Docker is not installed or not running."""


class APIKeyMissingError(RuntimeError):
    """Raised when a required LLM API key is missing."""


def check_docker() -> None:
    """Verify that Docker is installed and the daemon is running.

    Raises DockerNotAvailableError with a descriptive message.
    """
    if not shutil.which("docker"):
        raise DockerNotAvailableError(
            "Docker is not installed. shinygen requires Docker to run LLM "
            "agents in sandboxed containers.\n"
            "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
        )
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=15,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise DockerNotAvailableError(
            "Docker is installed but not running. Please start Docker Desktop "
            "and try again."
        )


def check_api_key(agent: str, model_id: str | None = None) -> None:
    """Verify the required API key is set for the given agent.

    Raises APIKeyMissingError with a descriptive message.
    """
    if model_id and is_lmstudio_model(model_id):
        return

    if model_id and is_opencode_go_model(model_id):
        if not os.environ.get("OPENCODE_GO_API_KEY"):
            raise APIKeyMissingError(
                "OPENCODE_GO_API_KEY environment variable is not set.\n"
                "Subscribe to OpenCode Go, copy your API key from "
                "https://opencode.ai/auth, and run:\n"
                "  export OPENCODE_GO_API_KEY='sk-...'"
            )
        return

    if agent == "claude_code":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise APIKeyMissingError(
                "ANTHROPIC_API_KEY environment variable is not set.\n"
                "Get your API key from https://console.anthropic.com/ and run:\n"
                "  export ANTHROPIC_API_KEY='sk-...'"
            )
    elif agent == "codex_cli":
        if not os.environ.get("OPENAI_API_KEY"):
            raise APIKeyMissingError(
                "OPENAI_API_KEY environment variable is not set.\n"
                "Get your API key from https://platform.openai.com/api-keys and run:\n"
                "  export OPENAI_API_KEY='sk-...'"
            )
    elif agent == "gemini_cli":
        if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
            raise APIKeyMissingError(
                "GEMINI_API_KEY environment variable is not set.\n"
                "Get your API key from https://aistudio.google.com/ and run:\n"
                "  export GEMINI_API_KEY='...'"
            )
    elif agent in {"opencode", "native_react_solver"}:
        if not model_id:
            raise APIKeyMissingError(
                f"{agent} requires a resolved Inspect model ID so shinygen "
                "can determine which provider API key is needed."
            )
        if model_id.startswith("anthropic/"):
            check_api_key("claude_code")
        elif model_id.startswith("openai/"):
            check_api_key("codex_cli")
        elif model_id.startswith("google/") or model_id.startswith("gemini/"):
            check_api_key("gemini_cli")
        elif is_opencode_go_model(model_id):
            if not os.environ.get("OPENCODE_GO_API_KEY"):
                raise APIKeyMissingError(
                    "OPENCODE_GO_API_KEY environment variable is not set.\n"
                    "Subscribe to OpenCode Go, copy your API key from "
                    "https://opencode.ai/auth, and run:\n"
                    "  export OPENCODE_GO_API_KEY='sk-...'"
                )
        else:
            raise APIKeyMissingError(
                f"No API key mapping is configured for model '{model_id}'."
            )


def preflight_checks(agent: str, model_id: str | None = None) -> None:
    """Run all pre-flight checks before starting generation.

    Raises DockerNotAvailableError or APIKeyMissingError on failure.

    LM Studio models run entirely on the host (model inference against the
    local LM Studio server and app validation via the project venv), so the
    Docker daemon check is skipped for them.
    """
    if not (model_id and is_lmstudio_model(model_id)):
        check_docker()
    check_api_key(agent, model_id)
