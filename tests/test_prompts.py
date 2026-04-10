"""Tests for shinygen.prompts"""

from shinygen.prompts import (
    build_refinement_prompt,
    build_system_prompt,
    build_user_prompt,
)


class TestBuildSystemPrompt:
    def test_python_prompt(self):
        prompt = build_system_prompt("shiny_python")
        assert "Python" in prompt
        assert "app.py" in prompt
        assert "R" in prompt  # "DO NOT use R" should be in there

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

    def test_screenshot_r_adds_visual_qa(self):
        prompt = build_system_prompt("shiny_r", screenshot=True)
        assert "VISUAL SELF-EVALUATION" in prompt
        assert "screenshot_helper.py" in prompt
        assert "Rscript" in prompt
        assert "7 seconds" in prompt

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
        prompt = build_refinement_prompt("Build a dashboard", feedback, 2, previous_code=code)
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
        prompt_none = build_refinement_prompt("Build a dashboard", feedback, 1, previous_code=None)
        prompt_omit = build_refinement_prompt("Build a dashboard", feedback, 1)
        assert prompt_none == prompt_omit
