"""Static checks for the benchmark GitHub Actions workflow."""

import json
from pathlib import Path

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "run-benchmark-matrix.yml"
)
QUICK_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "run-benchmark-quick.yml"
)
MULTI_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "run-benchmark-multi-model.yml"
)

BATCH_CONFIG_PATH = Path(__file__).resolve().parents[1] / "batch.json"


def test_benchmark_workflow_covers_python_and_r_with_visual_checks():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "framework:" in workflow
    assert "- shiny_python" in workflow
    assert "- shiny_r" in workflow
    assert '--framework "${{ matrix.framework }}"' in workflow
    assert '"${screenshot_flag}" \\' in workflow
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
    assert "- bike_share_stations.csv" in workflow
    assert "- library_usage.csv" in workflow
    assert "- health_inspection_scores.csv" in workflow
    assert "employee_retention.csv" not in workflow
    assert "e_commerce_sales.csv" not in workflow
    assert "marketing_campaigns.csv" not in workflow
    assert "supply_chain.csv" not in workflow
    assert "challenge:" in workflow
    assert "benchmark_prompt:" in workflow
    assert "quality_threshold:" in workflow
    assert "max_iterations:" in workflow


def test_benchmark_matrix_can_disable_screenshots_and_judges():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "enable_screenshot:" in workflow
    assert (
        'description: "Enable --screenshot (adds visual judging; slower & more expensive)"'
        in workflow
    )
    assert "enable_judges:" in workflow
    assert (
        'description: "Run the judge panel (uncheck to skip judging and only solve)"'
        in workflow
    )
    assert 'if [[ "${{ inputs.enable_judges }}" == "true" ]]; then' in workflow
    assert "needs_openai=1" in workflow
    assert 'case "${{ matrix.model.name }}" in' in workflow
    assert '[[ "${needs_anthropic}" -eq 1 && -z "${ANTHROPIC_API_KEY:-}" ]]' in workflow
    assert 'if [[ "${{ inputs.enable_screenshot }}" == "true" ]]; then' in workflow
    assert 'screenshot_flag="--no-screenshot"' in workflow
    assert 'screenshot_flag="--screenshot"' in workflow
    assert '"${screenshot_flag}" \\' in workflow


def test_benchmark_workflows_require_keys_for_configured_judge_providers():
    for path in (WORKFLOW_PATH, QUICK_WORKFLOW_PATH):
        workflow = path.read_text(encoding="utf-8")

        assert 'done <<< "${BENCHMARK_JUDGE_MODELS}"' in workflow
        assert "anthropic/*)" in workflow
        assert "openai/*)" in workflow


def test_benchmark_workflow_uses_generic_benchmark_metadata():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "BENCHMARK_CHALLENGE" in workflow
    assert "BENCHMARK_SLUG" in workflow
    assert "shinygen-${{ needs.prepare.outputs.benchmark_slug }}" in workflow
    assert 'benchmark": os.environ["BENCHMARK_CHALLENGE"]' in workflow
    assert "# Benchmark:" in workflow


def test_benchmark_workflows_use_gpt56_luna_judge():
    """Benchmarks default to a single visual judge: openai/gpt-5.6-luna.

    The workflows keep `BENCHMARK_JUDGE_MODELS` as a newline-separated list
    so additional judges can be added back later by editing one env var.
    """
    workflows = [
        WORKFLOW_PATH.read_text(encoding="utf-8"),
        QUICK_WORKFLOW_PATH.read_text(encoding="utf-8"),
    ]

    for workflow in workflows:
        assert "BENCHMARK_JUDGE_MODELS:" in workflow
        assert "openai/gpt-5.6-luna" in workflow
        # The generation step must expand the list into repeated --judge-model
        # flags rather than the old single-flag form, even with one entry, so
        # adding more judges later remains a one-line change.
        assert "BENCHMARK_JUDGE_MODEL " not in workflow
        assert '--judge-model "${BENCHMARK_JUDGE_MODEL}"' not in workflow
        assert "judge_args+=(--judge-model" in workflow


def test_benchmark_workflow_uses_sandbox_screenshots_without_runner_browser_install():
    """Benchmark jobs rely on the prebuilt sandbox images for screenshots.

    The runner should not download Playwright browsers or Shiny app runtime
    packages on every matrix cell.
    """
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "Install shinygen CLI on runner" in workflow
    assert 'uv pip install --system -e "."' in workflow
    assert 'uv pip install --system -e ".[screenshot]"' not in workflow
    assert "python -m playwright install --with-deps chromium" not in workflow
    assert 'SHINYGEN_REQUIRE_SCREENSHOTS_FOR_JUDGE: "1"' in workflow
    assert 'SHINYGEN_STRICT_SANDBOX_SCREENSHOT: "1"' in workflow
    assert "python -m pip install \\" not in workflow
    assert "install.packages(c(" not in workflow


