"""
Inspect AI task definition for generating Shiny apps using
Claude Code or Codex CLI in Docker sandboxes.
"""

from __future__ import annotations

import logging
import shlex
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ChatMessageSystem, ChatMessageUser
from inspect_ai.scorer import Score, Target, scorer
from inspect_ai.solver import TaskState
from inspect_ai.tool import Skill
from inspect_swe import claude_code, codex_cli

if TYPE_CHECKING:
    from inspect_ai.util import SandboxEnvironment

from .config import (
    FRAMEWORK_COMPOSE,
    FRAMEWORKS,
    SANDBOX_WORK_DIR,
    sandbox_time_limit_for_framework,
)
from .prompts import build_system_prompt, build_user_prompt
from .validation import validate_framework_artifact

logger = logging.getLogger(__name__)

CODEX_CLI_VERSION = "auto"
CODEX_CONFIG_OVERRIDES = {"web_search": "live"}
CODEX_DISALLOWED_TOOLS = ["web_search"]

# Artifact names we search for
APP_ARTIFACTS = ("app.py", "app.R")
DIRECT_ARTIFACT_DIRS = ("/home/user/project", "/", "/root")
ARTIFACT_SEARCH_ROOTS = (
    "/home/user/project",
    "/root",
    "/Users",
    "/tmp",
    "/workspace",
    "/workspaces",
    "/app",
)

# ---------------------------------------------------------------------------
# Docker file staging
# ---------------------------------------------------------------------------

DOCKERFILES_DIR = Path(__file__).parent / "dockerfiles"

# Image name env vars and defaults (must match compose.yaml / compose-python.yaml)
_SANDBOX_IMAGE_DEFAULTS: dict[str, tuple[str, str]] = {
    "shiny_r": ("SHINYGEN_SANDBOX_R_IMAGE", "ghcr.io/karangattu/shinygen-sandbox-r:latest"),
    "shiny_python": ("SHINYGEN_SANDBOX_PYTHON_IMAGE", "ghcr.io/karangattu/shinygen-sandbox-python:latest"),
}


def _docker_image_exists_locally(image: str) -> bool:
    """Return True when *image* is already available in the local Docker daemon."""
    import subprocess as _sp

    try:
        result = _sp.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False


def stage_docker_context(
    framework_key: str,
    results_dir: Path | None = None,
) -> Path:
    """Copy Dockerfiles and compose files to a temp directory for Inspect AI.

    When the pre-built sandbox image is already available locally (e.g.
    pulled by a CI pre-pull step), the staged compose file omits the
    ``build:`` section so that ``docker compose build`` (called by
    Inspect AI) becomes a no-op.  This avoids a 25+ minute rebuild of
    R packages from source on every benchmark run.

    Returns the path to the temp directory (caller should clean up).
    """
    import os
    import re

    tmp = Path(tempfile.mkdtemp(prefix="shinygen_"))
    compose_file = FRAMEWORK_COMPOSE.get(framework_key, "compose-python.yaml")

    # Resolve the sandbox image name from environment / defaults.
    env_var, default_image = _SANDBOX_IMAGE_DEFAULTS.get(
        framework_key, ("", "")
    )
    image_name = os.environ.get(env_var, default_image) if env_var else default_image

    if image_name and _docker_image_exists_locally(image_name):
        # Image is already pulled — write a minimal compose without the
        # build: section so Inspect AI does not trigger a rebuild.
        logger.info(
            "Pre-built sandbox image found locally (%s); skipping Dockerfile build",
            image_name,
        )
        src_compose = (DOCKERFILES_DIR / compose_file).read_text(encoding="utf-8")
        # Strip the build: block (build: + lines indented deeper than it)
        stripped = re.sub(
            r"^(\s*)build:\s*\n(?:\1\s+\S.*\n)*",
            "",
            src_compose,
            flags=re.MULTILINE,
        )
        # Also switch pull_policy to 'never' since the image is already local.
        stripped = stripped.replace("pull_policy: missing", "pull_policy: never")
        (tmp / compose_file).write_text(stripped, encoding="utf-8")
    else:
        # Fallback: copy compose + Dockerfile so Docker can build from source.
        shutil.copy2(DOCKERFILES_DIR / compose_file, tmp / compose_file)
        if framework_key == "shiny_r":
            shutil.copy2(DOCKERFILES_DIR / "Dockerfile.r", tmp / "Dockerfile.r")
        else:
            shutil.copy2(DOCKERFILES_DIR / "Dockerfile.python", tmp / "Dockerfile.python")

    # Create results dir for volume mount
    results = tmp / "results"
    results.mkdir(exist_ok=True)

    return tmp


