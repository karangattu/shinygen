"""
Native Inspect AI solvers for OpenCode Go models.

This bypasses ``inspect_swe.mini_swe_agent`` (and its litellm/openai-bridge
shim) entirely and instead drives the model via Inspect's own
Inspect solvers running inside the existing Docker sandbox.

Why a separate solver?

1. ``mini_swe_agent`` wraps Inspect's model API with
   ``inspect_swe._mini_swe_agent._model_without_responses_api`` which strips
   provider-specific reasoning fields between turns. Moonshot's Kimi models
   (``kimi-k2.5``, ``kimi-k2.6``) **require** ``reasoning_content`` to be
   echoed back inside subsequent assistant tool-call messages or they
   reject the request with HTTP 400.

2. ``mini_swe_agent`` constructs the Anthropic client without letting us
   normalise the base URL, which breaks the OpenCode Go MiniMax models
   (``minimax-m2.5``, ``minimax-m2.7``) — the Anthropic SDK auto-appends
   ``/v1/messages`` and we end up with ``…/v1/v1/messages`` → 404.

3. ``mini_swe_agent`` uses litellm for cost tracking, which does not know
   about OpenCode Go's synthetic provider names and crashes the run before
   the first turn unless ``MSWEA_COST_TRACKING=ignore_errors`` is set.

Calling Inspect's model API directly avoids these bridge problems and gives
us native ``ModelUsage`` accounting that flows straight into the existing
``shinygen.pricing`` lookup. For Kimi specifically, shinygen now uses a
single-turn direct artifact solver because the OpenCode Go provider returns
repeated 500s on the second tool-turn.
"""

from __future__ import annotations

import os
import shlex

from inspect_ai.agent import Agent, AgentPrompt, react
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, Model, get_model
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import bash, text_editor
from inspect_ai.util import sandbox

from .config import (
    OPENCODE_GO_BASE_URL,
    is_opencode_go_anthropic_model,
    is_opencode_go_model,
    opencode_go_anthropic_model_name,
)
from .extract import find_app_code_in_text
from .validation import validate_framework_artifact

# Default per-tool execution timeout (seconds). Generous because some
# OpenCode Go models like to run package installs / linters between edits.
_TOOL_TIMEOUT = 180
_DATA_CONTEXT_CHAR_LIMIT = 12_000


_REACT_INSTRUCTIONS_TEMPLATE = (
    "You are a coding agent that builds Shiny dashboards inside a Linux "
    "sandbox. Your working directory is `{cwd}`.\n\n"
    "You have two tools:\n"
    "  - `bash`: run shell commands in the sandbox.\n"
    "  - `text_editor`: view, create, and edit files in the sandbox.\n\n"
    "IMPORTANT RULES:\n"
    "- You MUST create the artifact file using `text_editor` before calling "
    "`submit`. Do NOT call `submit` until the file exists.\n"
    "- After creating the file, validate it (e.g. `python3 -c 'import app'` "
    "for Shiny for Python or `Rscript -e \"source('app.R')\"` for Shiny for "
    "R) and fix any errors before submitting.\n"
    "- If `submit` is called but no artifact file exists, you will be told "
    "the submission was incorrect and given another chance.\n\n"
    "Workflow:\n"
    "1. Use `bash` to inspect `{cwd}` (e.g. `ls -la`) and any data files "
    "(e.g. `head -n 5 *.csv`).\n"
    "2. Plan the dashboard structure briefly before editing.\n"
    "3. Create or edit the primary artifact file with `text_editor`.\n"
    "4. Validate by importing or running the app once. Fix any errors.\n"
    "5. When the artifact is complete and valid, call the `submit` tool "
    "with a one-line summary. Do not ask the user for confirmation.\n\n"
    "Always prefer surgical edits over rewriting whole files. The system "
    "and user messages already describe the dashboard requirements in "
    "detail — follow them carefully."
)


def _build_direct_artifact_instructions(
    *,
    framework: str,
    artifact: str,
    cwd: str,
    extra_instructions: str | None = None,
) -> str:
    """Build the no-tool prompt used for OpenCode Go artifact generation."""
    if framework == "shiny_r":
        language = "R"
        framework_label = "Shiny for R"
    else:
        language = "Python"
        framework_label = "Shiny for Python"

    instructions = (
        "You are generating a complete Shiny dashboard artifact for an "
        "automated benchmark.\n\n"
        f"Target file: `{cwd.rstrip('/')}/{artifact}`\n"
        f"Framework: {framework_label}\n"
        f"Language: {language}\n\n"
        "Do not call tools, do not ask follow-up questions, and do not describe "
        "a plan. The harness will write your answer to the target file.\n\n"
        "Return exactly one fenced code block containing the full contents of "
        f"`{artifact}`. Do not include prose outside the code block.\n\n"
        "The code must be complete, runnable, and robust to the provided CSV "
        "data. Prefer a working dashboard with clear KPIs, charts, filters, "
        "and a table over a complex app that may fail at startup."
    )

    if extra_instructions and extra_instructions.strip():
        instructions = f"{instructions}\n\nAdditional guidance:\n{extra_instructions.strip()}"

    return instructions


def _extract_direct_artifact_code(
    text: str,
    *,
    framework: str,
    artifact: str,
) -> str | None:
    """Extract and validate direct model output for the target artifact."""
    code = find_app_code_in_text(text, artifact)
    if not code:
        return None

    valid, _reason = validate_framework_artifact(framework, artifact, code)
    return code if valid else None


