"""Tests for shinygen.prompts"""

from shinygen.prompts import (
    build_dataset_context,
    build_refinement_prompt,
    build_runtime_refinement_prompt,
    build_system_prompt,
    build_truncation_retry_prompt,
    build_user_prompt,
)


class TestBuildSystemPrompt:
    def test_python_prompt(self):
        prompt = build_system_prompt("shiny_python")
        assert "Python" in prompt
        assert "app.py" in prompt
        assert "R" in prompt  # "DO NOT use R" should be in there

    def test_python_prompt_does_not_leak_skills_layout_rules(self):
        prompt = build_system_prompt("shiny_python")
        assert "fillable=False" not in prompt
        assert 'min_height="320px"' not in prompt
        assert "ui.page_navbar()" not in prompt
        assert "output_widget" not in prompt

    def test_python_prompt_prioritizes_writing_over_recon(self):
        prompt = build_system_prompt("shiny_python")
        assert "package version checks" in prompt
        assert "write the best complete working app.py immediately" in prompt

    def test_python_prompt_mentions_shiny_framework_basics(self):
        prompt = build_system_prompt("shiny_python")
        assert "shinywidgets" in prompt
        assert "page_sidebar" in prompt
        assert "value_box" in prompt

    def test_r_prompt(self):
        prompt = build_system_prompt("shiny_r")
        assert "app.R" in prompt

    def test_data_files_mentioned(self):
        prompt = build_system_prompt("shiny_python", ["data.csv", "meta.json"])
        assert "data.csv" in prompt
        assert "meta.json" in prompt

    def test_screenshot_python_adds_visual_qa(self):
        prompt = build_system_prompt("shiny_python", screenshot=True)
        assert "VISUAL SELF-EVALUATION" in prompt
        assert "screenshot_helper.py" in prompt
        assert "shiny run" in prompt
        assert "7 seconds" in prompt
        assert "tail -n 80 /tmp/app.log" in prompt

    def test_screenshot_r_adds_visual_qa(self):
        prompt = build_system_prompt("shiny_r", screenshot=True)
        assert "VISUAL SELF-EVALUATION" in prompt
        assert "screenshot_helper.py" in prompt
        assert "Rscript" in prompt
        assert "7 seconds" in prompt
        assert "tail -n 80 /tmp/app.log" in prompt

    def test_no_screenshot_omits_visual_qa(self):
        prompt = build_system_prompt("shiny_python")
        assert "VISUAL SELF-EVALUATION" not in prompt


class TestBuildUserPrompt:
    def test_contains_user_text(self):
        prompt = build_user_prompt("Build a dashboard for penguins", "shiny_python")
        assert "penguins" in prompt

    def test_contains_framework_label(self):
        prompt = build_user_prompt("Make a chart", "shiny_python")
        assert "Shiny for Python" in prompt

    def test_appends_dataset_context_when_data_files_provided(self):
        prompt = build_user_prompt(
            "Build a dashboard",
            "shiny_python",
            data_files={"sales.csv": "city,revenue\nAsheville,100\n"},
        )
        assert "DATASET(S) YOU MUST USE" in prompt
        assert "`sales.csv`" in prompt
        assert "city, revenue" in prompt
        assert "sales.csv" in prompt

    def test_omits_dataset_context_when_no_data_files(self):
        prompt = build_user_prompt("Build a dashboard", "shiny_python")
        assert "DATASET(S) YOU MUST USE" not in prompt


