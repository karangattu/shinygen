import json
from pathlib import Path


def test_eval_runs_artifacts():
    base_dir = Path(__file__).resolve().parent.parent / "eval_runs"
    vanilla_dir = base_dir / "asheville_gemini_3.7_flash_vanilla"
    skills_dir = base_dir / "asheville_gemini_3.7_flash_skills"

    assert vanilla_dir.exists()
    assert skills_dir.exists()

    for arm_dir in [vanilla_dir, skills_dir]:
        assert (arm_dir / "app.py").is_file()
        assert (arm_dir / "airbnb-asheville-short.csv").is_file()
        assert (arm_dir / "screenshot_01_landing.png").is_file()

        summary_file = arm_dir / "run_summary.json"
        assert summary_file.is_file()

        with open(summary_file, encoding="utf-8") as f:
            data = json.load(f)
            assert "score" in data
            assert "scores" in data
            assert "requirement_fidelity" in data["scores"]
            assert "code_maintainability" in data["scores"]
            assert "visual_ux_quality" in data["scores"]
            assert "code_robustness" in data["scores"]
