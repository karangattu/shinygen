"""
System and user prompt templates for Shiny app generation.
"""

from __future__ import annotations

import csv
import io

from .config import FRAMEWORKS

_DATASET_CONTEXT_PREVIEW_ROWS = 5
_DATASET_CONTEXT_COL_PREVIEW = 60
_DATASET_CONTEXT_CHAR_LIMIT = 4_000

# ---------------------------------------------------------------------------
# System prompts — enforce strict language/framework rules
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_PYTHON = """\
CRITICAL: You MUST use Python language, NOT R, for this task.

You are building a Shiny for Python dashboard application using the Python \
programming language. This requires Python code in an app.py file.

DO NOT use R. DO NOT create app.R. You must create app.py with Python code.
DO NOT use Streamlit. DO NOT use Dash. DO NOT use Gradio. DO NOT use Flask. \
DO NOT use FastAPI. Do not use any framework other than Shiny for Python.
If you create app.R, write R syntax, or use Streamlit/Dash instead of Shiny, \
the task FAILS.

IMPORTANT WORKFLOW:
1. cd to /home/user/project (this is your working directory)
2. Do not install packages during benchmark runs. The sandbox already includes
   shiny, shinyswatch, shinywidgets, plotly, faicons, pandas, matplotlib,
   seaborn, great-tables, itables, htmltools, folium, pydeck, lonboard,
   geopandas, numpy, and playwright. Jump straight to creating the app.
3. Create the file /home/user/project/app.py with the dashboard code.
   CRITICAL: The file MUST be app.py (NOT app.R). Use Python language syntax.
4. Verify Python syntax: python -c "import ast; \
ast.parse(open('/home/user/project/app.py').read()); print('OK')"

Produce clean, well-structured, production-quality Python code using Python \
language syntax. Use Shiny Express or Core API with modern layout functions \
(page_sidebar, card, value_box, etc.). Import from `shiny` or \
`shiny.express`, and construct a real Shiny app in `app.py`. Remember: Use \
Python, not R, and Shiny, not Streamlit or Dash. The file must be app.py.
"""

SYSTEM_PROMPT_VISUAL_QA = """\

VISUAL SELF-EVALUATION (screenshot mode is ON):
After creating your app, you MUST visually verify it:
1. Start the app: nohup python -m shiny run app.py --port 8000 > /tmp/app.log 2>&1 &
2. Inspect the server log before screenshotting: tail -n 80 /tmp/app.log
3. Once the app is up, take a screenshot with: python /home/user/project/.tools/screenshot_helper.py
    The helper waits 7 seconds before capturing so late-loading dashboard sections can render.
4. If the screenshot is blank or the helper fails, immediately inspect logs again: tail -n 80 /tmp/app.log
5. View the screenshot to check the visual output.
6. Evaluate: layout correctness, chart visibility, text readability, colours, styling.
7. Fix any visual issues, then re-screenshot to confirm.
8. Stop the app when done: pkill -f "shiny run" || true
You may iterate up to 3 times on visual fixes. If the screenshot is blank, \
check /tmp/app.log for errors.
"""

SYSTEM_PROMPT_VISUAL_QA_R = """\

VISUAL SELF-EVALUATION (screenshot mode is ON):
After creating your app, you MUST visually verify it:
1. Start the app: nohup Rscript -e "shiny::runApp('app.R', port=8000, launch.browser=FALSE)" > /tmp/app.log 2>&1 &
2. Inspect the server log before screenshotting: tail -n 80 /tmp/app.log
3. Once the app is up, take a screenshot with: python3 /home/user/project/.tools/screenshot_helper.py
    The helper waits 7 seconds before capturing so late-loading dashboard sections can render.
4. If the screenshot is blank or the helper fails, immediately inspect logs again: tail -n 80 /tmp/app.log
5. View the screenshot to check the visual output.
6. Evaluate: layout correctness, chart visibility, text readability, colours, styling.
7. Fix any visual issues, then re-screenshot to confirm.
8. Stop the app when done: pkill -f "Rscript" || true
You may iterate up to 3 times on visual fixes. If the screenshot is blank, \
check /tmp/app.log for errors.
"""