# ---------------------------------------------------------------------------
# Sandbox helpers
# ---------------------------------------------------------------------------


def _unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for path in paths:
        if path and path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


async def _discover_artifact_paths(
    sb: "SandboxEnvironment",
    artifact_names: tuple[str, ...] = APP_ARTIFACTS,
) -> dict[str, list[str]]:
    """Search the sandbox filesystem for artifact files."""
    discovered: dict[str, list[str]] = {name: [] for name in artifact_names}

    for artifact in artifact_names:
        for directory in DIRECT_ARTIFACT_DIRS:
            path = (
                f"{directory.rstrip('/')}/{artifact}"
                if directory != "/"
                else f"/{artifact}"
            )
            try:
                result = await sb.exec(["test", "-f", path])
            except Exception as exc:
                logger.debug("test -f %s failed: %s", path, exc)
                continue
            if result.returncode == 0:
                discovered[artifact].append(path)

    find_cmd = "find {roots} -type f \\( {names} \\) 2>/dev/null".format(
        roots=" ".join(shlex.quote(root) for root in ARTIFACT_SEARCH_ROOTS),
        names=" -o ".join(f"-name {shlex.quote(name)}" for name in artifact_names),
    )
    try:
        result = await sb.exec(["sh", "-lc", find_cmd])
        stdout = getattr(result, "stdout", "") or getattr(result, "output", "")
        for line in stdout.splitlines():
            path = line.strip()
            if not path:
                continue
            for artifact in artifact_names:
                if path.endswith(f"/{artifact}") or path == f"/{artifact}":
                    discovered[artifact].append(path)
    except Exception as exc:
        logger.debug("find command failed: %s", exc)

    return {artifact: _unique_paths(paths) for artifact, paths in discovered.items()}


async def _read_artifact_text(sb: "SandboxEnvironment", path: str) -> str | None:
    """Read a file from the sandbox, preferring sandbox().read_file()."""
    try:
        return await sb.read_file(path)
    except Exception as exc:
        logger.debug("sandbox read_file(%s) failed, falling back to cat: %s", path, exc)
    # Fallback to exec cat
    try:
        result = await sb.exec(["cat", path])
    except Exception:
        return None
    if getattr(result, "returncode", 1) != 0:
        return None
    return getattr(result, "stdout", "") or getattr(result, "output", "")


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


SANDBOX_AUTO_SCREENSHOT_TIMEOUT = 90


