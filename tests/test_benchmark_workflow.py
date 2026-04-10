"""Static checks for the benchmark GitHub Actions workflow."""

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


def test_benchmark_workflow_accepts_generic_dispatch_inputs():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'dataset:' in workflow
    assert 'challenge:' in workflow
    assert 'benchmark_prompt:' in workflow
    assert 'quality_threshold:' in workflow
    assert 'max_iterations:' in workflow


def test_benchmark_workflow_uses_generic_benchmark_metadata():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert 'BENCHMARK_CHALLENGE' in workflow
    assert 'BENCHMARK_SLUG' in workflow
    assert 'shinygen-${{ needs.prepare.outputs.benchmark_slug }}' in workflow
    assert 'benchmark": os.environ["BENCHMARK_CHALLENGE"]' in workflow
    assert '# Benchmark:' in workflow