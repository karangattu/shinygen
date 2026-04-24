"""Tests for skill loading and agent wiring."""

from pathlib import Path

import pytest

from shinygen.config import SANDBOX_TIME_LIMIT_BY_FRAMEWORK
from shinygen.generate import build_generation_task
from shinygen.skills import (
    load_default_skills,
    load_skill_context_text,
    load_visual_qa_skills,
)


class TestLoadDefaultSkills:
    @pytest.mark.parametrize(
        ("framework_key", "expected_name", "expected_reference"),
        [
            (
                "shiny_python",
                "shiny-python-dashboard",
                "layout-and-navigation.md",
            ),
            ("shiny_r", "shiny-bslib", "page-layouts.md"),
        ],
    )
    def test_loads_framework_skill_as_agent_skill(
        self,
        framework_key,
        expected_name,
        expected_reference,
    ):
        skills = load_default_skills(framework_key)

        assert len(skills) == 1
        assert skills[0].name == expected_name
        assert expected_reference in skills[0].references
        assert skills[0].description

    def test_loads_visual_qa_skill_as_agent_skill(self):
        skills = load_visual_qa_skills()

        assert len(skills) == 1
        assert skills[0].name == "visual-qa"
        assert "visually verify" in skills[0].description.lower()
        assert "screenshot" in skills[0].instructions.lower()

    def test_visual_qa_skill_includes_r_screenshot_workflow(self):
        skills = load_visual_qa_skills()

        assert len(skills) == 1
        instructions = skills[0].instructions

        assert "nohup Rscript -e \"shiny::runApp('app.R', port=8000, launch.browser=FALSE)\"" in instructions
        assert "python3 /home/user/project/.tools/screenshot_helper.py" in instructions
        assert "pkill -f \"Rscript\" || true" in instructions

    def test_shiny_python_skill_teaches_non_squished_dashboard_layouts(self):
        instructions = load_skill_context_text("shiny_python")

        assert 'width="240px"' in instructions
        assert 'Use `fillable=False` for dense dashboards' in instructions
        assert 'min_height="320px"' in instructions
        assert 'Do not place more than 2 medium or large visualization cards in a row' in instructions


