"""
Model mappings, framework definitions, and default constants.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Model aliases → (agent, full model ID)
# ---------------------------------------------------------------------------

MODEL_ALIASES: dict[str, tuple[str, str]] = {
    "claude-opus": ("claude_code", "anthropic/claude-opus-4-8"),
    "claude-opus-4-8": ("claude_code", "anthropic/claude-opus-4-8"),
    "claude-opus-4-7": ("claude_code", "anthropic/claude-opus-4-7"),
    "claude-opus-4-6": ("claude_code", "anthropic/claude-opus-4-6"),
    "claude-sonnet": ("claude_code", "anthropic/claude-sonnet-4-6"),
    "claude-sonnet-4-6": ("claude_code", "anthropic/claude-sonnet-4-6"),
    "claude-sonnet-4-5": ("claude_code", "anthropic/claude-sonnet-4-5"),
    "claude-haiku-4-5": ("claude_code", "anthropic/claude-haiku-4-5"),
    "gpt55": ("codex_cli", "openai/gpt-5.5"),
    "gpt-5.5": ("codex_cli", "openai/gpt-5.5"),
    "gpt-5.5-2026-04-23": ("codex_cli", "openai/gpt-5.5-2026-04-23"),
    "gpt54": ("codex_cli", "openai/gpt-5.4"),
    "gpt-5.4": ("codex_cli", "openai/gpt-5.4"),
    "gpt54-mini": ("codex_cli", "openai/gpt-5.4-mini-2026-03-17"),
    "gpt-5.4-mini": ("codex_cli", "openai/gpt-5.4-mini-2026-03-17"),
    "gpt-5.4-nano": ("codex_cli", "openai/gpt-5.4-nano"),
    "gemma-4-26b-a4b": ("native_react_solver", "openai/gemma-4-26b-a4b"),
    "openai/gemma-4-26b-a4b": ("native_react_solver", "openai/gemma-4-26b-a4b"),
    "qwen3.6-27b": ("native_react_solver", "openai/qwen3.6-27b"),
    "openai/qwen3.6-27b": ("native_react_solver", "openai/qwen3.6-27b"),
}

OPENCODE_GO_BASE_URL = "https://opencode.ai/zen/go/v1"

# OpenCode Go models that expose OpenAI-compatible chat completions endpoints.
OPENCODE_GO_OPENAI_COMPATIBLE_MODELS = (
    "glm-5.1",
    "glm-5",
    "kimi-k2.5",
    "kimi-k2.6",
    "deepseek-v4-pro",
    "deepseek-v4-flash",
    "mimo-v2-pro",
    "mimo-v2-omni",
    "mimo-v2.5-pro",
    "mimo-v2.5",
    "qwen3.6-plus",
    "qwen3.5-plus",
)

# OpenCode Go MiniMax models expose an Anthropic-compatible messages endpoint.
# Keep a distinct resolved-id marker so generation can route these through
# Inspect's Anthropic provider with the OpenCode Go base URL/API key without
# mutating the normal Anthropic environment used by the judge.
OPENCODE_GO_ANTHROPIC_COMPATIBLE_MODELS = (
    "minimax-m2.5",
    "minimax-m2.7",
)


def _register_opencode_go_aliases() -> None:
    for model_name in OPENCODE_GO_OPENAI_COMPATIBLE_MODELS:
        inspect_model_id = f"openai-api/opencode-go/{model_name}"
        for alias in (
            model_name,
            f"opencode-go/{model_name}",
            f"opencode-go-{model_name}",
        ):
            MODEL_ALIASES.setdefault(alias, ("native_react_solver", inspect_model_id))

    for model_name in OPENCODE_GO_ANTHROPIC_COMPATIBLE_MODELS:
        inspect_model_id = f"anthropic/opencode-go/{model_name}"
        for alias in (
            model_name,
            f"opencode-go/{model_name}",
            f"opencode-go-{model_name}",
        ):
            MODEL_ALIASES.setdefault(alias, ("native_react_solver", inspect_model_id))


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
            "pip install shiny shinywidgets plotly faicons pandas "
            "matplotlib seaborn"
        ),
        "skill_dir": "shiny-python-dashboard",
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
        "skill_dir": "shiny-bslib",
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
}

# Agent → skill directory path inside sandbox (per each CLI's documented
# discovery rules). Codex CLI scans `.agents/skills` per
# https://developers.openai.com/codex/skills. Claude Code uses `.claude/skills`.
# Note: inspect_swe's codex_cli solver internally installs skills under
# `$CODEX_HOME/skills` (i.e. `.codex/skills`), which is NOT one of Codex's
# documented scan paths. shinygen.generate also stages the bundled skill into
# `.agents/skills/<name>/` via Sample.files to guarantee discovery.
AGENT_SKILLS_DIR: dict[str, str] = {
    "claude_code": ".claude/skills",
    "codex_cli": ".agents/skills",
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
    # Allow passing a full model ID directly — infer agent from prefix
    if key.startswith("anthropic/"):
        return ("claude_code", alias)
    if key.startswith("openai/"):
        return ("codex_cli", alias)
    if key.startswith("openai-api/"):
        return ("native_react_solver", alias)
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
    return "gemma-4-26b-a4b" in model or "qwen3.6-27b" in model


def _build_lmstudio_model(model_id: str):
    """Construct an Inspect ``Model`` for a local LM Studio model."""
    from inspect_ai.model import get_model

    base_url = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    api_key = os.environ.get("LMSTUDIO_API_KEY", "lm-studio")
    return get_model(
        model_id,
        base_url=base_url,
        api_key=api_key,
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
    elif agent == "native_react_solver":
        if not model_id:
            raise APIKeyMissingError(
                "native_react_solver requires a resolved Inspect model ID so shinygen "
                "can determine which provider API key is needed."
            )


def preflight_checks(agent: str, model_id: str | None = None) -> None:
    """Run all pre-flight checks before starting generation.

    Raises DockerNotAvailableError or APIKeyMissingError on failure.
    """
    check_docker()
    check_api_key(agent, model_id)
