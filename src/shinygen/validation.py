"""
Framework artifact validation — checks that generated code is
valid for the target framework (correct language, syntax, markers).
"""

from __future__ import annotations

import ast


def validate_framework_artifact(
    framework: str,
    artifact_name: str,
    text: str,
) -> tuple[bool, str]:
    """Validate that generated code matches the expected framework.

    Args:
        framework: "shiny_python" or "shiny_r"
        artifact_name: Expected filename ("app.py" or "app.R")
        text: The generated source code.

    Returns:
        (valid, reason) tuple.
    """
    content = text.strip()
    lower = content.lower()

    if framework == "shiny_python":
        if artifact_name != "app.py":
            return False, "expected app.py for Shiny for Python"

        # Check for R code leakage
        if "library(shiny)" in lower or "shinyapp(" in lower:
            return False, "contains R Shiny content"

        # Check for banned frameworks
        banned_frameworks = {
            "Streamlit": "import streamlit" in lower or "streamlit run app.py" in lower,
            "Dash": "import dash" in lower or "from dash" in lower,
            "Gradio": "import gradio" in lower or "import gradio as gr" in lower,
            "Flask": "from flask import" in lower or "import flask" in lower,
            "FastAPI": "from fastapi import" in lower or "import fastapi" in lower,
        }
        for name, present in banned_frameworks.items():
            if present:
                return False, f"contains {name} content"

        # Python syntax check
        try:
            ast.parse(content)
        except SyntaxError:
            return False, "invalid Python syntax"

        # Require Shiny markers
        shiny_markers = (
            "from shiny",
            "import shiny",
            "from shiny.express",
            "app = app(",
            " app(",
            "app(",
            "page_sidebar",
            "page_navbar",
            "value_box",
        )
        if not any(marker in lower for marker in shiny_markers):
            return False, "missing Shiny for Python markers"

        return True, "valid Shiny for Python artifact"

    if framework == "shiny_r":
        if artifact_name != "app.R":
            return False, "expected app.R for Shiny for R"

        # Check for Python content
        if "import streamlit" in lower or "from shiny import" in lower:
            return False, "contains Python content"

        # Require R Shiny markers
        shiny_markers = (
            "library(shiny)",
            "shiny::",
            "shinyapp(",
            "page_sidebar(",
            "page_navbar(",
            "value_box(",
        )
        if not any(marker in lower for marker in shiny_markers):
            return False, "missing Shiny for R markers"

        return True, "valid Shiny for R artifact"

    return True, "no framework validation available"
