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
from inspect_ai.tool import bash, text_editor, python, tool, Tool
from inspect_ai.util import sandbox

from .config import (
    OPENCODE_GO_BASE_URL,
    is_lmstudio_model,
    _build_lmstudio_model,
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
_DIRECT_ARTIFACT_ATTEMPTS = 3
_SERVER_VALIDATION_TIMEOUT = 45


_REACT_INSTRUCTIONS_TEMPLATE = (
    "You are a coding agent that builds Shiny dashboards inside a Linux "
    "sandbox. Your working directory is `{cwd}`.\n\n"
    "You have the following tools:\n"
    "  - `bash`: run shell commands in the sandbox.\n"
    "  - `python`: execute Python code snippets to explore data or test logic.\n"
    "  - `text_editor`: view, create, and edit files in the sandbox.\n"
    "  - `validate_app_tool`: starts the generated app and returns server logs.\n"
    "  - `web_browser`: (if available) fetch web pages to check documentation.\n\n"
    "IMPORTANT RULES:\n"
    "- You MUST create the artifact file using `text_editor` before calling "
    "`submit`. Do NOT call `submit` until the file exists.\n"
    "- After creating the file, validate it using the `validate_app_tool` tool. Fix any errors in the logs before submitting.\n"
    "- If `submit` is called but no artifact file exists, you will be told "
    "the submission was incorrect and given another chance.\n"
    "- Do NOT print the full app source as a code block in chat. Write it "
    "to disk with `text_editor` instead. The benchmark only reads the "
    "file on disk.\n"
    "- Keep your prose between tool calls to one short sentence. No plans, "
    "no recaps, no explanations of what you are about to do.\n\n"
    "Workflow:\n"
    "1. Review the dataset context provided in the chat.\n"
    "2. Plan the dashboard structure briefly before editing.\n"
    "3. Create or edit the primary artifact file with `text_editor`.\n"
    "4. Validate by using `validate_app_tool`. Fix any errors.\n"
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
        "OUTPUT CONTRACT (read carefully):\n"
        "- Reply with EXACTLY ONE fenced code block.\n"
        f"- The fence MUST be ```{language.lower()} ... ``` (lowercase "
        "language tag).\n"
        f"- The block MUST contain the FULL contents of `{artifact}`, "
        "ready to run as-is.\n"
        "- NO prose before the opening fence. NO prose after the closing "
        "fence. NO second fence anywhere in the response.\n"
        "- Do NOT include diffs, patches, ellipses, `...`, or "
        "placeholder comments such as `# rest of code`.\n"
        "- Do NOT wrap the answer in extra Markdown headings or quoting.\n\n"
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


def _server_validation_command(*, framework: str, artifact: str, cwd: str) -> str:
    """Return a shell command that starts the app and prints server logs."""
    quoted_cwd = shlex.quote(cwd)
    quoted_artifact = shlex.quote(artifact)
    log_path = "/tmp/shinygen_app_validation.log"

    if framework == "shiny_r":
        start_cmd = (
            f"Rscript -e \"shiny::runApp('{artifact}', port=8000, "
            "launch.browser=FALSE)\""
        )
        process_pattern = "Rscript"
    else:
        start_cmd = f"python3 -m shiny run {quoted_artifact} --port 8000"
        process_pattern = "shiny run"

    return f"""
set +e
cd {quoted_cwd} || exit 1
rm -f {log_path}
({start_cmd}) > {log_path} 2>&1 &
app_pid=$!
sleep 6
if kill -0 "$app_pid" 2>/dev/null; then
  tail -n 120 {log_path} || true
  pkill -f {shlex.quote(process_pattern)} || kill "$app_pid" 2>/dev/null || true
  exit 0
fi
wait "$app_pid"
status=$?
tail -n 120 {log_path} || true
exit "$status"
""".strip()


def _build_direct_repair_prompt(*, artifact: str, validation_output: str) -> str:
    """Build a no-tool repair prompt from server validation output."""
    trimmed = validation_output.strip()
    if len(trimmed) > 8_000:
        trimmed = trimmed[-8_000:]

    return (
        f"The generated `{artifact}` server validation failed. The harness "
        "started the app and captured these server logs:\n\n"
        f"```\n{trimmed}\n```\n\n"
        f"Return a corrected complete `{artifact}` as exactly one fenced code "
        "block. Do not call tools and do not include prose outside the code "
        "block."
    )


def _build_invalid_code_retry_prompt(*, artifact: str, previous_output: str) -> str:
    """Build a no-tool retry prompt when model output was not extractable."""
    trimmed = previous_output.strip()
    if len(trimmed) > 6_000:
        trimmed = trimmed[-6_000:]

    return (
        f"No valid `{artifact}` code block was found in your previous answer. "
        "The benchmark cannot use plans, explanations, diffs, shell commands, "
        "or partial snippets.\n\n"
        "Previous answer excerpt:\n\n"
        f"```\n{trimmed or '(empty response)'}\n```\n\n"
        f"Return the complete contents of `{artifact}` as exactly one fenced "
        "code block. Do not call tools and do not include prose outside the "
        "code block."
    )


async def _validate_artifact_server(
    *,
    cwd: str,
    framework: str,
    artifact: str,
) -> tuple[bool, str]:
    """Start the generated app in the sandbox and return server logs."""
    command = _server_validation_command(framework=framework, artifact=artifact, cwd=cwd)
    try:
        result = await sandbox().exec(
            ["sh", "-lc", command],
            timeout=_SERVER_VALIDATION_TIMEOUT,
        )
    except Exception as exc:
        return False, str(exc)

    stdout = getattr(result, "stdout", "") or getattr(result, "output", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    output = "\n".join(part for part in (stdout, stderr) if part).strip()
    return getattr(result, "returncode", 1) == 0, output


@tool
def validate_app_tool(cwd: str, framework: str, artifact: str) -> Tool:
    """A tool that starts the generated app and captures server logs."""
    async def execute() -> str:
        """
        Start the generated app and capture server logs. Use this to verify that the app
        starts correctly without errors. It will return the startup logs.
        """
        valid, output = await _validate_artifact_server(
            cwd=cwd, framework=framework, artifact=artifact
        )
        if valid:
            return f"Success. App started without errors.\n\nLogs:\n{output}"
        else:
            return f"Error. App failed to start.\n\nLogs:\n{output}"
    return execute



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
    """Direct OpenCode Go solver that writes and validates the artifact.

    OpenCode Go Kimi currently returns repeated provider 500s on the second
    tool-turn when driven through Inspect's ReAct loop. This solver avoids
    provider tool-call state entirely: shinygen gathers a small data preview,
    asks for one complete artifact, writes it, starts the app, and gives the
    model server logs for one no-tool repair attempt if startup fails.
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

        for attempt in range(1, _DIRECT_ARTIFACT_ATTEMPTS + 1):
            state = await generate(state, tool_calls="none")
            code = _extract_direct_artifact_code(
                state.output.completion,
                framework=framework,
                artifact=artifact,
            )
            if not code:
                if attempt < _DIRECT_ARTIFACT_ATTEMPTS:
                    state.messages.append(
                        ChatMessageUser(
                            content=_build_invalid_code_retry_prompt(
                                artifact=artifact,
                                previous_output=state.output.completion,
                            )
                        )
                    )
                continue

            await sandbox().write_file(f"{cwd.rstrip('/')}/{artifact}", code)
            valid, validation_output = await _validate_artifact_server(
                cwd=cwd,
                framework=framework,
                artifact=artifact,
            )
            if valid or attempt >= _DIRECT_ARTIFACT_ATTEMPTS:
                break

            state.messages.append(
                ChatMessageUser(
                    content=_build_direct_repair_prompt(
                        artifact=artifact,
                        validation_output=validation_output,
                    )
                )
            )

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
    framework: str,
    artifact: str,
    web_fetch: bool = True,
    extra_instructions: str | None = None,
) -> Solver:
    """Return an Inspect ``Solver`` driven by the native ``react()`` agent."""
    if is_lmstudio_model(model_id):
        model = _build_lmstudio_model(model_id)
    elif is_opencode_go_model(model_id):
        model = _build_opencode_go_model(model_id)
    else:
        # Allow the native solver to be used for non-OpenCode-Go models too;
        # this keeps the door open for migrating other providers off the
        # mini_swe_agent bridge in future.
        model = get_model(model_id, memoize=False)

    instructions = _REACT_INSTRUCTIONS_TEMPLATE.format(cwd=cwd)
    if extra_instructions and extra_instructions.strip():
        instructions = f"{instructions}\n\n{extra_instructions.strip()}"

    tools = [
        bash(timeout=_TOOL_TIMEOUT),
        python(timeout=_TOOL_TIMEOUT),
        text_editor(timeout=_TOOL_TIMEOUT),
        validate_app_tool(cwd=cwd, framework=framework, artifact=artifact),
    ]

    if web_fetch:
        try:
            from inspect_ai.tool import web_browser
            tools.extend(web_browser())
        except ImportError:
            pass

    agent = react(
        model=model,
        tools=tools,
        prompt=AgentPrompt(instructions=instructions),
        attempts=5,
    )

    @solver
    def react_with_init() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
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
            return await agent(state)
        return solve

    return react_with_init()
