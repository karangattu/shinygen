"""Tests for shinygen.extract"""

import json
import struct
import zlib
from pathlib import Path

import zstandard as zstd

from shinygen.extract import (
    extract_from_log,
    find_app_code_in_messages,
    find_app_code_in_text,
    strip_line_numbers,
)


def _write_zstd_zip_member(zip_path: Path, member_name: str, payload: bytes) -> None:
    """Write a minimal ZIP archive containing one zstd-compressed member."""
    compressed = zstd.ZstdCompressor().compress(payload)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    name_bytes = member_name.encode("utf-8")

    local_header = struct.pack(
        "<IHHHHHIIIHH",
        0x04034B50,
        20,
        0,
        93,
        0,
        0,
        crc,
        len(compressed),
        len(payload),
        len(name_bytes),
        0,
    )

    central_header = struct.pack(
        "<IHHHHHHIIIHHHHHII",
        0x02014B50,
        20,
        20,
        0,
        93,
        0,
        0,
        crc,
        len(compressed),
        len(payload),
        len(name_bytes),
        0,
        0,
        0,
        0,
        0,
        0,
    )

    end_record = struct.pack(
        "<IHHHHIIH",
        0x06054B50,
        0,
        0,
        1,
        1,
        len(central_header) + len(name_bytes),
        len(local_header) + len(name_bytes) + len(compressed),
        0,
    )

    zip_path.write_bytes(
        local_header
        + name_bytes
        + compressed
        + central_header
        + name_bytes
        + end_record
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

    def test_shell_heredoc_write(self):
        messages = [
            {
                "role": "assistant",
                "content": (
                    "exec\n"
                    "/bin/bash -lc \"cat > /home/user/project/app.R <<'EOF'\n"
                    "library(shiny)\n"
                    "library(bslib)\n\n"
                    "ui <- page_sidebar(\n"
                    "  sidebar = sidebar(),\n"
                    "  textOutput('result')\n"
                    ")\n\n"
                    "server <- function(input, output, session) {\n"
                    "  output$result <- renderText('ok')\n"
                    "}\n\n"
                    "shinyApp(ui, server)\n"
                    "EOF\""
                ),
            }
        ]

        result = find_app_code_in_messages(messages, "app.R")
        assert result is not None
        assert "library(shiny)" in result
        assert "shinyApp(ui, server)" in result

    def test_shell_heredoc_in_tool_call_arguments(self):
        messages = [
            {
                "role": "assistant",
                "content": [],
                "tool_calls": [
                    {
                        "id": "call_123",
                        "function": "exec_command",
                        "arguments": {
                            "cmd": (
                                "cat > /home/user/project/app.R <<'EOF'\n"
                                "library(shiny)\n"
                                "library(bslib)\n\n"
                                "ui <- page_sidebar(\n"
                                "  sidebar = sidebar(),\n"
                                "  textOutput('result')\n"
                                ")\n\n"
                                "server <- function(input, output, session) {\n"
                                "  output$result <- renderText('ok')\n"
                                "}\n\n"
                                "shinyApp(ui, server)\n"
                                "EOF\n"
                                "Rscript -e \"parse('app.R')\""
                            )
                        },
                    }
                ],
            }
        ]

        result = find_app_code_in_messages(messages, "app.R")
        assert result is not None
        assert result.startswith("library(shiny)")
        assert "shinyApp(ui, server)" in result

    def test_no_relevant_messages(self):
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        result = find_app_code_in_messages(messages, "app.py")
        assert result is None


class TestExtractFromLog:
    def test_reads_zstd_eval_and_recovers_heredoc_artifact(self, tmp_path):
        sample = {
            "id": "shinygen/generate",
            "metadata": {
                "framework": "shiny_r",
                "primary_artifact": "app.R",
            },
            "messages": [
                {
                    "role": "assistant",
                    "content": [],
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "function": "exec_command",
                            "arguments": {
                                "cmd": (
                                    "cat > /home/user/project/app.R <<'EOF'\n"
                                    "library(shiny)\n"
                                    "library(bslib)\n\n"
                                    "ui <- page_sidebar(\n"
                                    "  sidebar = sidebar(),\n"
                                    "  textOutput('result')\n"
                                    ")\n\n"
                                    "server <- function(input, output, session) {\n"
                                    "  output$result <- renderText('ok')\n"
                                    "}\n\n"
                                    "shinyApp(ui, server)\n"
                                    "EOF\n"
                                    "Rscript -e \"parse('app.R')\""
                                )
                            },
                        }
                    ],
                }
            ],
        }

        log_path = tmp_path / "sample.eval"
        _write_zstd_zip_member(
            log_path,
            "samples/shinygen/generate_epoch_1.json",
            json.dumps(sample).encode("utf-8"),
        )

        extracted = extract_from_log(log_path)

        assert extracted["shinygen/generate"].startswith("library(shiny)")
        assert "shinyApp(ui, server)" in extracted["shinygen/generate"]
