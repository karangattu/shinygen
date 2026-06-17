"""Tests for the OpenCode Go native solver helpers."""

from __future__ import annotations

from shinygen.native_solver import (
    _build_direct_artifact_instructions,
    _build_invalid_code_retry_prompt,
    _build_direct_repair_prompt,
    _extract_direct_artifact_code,
    _server_validation_command,
)


def test_extract_direct_artifact_code_accepts_py_fence():
    text = """Here is the file:

```py
from shiny import App, ui, render

app_ui = ui.page_fluid(ui.output_text("result"))

def server(input, output, session):
    @render.text
    def result():
        return "ok"

app = App(app_ui, server)
```
"""

    code = _extract_direct_artifact_code(
        text,
        framework="shiny_python",
        artifact="app.py",
    )

    assert code is not None
    assert code.startswith("from shiny import")
    assert "app = App(app_ui, server)" in code


def test_direct_artifact_instructions_disable_tool_use():
    instructions = _build_direct_artifact_instructions(
        framework="shiny_python",
        artifact="app.py",
        cwd="/home/user/project",
        extra_instructions="Prefer ui.card layouts.",
    )

    assert "Do not call tools" in instructions
    assert "EXACTLY ONE fenced code block" in instructions
    assert "app.py" in instructions
    assert "Prefer ui.card layouts." in instructions


def test_server_validation_command_captures_python_logs():
    command = _server_validation_command(
        framework="shiny_python",
        artifact="app.py",
        cwd="/home/user/project",
    )

    assert "python3 -m shiny run app.py --port 8000" in command
    assert "/tmp/shinygen_app_validation.log" in command
    assert "tail -n 120 /tmp/shinygen_app_validation.log" in command


def test_direct_repair_prompt_includes_server_logs():
    prompt = _build_direct_repair_prompt(
        artifact="app.py",
        validation_output="Traceback: missing column",
    )

    assert "server validation failed" in prompt
    assert "Traceback: missing column" in prompt
    assert "exactly one fenced code block" in prompt


def test_invalid_code_retry_prompt_shows_previous_model_output():
    prompt = _build_invalid_code_retry_prompt(
        artifact="app.py",
        previous_output="I cannot create files, but here is a plan...",
    )

    assert "No valid `app.py` code block was found" in prompt
    assert "I cannot create files" in prompt
    assert "exactly one fenced code block" in prompt


def test_web_browser_tools_are_flattened_into_tools_list():
    from unittest.mock import patch, MagicMock

    fake_tool_a = MagicMock(name="tool_a")
    fake_tool_b = MagicMock(name="tool_b")

    with patch("shinygen.native_solver.react") as mock_react, \
         patch("shinygen.native_solver.get_model") as mock_get_model, \
         patch("inspect_ai.tool.web_browser", return_value=[fake_tool_a, fake_tool_b]):
        mock_get_model.return_value = MagicMock()
        mock_react.return_value = MagicMock()

        from shinygen.native_solver import native_react_solver
        native_react_solver(
            model_id="openai-api/opencode-go/glm-5.2",
            cwd="/home/user/project",
            framework="shiny_python",
            artifact="app.py",
            web_fetch=True,
        )

        called_tools = mock_react.call_args.kwargs["tools"]
        assert fake_tool_a in called_tools
        assert fake_tool_b in called_tools
        for t in called_tools:
            assert not isinstance(t, list), "web_browser tools should be flattened, not nested"
