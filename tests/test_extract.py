"""Tests for shinygen.extract"""

from shinygen.extract import (
    find_app_code_in_messages,
    find_app_code_in_text,
    strip_line_numbers,
)


class TestStripLineNumbers:
    def test_numbered_lines(self):
        text = "     1\tfrom shiny import App\n     2\timport pandas"
        result = strip_line_numbers(text)
        assert "from shiny import App" in result
        assert "import pandas" in result

    def test_plain_text_unchanged(self):
        text = "from shiny import App\nimport pandas"
        assert strip_line_numbers(text) == text


class TestFindAppCodeInText:
    def test_python_code_block(self):
        text = """Here is the app:

```python
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
```

That should work!
"""
        result = find_app_code_in_text(text, "app.py")
        assert result is not None
        assert "from shiny" in result
        assert "App(" in result

    def test_r_code_block(self):
        text = """```r
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
```"""
        result = find_app_code_in_text(text, "app.R")
        assert result is not None
        assert "library(shiny)" in result

    def test_no_app_code(self):
        text = "This is just a regular paragraph with no code."
        result = find_app_code_in_text(text, "app.py")
        assert result is None


class TestFindAppCodeInMessages:
    def test_file_write_tool_call(self):
        messages = [
            {
                "role": "assistant",
                "content": [
                    {
                        "name": "write_file",
                        "input": {
                            "file_path": "/home/user/project/app.py",
                            "content": "from shiny import App, ui\napp = App(ui.page_fluid(), lambda i, o, s: None)",
                        },
                    }
                ],
            }
        ]
        result = find_app_code_in_messages(messages, "app.py")
        assert result is not None
        assert "from shiny" in result

    def test_no_relevant_messages(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = find_app_code_in_messages(messages, "app.py")
        assert result is None
