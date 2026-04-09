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
        valid, reason = validate_framework_artifact("shiny_python", "app.py", code)
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
        valid, reason = validate_framework_artifact("shiny_python", "app.py", code)
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