SYSTEM_PROMPT_R = """\
LANGUAGE REQUIREMENT: R (NOT Python)

You are building a Shiny for R dashboard application.

RULES YOU MUST FOLLOW:
- Write ALL code in the R programming language
- Create a file named app.R (NOT app.py)
- Use library() for imports (NOT import or from ... import)
- Use <- for assignment (NOT = in the Python sense)
- Use function() to define functions
- If you create app.py or write Python code, the task FAILS

WORKFLOW:
1. cd /home/user/project
2. The following R packages are ALREADY INSTALLED — do NOT reinstall them:
   shiny, bslib, bsicons, ggplot2, dplyr, readr, tidyr, stringr,
   lubridate, plotly, DT, leaflet, scales, thematic, htmltools, htmlwidgets.
   Do not install packages during benchmark runs; the sandbox image is
   preloaded. Outside benchmarks, only install packages that are NOT in the list above:
   Run `install.packages(c("package1", "package2"), repos = "https://cloud.r-project.org")` only for packages that are actually missing.
3. Write your R code to /home/user/project/app.R
4. Verify: Rscript -e "parse('app.R'); cat('OK\\n')"

Do NOT spend time running install.packages() for packages that are already \
installed. Jump straight to creating app.R.

Use modern bslib layout (page_sidebar, card, value_box, layout_columns). \
Produce clean, production-quality R code.
"""


# ---------------------------------------------------------------------------
# Build functions
# ---------------------------------------------------------------------------


def build_system_prompt(
    framework_key: str,
    data_files: list[str] | None = None,
    screenshot: bool = False,
) -> str:
    """Build the system prompt for a given framework.

    Args:
        framework_key: "shiny_python" or "shiny_r"
        data_files: Optional list of data file names present in the sandbox.
        screenshot: Whether visual self-evaluation is enabled.
    """
    fw = FRAMEWORKS[framework_key]
    if framework_key == "shiny_r":
        template = SYSTEM_PROMPT_R
    else:
        template = SYSTEM_PROMPT_PYTHON

    prompt = template.format(install_command=fw["install_command"])
    artifact = fw["primary_artifact"]

    prompt += (
        "\n\nEXECUTION PRIORITY:\n"
        "- Do not spend time on package version checks, repeated filesystem "
        "exploration, or broad reconnaissance.\n"
        f"- Read only the files you need, then create /home/user/project/{artifact} early.\n"
        f"- Save a complete, runnable {artifact} as a checkpoint as soon as "
        "you have a minimal working version (basic layout + at least one "
        "input bound to one output that uses the data). You may then keep "
        "refining the same file in further edits — but the file on disk "
        "must always be runnable, never a partial draft.\n"
        f"- If time or output tokens are running low, stop analysis and write "
        f"the best complete working {artifact} immediately. A simple "
        "dashboard that runs is always better than a sophisticated one that "
        "was never written.\n"
    )

    if screenshot:
        if framework_key == "shiny_r":
            prompt += SYSTEM_PROMPT_VISUAL_QA_R
        else:
            prompt += SYSTEM_PROMPT_VISUAL_QA

    if data_files:
        file_list = ", ".join(f"`{f}`" for f in data_files)
        prompt += (
            f"\n\nThe following data file(s) are already present in "
            f"/home/user/project/: {file_list}\n"
        )

    return prompt


