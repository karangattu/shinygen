"""
Native Inspect AI ReAct solver for OpenCode Go models.

This bypasses ``inspect_swe.mini_swe_agent`` (and its litellm/openai-bridge
shim) entirely and instead drives the model via Inspect's own
``react()`` agent with ``bash`` + ``text_editor`` tools running inside
the existing Docker sandbox.

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

Calling Inspect's model API directly avoids all three problems and gives
us native ``ModelUsage`` accounting that flows straight into the existing
``shinygen.pricing`` lookup.
"""

from __future__ import annotations

import os

from inspect_ai.agent import Agent, AgentPrompt, react
from inspect_ai.model import Model, get_model
from inspect_ai.tool import bash, text_editor

from .config import (
    OPENCODE_GO_BASE_URL,
    is_opencode_go_anthropic_model,
    is_opencode_go_model,
    opencode_go_anthropic_model_name,
)

# Default per-tool execution timeout (seconds). Generous because some
# OpenCode Go models like to run package installs / linters between edits.
_TOOL_TIMEOUT = 180


_REACT_INSTRUCTIONS_TEMPLATE = (
    "You are a coding agent that builds Shiny dashboards inside a Linux "
    "sandbox. Your working directory is `{cwd}`.\n\n"
    "You have two tools:\n"
    "  - `bash`: run shell commands in the sandbox.\n"
    "  - `text_editor`: view, create, and edit files in the sandbox.\n\n"
    "Workflow:\n"
    "1. Use `bash` to inspect `{cwd}` (e.g. `ls -la`) and any data files "
    "(e.g. `head -n 5 *.csv`).\n"
    "2. Plan the dashboard structure briefly before editing.\n"
    "3. Create or edit the primary artifact file with `text_editor`.\n"
    "4. Validate by importing or running the app once (e.g. "
    "`python3 -c 'import app'` for Shiny for Python or "
    "`Rscript -e \"source('app.R')\"` for Shiny for R). Fix any errors.\n"
    "5. When the artifact is complete and valid, call the `submit` tool "
    "with a one-line summary. Do not ask the user for confirmation.\n\n"
    "Always prefer surgical edits over rewriting whole files. The system "
    "and user messages already describe the dashboard requirements in "
    "detail — follow them carefully."
)


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
        attempts=1,
    )
    return agent
