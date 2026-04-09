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
    "claude-opus": ("claude_code", "anthropic/claude-opus-4-6"),
    "claude-opus-4-6": ("claude_code", "anthropic/claude-opus-4-6"),
    "claude-sonnet": ("claude_code", "anthropic/claude-sonnet-4-6"),
    "claude-sonnet-4-6": ("claude_code", "anthropic/claude-sonnet-4-6"),
    "claude-sonnet-4-5": ("claude_code", "anthropic/claude-sonnet-4-5"),
    "claude-haiku-4-5": ("claude_code", "anthropic/claude-haiku-4-5"),
    "gpt54": ("codex_cli", "openai/gpt-5.4"),
    "gpt-5.4": ("codex_cli", "openai/gpt-5.4"),
    "gpt54-mini": ("codex_cli", "openai/gpt-5.4-mini-2026-03-17"),
    "gpt-5.4-mini": ("codex_cli", "openai/gpt-5.4-mini-2026-03-17"),
    "gpt-5.4-nano": ("codex_cli", "openai/gpt-5.4-nano"),
    "codex-gpt53": ("codex_cli", "openai/gpt-5.3-codex"),
    "gpt-5.3-codex": ("codex_cli", "openai/gpt-5.3-codex"),
}

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
            "pip install shiny plotly faicons pandas matplotlib seaborn"
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
            'Rscript -e \'install.packages(c("shiny", "bslib", "bsicons", '
            '"ggplot2", "dplyr", "readr", "plotly", "DT", "leaflet"), '
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

# Agent → skill directory path inside sandbox
AGENT_SKILLS_DIR: dict[str, str] = {
    "claude_code": ".claude/skills",
    "codex_cli": ".agents/skills",
}

# Framework → compose file
FRAMEWORK_COMPOSE: dict[str, str] = {
    "shiny_r": "compose.yaml",
    "shiny_python": "compose-python.yaml",
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_FRAMEWORK = "shiny_python"
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_QUALITY_THRESHOLD = 7.0
SANDBOX_WORK_DIR = "/home/user/project"
SANDBOX_TIME_LIMIT = 10 * 60  # 10 minutes
BASE_PORT = 18801
STARTUP_TIMEOUT = 25
PAGE_LOAD_WAIT = 5
POST_INTERACT_WAIT = 5
SCREENSHOT_VIEWPORT = (1920, 1080)


def find_free_port() -> int:
    """Find and return a free TCP port on localhost."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


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
    raise ValueError(
        f"Unknown model '{alias}'. Choose from: "
        f"{', '.join(sorted(MODEL_ALIASES.keys()))}"
    )


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


def check_api_key(agent: str) -> None:
    """Verify the required API key is set for the given agent.

    Raises APIKeyMissingError with a descriptive message.
    """
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


def preflight_checks(agent: str) -> None:
    """Run all pre-flight checks before starting generation.

    Raises DockerNotAvailableError or APIKeyMissingError on failure.
    """
    check_docker()
    check_api_key(agent)
