"""Tests for shinygen.validation"""

from shinygen.validation import validate_framework_artifact


class TestPythonValidation:
    def test_valid_shiny_app(self):
        code = """
from shiny import App, ui, render

app_ui = ui.page_sidebar(
    ui.sidebar(ui.input_slider("n", "N", 1, 100, 50)),
    ui.output_text("result"),
)

def server(input, output, session):
    @render.text
    def result():
        return str(input.n())

app = App(app_ui, server)
"""
        valid, reason = validate_framework_artifact(
            "shiny_python", "app.py", code
        )
        assert valid, f"Expected valid, got: {reason}"

    def test_invalid_syntax(self):
        code = "def broken(:\n  pass"
        valid, reason = validate_framework_artifact("shiny_python", "app.py", code)
        assert not valid
        assert "syntax" in reason.lower() or "parse" in reason.lower()

    def test_no_shiny_imports(self):
        code = """
import pandas as pd
df = pd.DataFrame({"a": [1, 2, 3]})
print(df)
"""
        valid, reason = validate_framework_artifact("shiny_python", "app.py", code)
        assert not valid

    def test_streamlit_rejected(self):
        code = """
import streamlit as st
st.title("Hello")
"""
        valid, reason = validate_framework_artifact("shiny_python", "app.py", code)
        assert not valid

    def test_express_api(self):
        code = """
from shiny.express import input, render, ui

ui.page_opts(title="My App")

@render.text
def txt():
    return f"n = {input.n()}"
"""
        valid, reason = validate_framework_artifact(
            "shiny_python", "app.py", code
        )
        assert valid, f"Expected valid, got: {reason}"

    def test_rejects_plotly_figure_in_render_plot(self):
        code = """
import plotly.express as px
from shiny import App, render, ui

app_ui = ui.page_sidebar(ui.output_plot("chart"))


def server(input, output, session):
    @output
    @render.plot
    def chart():
        return px.scatter(x=[1, 2, 3], y=[3, 1, 2])


app = App(app_ui, server)
"""
        valid, reason = validate_framework_artifact(
            "shiny_python", "app.py", code
        )
        assert not valid
        assert "plotly" in reason.lower()
        assert "render.plot" in reason.lower()

    def test_rejects_output_plot_with_render_plotly(self):
        code = """
import plotly.express as px
from shiny import App, ui
from shinywidgets import render_plotly

app_ui = ui.page_sidebar(ui.output_plot("chart"))


def server(input, output, session):
    @render_plotly
    def chart():
        return px.scatter(x=[1, 2, 3], y=[3, 1, 2])


app = App(app_ui, server)
"""
        valid, reason = validate_framework_artifact(
            "shiny_python", "app.py", code
        )
        assert not valid
        assert "output_widget" in reason

    def test_allows_plotly_with_shinywidgets_renderers(self):
        code = """
import plotly.express as px
from shiny import App, ui
from shinywidgets import output_widget, render_plotly

app_ui = ui.page_sidebar(output_widget("chart"))


def server(input, output, session):
    @render_plotly
    def chart():
        return px.scatter(x=[1, 2, 3], y=[3, 1, 2])


app = App(app_ui, server)
"""
        valid, reason = validate_framework_artifact(
            "shiny_python", "app.py", code
        )
        assert valid, f"Expected valid, got: {reason}"


class TestRValidation:
    def test_valid_r_app(self):
        code = """
library(shiny)
library(bslib)

ui <- page_sidebar(
  sidebar = sidebar(sliderInput("n", "N", 1, 100, 50)),
  textOutput("result")
)

server <- function(input, output, session) {
  output$result <- renderText({ input$n })
}

shinyApp(ui, server)
"""
        valid, reason = validate_framework_artifact("shiny_r", "app.R", code)
        assert valid, f"Expected valid, got: {reason}"

    def test_missing_library(self):
        code = """
x <- 1 + 2
print(x)
"""
        valid, reason = validate_framework_artifact("shiny_r", "app.R", code)
        assert not valid


class TestUnknownFramework:
    def test_unknown_framework_returns_failure(self):
        valid, reason = validate_framework_artifact("unknown_framework", "app.py", "code")
        assert not valid
        assert "unknown framework" in reason.lower()
        assert "unknown_framework" in reason

    def test_typo_in_framework_name_returns_failure(self):
        valid, reason = validate_framework_artifact("shiny_pyhton", "app.py", "code")
        assert not valid
        assert "unknown framework" in reason.lower()