async def _ensure_sandbox_screenshot(
    sb: "SandboxEnvironment",
    framework: str,
) -> bool:
    """Capture screenshot.png in the sandbox project dir if missing.

    The agent is asked to take its own screenshot, but in production runs
    it sometimes skips this step. This fallback runs the bundled helper
    against the agent's app inside the sandbox so the judge always has a
    visual signal — independent of agent compliance.

    Returns True when a screenshot file exists at the end of the call.
    """
    project = SANDBOX_WORK_DIR
    screenshot_path = f"{project}/screenshot.png"
    helper_path = f"{project}/.tools/screenshot_helper.py"

    try:
        existing = await sb.exec(["test", "-f", screenshot_path])
        if existing.returncode == 0:
            return True
    except Exception as exc:
        logger.debug("test -f %s failed: %s", screenshot_path, exc)

    try:
        helper_check = await sb.exec(["test", "-f", helper_path])
        if helper_check.returncode != 0:
            logger.debug("Screenshot helper not present at %s; skipping", helper_path)
            return False
    except Exception as exc:
        logger.debug("Helper presence check failed: %s", exc)
        return False

    if framework == "shiny_r":
        start_cmd = (
            "cd {p} && nohup Rscript -e \"shiny::runApp('app.R', port=8000, "
            "launch.browser=FALSE)\" > /tmp/auto_app.log 2>&1 &"
        ).format(p=project)
        stop_cmd = "pkill -f 'Rscript' || true"
    else:
        start_cmd = (
            "cd {p} && nohup python3 -m shiny run app.py --port 8000 "
            "> /tmp/auto_app.log 2>&1 &"
        ).format(p=project)
        stop_cmd = "pkill -f 'shiny run' || true"

    try:
        await sb.exec(["sh", "-lc", start_cmd])
    except Exception as exc:
        logger.warning("Auto-screenshot: failed to launch app: %s", exc)
        return False

    try:
        result = await sb.exec(
            [
                "sh",
                "-lc",
                (
                    f"python3 {helper_path} --port 8000 --output {screenshot_path} "
                    "--wait 7 || true"
                ),
            ],
            timeout=SANDBOX_AUTO_SCREENSHOT_TIMEOUT,
        )
        stdout = getattr(result, "stdout", "") or getattr(result, "output", "")
        if stdout:
            logger.debug("Auto-screenshot helper output: %s", stdout.strip())
    except Exception as exc:
        logger.warning("Auto-screenshot helper failed: %s", exc)
    finally:
        try:
            await sb.exec(["sh", "-lc", stop_cmd])
        except Exception:
            pass

    try:
        check = await sb.exec(["test", "-f", screenshot_path])
        return check.returncode == 0
    except Exception:
        return False


@scorer(metrics=[])
def app_created_scorer(screenshot: bool = False):
    """1.0 if the expected artifact exists and is valid, 0.0 otherwise.

    When ``screenshot`` is True, the scorer also ensures a screenshot of
    the running app is captured inside the sandbox (using the bundled
    helper) before the project is copied to the output volume. This makes
    visual evaluation independent of whether the agent voluntarily ran
    the screenshot tool.
    """

    async def do_score(state: TaskState, target: Target) -> Score:
        from inspect_ai.util import sandbox

        sb = sandbox()
        artifact = state.metadata.get("primary_artifact", "app.py")
        framework = state.metadata.get("framework", "")

        canonical = f"{SANDBOX_WORK_DIR}/{artifact}"
        discovered = await _discover_artifact_paths(sb)
        expected_paths = discovered.get(artifact, [])

        found_path = None
        if canonical in expected_paths:
            found_path = canonical
        elif expected_paths:
            found_path = expected_paths[0]
            try:
                await sb.exec(["cp", found_path, canonical])
                found_path = canonical
            except Exception as exc:
                logger.warning("Failed to copy artifact to canonical path: %s", exc)

        # Ensure a sandbox screenshot exists before copying the project so
        # the host-side judge always has a visual signal (even when the
        # agent forgot to take one itself).
        if screenshot and found_path:
            try:
                captured = await _ensure_sandbox_screenshot(sb, framework)
                if not captured:
                    logger.warning(
                        "Auto-screenshot did not produce screenshot.png; "
                        "judge will fall back to agent attachment if any"
                    )
            except Exception as exc:
                logger.warning("Auto-screenshot wrapper failed: %s", exc)

        # Copy project files to output volume
        sample_id = state.sample_id or "unknown"
        output_dir = f"/output/{sample_id}"
        try:
            await sb.exec(["mkdir", "-p", output_dir])
            await sb.exec(["sh", "-c", f"cp -r {SANDBOX_WORK_DIR}/* {output_dir}/"])
        except Exception as exc:
            logger.warning("Failed to copy project files to output volume: %s", exc)

        # Verify the artifact was copied to the output volume
        try:
            verify = await sb.exec(["test", "-f", f"{output_dir}/{artifact}"])
            if verify.returncode != 0:
                logger.warning("Artifact not found in output volume, retrying copy")
                if found_path:
                    await sb.exec(["cp", found_path, f"{output_dir}/{artifact}"])
        except Exception as exc:
            logger.debug("Output volume verification failed: %s", exc)

        if not found_path:
            return Score(
                value=0.0,
                answer=f"{artifact} NOT found",
                explanation=f"Searched: {', '.join(DIRECT_ARTIFACT_DIRS)}",
            )

        content = await _read_artifact_text(sb, found_path)
        if content is None:
            return Score(
                value=0.0,
                answer=f"{artifact} found but unreadable",
                explanation=f"Path: {found_path}",
            )

        valid, reason = validate_framework_artifact(framework, artifact, content)
        if not valid:
            return Score(
                value=0.0,
                answer=f"{artifact} invalid: {reason}",
                explanation=f"Content validation failed: {reason}",
            )

        return Score(
            value=1.0,
            answer=f"{artifact} found and valid",
            explanation=f"Path: {found_path}; {reason}",
        )

    return do_score


