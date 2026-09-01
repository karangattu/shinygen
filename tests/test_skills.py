"""Tests for skill loading and agent wiring."""

import asyncio
import io
import tarfile
from types import SimpleNamespace

import pytest

from shinygen.config import SANDBOX_TIME_LIMIT_BY_FRAMEWORK
from shinygen.generate import _ensure_sandbox_screenshot, build_generation_task
from shinygen.skills import (
    collect_skill_sample_files,
    load_default_skills,
    load_skill_context_text,
    load_visual_qa_skills,
)


@pytest.fixture(autouse=True)
def py_shiny_skill_archive(tmp_path, monkeypatch):
    """Serve an upstream-shaped py-shiny skill archive without network I/O."""
    archive_path = tmp_path / "py-shiny.tar.gz"
    files = {
        "py-shiny-main/shiny/.agents/skills/shiny-for-python/SKILL.md": (
            "---\n"
            "name: shiny-for-python\n"
            "description: Official Shiny for Python app-authoring guidance.\n"
            "---\n\n"
            "# Shiny for Python\n\n"
            "Read [layouts](references/layouts.md).\n"
        ),
        "py-shiny-main/shiny/.agents/skills/shiny-for-python/references/layouts.md": (
            "# Layouts\n\nUse current Shiny layout APIs.\n"
        ),
        # Contributor skills under .claude must not be installed into generated apps.
        "py-shiny-main/.claude/skills/py-shiny-release/SKILL.md": (
            "---\nname: py-shiny-release\ndescription: Release py-shiny.\n---\n"
        ),
    }
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, content in files.items():
            payload = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    monkeypatch.setenv("SHINYGEN_PY_SHINY_SKILL_ARCHIVE_URL", archive_path.as_uri())
    monkeypatch.setenv("SHINYGEN_SKILLS_CACHE_DIR", str(tmp_path / "cache"))


@pytest.fixture(autouse=True)
def r_shiny_skill_archive(tmp_path, monkeypatch):
    """Serve an upstream-shaped r-shiny skill archive without network I/O."""
    archive_path = tmp_path / "r-shiny.tar.gz"
    files = {
        "shiny-main/inst/skills/shiny-for-r/SKILL.md": (
            "---\n"
            "name: shiny-for-r\n"
            "description: Official Shiny for R app-authoring guidance.\n"
            "---\n\n"
            "# Shiny for R\n\n"
            "Read [layouts](references/layouts.md).\n"
        ),
        "shiny-main/inst/skills/shiny-for-r/references/layouts.md": (
            "# Layouts\n\nUse modern bslib layout APIs.\n"
        ),
        "shiny-main/.claude/skills/r-shiny-release/SKILL.md": (
            "---\nname: r-shiny-release\ndescription: Release r-shiny.\n---\n"
        ),
    }
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, content in files.items():
            payload = content.encode()
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    monkeypatch.setenv("SHINYGEN_R_SHINY_SKILL_ARCHIVE_URL", archive_path.as_uri())