class TestBuildGenerationTask:
    def test_codex_solver_uses_auto_cli_with_live_web_search(
        self,
        tmp_path,
        monkeypatch,
    ):
        captured = {}
        sentinel_solver = object()

        def fake_solver(**kwargs):
            captured.update(kwargs)
            return sentinel_solver

        monkeypatch.setattr("shinygen.generate.codex_cli", fake_solver)

        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent="codex_cli",
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
        )

        assert task.solver is sentinel_solver
        # `auto` makes inspect_swe prefer the codex binary baked into the
        # pre-built sandbox image, falling back to a download when missing.
        assert captured["version"] == "auto"
        assert captured["config_overrides"] == {"web_search": "live"}
        # web_fetch defaults to True, so web_search must NOT be disallowed.
        assert captured["disallowed_tools"] == []

    def test_codex_solver_disallows_web_search_when_web_fetch_false(
        self,
        tmp_path,
        monkeypatch,
    ):
        captured = {}
        sentinel_solver = object()

        def fake_solver(**kwargs):
            captured.update(kwargs)
            return sentinel_solver

        monkeypatch.setattr("shinygen.generate.codex_cli", fake_solver)

        build_generation_task(
            user_prompt="Build a dashboard",
            agent="codex_cli",
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
            web_fetch=False,
        )

        assert captured["disallowed_tools"] == ["web_search"]

    @pytest.mark.parametrize("agent", ["claude_code", "codex_cli"])
    def test_use_skills_false_runs_vanilla_baseline(
        self,
        tmp_path,
        monkeypatch,
        agent,
    ):
        """Control arm: no bundled skills, no .agents/skills/ staging."""
        captured = {}
        sentinel_solver = object()

        def fake_solver(**kwargs):
            captured.update(kwargs)
            return sentinel_solver

        if agent == "claude_code":
            monkeypatch.setattr("shinygen.generate.claude_code", fake_solver)
        else:
            monkeypatch.setattr("shinygen.generate.codex_cli", fake_solver)

        skills = load_default_skills("shiny_python")
        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent=agent,
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
            data_files={"sales.csv": "x,y\n1,2\n"},
            skills=skills,
            use_skills=False,
            screenshot=True,
        )

        assert task.solver is sentinel_solver
        # Even if the caller passed skills, the vanilla arm must drop them.
        assert captured["skills"] is None

        sample_files = task.dataset.samples[0].files or {}
        # Data files still present.
        assert sample_files["sales.csv"] == "x,y\n1,2\n"
        # Screenshot helper script still present (vanilla arm still
        # captures screenshots; only the SKILL.md guidance is removed).
        assert ".tools/screenshot_helper.py" in sample_files
        # No bundled skill files staged for codex_cli either.
        staged = [k for k in sample_files if k.startswith(".agents/skills/")]
        assert staged == []

    @pytest.mark.parametrize("agent", ["claude_code", "codex_cli"])
    def test_passes_skills_to_solver_instead_of_sample_files(
        self,
        tmp_path,
        monkeypatch,
        agent,
    ):
        captured = {}
        sentinel_solver = object()

        def fake_solver(**kwargs):
            captured.update(kwargs)
            return sentinel_solver

        if agent == "claude_code":
            monkeypatch.setattr("shinygen.generate.claude_code", fake_solver)
        else:
            monkeypatch.setattr("shinygen.generate.codex_cli", fake_solver)

        skills = load_default_skills("shiny_python")
        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent=agent,
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
            data_files={"sales.csv": "x,y\n1,2\n"},
            skills=skills,
        )

        assert task.solver is sentinel_solver
        assert captured["skills"] == skills

        sample_files = task.dataset.samples[0].files or {}
        assert sample_files["sales.csv"] == "x,y\n1,2\n"
        if agent == "codex_cli":
            # codex_cli additionally stages bundled skill files into the
            # documented `.agents/skills/<name>/` discovery path because
            # inspect_swe writes to `$CODEX_HOME/skills` only.
            staged = [k for k in sample_files if k.startswith(".agents/skills/")]
            assert staged, "expected bundled skill files staged for codex_cli"
            assert any(k.endswith("/SKILL.md") for k in staged)
        else:
            assert sample_files == {"sales.csv": "x,y\n1,2\n"}

    @pytest.mark.parametrize("agent", ["claude_code", "codex_cli"])
    def test_screenshot_skills_arm_adds_visual_qa_skill_only_when_enabled(
        self,
        tmp_path,
        monkeypatch,
        agent,
    ):
        captured = {}
        sentinel_solver = object()

        def fake_solver(**kwargs):
            captured.update(kwargs)
            return sentinel_solver

        if agent == "claude_code":
            monkeypatch.setattr("shinygen.generate.claude_code", fake_solver)
        else:
            monkeypatch.setattr("shinygen.generate.codex_cli", fake_solver)

        skills = load_default_skills("shiny_python")
        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent=agent,
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
            skills=skills,
            use_skills=True,
            screenshot=True,
        )

        assert task.solver is sentinel_solver
        skill_names = [skill.name for skill in captured["skills"]]
        assert skill_names == ["shiny-python-dashboard", "visual-qa"]

        sample_files = task.dataset.samples[0].files or {}
        assert ".tools/screenshot_helper.py" in sample_files
        staged = [key for key in sample_files if key.startswith(".agents/skills/")]
        if agent == "codex_cli":
            assert all(not key.startswith("/") for key in staged)
            assert any(key.startswith(".agents/skills/shiny-python-dashboard/") for key in staged)
            assert any(key.startswith(".agents/skills/visual-qa/") for key in staged)
        else:
            assert staged == []

    @pytest.mark.parametrize(
        ("framework_key", "expected_limit"),
        [
            (
                "shiny_python",
                SANDBOX_TIME_LIMIT_BY_FRAMEWORK["shiny_python"],
            ),
            ("shiny_r", SANDBOX_TIME_LIMIT_BY_FRAMEWORK["shiny_r"]),
        ],
    )
    def test_applies_framework_specific_time_limits(
        self,
        tmp_path,
        monkeypatch,
        framework_key,
        expected_limit,
    ):
        sentinel_solver = object()

        def fake_solver(**kwargs):
            return sentinel_solver

        monkeypatch.setattr("shinygen.generate.codex_cli", fake_solver)

        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent="codex_cli",
            framework_key=framework_key,
            docker_context_dir=tmp_path,
        )

        assert task.solver is sentinel_solver
        assert task.time_limit == expected_limit
        assert task.working_limit == expected_limit
