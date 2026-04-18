"""
System and user prompt templates for Shiny app generation.
"""

from __future__ import annotations

from .config import FRAMEWORKS

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
2. Install any additional Python packages you need: {install_command}
   NOTE: shiny, plotly, faicons, pandas, matplotlib, seaborn are \
already installed.
3. Create the file /home/user/project/app.py with the dashboard code.
   CRITICAL: The file MUST be app.py (NOT app.R). Use Python language syntax.
4. Verify Python syntax: python -c "import ast; \
ast.parse(open('/home/user/project/app.py').read()); print('OK')"

Produce clean, well-structured, production-quality Python code using Python \
language syntax. Use Shiny Express or Core API with modern layout functions \
(page_sidebar, card, value_box, etc.). Import from `shiny` or \
`shiny.express`, and construct a real Shiny app in `app.py`. Remember: Use \
Python, not R, and Shiny, not Streamlit or Dash. The file must be app.py.

Dashboard layout rules for Python Shiny:
- Put KPI and value-box rows in ui.layout_column_wrap(..., width="240px", gap="1rem", fill=False).
- Always pass gap="1rem" (or roomier) to ui.layout_columns() and ui.layout_column_wrap() so cards do not touch.
- For dense dashboards with a KPI row plus multiple chart, map, or table rows, set fillable=False on the page.
- Never place multiple cards or value boxes as bare sequential page children; wrap them in ui.layout_columns() or ui.layout_column_wrap().
- Give chart and table cards min_height="320px" or larger so they do not collapse into shallow strips.
"""

SYSTEM_PROMPT_VISUAL_QA = """\

VISUAL SELF-EVALUATION (screenshot mode is ON):
After creating your app, you MUST visually verify it:
1. Start the app: nohup python -m shiny run app.py --port 8000 > /tmp/app.log 2>&1 &
2. Once the app is up, take a screenshot with: python /home/user/project/.tools/screenshot_helper.py
    The helper waits 7 seconds before capturing so late-loading dashboard sections can render.
3. View the screenshot to check the visual output.
4. Evaluate: layout correctness, chart visibility, text readability, colours, styling.
5. Fix any visual issues, then re-screenshot to confirm.
6. Stop the app when done: pkill -f "shiny run" || true
You may iterate up to 3 times on visual fixes. If the screenshot is blank, \
check /tmp/app.log for errors.
"""

SYSTEM_PROMPT_VISUAL_QA_R = """\

VISUAL SELF-EVALUATION (screenshot mode is ON):
After creating your app, you MUST visually verify it:
1. Start the app: nohup Rscript -e "shiny::runApp('app.R', port=8000, launch.browser=FALSE)" > /tmp/app.log 2>&1 &
2. Once the app is up, take a screenshot with: python3 /home/user/project/.tools/screenshot_helper.py
    The helper waits 7 seconds before capturing so late-loading dashboard sections can render.
3. View the screenshot to check the visual output.
4. Evaluate: layout correctness, chart visibility, text readability, colours, styling.
5. Fix any visual issues, then re-screenshot to confirm.
6. Stop the app when done: pkill -f "Rscript" || true
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
   Only install packages that are NOT in the list above:
   {install_command}
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
        f"- If time or output tokens are running low, stop analysis and write "
        f"the best complete working {artifact} immediately.\n"
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


def build_user_prompt(
    user_prompt: str,
    framework_key: str,
) -> str:
    """Build the full user prompt combining the user's request with
    framework-specific instructions.

    Args:
        user_prompt: The user's natural-language description of the app.
        framework_key: "shiny_python" or "shiny_r"
    """
    fw = FRAMEWORKS[framework_key]
    artifact = fw["primary_artifact"]
    language = fw["language"]
    label = fw["label"]

    return (
        f"{user_prompt}\n\n"
        f"IMPORTANT: Build this using {label}. "
        f"Write {language} code and save it as `{artifact}`. "
        f"The app must be runnable with: {fw['run_command'].format(port=8000)}"
    )


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
        f"producing {artifact}. Do not repeat reconnaissance, package version "
        "checks, or skill-file exploration. Immediately write a complete "
        f"working {artifact} to /home/user/project/{artifact} using {label} "
        f"and {language} code. If you need data context, inspect only the "
        f"required columns or a small sample, then finish {artifact}."
    )


def build_refinement_prompt(
    original_prompt: str,
    judge_feedback: dict[str, dict[str, str | float]],
    iteration: int,
    previous_code: str | None = None,
) -> str:
    """Build a refinement prompt incorporating judge feedback.

    Args:
        original_prompt: The original user prompt.
        judge_feedback: Dict of criterion → {score, rationale}.
        iteration: Current iteration number.
        previous_code: The source code from the previous iteration.
            When provided, the agent can see and incrementally improve it
            rather than regenerating from scratch.
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

    parts.append(
        f"\nThe previous version received the following scores. "
        f"Please improve the app to address the feedback:\n\n"
        f"{feedback_text}\n\n"
        f"Focus on improving the lowest-scoring areas while maintaining "
        f"what already works well. Produce the complete, improved app file."
    )

    return "".join(parts)