class TestLoadDefaultSkills:
    @pytest.mark.parametrize(
        ("framework_key", "expected_name", "expected_reference"),
        [
            (
                "shiny_python",
                "shiny-for-python",
                "layouts.md",
            ),
            ("shiny_r", "shiny-for-r", "layouts.md"),
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
        assert "tail -n 80 /tmp/app.log" in skills[0].instructions

    def test_visual_qa_skill_includes_r_screenshot_workflow(self):
        skills = load_visual_qa_skills()

        assert len(skills) == 1
        instructions = skills[0].instructions

        assert (
            "nohup Rscript -e \"shiny::runApp('app.R', port=8000, launch.browser=FALSE)\""
            in instructions
        )
        assert "python3 /home/user/project/.tools/screenshot_helper.py" in instructions

    def test_visual_qa_skill_stops_only_the_recorded_app_process(self):
        instructions = load_visual_qa_skills()[0].instructions

        assert "printf '%s\\n' \"$!\" > /tmp/shinygen_app.pid" in instructions
        assert "read -r app_pid < /tmp/shinygen_app.pid" in instructions
        assert 'kill "$app_pid"' in instructions
        assert "pkill -f" not in instructions

    def test_visual_qa_skill_teaches_human_preference_calibration(self):
        skills = load_visual_qa_skills()

        assert len(skills) == 1
        skill = skills[0]
        instructions = skill.instructions

        assert "Human Preference Calibration" in instructions
        assert "one-screen usefulness" in instructions
        assert "Clean alone is not enough" in instructions
        assert "render-state gate" in instructions
        assert "human_visual_preferences.md" in skill.references

    def test_shiny_python_context_comes_from_upstream_skill(self):
        instructions = load_skill_context_text("shiny_python")

        assert "# Shiny for Python" in instructions
        assert "Use current Shiny layout APIs." in instructions

    def test_shiny_r_context_comes_from_upstream_skill(self):
        instructions = load_skill_context_text("shiny_r")

        assert "# Shiny for R" in instructions
        assert "Use modern bslib layout APIs." in instructions

    def test_stages_only_the_upstream_app_authoring_skill(self):
        files = collect_skill_sample_files("shiny_python")

        assert ".agents/skills/shiny-for-python/SKILL.md" in files
        assert ".agents/skills/shiny-for-python/references/layouts.md" in files
        assert not any("py-shiny-release" in path for path in files)

    def test_stages_only_the_upstream_r_app_authoring_skill(self):
        files = collect_skill_sample_files("shiny_r")

        assert ".agents/skills/shiny-for-r/SKILL.md" in files
        assert ".agents/skills/shiny-for-r/references/layouts.md" in files
        assert not any("r-shiny-release" in path for path in files)

    def test_uses_cached_python_skill_when_refresh_fails(self, monkeypatch):
        assert load_default_skills("shiny_python")[0].name == "shiny-for-python"

        monkeypatch.setenv(
            "SHINYGEN_PY_SHINY_SKILL_ARCHIVE_URL",
            "file:///archive-that-does-not-exist.tar.gz",
        )

        assert load_default_skills("shiny_python")[0].name == "shiny-for-python"

    def test_uses_cached_r_skill_when_refresh_fails(self, monkeypatch):
        assert load_default_skills("shiny_r")[0].name == "shiny-for-r"

        monkeypatch.setenv(
            "SHINYGEN_R_SHINY_SKILL_ARCHIVE_URL",
            "file:///archive-that-does-not-exist.tar.gz",
        )

        assert load_default_skills("shiny_r")[0].name == "shiny-for-r"


class TestEnsureSandboxScreenshot:
    def test_auto_screenshot_cleanup_stops_only_the_recorded_app_process(self):
        class FakeSandbox:
            def __init__(self):
                self.commands: list[list[str]] = []
                self.screenshot_exists = False

            async def exec(self, command, **_kwargs):
                self.commands.append(command)
                shell_command = command[-1] if command[:2] == ["sh", "-lc"] else ""

                if shell_command.startswith("find "):
                    screenshot = (
                        "/home/user/project/screenshot.png\n"
                        if self.screenshot_exists
                        else ""
                    )
                    return SimpleNamespace(returncode=0, stdout=screenshot)
                if command == [
                    "test",
                    "-f",
                    "/home/user/project/.tools/screenshot_helper.py",
                ]:
                    return SimpleNamespace(returncode=0, stdout="")
                if "screenshot_helper.py" in shell_command:
                    self.screenshot_exists = True
                return SimpleNamespace(returncode=0, stdout="")

        sandbox = FakeSandbox()

        captured = asyncio.run(
            _ensure_sandbox_screenshot(sandbox, "shiny_python")  # type: ignore[arg-type]
        )

        assert captured is True
        shell_commands = "\n".join(
            command[-1] for command in sandbox.commands if command[:2] == ["sh", "-lc"]
        )
        assert "printf '%s\\n' \"$!\" > /tmp/shinygen_auto_app.pid" in shell_commands
        assert "read -r app_pid < /tmp/shinygen_auto_app.pid" in shell_commands
        assert 'kill "$app_pid"' in shell_commands
        assert "pkill -f" not in shell_commands


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

    @pytest.mark.parametrize("tier", ["sol", "terra", "luna"])
    def test_gpt56_uses_bridge_compatible_codex_profile(
        self,
        tmp_path,
        monkeypatch,
        tier,
    ):
        captured = {}

        def fake_solver(**kwargs):
            captured.update(kwargs)
            return object()

        monkeypatch.setattr("shinygen.generate.codex_cli", fake_solver)

        build_generation_task(
            user_prompt="Build a dashboard",
            agent="codex_cli",
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
            model_id=f"openai/gpt-5.6-{tier}",
        )

        assert captured["model_config"] == "inspect-generic"

    def test_opencode_go_openai_model_uses_opencode_solver(
        self,
        tmp_path,
        monkeypatch,
    ):
        captured = {}
        sentinel_agent = object()

        def fake_opencode(**kwargs):
            captured.update(kwargs)
            return sentinel_agent

        monkeypatch.setattr("shinygen.generate.opencode", fake_opencode)

        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent="opencode",
            model_id="openai-api/opencode-go/deepseek-v4-flash",
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
        )

        assert task.solver is sentinel_agent
        assert captured["model"] == "openai-api/opencode-go/deepseek-v4-flash"
        assert captured["version"] == "auto"
        # Fail-fast 10-min ceiling for the open-weights tier.
        assert task.time_limit == 600
        assert task.working_limit == 600

    def test_gemini_cli_model_uses_gemini_cli_solver(
        self,
        tmp_path,
        monkeypatch,
    ):
        captured = {}
        sentinel_agent = object()

        def fake_gemini_cli(**kwargs):
            captured.update(kwargs)
            return sentinel_agent

        monkeypatch.setattr("shinygen.generate.gemini_cli", fake_gemini_cli)

        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent="gemini_cli",
            model_id="google/gemini-2.5-pro",
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
            web_fetch=True,
        )

        assert task.solver is sentinel_agent
        assert captured["model"] == "google/gemini-2.5-pro"
        assert captured["web_search"] is True
        assert captured["version"] == "auto"

    def test_lmstudio_model_gets_local_generation_time_limit(
        self,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.setattr("shinygen.generate.opencode", lambda **kwargs: object())

        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent="opencode",
            model_id="lmstudio/qwen3.5-9b",
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
        )

        assert task.time_limit == 1200
        assert task.working_limit == 1200

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

        sample_files = task.dataset[0].files or {}
        # Data files still present.
        assert sample_files["sales.csv"] == "x,y\n1,2\n"
        # Screenshot helper script still present (vanilla arm still
        # captures screenshots; only the SKILL.md guidance is removed).
        assert ".tools/screenshot_helper.py" in sample_files
        # No bundled skill files staged for codex_cli either.
        staged = [k for k in sample_files if k.startswith(".agents/skills/")]
        assert staged == []

    @pytest.mark.parametrize("agent", ["claude_code", "codex_cli"])
    @pytest.mark.parametrize(
        ("framework_key", "expected_skill_name"),
        [("shiny_python", "shiny-for-python"), ("shiny_r", "shiny-for-r")],
    )
    def test_passes_skills_to_solver_instead_of_sample_files(
        self,
        tmp_path,
        monkeypatch,
        agent,
        framework_key,
        expected_skill_name,
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

        skills = load_default_skills(framework_key)
        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent=agent,
            framework_key=framework_key,
            docker_context_dir=tmp_path,
            data_files={"sales.csv": "x,y\n1,2\n"},
            skills=skills,
        )

        assert task.solver is sentinel_solver
        assert captured["skills"] == skills

        sample_files = task.dataset[0].files or {}
        assert sample_files["sales.csv"] == "x,y\n1,2\n"
        if agent == "codex_cli":
            # codex_cli additionally stages bundled skill files into the
            # documented `.agents/skills/<name>/` discovery path because
            # inspect_swe writes to `$CODEX_HOME/skills` only.
            staged = [k for k in sample_files if k.startswith(".agents/skills/")]
            assert staged, "expected bundled skill files staged for codex_cli"
            assert any(
                k.startswith(f".agents/skills/{expected_skill_name}/") for k in staged
            )
            assert any(k.endswith("/SKILL.md") for k in staged)
        else:
            assert sample_files == {"sales.csv": "x,y\n1,2\n"}

    @pytest.mark.parametrize("agent", ["claude_code", "codex_cli"])
    @pytest.mark.parametrize(
        ("framework_key", "expected_skill_name"),
        [("shiny_python", "shiny-for-python"), ("shiny_r", "shiny-for-r")],
    )
    def test_screenshot_skills_arm_adds_visual_qa_skill_only_when_enabled(
        self,
        tmp_path,
        monkeypatch,
        agent,
        framework_key,
        expected_skill_name,
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

        skills = load_default_skills(framework_key)
        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent=agent,
            framework_key=framework_key,
            docker_context_dir=tmp_path,
            skills=skills,
            use_skills=True,
            screenshot=True,
        )

        assert task.solver is sentinel_solver
        skill_names = [skill.name for skill in captured["skills"]]
        assert skill_names == [expected_skill_name, "visual-qa"]

        sample_files = task.dataset[0].files or {}
        assert ".tools/screenshot_helper.py" in sample_files
        staged = [key for key in sample_files if key.startswith(".agents/skills/")]
        if agent == "codex_cli":
            assert all(not key.startswith("/") for key in staged)
            assert any(
                key.startswith(f".agents/skills/{expected_skill_name}/")
                for key in staged
            )
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