def build_dataset_context(data_files: dict[str, str] | None) -> str | None:
    """Build a compact, host-side dataset context block from file contents.

    For each CSV in ``data_files`` (filename -> content), emit the exact
    filename, its columns, row count, and a small preview. This gives the
    agent the real dataset shape without sandbox tool calls and pins it to
    the exact filename so it does not substitute a built-in/example dataset.

    Non-CSV files are listed by name only. Returns ``None`` when
    ``data_files`` is empty.
    """
    if not data_files:
        return None

    blocks: list[str] = []
    for filename, content in data_files.items():
        if not filename.lower().endswith(".csv"):
            blocks.append(
                f"- `{filename}` (non-CSV file, present in /home/user/project/)"
            )
            continue
        if content is None:
            blocks.append(
                f"- `{filename}` (CSV present in /home/user/project/, content unavailable)"
            )
            continue
        try:
            reader = csv.reader(io.StringIO(content))
            rows: list[list[str]] = []
            total = -1
            for index, row in enumerate(reader):
                total = index
                if index < _DATASET_CONTEXT_PREVIEW_ROWS:
                    rows.append(row)
            row_count = max(total, 0)
        except csv.Error:
            blocks.append(
                f"- `{filename}` (CSV present in /home/user/project/, unparseable)"
            )
            continue

        if not rows:
            blocks.append(f"- `{filename}` (empty CSV present in /home/user/project/)")
            continue

        columns = rows[0]
        col_line = ", ".join(col[:_DATASET_CONTEXT_COL_PREVIEW] for col in columns)
        preview_lines: list[str] = []
        for row in rows[1:]:
            padded = row + [""] * (len(columns) - len(row))
            preview_lines.append(
                ", ".join(
                    (val or "")[:_DATASET_CONTEXT_COL_PREVIEW]
                    for val in padded[: len(columns)]
                )
            )
        preview = "\n".join(preview_lines)

        block = (
            f"- `{filename}` — {len(columns)} columns, {row_count} data row(s)\n"
            f"  columns: {col_line}\n"
            f"  preview (first {len(preview_lines)} row(s)):\n{preview}"
        )
        blocks.append(block)

    if not blocks:
        return None

    body = "\n".join(blocks)
    if len(body) > _DATASET_CONTEXT_CHAR_LIMIT:
        body = body[:_DATASET_CONTEXT_CHAR_LIMIT] + "\n... [truncated]"

    return (
        "DATASET(S) YOU MUST USE (already present in /home/user/project/):\n"
        f"{body}\n\n"
        "Read these exact files by the names above. Do NOT substitute "
        "`data.csv`, `economics.csv`, `mtcars`, `penguins`, `iris`, "
        "`diamonds`, or any other built-in or example dataset — use only "
        "the file(s) listed here."
    )


def build_user_prompt(
    user_prompt: str,
    framework_key: str,
    data_files: dict[str, str] | None = None,
) -> str:
    """Build the full user prompt combining the user's request with
    framework-specific instructions.

    Args:
        user_prompt: The user's natural-language description of the app.
        framework_key: "shiny_python" or "shiny_r"
        data_files: Optional mapping of filename -> content for data files
            staged in the sandbox. When provided, a dataset-context block
            naming each CSV and its columns/preview is appended so the agent
            reads the exact file instead of substituting a built-in dataset.
    """
    fw = FRAMEWORKS[framework_key]
    artifact = fw["primary_artifact"]
    language = fw["language"]
    label = fw["label"]

    parts = [
        user_prompt,
        "\n\n",
        f"IMPORTANT: Build this using {label}. "
        f"Write {language} code and save it as `{artifact}`. "
        f"The app must be runnable with: {fw['run_command'].format(port=8000)}",
    ]

    dataset_context = build_dataset_context(data_files)
    if dataset_context:
        parts.append("\n\n")
        parts.append(dataset_context)

    return "".join(parts)