class TestBuildDatasetContext:
    def test_returns_none_for_empty_or_none(self):
        assert build_dataset_context(None) is None
        assert build_dataset_context({}) is None

    def test_names_exact_csv_filename_columns_and_row_count(self):
        ctx = build_dataset_context(
            {
                "airbnb-asheville-short.csv": "neighbourhood,price,room_type\nA,100,Entire\nB,200,Private\n"
            }
        )
        assert ctx is not None
        assert "`airbnb-asheville-short.csv`" in ctx
        assert "neighbourhood, price, room_type" in ctx
        assert "2 data row(s)" in ctx

    def test_includes_anti_swap_directive(self):
        ctx = build_dataset_context({"sales.csv": "a,b\n1,2\n"})
        assert ctx is not None
        assert "Do NOT substitute" in ctx
        assert "mtcars" in ctx
        assert "penguins" in ctx
        assert "data.csv" in ctx

    def test_lists_non_csv_files_by_name_only(self):
        ctx = build_dataset_context({"meta.json": '{"k":"v"}'})
        assert ctx is not None
        assert "`meta.json`" in ctx
        assert "non-CSV file" in ctx

    def test_handles_empty_csv(self):
        ctx = build_dataset_context({"empty.csv": ""})
        assert ctx is not None
        assert "`empty.csv`" in ctx
        assert "empty CSV" in ctx

    def test_truncates_oversized_context(self):
        big_row = ",".join(f"column_name_{i}_padding" for i in range(500))
        ctx = build_dataset_context({"big.csv": big_row + "\n"})
        assert ctx is not None
        assert "[truncated]" in ctx


class TestBuildTruncationRetryPrompt:
    def test_focuses_retry_on_direct_artifact_write(self):
        prompt = build_truncation_retry_prompt(
            "Build a dashboard for penguins",
            "shiny_python",
        )
        assert "previous attempt hit the output token limit" in prompt
        assert "/home/user/project/app.py" in prompt
        # Retry prompt should suppress exploration and demand a single
        # complete-file write of a small but runnable dashboard.
        assert "Skip ALL exploration" in prompt
        assert "in one write" in prompt
        assert "checkpoint" in prompt


class TestBuildRefinementPrompt:
    def test_includes_feedback(self):
        feedback = {
            "requirement_fidelity": {"score": 3, "rationale": "Missing filters"},
            "code_maintainability": {"score": 4, "rationale": "Good structure"},
        }
        prompt = build_refinement_prompt("Build a dashboard", feedback, 1)
        assert "Missing filters" in prompt
        assert "iteration" in prompt.lower() or "Iteration" in prompt

    def test_includes_previous_code(self):
        feedback = {
            "requirement_fidelity": {"score": 5, "rationale": "OK"},
        }
        code = "from shiny import App\napp = App(None, None)"
        prompt = build_refinement_prompt(
            "Build a dashboard", feedback, 2, previous_code=code
        )
        assert "from shiny import App" in prompt
        assert "previous version" in prompt.lower()
        assert "```" in prompt

    def test_no_previous_code_omits_block(self):
        feedback = {
            "requirement_fidelity": {"score": 5, "rationale": "OK"},
        }
        prompt = build_refinement_prompt("Build a dashboard", feedback, 1)
        assert "```" not in prompt
        assert "previous version of the app that was evaluated" not in prompt

    def test_previous_code_none_same_as_omitted(self):
        feedback = {
            "requirement_fidelity": {"score": 5, "rationale": "OK"},
        }
        prompt_none = build_refinement_prompt(
            "Build a dashboard", feedback, 1, previous_code=None
        )
        prompt_omit = build_refinement_prompt("Build a dashboard", feedback, 1)
        assert prompt_none == prompt_omit


class TestBuildRuntimeRefinementPrompt:
    def test_includes_previous_code_and_server_logs(self):
        prompt = build_runtime_refinement_prompt(
            "Build an ED operations dashboard",
            previous_code="from shiny import App\napp = App(None, None)",
            runtime_logs="Listening on http://127.0.0.1:8000\nTraceback: bad column",
            iteration=1,
        )

        assert "RUNTIME LOG REVIEW" in prompt
        assert "previous version" in prompt.lower()
        assert "Traceback: bad column" in prompt
        assert "from shiny import App" in prompt
        assert "Return a complete replacement" in prompt