class TestDatasetContextInjection:
    """The agent's user message must name the exact CSV + columns so it
    does not substitute a built-in/example dataset (notably for Claude R)."""

    @pytest.mark.parametrize("agent", ["claude_code", "codex_cli"])
    @pytest.mark.parametrize("use_skills", [True, False])
    def test_dataset_context_in_user_message_for_claude_and_codex(
        self, tmp_path, monkeypatch, agent, use_skills
    ):
        sentinel_solver = object()
        monkeypatch.setattr(f"shinygen.generate.{agent}", lambda **kw: sentinel_solver)

        task = build_generation_task(
            user_prompt="Build a dashboard for the selected dataset",
            agent=agent,
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
            data_files={
                "airbnb-asheville-short.csv": "neighbourhood,price\nA,100\nB,200\n"
            },
            skills=load_default_skills("shiny_python"),
            use_skills=use_skills,
        )

        sample_input = task.dataset[0].input
        assert not isinstance(sample_input, str)
        user_msgs = [m for m in sample_input if m.role == "user"]
        assert user_msgs, "expected at least one user message in the sample input"
        user_content = user_msgs[-1].content
        # Exact filename, columns, and anti-swap directive must reach the
        # agent in both the skills and vanilla arms.
        assert "airbnb-asheville-short.csv" in user_content
        assert "neighbourhood, price" in user_content
        assert "Do NOT substitute" in user_content

    def test_no_dataset_context_when_no_data_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr("shinygen.generate.claude_code", lambda **kw: object())

        task = build_generation_task(
            user_prompt="Build a dashboard",
            agent="claude_code",
            framework_key="shiny_python",
            docker_context_dir=tmp_path,
        )

        sample_input = task.dataset[0].input
        assert not isinstance(sample_input, str)
        user_msgs = [m for m in sample_input if m.role == "user"]
        user_content = user_msgs[-1].content
        assert "DATASET(S) YOU MUST USE" not in user_content