def build_truncation_retry_prompt(
    user_prompt: str,
    framework_key: str,
) -> str:
    """Build a focused retry prompt after an output-token truncation."""
    if "previous attempt hit the output token limit" in user_prompt:
        return user_prompt

    fw = FRAMEWORKS[framework_key]
    artifact = fw["primary_artifact"]
    label = fw["label"]
    language = fw["language"]

    return (
        f"{user_prompt}\n\n"
        "IMPORTANT: The previous attempt hit the output token limit before "
        f"producing {artifact}. Skip ALL exploration this time:\n"
        "- Do NOT read skills files, do NOT inspect packages, do NOT preview "
        "the data beyond the column names you already need.\n"
        f"- Your FIRST action must be to write a complete, runnable {artifact} "
        f"to /home/user/project/{artifact} using {label} and {language}. "
        "Aim for a small but complete dashboard (one sidebar + one main panel "
        "with one chart and one table is fine). Do not stream the file in "
        "tiny edits — emit the whole thing in one write.\n"
        "- Only after that file exists and runs may you refine it. If you run "
        "out of tokens again, the checkpoint already on disk will be used."
    )


def build_refinement_prompt(
    original_prompt: str,
    judge_feedback: dict[str, dict[str, str | float]],
    iteration: int,
    previous_code: str | None = None,
    runtime_logs: str | None = None,
    validation_passed: bool | None = None,
) -> str:
    """Build a refinement prompt incorporating judge feedback.

    Args:
        original_prompt: The original user prompt.
        judge_feedback: Dict of criterion → {score, rationale}.
        iteration: Current iteration number.
        previous_code: The source code from the previous iteration.
            When provided, the agent can see and incrementally improve it
            rather than regenerating from scratch.
        runtime_logs: Optional startup/server logs.
        validation_passed: Optional boolean indicating if startup passed.
    """
    feedback_lines = []
    for criterion, entry in judge_feedback.items():
        label = criterion.replace("_", " ").title()
        score = entry.get("score", 0)
        rationale = entry.get("rationale", "")
        feedback_lines.append(f"  - {label}: {score}/10 — {rationale}")

    feedback_text = "\n".join(feedback_lines)

    parts = [
        original_prompt,
        f"\n\n--- REFINEMENT (iteration {iteration}) ---\n",
    ]

    if previous_code:
        parts.append(
            f"\nHere is the previous version of the app that was evaluated:\n\n"
            f"```\n{previous_code}\n```\n"
        )

    if runtime_logs and validation_passed is False:
        trimmed_logs = runtime_logs.strip() or "(no server output captured)"
        if len(trimmed_logs) > 8_000:
            trimmed_logs = trimmed_logs[-8_000:]
        parts.append(
            f"\nAdditionally, the app failed to start locally. "
            f"Please fix the following startup/server errors before addressing the judge feedback:\n\n"
            f"```\n{trimmed_logs}\n```\n"
        )

    parts.append(
        f"\nThe previous version received the following scores. "
        f"Please improve the app to address the feedback:\n\n"
        f"{feedback_text}\n\n"
        f"Focus on improving the lowest-scoring areas while maintaining "
        f"what already works well. Produce the complete, improved app file."
    )

    return "".join(parts)


def build_runtime_refinement_prompt(
    original_prompt: str,
    *,
    previous_code: str,
    runtime_logs: str,
    iteration: int,
) -> str:
    """Build a refinement prompt from startup/server logs for a broken app."""
    trimmed_logs = runtime_logs.strip() or "(no server output captured)"
    if len(trimmed_logs) > 8_000:
        trimmed_logs = trimmed_logs[-8_000:]

    return (
        f"{original_prompt}\n\n"
        f"--- RUNTIME LOG REVIEW (iteration {iteration}) ---\n"
        "The app did not pass startup validation. Fix the errors shown "
        "in the logs before final submission.\n\n"
        "Here is the previous version of the app that was run:\n\n"
        f"```\n{previous_code}\n```\n\n"
        "Server/startup logs from that run:\n\n"
        f"```\n{trimmed_logs}\n```\n\n"
        "Return a complete replacement app that preserves the requested "
        "dashboard, fixes any runtime/log issues, and adds defensive handling "
        "for empty data, missing columns, invalid filters, and render-time "
        "exceptions. Save the final result as the required app artifact."
    )
