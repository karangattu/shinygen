"""Static checks for the Asheville benchmark GitHub Actions workflow."""

from pathlib import Path


WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "run-airbnb-asheville-benchmark.yml"
)


def test_benchmark_workflow_covers_python_and_r_with_visual_checks():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'framework:' in workflow
    assert '- shiny_python' in workflow
    assert '- shiny_r' in workflow
    assert '--framework "${{ matrix.framework }}"' in workflow
    assert '--screenshot \\' in workflow
    assert 'Rscript -e' in workflow
    assert 'install.packages' in workflow


def test_benchmark_artifacts_include_framework_dimension():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert '${{ matrix.framework }}' in workflow
    assert 'framework' in workflow
    assert 'artifact_dir' in workflow


def test_benchmark_workflow_publishes_comparison_table_to_step_summary():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'GITHUB_STEP_SUMMARY' in workflow
    assert 'INDEX.md' in workflow
    assert 'cat "${root}/INDEX.md" >> "${GITHUB_STEP_SUMMARY}"' in workflow