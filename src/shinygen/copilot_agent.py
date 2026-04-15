"""
Copilot SDK agent integration for shinygen.

Uses the GitHub Copilot SDK (github-copilot-sdk) as an alternative agent
runtime, routing model calls through GitHub Copilot instead of directly
through Anthropic/OpenAI APIs.

Auth: Set GITHUB_TOKEN, GH_TOKEN, or COPILOT_GITHUB_TOKEN.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CopilotGenerationResult:
    """Result from a Copilot SDK generation run."""

    code: str | None = None
    messages: list[str] = field(default_factory=list)
    error: str | None = None


def _resolve_copilot_model(model_id: str) -> str:
    """Map a shinygen model_id to a Copilot SDK model name.

    The Copilot SDK accepts model names like "gpt-5", "claude-sonnet-4.5",
    etc. We strip the provider prefix from our internal model IDs.
    """
    # Our model IDs look like "anthropic/claude-opus-4-6" or "openai/gpt-5.4"
    # The Copilot SDK wants "claude-opus-4-6" or "gpt-5.4"
    if "/" in model_id:
        return model_id.split("/", 1)[1]
    return model_id


async def _run_copilot_session(
    system_prompt: str,
    user_prompt: str,
    model_name: str,
    work_dir: Path,
    artifact_name: str,
    timeout_seconds: int = 600,
    reasoning_effort: str | None = None,
) -> CopilotGenerationResult:
    """Run a Copilot SDK session to generate a Shiny app.

    Creates a CopilotClient, starts a session with the given model,
    sends the prompts, and waits for the agent to finish. The generated
    app is read from the working directory.
    """
    from copilot import CopilotClient, SubprocessConfig
    from copilot.generated.session_events import (
        AssistantMessageData,
        SessionIdleData,
    )
    from copilot.session import PermissionHandler

    result = CopilotGenerationResult()

    config = SubprocessConfig(
        cwd=str(work_dir),
        log_level="warn",
    )

    try:
        async with CopilotClient(config) as client:
            session_kwargs: dict = {
                "on_permission_request": PermissionHandler.approve_all,
                "model": model_name,
                "system_message": {"type": "text", "content": system_prompt},
                "infinite_sessions": {"enabled": False},
            }

            if reasoning_effort:
                session_kwargs["reasoning_effort"] = reasoning_effort

            async with await client.create_session(**session_kwargs) as session:
                done = asyncio.Event()
                messages: list[str] = []

                def on_event(event):
                    match event.data:
                        case AssistantMessageData() as data:
                            if data.content:
                                messages.append(data.content)
                        case SessionIdleData():
                            done.set()

                session.on(on_event)
                await session.send(user_prompt)

                try:
                    await asyncio.wait_for(done.wait(), timeout=timeout_seconds)
                except asyncio.TimeoutError:
                    result.error = (
                        f"Copilot session timed out after {timeout_seconds}s"
                    )
                    return result

                result.messages = messages

    except Exception as exc:
        result.error = f"Copilot SDK error: {exc}"
        logger.error("Copilot SDK session failed: %s", exc)
        return result

    # Read the generated artifact from the working directory
    artifact_path = work_dir / artifact_name
    if artifact_path.exists():
        code = artifact_path.read_text(encoding="utf-8")
        if code.strip():
            result.code = code
            logger.info(
                "Copilot SDK: Read %d chars from %s", len(code), artifact_name
            )
        else:
            result.error = f"Copilot SDK: {artifact_name} exists but is empty"
    else:
        # Search recursively in case the agent put it in a subdirectory
        found = list(work_dir.rglob(artifact_name))
        if found:
            code = found[0].read_text(encoding="utf-8")
            if code.strip():
                result.code = code
                logger.info(
                    "Copilot SDK: Read %d chars from %s",
                    len(code),
                    found[0],
                )
            else:
                result.error = (
                    f"Copilot SDK: {artifact_name} found but empty at {found[0]}"
                )
        else:
            result.error = (
                f"Copilot SDK: {artifact_name} not found in {work_dir}"
            )
            logger.warning(
                "Copilot SDK: artifact %s not found. Work dir contents: %s",
                artifact_name,
                list(work_dir.iterdir()),
            )

    return result


def run_copilot_generation(
    prompt: str,
    model_id: str,
    framework_key: str,
    data_files: dict[str, str] | None = None,
    screenshot: bool = False,
    reasoning_effort: str | None = None,
) -> tuple[str | None, list[dict[str, object]]]:
    """Run a generation using the Copilot SDK agent.

    This is the synchronous entry point called from iterate.py.
    It sets up a temporary working directory, writes data files,
    runs the async Copilot session, and returns extracted code.

    Returns:
        Tuple of (code_or_none, usage_rows).
        Usage tracking is limited since the Copilot SDK doesn't expose
        detailed token counts in the same way as direct API calls.
    """
    from .config import FRAMEWORKS
    from .prompts import build_system_prompt, build_user_prompt

    fw = FRAMEWORKS[framework_key]
    artifact_name = fw["primary_artifact"]

    sys_prompt = build_system_prompt(
        framework_key,
        list(data_files.keys()) if data_files else None,
        screenshot=screenshot,
    )
    user_prompt = build_user_prompt(prompt, framework_key)
    model_name = _resolve_copilot_model(model_id)

    # Set up temporary working directory with data files
    work_dir = Path(tempfile.mkdtemp(prefix="shinygen_copilot_"))
    if data_files:
        for filename, content in data_files.items():
            file_path = work_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

    logger.info(
        "Starting Copilot SDK generation: model=%s, work_dir=%s",
        model_name,
        work_dir,
    )

    # Run the async session
    result = asyncio.run(
        _run_copilot_session(
            system_prompt=sys_prompt,
            user_prompt=user_prompt,
            model_name=model_name,
            work_dir=work_dir,
            artifact_name=artifact_name,
            reasoning_effort=reasoning_effort,
        )
    )

    if result.error:
        logger.warning("Copilot SDK generation failed: %s", result.error)

    # Build minimal usage rows (Copilot SDK doesn't expose per-token billing)
    usage_rows: list[dict[str, object]] = []
    if result.code is not None:
        usage_rows.append(
            {
                "model": model_name,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
                "cost": None,
                "cost_override": None,
            }
        )

    return result.code, usage_rows