# ---------------------------------------------------------------------------
# Task builder
# ---------------------------------------------------------------------------


def build_generation_task(
    user_prompt: str,
    agent: str,
    framework_key: str,
    docker_context_dir: Path,
    data_files: dict[str, str] | None = None,
    skills: list[Skill] | None = None,
    web_fetch: bool = True,
    screenshot: bool = False,
) -> Task:
    """Build an Inspect AI Task for generating a Shiny app.

    Args:
        user_prompt: The user's natural language app description.
        agent: "claude_code" or "codex_cli".
        framework_key: "shiny_python" or "shiny_r".
        docker_context_dir: Path to staged Docker context.
        data_files: Dict of {filename: content} for data files.
        skills: Agent skills to install inside the sandbox.
        web_fetch: Whether to allow web search tools.
        screenshot: Whether to inject visual self-evaluation tools.

    Returns:
        An Inspect AI Task ready to be evaluated.
    """
    fw = FRAMEWORKS[framework_key]
    artifact = fw["primary_artifact"]
    compose_file = FRAMEWORK_COMPOSE.get(framework_key, "compose-python.yaml")

    # Build data file names list for system prompt
    data_file_names = list(data_files.keys()) if data_files else None

    sys_prompt = build_system_prompt(
        framework_key,
        data_file_names,
        screenshot=screenshot,
    )
    full_user_prompt = build_user_prompt(user_prompt, framework_key)
    resolved_skills = list(skills or [])

    # Merge sample files
    sample_files: dict[str, str] = {}
    if data_files:
        sample_files.update(data_files)

    # Inject visual self-evaluation tools when screenshot mode is on
    if screenshot:
        from .skills import load_visual_qa_skills

        resolved_skills.extend(load_visual_qa_skills())

        # Inject the screenshot helper script
        helper_script = (Path(__file__).parent / "screenshot_helper.py").read_text()
        sample_files[".tools/screenshot_helper.py"] = helper_script

    sample = Sample(
        id="shinygen/generate",
        input=[
            ChatMessageSystem(content=sys_prompt),
            ChatMessageUser(content=full_user_prompt),
        ],
        target=artifact,
        metadata={
            "framework": framework_key,
            "primary_artifact": artifact,
            "language": fw["language"],
        },
        files=sample_files if sample_files else None,
        sandbox=("docker", str(docker_context_dir / compose_file)),
    )

    dataset = MemoryDataset(samples=[sample])

    # Select solver
    if agent == "claude_code":
        solver = claude_code(
            cwd=SANDBOX_WORK_DIR,
            attempts=1,
            skills=resolved_skills or None,
        )
    else:
        solver = codex_cli(
            cwd=SANDBOX_WORK_DIR,
            attempts=1,
            skills=resolved_skills or None,
            version=CODEX_CLI_VERSION,
            config_overrides=CODEX_CONFIG_OVERRIDES,
            disallowed_tools=CODEX_DISALLOWED_TOOLS,
        )

    time_limit = sandbox_time_limit_for_framework(framework_key)

    return Task(
        dataset=dataset,
        solver=solver,
        scorer=app_created_scorer(screenshot=screenshot),
        sandbox=("docker", str(docker_context_dir / compose_file)),
        time_limit=time_limit,
        working_limit=time_limit,
    )