async def _collect_sandbox_data_context(cwd: str) -> str:
    """Collect a compact, host-driven data preview without model tool calls."""
    quoted_cwd = shlex.quote(cwd)
    command = f"""
set +e
cd {quoted_cwd} || exit 0
echo "Files in working directory:"
find . -maxdepth 1 -type f -printf '%f\\n' | sort
for f in *.csv; do
  [ -f "$f" ] || continue
  echo
  echo "### $f"
  python3 - "$f" <<'PY' 2>/dev/null || head -n 8 "$f"
import csv
import sys
from pathlib import Path

path = Path(sys.argv[1])
with path.open(newline="", encoding="utf-8", errors="replace") as handle:
    reader = csv.reader(handle)
    rows = []
    for index, row in enumerate(reader):
        if index < 8:
            rows.append(row)
        elif index > 2000:
            break
    handle.seek(0)
    total_rows = max(sum(1 for _ in handle) - 1, 0)

if rows:
    print("columns: " + ", ".join(rows[0]))
    print(f"data_rows: {{total_rows}}")
    print("preview_csv:")
    for row in rows:
        print(",".join(row))
PY
done
""".strip()

    try:
        result = await sandbox().exec(["sh", "-lc", command])
    except Exception:
        return ""

    output = (result.stdout or "").strip()
    if len(output) > _DATA_CONTEXT_CHAR_LIMIT:
        return output[:_DATA_CONTEXT_CHAR_LIMIT] + "\n... [truncated]"
    return output


@solver
def native_direct_artifact_solver(
    *,
    cwd: str,
    framework: str,
    artifact: str,
    extra_instructions: str | None = None,
) -> Solver:
    """Single-turn OpenCode Go solver that writes the generated artifact.

    OpenCode Go Kimi currently returns repeated provider 500s on the second
    tool-turn when driven through Inspect's ReAct loop. This solver avoids
    provider tool-call state entirely: shinygen gathers a small data preview,
    asks for one complete artifact, extracts it, and writes it into the
    sandbox for the normal scorer.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        instructions = _build_direct_artifact_instructions(
            framework=framework,
            artifact=artifact,
            cwd=cwd,
            extra_instructions=extra_instructions,
        )
        state.messages.insert(0, ChatMessageSystem(content=instructions))

        data_context = await _collect_sandbox_data_context(cwd)
        if data_context:
            state.messages.append(
                ChatMessageUser(
                    content=(
                        "Dataset context gathered from the sandbox. Use these "
                        "columns and preview rows when writing the app:\n\n"
                        f"{data_context}"
                    )
                )
            )

        state = await generate(state, tool_calls="none")
        code = _extract_direct_artifact_code(
            state.output.completion,
            framework=framework,
            artifact=artifact,
        )
        if code:
            await sandbox().write_file(f"{cwd.rstrip('/')}/{artifact}", code)

        return state

    return solve


def _build_opencode_go_model(model_id: str) -> Model:
    """Construct an Inspect ``Model`` for an OpenCode Go model.

    Configures the correct base URL and API key without going through the
    mini-swe-agent bridge. Preserves provider-specific fields such as
    Kimi's ``reasoning_content`` across turns and avoids the Anthropic
    SDK's ``/v1`` double-prefix issue for MiniMax models.
    """
    api_key = os.environ.get("OPENCODE_GO_API_KEY", "sk-none")
    base = os.environ.get(
        "OPENCODE_GO_BASE_URL", OPENCODE_GO_BASE_URL
    ).rstrip("/")

    if is_opencode_go_anthropic_model(model_id):
        # The Anthropic SDK appends "/v1/messages" to ``base_url``; strip
        # the trailing "/v1" so we don't end up with "/v1/v1/messages".
        if base.endswith("/v1"):
            base = base[: -len("/v1")]
        return get_model(
            f"anthropic/{opencode_go_anthropic_model_name(model_id)}",
            base_url=base,
            api_key=api_key,
            memoize=False,
        )

    # OpenAI-compatible: the model_id already looks like
    # "openai-api/opencode-go/<name>" and Inspect's openai-api provider
    # picks up OPENCODE_GO_API_KEY / OPENCODE_GO_BASE_URL from the env.
    return get_model(model_id, memoize=False)


def native_react_solver(
    *,
    model_id: str,
    cwd: str,
    extra_instructions: str | None = None,
) -> Agent:
    """Return an Inspect ``Agent`` driven by the native ``react()`` agent.

    Args:
        model_id: Resolved Inspect model ID (e.g.
            ``"openai-api/opencode-go/mimo-v2.5"`` or
            ``"anthropic/opencode-go/minimax-m2.5"``).
        cwd: Working directory inside the sandbox.
        extra_instructions: Optional text appended to the react agent's
            system instructions (used to inject the framework skill
            guidance when ``use_skills=True``).
    """
    if is_opencode_go_model(model_id):
        model = _build_opencode_go_model(model_id)
    else:
        # Allow the native solver to be used for non-OpenCode-Go models too;
        # this keeps the door open for migrating other providers off the
        # mini_swe_agent bridge in future.
        model = get_model(model_id, memoize=False)

    instructions = _REACT_INSTRUCTIONS_TEMPLATE.format(cwd=cwd)
    if extra_instructions and extra_instructions.strip():
        instructions = f"{instructions}\n\n{extra_instructions.strip()}"

    agent = react(
        model=model,
        tools=[
            bash(timeout=_TOOL_TIMEOUT),
            text_editor(timeout=_TOOL_TIMEOUT),
        ],
        prompt=AgentPrompt(instructions=instructions),
        attempts=3,
    )
    return agent
