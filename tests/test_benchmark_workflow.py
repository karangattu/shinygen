"""Static checks for the benchmark GitHub Actions workflow."""

import json
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "run-benchmark-matrix.yml"
)

BATCH_CONFIG_PATH = Path(__file__).resolve().parents[1] / "batch.json"


def test_benchmark_workflow_covers_python_and_r_with_visual_checks():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "framework:" in workflow
    assert "- shiny_python" in workflow
    assert "- shiny_r" in workflow
    assert '--framework "${{ matrix.framework }}"' in workflow
    assert "--screenshot \\" in workflow
    assert "SHINYGEN_SANDBOX_PYTHON_IMAGE" in workflow
    assert "SHINYGEN_SANDBOX_R_IMAGE" in workflow
    assert 'docker pull "${image}"' in workflow


def test_benchmark_artifacts_include_framework_dimension():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "${{ matrix.framework }}" in workflow
    assert "framework" in workflow
    assert "artifact_dir" in workflow


def test_benchmark_workflow_publishes_comparison_table_to_step_summary():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "GITHUB_STEP_SUMMARY" in workflow
    assert "INDEX.md" in workflow
    assert 'cat "${root}/INDEX.md" >> "${GITHUB_STEP_SUMMARY}"' in workflow


def test_benchmark_workflow_accepts_generic_dispatch_inputs():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "dataset:" in workflow
    assert "type: choice" in workflow
    assert "- airbnb-asheville-short.csv" in workflow
    assert "- air_quality.csv" in workflow
    assert "challenge:" in workflow
    assert "benchmark_prompt:" in workflow
    assert "quality_threshold:" in workflow
    assert "max_iterations:" in workflow


def test_benchmark_workflow_uses_generic_benchmark_metadata():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "BENCHMARK_CHALLENGE" in workflow
    assert "BENCHMARK_SLUG" in workflow
    assert "shinygen-${{ needs.prepare.outputs.benchmark_slug }}" in workflow
    assert 'benchmark": os.environ["BENCHMARK_CHALLENGE"]' in workflow
    assert "# Benchmark:" in workflow


def test_benchmark_workflow_uses_dual_judge_panel():
    """Benchmarks default to a panel of two judges (anthropic + openai) so
    every score is the average of an independent Claude and GPT review.
    Keeping both vendors in the panel cancels per-vendor bias.
    """
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "BENCHMARK_JUDGE_MODELS:" in workflow
    assert "anthropic/claude-sonnet-4-6" in workflow
    assert "openai/gpt-5.4-mini-2026-03-17" in workflow
    # The generation step must expand the panel into repeated --judge-model
    # flags rather than the old single-flag form.
    assert "BENCHMARK_JUDGE_MODEL " not in workflow
    assert '--judge-model "${BENCHMARK_JUDGE_MODEL}"' not in workflow
    assert "judge_args+=(--judge-model" in workflow


def test_benchmark_workflow_installs_screenshot_extras_for_host_fallback():
    """The runner must have Playwright + Shiny runtime so the host-side
    screenshot fallback in iterate.py can capture an image when the agent
    fails to produce one in the sandbox.
    """
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "Install shinygen CLI on runner" in workflow
    assert 'python -m pip install -e ".[screenshot]"' in workflow
    assert "python -m playwright install --with-deps chromium" in workflow
    assert 'SHINYGEN_REQUIRE_SCREENSHOTS_FOR_JUDGE: "1"' in workflow
    for package in [
        "shinyswatch",
        "great-tables",
        "folium",
        "pydeck",
        "lonboard",
        "geopandas",
    ]:
        assert package in workflow
    # R packages are NOT reinstalled on the runner — host fallback for R
    # is best-effort, but the benchmark will no longer accept code-only
    # judging when screenshot mode is enabled.
    assert "install.packages(c(" not in workflow


def test_benchmark_workflow_runs_both_opus_generations_for_comparison():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: claude-opus-4-6" in workflow
    assert "name: claude-opus-4-7" in workflow


def test_benchmark_workflow_includes_gpt55_in_generation_matrix():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: gpt-5.5" in workflow


def test_benchmark_aggregate_validates_expected_matrix_cells():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "BENCHMARK_EXPECTED_FRAMEWORKS" in workflow
    assert "BENCHMARK_EXPECTED_MODELS" in workflow
    assert "BENCHMARK_EXPECTED_ARMS" in workflow
    assert "missing_matrix_cells" in workflow
    assert "benchmark_validation_failed.txt" in workflow


def test_benchmark_aggregate_reports_screenshot_counts():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "screenshot_count" in workflow
    assert "| Screenshots |" in workflow


def test_local_batch_uses_same_pinned_judge_as_benchmark_workflow():
    batch_config = json.loads(BATCH_CONFIG_PATH.read_text(encoding="utf-8"))

    assert batch_config
    for entry in batch_config:
        assert entry["judge_model"] == "openai/gpt-5.4-mini-2026-03-17"