def test_benchmark_workflow_runs_all_opus_generations_for_comparison():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: claude-opus-4-8" in workflow
    assert "name: claude-opus-4-7" not in workflow
    assert "name: claude-opus-4-6" not in workflow


def test_benchmark_workflow_includes_gpt55_in_generation_matrix():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: gpt-5.5" in workflow


def test_benchmark_workflows_include_all_documented_opencode_go_models():
    matrix_workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    quick_workflow = QUICK_WORKFLOW_PATH.read_text(encoding="utf-8")

    for model in [
        "glm-5.2",
        "glm-5.1",
        "kimi-k2.6",
        "kimi-k2.7-code",
        "mimo-v2.5",
        "mimo-v2.5-pro",
        "minimax-m2.5",
        "minimax-m2.7",
        "qwen3.7-max",
        "qwen3.6-plus",
        "deepseek-v4-pro",
        "deepseek-v4-flash",
    ]:
        assert f"name: {model}" in matrix_workflow
        assert f"- {model}" in quick_workflow

    assert "- qwen3.7-plus" in quick_workflow
    assert "OPENCODE_GO_API_KEY" in matrix_workflow
    assert "OPENCODE_GO_API_KEY" in quick_workflow


def test_benchmark_aggregate_validates_expected_matrix_cells():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "BENCHMARK_EXPECTED_FRAMEWORKS" in workflow
    assert "BENCHMARK_EXPECTED_MODELS" in workflow
    assert "BENCHMARK_EXPECTED_ARMS" in workflow
    assert "missing_matrix_cells" in workflow
    assert "benchmark_validation_failed.txt" in workflow


def test_benchmark_aggregate_expected_models_match_run_matrix():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: kimi-k2.7-code" in workflow
    assert "kimi-k2.7-code" in workflow
    assert "kimi-k2.5" not in workflow


def test_benchmark_aggregate_reports_screenshot_counts():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "screenshot_count" in workflow
    assert "| Screenshots |" in workflow


def test_benchmark_artifacts_report_generation_timing_and_iteration_usage():
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "generation_time_seconds" in workflow
    assert "iteration_usage" in workflow
    assert "| Generation Time |" in workflow
    assert "| Total Time |" in workflow
    assert "skills_gen_time" in workflow
    assert "vanilla_gen_time" in workflow
    assert "| Skills time |" in workflow
    assert "| Vanilla time |" in workflow


def test_benchmark_quick_artifacts_report_timing():
    workflow = QUICK_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "generation_time_seconds" in workflow
    assert "total_time_seconds" in workflow
    assert "| Gen Time (s) | Total Time (s) |" in workflow
    assert "skills_gen_time" in workflow
    assert "vanilla_gen_time" in workflow
    assert "Skills time:" in workflow
    assert "Vanilla time:" in workflow


def test_benchmark_multi_model_artifacts_report_timing():
    workflow = MULTI_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "generation_time" in workflow
    assert "total_time" in workflow
    assert "| Gen Time (s) | Total Time (s) |" in workflow
    assert "benchmark_total_time = sum" in workflow
    assert "Total" in workflow


def test_local_batch_uses_same_pinned_judge_as_benchmark_workflow():
    batch_config = json.loads(BATCH_CONFIG_PATH.read_text(encoding="utf-8"))

    assert batch_config
    for entry in batch_config:
        assert entry["judge_model"] == "openai/gpt-5.6-luna"


def test_benchmark_workflows_support_gemini_flash_37():
    for path in (WORKFLOW_PATH, QUICK_WORKFLOW_PATH, MULTI_WORKFLOW_PATH):
        workflow = path.read_text(encoding="utf-8")
        assert "gemini-3.7-flash" in workflow
        assert "GEMINI_API_KEY" in workflow
        assert "needs_gemini" in workflow


def test_benchmark_workflows_support_latest_anthropic_models():
    for path in (WORKFLOW_PATH, QUICK_WORKFLOW_PATH, MULTI_WORKFLOW_PATH):
        workflow = path.read_text(encoding="utf-8")
        assert "claude-opus-4-8" in workflow
        assert "claude-sonnet-5" in workflow
        assert "claude-haiku-4-5" in workflow
