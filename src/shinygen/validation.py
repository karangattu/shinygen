"""
Framework artifact validation — checks that generated code is
valid for the target framework (correct language, syntax, markers).
"""

from __future__ import annotations

import ast


def _attribute_chain(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        parts.reverse()
        return tuple(parts)
    return ()


def _decorator_chain(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Name):
        return (node.id,)
    return _attribute_chain(node)


def _target_names(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in node.elts:
            names.update(_target_names(element))
        return names
    return set()


def _collect_plotly_symbols(tree: ast.AST) -> dict[str, set[str]]:
    symbols: dict[str, set[str]] = {
        "plotly_roots": set(),
        "express_aliases": set(),
        "graph_aliases": set(),
        "express_functions": set(),
        "figure_names": set(),
        "subplot_names": set(),
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "plotly":
                    symbols["plotly_roots"].add(alias.asname or "plotly")
                elif alias.name == "plotly.express":
                    if alias.asname:
                        symbols["express_aliases"].add(alias.asname)
                    else:
                        symbols["plotly_roots"].add("plotly")
                elif alias.name in {
                    "plotly.graph_objects",
                    "plotly.graph_objs",
                }:
                    if alias.asname:
                        symbols["graph_aliases"].add(alias.asname)
                    else:
                        symbols["plotly_roots"].add("plotly")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "plotly":
                for alias in node.names:
                    if alias.name == "express":
                        symbols["express_aliases"].add(
                            alias.asname or alias.name
                        )
                    elif alias.name in {"graph_objects", "graph_objs"}:
                        symbols["graph_aliases"].add(
                            alias.asname or alias.name
                        )
            elif node.module == "plotly.express":
                for alias in node.names:
                    symbols["express_functions"].add(
                        alias.asname or alias.name
                    )
            elif node.module in {"plotly.graph_objects", "plotly.graph_objs"}:
                for alias in node.names:
                    if alias.name == "Figure":
                        symbols["figure_names"].add(alias.asname or alias.name)
            elif node.module == "plotly.subplots":
                for alias in node.names:
                    if alias.name == "make_subplots":
                        symbols["subplot_names"].add(
                            alias.asname or alias.name
                        )

    return symbols


def _expr_is_plotly_figure(
    expr: ast.AST | None,
    *,
    symbols: dict[str, set[str]],
    plotly_helpers: set[str],
    plotly_vars: set[str],
) -> bool:
    if expr is None:
        return False

    if isinstance(expr, ast.Name):
        return expr.id in plotly_vars

    if isinstance(expr, ast.IfExp):
        return _expr_is_plotly_figure(
            expr.body,
            symbols=symbols,
            plotly_helpers=plotly_helpers,
            plotly_vars=plotly_vars,
        ) or _expr_is_plotly_figure(
            expr.orelse,
            symbols=symbols,
            plotly_helpers=plotly_helpers,
            plotly_vars=plotly_vars,
        )

    if not isinstance(expr, ast.Call):
        return False

    chain = _attribute_chain(expr.func)
    if chain:
        root = chain[0]
        if root in symbols["express_aliases"]:
            return True
        if (
            root in symbols["plotly_roots"]
            and len(chain) >= 2
            and chain[1] == "express"
        ):
            return True
        if root in symbols["graph_aliases"] and chain[-1:] == ("Figure",):
            return True
        if (
            root in symbols["plotly_roots"]
            and len(chain) >= 3
            and chain[1] in {"graph_objects", "graph_objs"}
            and chain[2] == "Figure"
        ):
            return True
        if _expr_is_plotly_figure(
            getattr(expr.func, "value", None),
            symbols=symbols,
            plotly_helpers=plotly_helpers,
            plotly_vars=plotly_vars,
        ):
            return True

    if isinstance(expr.func, ast.Name):
        return expr.func.id in (
            symbols["express_functions"]
            | symbols["figure_names"]
            | symbols["subplot_names"]
            | plotly_helpers
        )

    return False


def _function_returns_plotly_figure(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    symbols: dict[str, set[str]],
    plotly_helpers: set[str],
) -> bool:
    plotly_vars: set[str] = set()

    for node in ast.walk(function):
        value: ast.AST | None = None
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            value = node.value
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = [node.target]
        elif isinstance(node, ast.NamedExpr):
            value = node.value
            targets = [node.target]

        if value is None or not targets:
            continue

        if _expr_is_plotly_figure(
            value,
            symbols=symbols,
            plotly_helpers=plotly_helpers,
            plotly_vars=plotly_vars,
        ):
            for target in targets:
                plotly_vars.update(_target_names(target))

    for node in ast.walk(function):
        if isinstance(node, ast.Return) and _expr_is_plotly_figure(
            node.value,
            symbols=symbols,
            plotly_helpers=plotly_helpers,
            plotly_vars=plotly_vars,
        ):
            return True

    return False


def _has_plotly_render_plot_mismatch(tree: ast.AST) -> bool:
    symbols = _collect_plotly_symbols(tree)
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    plotly_helpers: set[str] = set()
    changed = True
    while changed:
        changed = False
        for function in functions:
            if function.name in plotly_helpers:
                continue
            if _function_returns_plotly_figure(
                function,
                symbols=symbols,
                plotly_helpers=plotly_helpers,
            ):
                plotly_helpers.add(function.name)
                changed = True

    plotly_renderers: set[str] = set()
    output_plot_ids: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = {
                _decorator_chain(decorator)
                for decorator in node.decorator_list
            }
            if (
                ("render", "plot") in decorators
                and _function_returns_plotly_figure(
                    node,
                    symbols=symbols,
                    plotly_helpers=plotly_helpers,
                )
            ):
                return True
            if any(
                decorator
                and decorator[-1] in {"render_plotly", "render_widget"}
                for decorator in decorators
            ):
                plotly_renderers.add(node.name)
        elif isinstance(node, ast.Call):
            chain = _attribute_chain(node.func)
            if not chain and isinstance(node.func, ast.Name):
                chain = (node.func.id,)
            if chain and chain[-1] == "output_plot" and node.args:
                first_arg = node.args[0]
                if (
                    isinstance(first_arg, ast.Constant)
                    and isinstance(first_arg.value, str)
                ):
                    output_plot_ids.add(first_arg.value)

    return bool(plotly_renderers & output_plot_ids)


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
            "Streamlit": (
                "import streamlit" in lower
                or "streamlit run app.py" in lower
            ),
            "Dash": "import dash" in lower or "from dash" in lower,
            "Gradio": (
                "import gradio" in lower or "import gradio as gr" in lower
            ),
            "Flask": "from flask import" in lower or "import flask" in lower,
            "FastAPI": (
                "from fastapi import" in lower or "import fastapi" in lower
            ),
        }
        for name, present in banned_frameworks.items():
            if present:
                return False, f"contains {name} content"

        # Python syntax check
        try:
            ast.parse(content)
        except SyntaxError:
            return False, "invalid Python syntax"

        tree = ast.parse(content)

        if _has_plotly_render_plot_mismatch(tree):
            return (
                False,
                "Plotly figures in Shiny for Python must use shinywidgets "
                "output_widget() with render_plotly()/render_widget(), not "
                "@render.plot or ui.output_plot()",
            )

        # Require Shiny markers
        python_markers: tuple[str, ...] = (
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
        if not any(marker in lower for marker in python_markers):
            return False, "missing Shiny for Python markers"

        return True, "valid Shiny for Python artifact"

    if framework == "shiny_r":
        if artifact_name != "app.R":
            return False, "expected app.R for Shiny for R"

        # Check for Python content
        if "import streamlit" in lower or "from shiny import" in lower:
            return False, "contains Python content"

        # Require R Shiny markers
        r_markers: tuple[str, ...] = (
            "library(shiny)",
            "shiny::",
            "shinyapp(",
            "page_sidebar(",
            "page_navbar(",
            "value_box(",
        )
        if not any(marker in lower for marker in r_markers):
            return False, "missing Shiny for R markers"

        return True, "valid Shiny for R artifact"

    return (
        False,
        f"unknown framework {framework!r}; expected 'shiny_python' or 'shiny_r'",
    )
