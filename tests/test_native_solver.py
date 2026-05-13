"""Tests for the OpenCode Go native solver helpers."""

from __future__ import annotations

from shinygen.native_solver import (
    _build_direct_artifact_instructions,
    _extract_direct_artifact_code,
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
    assert "exactly one fenced code block" in instructions
    assert "app.py" in instructions
    assert "Prefer ui.card layouts." in instructions
