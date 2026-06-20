"""
Main orchestration loop: generate → extract → screenshot → judge → refine.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from .config import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_QUALITY_THRESHOLD,
    FRAMEWORKS,
    OPENCODE_GO_BASE_URL,
    SANDBOX_IMAGE_ENV_DEFAULTS,
    _build_lmstudio_model,
    find_free_port,
    is_lmstudio_model,
    is_opencode_go_anthropic_model,
    opencode_go_anthropic_model_name,
    preflight_checks,
    prepare_model_environment,
    resolve_framework,
    resolve_model,
)
from .extract import _read_zip_member, extract_from_log
from .pricing import Timer, UsageStats, calculate_value_score

if TYPE_CHECKING:
    from inspect_ai.log import EvalLog
    from inspect_ai.tool import Skill

logger = logging.getLogger(__name__)
AGENT_LAST_SCREENSHOT_NAME = "agent_last_screenshot.png"
RUNTIME_VALIDATION_STARTUP_WAIT = 6
RUNTIME_VALIDATION_TIMEOUT = 45
RUNTIME_LOG_SUMMARY_LIMIT = 8_000


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


def _trim_runtime_logs(logs: str, limit: int = RUNTIME_LOG_SUMMARY_LIMIT) -> str:
    """Return the tail of startup logs for prompts and run summaries."""
    stripped = logs.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[-limit:]


@dataclass
class GenerationResult:
    """Result of a generation + refinement pipeline."""

    app_dir: Path | None = None
    source_code: str = ""
    score: float = 0.0
    quality_score: float = 0.0
    value_score: float = 0.0
    iterations: int = 0
    passed: bool = False
    judge_feedback: dict | None = None
    score_breakdown: dict | None = None
    screenshot_paths: list[Path] = field(default_factory=list)
    runtime_valid: bool | None = None
    runtime_logs: str = ""
    error: str | None = None
    usage: UsageStats = field(default_factory=UsageStats)


def _write_run_summary(
    output_path: Path,
    result: GenerationResult,
    *,
    prompt: str,
    requested_model: str,
    resolved_model_id: str,
    agent: str,
    framework_key: str,
    artifact_name: str,
    judge_models: list[str],
    data_file_names: list[str],
    use_skills: bool = True,
    web_fetch: bool = True,
) -> Path:
    """Persist structured run metadata for workflow artifacts."""
    summary = {
        "prompt": prompt,
        "model": {
            "requested": requested_model,
            "resolved_id": resolved_model_id,
            "agent": agent,
        },
        "framework": framework_key,
        "artifact_name": artifact_name,
        "judge_model": judge_models[0] if len(judge_models) == 1 else None,
        "judge_models": list(judge_models),
        "arm": "skills" if use_skills else "vanilla",
        "use_skills": use_skills,
        "web_fetch": web_fetch,
        "passed": result.passed,
        "score": result.score,
        "quality_score": result.quality_score,
        "value_score": result.value_score,
        "score_breakdown": result.score_breakdown,
        "iterations": result.iterations,
        "error": result.error,
        "data_files": sorted(data_file_names),
        "screenshots": [path.name for path in result.screenshot_paths],
        "runtime_validation": {
            "passed": result.runtime_valid,
            "logs_tail": _trim_runtime_logs(result.runtime_logs),
        },
        "judge_feedback": result.judge_feedback,
        "usage": result.usage.to_dict(),
    }
    summary_path = output_path / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def _extract_generation_usage_rows(log: "EvalLog") -> list[dict[str, object]]:
    """Extract model usage rows from an Inspect eval log object."""
    stats = getattr(log, "stats", None)
    model_usage = getattr(stats, "model_usage", None) or {}
    rows: list[dict[str, object]] = []

    for model_name, usage in model_usage.items():
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        cache_write = int(getattr(usage, "input_tokens_cache_write", 0) or 0)
        cache_read = int(getattr(usage, "input_tokens_cache_read", 0) or 0)
        total_cost = getattr(usage, "total_cost", None)
        cost_override: float | None = None
        if total_cost is not None:
            try:
                cost_override = float(total_cost)
            except (TypeError, ValueError):
                cost_override = None

        rows.append(
            {
                "model": str(model_name),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_write_tokens": cache_write,
                "cache_read_tokens": cache_read,
                "cost_override": cost_override,
            }
        )

    return rows


def _runtime_validation_command(
    *,
    framework_key: str,
    artifact_name: str,
    port: int,
    wait_seconds: int = RUNTIME_VALIDATION_STARTUP_WAIT,
    python_executable: str = "python3",
) -> str:
    """Return a shell command that starts an app and prints startup logs."""
    quoted_artifact = shlex.quote(artifact_name)
    log_path = "/tmp/shinygen_runtime_validation.log"

    if framework_key == "shiny_r":
        start_cmd = (
            f"Rscript -e \"shiny::runApp('{artifact_name}', port={port}, "
            'launch.browser=FALSE)"'
        )
        process_pattern = f"Rscript.*{artifact_name}.*{port}"
    else:
        start_cmd = (
            f"{shlex.quote(python_executable)} -m shiny run {quoted_artifact} "
            f"--port {port}"
        )
        process_pattern = f"shiny run {artifact_name} --port {port}"

    return f"""
set +e
rm -f {log_path}
app_pid=""
cleanup() {{
  if [ -n "${{app_pid:-}}" ]; then
    kill "$app_pid" 2>/dev/null || true
  fi
  pkill -f {shlex.quote(process_pattern)} 2>/dev/null || true
}}
trap cleanup EXIT
({start_cmd}) > {log_path} 2>&1 &
app_pid=$!
sleep {wait_seconds}
if kill -0 "$app_pid" 2>/dev/null; then
  echo "Startup validation: process is still running after {wait_seconds}s."
  tail -n 160 {log_path} || true
  exit 0
fi
wait "$app_pid"
status=$?
echo "Startup validation: process exited with status $status."
tail -n 160 {log_path} || true
exit "$status"
""".strip()


def _runtime_logs_indicate_failure(logs: str) -> bool:
    """Return True when startup logs contain a Python/R exception signature."""
    failure_markers = (
        "Traceback (most recent call last):",
        "TypeError:",
        "ValueError:",
        "NameError:",
        "ImportError:",
        "ModuleNotFoundError:",
        "SyntaxError:",
        "Error in ",
        "Execution halted",
    )
    return any(marker in logs for marker in failure_markers)


def _validate_generated_app_runtime(
    app_dir: Path,
    framework_key: str,
    artifact_name: str,
    port: int,
    *,
    model_id: str | None = None,
) -> tuple[bool, str]:
    """Start a generated app and return (startup_ok, logs).

    By default the app is started inside the pre-built sandbox Docker image
    (matching the generation environment). For LM Studio models the Docker
    step is skipped and validation runs directly on the host with the
    project venv, since those models never use a sandbox.
    """
    command = _runtime_validation_command(
        framework_key=framework_key,
        artifact_name=artifact_name,
        port=port,
    )

    use_docker = not (model_id and is_lmstudio_model(model_id))
    env_var, default_image = SANDBOX_IMAGE_ENV_DEFAULTS.get(framework_key, ("", ""))
    image = os.environ.get(env_var, default_image) if env_var else ""
    if use_docker and image:
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{app_dir.resolve()}:/home/user/project",
            "-w",
            "/home/user/project",
            image,
            "sh",
            "-lc",
            command,
        ]
        try:
            completed = subprocess.run(
                docker_cmd,
                text=True,
                capture_output=True,
                timeout=RUNTIME_VALIDATION_TIMEOUT,
            )
            output = "\n".join(
                part for part in (completed.stdout, completed.stderr) if part
            ).strip()
            return (
                completed.returncode == 0
                and not _runtime_logs_indicate_failure(output),
                output,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning(
                "Docker runtime validation failed (%s); falling back to host",
                exc,
            )

    try:
        host_command = _runtime_validation_command(
            framework_key=framework_key,
            artifact_name=artifact_name,
            port=port,
            python_executable=sys.executable,
        )
        completed = subprocess.run(
            ["sh", "-lc", host_command],
            cwd=app_dir,
            text=True,
            capture_output=True,
            timeout=RUNTIME_VALIDATION_TIMEOUT,
        )
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(
            part
            for part in (
                "Startup validation timed out.",
                exc.stdout or "",
                exc.stderr or "",
            )
            if part
        )
        return False, output

    output = "\n".join(
        part for part in (completed.stdout, completed.stderr) if part
    ).strip()
    return (
        completed.returncode == 0 and not _runtime_logs_indicate_failure(output),
        output,
    )


def _generation_extra_config(agent: str) -> dict[str, object]:
    """Return provider-specific generation settings."""
    if agent == "claude_code":
        # Medium reasoning keeps Claude 4.6 on adaptive thinking without
        # pushing generation into long reconnaissance-heavy runs.
        return {"reasoning_effort": "medium"}
    return {}


def _log_hit_output_token_limit(log_path: Path | None) -> bool:
    """Return True when an eval log shows a token-limit continuation prompt."""
    if log_path is None or not log_path.exists():
        return False

    try:
        with zipfile.ZipFile(log_path) as archive:
            sample_files = sorted(
                name
                for name in archive.namelist()
                if name.startswith("samples/") and name.endswith(".json")
            )

            for sample_file in sample_files:
                sample = json.loads(
                    _read_zip_member(archive, archive.getinfo(sample_file))
                )
                for message in sample.get("messages", []):
                    content = message.get("content")
                    if isinstance(content, str):
                        texts = [content]
                    elif isinstance(content, list):
                        texts = [
                            part.get("text", "")
                            for part in content
                            if isinstance(part, dict)
                            and isinstance(part.get("text"), str)
                        ]
                    else:
                        texts = []

                    if any("Output token limit hit" in text for text in texts):
                        return True
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        logger.debug(
            "Failed to inspect eval log %s for token limits: %s", log_path, exc
        )

    return False


def _recover_code_from_eval_logs(
    logs_dir: Path,
    artifact_name: str,
) -> tuple[str | None, Path | None]:
    """Recover app code from the newest copied eval log when sandbox output is missing."""
    if not logs_dir.exists():
        return None, None

    log_candidates = sorted(logs_dir.rglob("*.eval"))
    log_path = _latest_path(log_candidates)
    if log_path is None:
        return None, None

    try:
        code_map = extract_from_log(log_path)
    except Exception as exc:
        logger.debug("Failed to recover code from eval log %s: %s", log_path, exc)
        return None, log_path

    if not code_map:
        return None, log_path

    if len(code_map) == 1:
        return next(iter(code_map.values())), log_path
    if "shinygen/generate" in code_map:
        return code_map["shinygen/generate"], log_path
    return next(iter(code_map.values())), log_path


def _latest_path(paths: list[Path]) -> Path | None:
    """Return the most recently modified path from a non-empty list."""
    if not paths:
        return None
    return max(paths, key=lambda path: (path.stat().st_mtime_ns, str(path)))


def _find_agent_screenshot_in_results(results_dir: Path | None) -> Path | None:
    """Find the raw agent landing-page screenshot from the results volume.

    Used as a "did the agent screenshot anything at all?" signal. The full
    multi-tab capture is gathered separately by
    :func:`_collect_agent_screenshots_in_results`.
    """
    if results_dir is None or not results_dir.exists():
        return None

    # Prefer the new numbered landing screenshot, then any legacy single-file
    # capture, then anything else that looks like a screenshot.
    landing_matches = [
        path for path in results_dir.rglob("screenshot_01_*.png") if path.is_file()
    ]
    preferred = _latest_path(landing_matches)
    if preferred is not None:
        return preferred

    full_page_matches = [
        path for path in results_dir.rglob("screenshot.png") if path.is_file()
    ]
    preferred = _latest_path(full_page_matches)
    if preferred is not None:
        return preferred

    fallback_matches = [
        path for path in results_dir.rglob("screenshot*.png") if path.is_file()
    ]
    fallback_matches.extend(
        path for path in results_dir.rglob(AGENT_LAST_SCREENSHOT_NAME) if path.is_file()
    )
    return _latest_path(fallback_matches)


def _collect_agent_screenshots_in_results(results_dir: Path | None) -> list[Path]:
    """Find every per-tab screenshot the agent captured in the sandbox.

    Returns an ordered list (landing first, then tabs). Multi-tab dashboards
    benefit because the judge sees every panel instead of only the first
    rendered view. Falls back to the legacy single ``screenshot.png`` when
    the agent only emitted one image.
    """
    if results_dir is None or not results_dir.exists():
        return []

    # New layout: ``screenshot_01_landing.png``, ``screenshot_02_<slug>.png``...
    numbered = sorted(
        (
            path
            for path in results_dir.rglob("screenshot_[0-9][0-9]_*.png")
            if path.is_file()
        ),
        key=lambda p: p.name,
    )
    if numbered:
        return numbered

    # Legacy layout: a single ``screenshot.png`` or the explicit
    # ``agent_last_screenshot.png`` requested by older prompts.
    legacy = [
        path
        for name in ("screenshot.png", AGENT_LAST_SCREENSHOT_NAME)
        for path in results_dir.rglob(name)
        if path.is_file()
    ]
    latest_legacy = _latest_path(legacy)
    if latest_legacy is not None:
        return [latest_legacy]

    return []


def _copy_agent_screenshot_artifact(
    output_path: Path,
    *,
    results_dir: Path | None,
    log_path: Path | None,
) -> Path | None:
    """Copy every coding-agent screenshot into the model artifact directory.

    Returns the canonical landing-page screenshot path
    (``agent_last_screenshot.png``) for backwards compatibility with callers
    that only need a "did the agent screenshot?" signal. All per-tab
    captures are also copied with their original numbered names so the
    judge can pick them up in :func:`_resolve_judge_screenshot_paths`.
    """
    destination = output_path / AGENT_LAST_SCREENSHOT_NAME

    captures = _collect_agent_screenshots_in_results(results_dir)
    if captures:
        # Preserve the numbered per-tab files alongside the canonical
        # ``agent_last_screenshot.png`` (which mirrors the landing page
        # for legacy tooling that expects exactly one filename).
        for source in captures:
            target = output_path / source.name
            try:
                shutil.copy2(source, target)
            except Exception as exc:  # pragma: no cover - filesystem dependent
                logger.warning("Failed to copy %s -> %s: %s", source, target, exc)
        try:
            shutil.copy2(captures[0], destination)
        except Exception as exc:  # pragma: no cover - filesystem dependent
            logger.warning(
                "Failed to copy landing screenshot to %s: %s", destination, exc
            )
        return destination

    if log_path is not None and log_path.exists():
        from .extract import extract_last_image_attachment

        extracted = extract_last_image_attachment(log_path, destination)
        if extracted is not None:
            return extracted

    if destination.exists():
        return destination

    return None


def _gather_numbered_screenshots(output_path: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in output_path.glob("screenshot_[0-9][0-9]_*.png")
            if path.is_file()
        ),
        key=lambda p: p.name,
    )


def _gather_legacy_screenshots(output_path: Path) -> list[Path]:
    legacy = output_path / AGENT_LAST_SCREENSHOT_NAME
    if legacy.exists():
        return [legacy]

    fallback = output_path / "screenshot.png"
    if fallback.exists():
        return [fallback]

    return []


def _gather_existing_screenshots(output_path: Path) -> list[Path]:
    """Return every per-tab screenshot already present in ``output_path``.

    Numbered ``screenshot_NN_<slug>.png`` files come first (landing then
    tabs in DOM order). The canonical ``agent_last_screenshot.png`` is
    only returned when no numbered captures exist, so the judge never sees
    the same landing image twice.
    """
    numbered = _gather_numbered_screenshots(output_path)
    if numbered:
        return numbered

    return _gather_legacy_screenshots(output_path)


def _resolve_judge_screenshot_paths(
    output_path: Path,
    eval_dir: Path,
    framework_key: str,
    port: int,
    *,
    allow_host_fallback: bool | None = None,
) -> list[Path]:
    """Return screenshots for judging / artifact capture.

    Preference order:
    1. Sandbox-captured per-tab series (``screenshot_01_landing.png``,
         ``screenshot_02_<slug>.png``, ...).
    2. Host-side capture of the extracted code (best-effort fallback when
         numbered sandbox screenshots are missing — e.g. agent SIGTERMed mid-task).
       Captures every tab via the same multi-view helper.
     3. Legacy single ``agent_last_screenshot.png`` / ``screenshot.png`` only
         when multi-tab capture is unavailable.
     4. Raise ``RuntimeError`` so the caller can decide whether to retry or
       proceed with code-only judging.

    ``allow_host_fallback`` controls step 2:
      - ``None`` (default): honour ``SHINYGEN_STRICT_SANDBOX_SCREENSHOT`` —
        when set, the host-side fallback is disabled so a judge never
        scores a host-rendered image instead of the agent's own.
      - ``True``: always attempt host-side capture, ignoring the strict
        flag. Use this when the screenshot is an artifact rather than a
        judge input (i.e. ``--screenshot`` with no judge), where producing
        *any* screenshot is better than none.
      - ``False``: never attempt host-side capture.

    Multi-image judging matters because multi-tab dashboards used to be
    judged on the landing page only, biasing visual_ux_quality scores
    against ``page_navbar`` / ``navset_*`` apps that hide secondary
    content behind tabs.
    """
    numbered = _gather_numbered_screenshots(output_path)
    if numbered:
        logger.info(
            "Using %d agent screenshot(s) for judge: %s",
            len(numbered),
            ", ".join(p.name for p in numbered),
        )
        return numbered

    legacy = _gather_legacy_screenshots(output_path)

    if allow_host_fallback is None:
        allow_host_fallback = not _env_truthy("SHINYGEN_STRICT_SANDBOX_SCREENSHOT")
    if allow_host_fallback:
        try:
            from . import screenshot as host_screenshot

            logger.warning(
                "Sandbox screenshot missing; attempting host-side capture "
                "fallback (framework=%s, port=%d)",
                framework_key,
                port,
            )
            captured = host_screenshot.take_screenshots(eval_dir, framework_key, port)
        except Exception as exc:  # pragma: no cover - host env dependent
            logger.warning("Host-side screenshot fallback raised: %s", exc)
            captured = []

        # ``take_screenshots`` now returns a list of paths (one per tab).
        if isinstance(captured, Path):
            captured = [captured]
        captured = [Path(p) for p in (captured or []) if Path(p).exists()]

        if captured:
            destinations: list[Path] = []
            for source in captured:
                target = output_path / source.name
                try:
                    if source.resolve() != target.resolve():
                        shutil.copy2(source, target)
                    destinations.append(target)
                except Exception as exc:  # pragma: no cover - filesystem dependent
                    logger.warning(
                        "Failed to copy host screenshot %s -> %s: %s",
                        source,
                        target,
                        exc,
                    )
                    destinations.append(source)
            # Keep the legacy single-file name pointing at the landing
            # capture so older inspection tools still work.
            try:
                shutil.copy2(destinations[0], output_path / AGENT_LAST_SCREENSHOT_NAME)
            except Exception as exc:  # pragma: no cover
                logger.debug("Could not copy landing alias: %s", exc)
            logger.info(
                "Using %d host-side fallback screenshot(s) for judge: %s",
                len(destinations),
                ", ".join(p.name for p in destinations),
            )
            return destinations

        if legacy:
            logger.warning(
                "Host-side screenshot fallback did not produce an image; "
                "falling back to the legacy single screenshot."
            )
        else:
            logger.warning(
                "Host-side screenshot fallback did not produce an image; "
                "judge will need to operate without a screenshot."
            )

    if legacy:
        logger.warning(
            "Using legacy single screenshot for judge after multi-tab capture "
            "was unavailable: %s",
            ", ".join(p.name for p in legacy),
        )
        return legacy

    raise RuntimeError(
        "Missing sandbox screenshot: expected "
        f"{AGENT_LAST_SCREENSHOT_NAME} in {output_path}. "
        "Host-side fallback also failed."
    )


def _copy_output_screenshots(
    output_path: Path, screenshot_paths: list[Path]
) -> list[Path]:
    """Copy screenshots into the output directory and return normalized paths."""
    output_screenshots: list[Path] = []

    for screenshot_path in screenshot_paths:
        if not screenshot_path.exists():
            continue

        destination = output_path / screenshot_path.name
        if screenshot_path.resolve() != destination.resolve():
            shutil.copy2(screenshot_path, destination)
        output_screenshots.append(destination)

    return output_screenshots


def generate_and_refine(
    prompt: str,
    model: str,
    framework: str = "shiny_python",
    output_dir: str | Path = "output",
    skills_dir: str | Path | None = None,
    data_files: dict[str, str] | None = None,
    screenshot: bool = False,
    judge_model: str | Sequence[str] | None = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
    web_fetch: bool = True,
    use_skills: bool = True,
    port: int | None = None,
    verbose: bool = False,
) -> GenerationResult:
    """Generate a Shiny app with optional iterative refinement.

    This is the primary orchestration function. It:
    1. Generates an app using an LLM agent in a Docker sandbox.
    2. Extracts the generated code from the eval log.
    3. Optionally takes screenshots of the running app.
    4. Optionally judges quality with an LLM and refines.
    5. Copies the final app to the output directory.

    Args:
        prompt: Natural language description of the desired app.
        model: Model alias or full model ID (e.g., "claude-sonnet").
        framework: Target framework ("shiny_python" or "shiny_r").
        output_dir: Where to save the final app.
        skills_dir: Path to custom skill files to inject.
        data_files: Dict of {filename: content} for data files.
        screenshot: Whether to take screenshots for visual evaluation.
        judge_model: Model(s) to use for quality judging. Pass a single
            model ID/alias for the classic single-judge flow, or pass a
            sequence (e.g. ``["claude-sonnet", "openai/gpt-5.4-mini-..."]``)
            to run a panel of judges and average their scores per
            criterion. ``None`` skips judging entirely.
        max_iterations: Maximum refinement iterations.
        quality_threshold: Minimum value-adjusted score to accept (1-10
            scale) when judging is enabled. Raw judge quality is preserved
            separately on ``GenerationResult.quality_score``.
        web_fetch: Allow web search tools in the sandbox (default: True).
        use_skills: When True (default), inject the bundled framework skill
            (and any ``skills_dir``) into the agent context. When False, run
            a vanilla baseline with no skills loaded — used for
            control/treatment benchmarks comparing skill gains.
        port: Port for running the app during screenshots.
        verbose: Enable verbose logging.

    Returns:
        GenerationResult with the final app and metadata.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Resolve configuration
    framework_key = resolve_framework(framework)
    agent, model_id = resolve_model(model)
    prepare_model_environment(model_id)

    # Pre-flight: Docker running + API key present
    preflight_checks(agent, model_id)

    if judge_model:
        if isinstance(judge_model, str):
            judge_inputs: list[str] = [judge_model]
        else:
            judge_inputs = [m for m in judge_model if m]
        judge_models = [resolve_model(m)[1] for m in judge_inputs]
    else:
        judge_models = []
    fw = FRAMEWORKS[framework_key]
    artifact_name = fw["primary_artifact"]
    effective_port = port or find_free_port()

    result = GenerationResult()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load skills (skipped entirely when use_skills=False so we have a
    # truly vanilla baseline arm for control/treatment benchmarks).
    from .skills import load_default_skills, load_skill_files

    skills: list[Skill] = []
    if use_skills:
        skills.extend(load_default_skills(framework_key))
        if skills_dir:
            skills.extend(load_skill_files(Path(skills_dir)))
    elif skills_dir:
        logger.info(
            "use_skills=False: ignoring --skills-dir %s for vanilla baseline",
            skills_dir,
        )

    logger.info(
        "Starting generation: model=%s, agent=%s, framework=%s",
        model_id,
        agent,
        framework_key,
    )

    current_prompt = prompt
    best_code: str | None = None
    best_score: float = 0.0
    best_quality_score: float = 0.0
    best_feedback: dict | None = None
    best_score_breakdown: dict | None = None
    best_runtime_valid: bool | None = None
    best_runtime_logs: str = ""

    for iteration in range(1, max_iterations + 1):
        logger.info("=== Iteration %d / %d ===", iteration, max_iterations)
        result.iterations = iteration

        # --- Step 1: Generate (with retry on no-code-extracted) ---
        from .prompts import build_truncation_retry_prompt

        code: str | None = None
        generation_usage_rows: list[dict[str, object]] = []
        # 3 attempts before any artifact exists: original prompt, direct-write
        # retry on truncation, and one more direct-write attempt if needed.
        # Once we already have a fallback app from an earlier iteration, avoid
        # spending another full benchmark window on repeated no-code retries.
        max_retries = 1 if best_code is not None else 3
        prompt_for_attempt = current_prompt
        hit_output_token_limit = False
        for attempt in range(1, max_retries + 1):
            if screenshot:
                # Clear stale screenshots from previous attempts so the
                # judge never sees images from a discarded iteration.
                (output_path / AGENT_LAST_SCREENSHOT_NAME).unlink(missing_ok=True)
                (output_path / "screenshot.png").unlink(missing_ok=True)
                for stale in output_path.glob("screenshot_[0-9][0-9]_*.png"):
                    stale.unlink(missing_ok=True)

            with Timer() as gen_timer:
                code, generation_usage_rows, hit_output_token_limit = _run_generation(
                    prompt_for_attempt,
                    agent,
                    model_id,
                    framework_key,
                    data_files,
                    skills,
                    web_fetch,
                    iteration,
                    screenshot,
                    output_path,
                    use_skills=use_skills,
                )
            result.usage.add_time(
                "generate",
                gen_timer.elapsed,
                iteration=iteration,
                attempt=attempt,
            )
            for row in generation_usage_rows:
                result.usage.add(
                    stage="generate",
                    model=str(row.get("model", model_id)),
                    input_tokens=int(row.get("input_tokens", 0) or 0),
                    output_tokens=int(row.get("output_tokens", 0) or 0),
                    elapsed=0.0,
                    iteration=iteration,
                    cost_override=row.get("cost_override"),
                    cache_write_tokens=int(row.get("cache_write_tokens", 0) or 0),
                    cache_read_tokens=int(row.get("cache_read_tokens", 0) or 0),
                )
            if code is not None:
                if (
                    hit_output_token_limit
                    and screenshot
                    and not (output_path / AGENT_LAST_SCREENSHOT_NAME).exists()
                ):
                    logger.warning(
                        "Iteration %d: Output token limit hit and screenshot missing, treating extraction as failed",
                        iteration,
                    )
                    code = None
                else:
                    break
            if hit_output_token_limit and attempt < max_retries:
                logger.warning(
                    "Iteration %d: Output token limit hit before artifact creation; retrying with direct-write prompt",
                    iteration,
                )
                prompt_for_attempt = build_truncation_retry_prompt(
                    current_prompt,
                    framework_key,
                )
            if attempt < max_retries:
                logger.warning(
                    "Iteration %d: No code extracted (attempt %d/%d), retrying...",
                    iteration,
                    attempt,
                    max_retries,
                )

        if code is None:
            logger.warning("Iteration %d: No code extracted", iteration)
            if best_code:
                break
            if iteration == max_iterations:
                result.error = "Failed to extract app code from any iteration"
                break
            if hit_output_token_limit:
                current_prompt = build_truncation_retry_prompt(
                    current_prompt,
                    framework_key,
                )
            continue

        logger.info("Iteration %d: Extracted %d chars of code", iteration, len(code))

        # --- Step 2: Write to temp dir for evaluation ---
        eval_dir = Path(tempfile.mkdtemp(prefix=f"shinygen_eval_{iteration}_"))
        (eval_dir / artifact_name).write_text(code, encoding="utf-8")

        # Copy data files alongside
        if data_files:
            for fname, content in data_files.items():
                (eval_dir / fname).write_text(content, encoding="utf-8")

        # --- Step 3: Runtime Validation ---
        runtime_valid, runtime_logs = _validate_generated_app_runtime(
            eval_dir,
            framework_key,
            artifact_name,
            effective_port,
            model_id=model_id,
        )
        result.runtime_valid = runtime_valid
        result.runtime_logs = runtime_logs
        if runtime_valid:
            logger.info(
                "Iteration %d: Runtime validation passed; captured startup logs",
                iteration,
            )
        else:
            logger.warning(
                "Iteration %d: Runtime validation failed; captured startup logs:\n%s",
                iteration,
                runtime_logs,
            )

        if not runtime_valid:
            if best_runtime_valid is not True:
                best_code = code
                best_runtime_valid = False
                best_runtime_logs = runtime_logs
                best_score = 0.0
                best_quality_score = 0.0

            if iteration < max_iterations:
                from .prompts import build_runtime_refinement_prompt

                current_prompt = build_runtime_refinement_prompt(
                    prompt,
                    previous_code=code,
                    runtime_logs=runtime_logs,
                    iteration=iteration,
                )
                logger.info(
                    "Preparing runtime-log refinement prompt for next iteration"
                )
                continue

            if best_runtime_valid is not True:
                result.error = (
                    "Failed runtime validation after "
                    f"{iteration} iteration(s). See runtime_validation.logs_tail "
                    "in run_summary.json for startup logs."
                )
            result.passed = False
            break

        # --- Step 3.5: Screenshots (host-side, for external judge) ---
        screenshot_paths: list[Path] = []
        if screenshot:
            # When a judge is configured, honour SHINYGEN_STRICT_SANDBOX_SCREENSHOT
            # so the judge never scores a host-rendered image. When there is no
            # judge, the screenshot is an artifact for the user, not a judge
            # input — so always allow the host-side fallback to produce one
            # from the extracted code (e.g. when the agent was SIGTERM'd
            # before it could take its own screenshot).
            host_fallback = True if not judge_models else None
            try:
                screenshot_paths = _resolve_judge_screenshot_paths(
                    output_path,
                    eval_dir,
                    framework_key,
                    effective_port,
                    allow_host_fallback=host_fallback,
                )
                logger.info(
                    "Iteration %d: Captured %d screenshots",
                    iteration,
                    len(screenshot_paths),
                )
            except RuntimeError as exc:
                # Screenshots are only consumed by the judge. When there are
                # no judges, a missing screenshot (e.g. the agent was
                # SIGTERM'd before taking one) must not fail an otherwise
                # successful run — the generated app is still usable.
                if judge_models and _env_truthy(
                    "SHINYGEN_REQUIRE_SCREENSHOTS_FOR_JUDGE"
                ):
                    logger.error(
                        "Iteration %d: %s Screenshot-backed judging is required; "
                        "stopping without code-only judging.",
                        iteration,
                        exc,
                    )
                    result.error = str(exc)
                    if best_code is None:
                        best_code = code
                        best_runtime_valid = True
                        best_runtime_logs = runtime_logs
                        best_score = 0.0
                        best_quality_score = 0.0
                    break
                if not judge_models:
                    # No judging configured: the screenshot is cosmetic.
                    # Don't retry, don't fail — just record it and move on.
                    logger.warning(
                        "Iteration %d: %s No judge configured, so the "
                        "missing screenshot is non-fatal; proceeding.",
                        iteration,
                        exc,
                    )
                    screenshot_paths = []
                elif iteration == max_iterations:
                    # Final iteration: don't hard-fail the whole run just
                    # because the screenshot pipeline broke. Proceed with
                    # code-only judging so we still get a usable result.
                    logger.warning(
                        "Iteration %d: %s Proceeding with code-only "
                        "judging (no screenshot available).",
                        iteration,
                        exc,
                    )
                    screenshot_paths = []
                else:
                    # Recoverable: next iteration will retry with a prompt
                    # asking the agent to take its own screenshot.
                    logger.warning(
                        "Iteration %d: %s Retrying with screenshot-focused "
                        "prompt for the next iteration.",
                        iteration,
                        exc,
                    )
                    current_prompt = (
                        f"Your previous attempt failed: {exc}. "
                        "Ensure your app runs locally without errors, and that you "
                        "successfully run the screenshot tool before finishing."
                    )
                    continue

        # --- Step 4: Judge ---
        if judge_models:
            try:
                from .judge import judge_app_with_models

                with Timer() as judge_timer:
                    judge_result = judge_app_with_models(
                        code,
                        judge_models,
                        screenshot_paths or None,
                        prompt,
                    )
                # Attribute token usage per judge so the cost breakdown stays
                # accurate when more than one judge runs. Fall back to the
                # merged totals if per-judge attribution is unavailable.
                if judge_result.per_judge:
                    elapsed_share = judge_timer.elapsed / max(
                        len(judge_result.per_judge), 1
                    )
                    for entry in judge_result.per_judge:
                        if "error" in entry:
                            continue
                        result.usage.add(
                            stage="judge",
                            model=str(entry.get("model", judge_models[0])),
                            input_tokens=int(entry.get("input_tokens", 0) or 0),
                            output_tokens=int(entry.get("output_tokens", 0) or 0),
                            elapsed=elapsed_share,
                            iteration=iteration,
                        )
                else:
                    result.usage.add(
                        stage="judge",
                        model=judge_models[0],
                        input_tokens=judge_result.input_tokens,
                        output_tokens=judge_result.output_tokens,
                        elapsed=judge_timer.elapsed,
                        iteration=iteration,
                    )
                quality_score = judge_result.composite
                value_score = calculate_value_score(
                    quality_score=quality_score,
                    iterations=iteration,
                    generation_cost=result.usage.generation_cost,
                )
                score = value_score.value_score
                if len(judge_models) > 1:
                    panel_breakdown = ", ".join(
                        f"{entry.get('model')}={entry.get('composite', 0):.2f}"
                        for entry in judge_result.per_judge
                        if "error" not in entry
                    )
                    logger.info(
                        "Iteration %d: Panel quality = %.2f, value score = %.2f "
                        "(threshold = %.2f, cost penalty = %.2f, iteration penalty = %.2f) [%s]",
                        iteration,
                        quality_score,
                        score,
                        quality_threshold,
                        value_score.cost_penalty,
                        value_score.iteration_penalty,
                        panel_breakdown or "no judges responded",
                    )
                else:
                    logger.info(
                        "Iteration %d: Quality = %.2f, value score = %.2f "
                        "(threshold = %.2f, cost penalty = %.2f, iteration penalty = %.2f)",
                        iteration,
                        quality_score,
                        score,
                        quality_threshold,
                        value_score.cost_penalty,
                        value_score.iteration_penalty,
                    )

                if score > best_score:
                    best_score = score
                    best_quality_score = quality_score
                    best_code = code
                    best_feedback = judge_result.feedback_dict()
                    best_score_breakdown = value_score.to_dict()
                    best_runtime_valid = True
                    best_runtime_logs = runtime_logs
                    result.screenshot_paths = screenshot_paths

                if score >= quality_threshold:
                    logger.info("Value threshold met! Accepting app.")
                    result.score = score
                    result.quality_score = quality_score
                    result.value_score = score
                    result.score_breakdown = value_score.to_dict()
                    result.judge_feedback = judge_result.feedback_dict()
                    result.runtime_valid = True
                    result.runtime_logs = runtime_logs
                    result.passed = True
                    break

                # Prepare refinement prompt for next iteration
                if iteration < max_iterations:
                    from .prompts import build_refinement_prompt

                    current_prompt = build_refinement_prompt(
                        prompt,
                        judge_result.feedback_dict(),
                        iteration,
                        previous_code=code,
                        runtime_logs=runtime_logs,
                        validation_passed=runtime_valid,
                    )
                    logger.info("Preparing refinement prompt for next iteration")

            except Exception as exc:
                logger.warning("Judge failed: %s", exc)
                best_code = code
                best_runtime_valid = True
                best_runtime_logs = runtime_logs
                best_score = 0.0
                best_quality_score = 0.0
        else:
            # No judge — accept the app as soon as it runs cleanly. The
            # no-judge arm only iterates again when the app is actually
            # broken, using the captured server logs as the fix signal.
            best_code = code
            best_runtime_valid = runtime_valid
            best_runtime_logs = runtime_logs
            best_score = 10.0 if runtime_valid else 0.0
            best_quality_score = best_score
            result.screenshot_paths = screenshot_paths

            if runtime_valid:
                result.passed = True
                result.score = best_score
                result.quality_score = best_quality_score
                result.value_score = best_score
                break

            # App is broken — refine against the server logs if budget remains.
            if iteration < max_iterations:
                from .prompts import build_runtime_refinement_prompt

                current_prompt = build_runtime_refinement_prompt(
                    prompt,
                    previous_code=code,
                    runtime_logs=runtime_logs,
                    iteration=iteration,
                )
                logger.info(
                    "Preparing runtime-log refinement prompt for next iteration"
                )
                continue

            result.passed = False
            result.score = best_score
            result.quality_score = best_quality_score
            result.value_score = best_score
            break

    # --- Step 5: Copy final app to output ---
    if best_code:
        final_app = output_path / artifact_name
        final_app.write_text(best_code, encoding="utf-8")

        # Copy data files
        if data_files:
            for fname, content in data_files.items():
                (output_path / fname).write_text(content, encoding="utf-8")

        # Copy screenshots and update paths to point to output dir
        result.screenshot_paths = _copy_output_screenshots(
            output_path,
            result.screenshot_paths,
        )

        result.app_dir = output_path
        result.source_code = best_code
        if best_runtime_valid is not None:
            result.runtime_valid = best_runtime_valid
            result.runtime_logs = best_runtime_logs
        if not judge_models and best_runtime_valid is not None:
            result.passed = best_runtime_valid
            result.score = best_score
            result.quality_score = best_quality_score
            result.value_score = best_score
        elif not result.passed:
            result.score = best_score
            result.quality_score = best_quality_score
            result.value_score = best_score
            result.score_breakdown = best_score_breakdown
            result.judge_feedback = best_feedback

        logger.info(
            "Final app written to %s (score=%.2f, iterations=%d)",
            output_path,
            result.score,
            result.iterations,
        )
    else:
        if result.error is None:
            result.error = "No valid app code generated in any iteration"

    _write_run_summary(
        output_path,
        result,
        prompt=prompt,
        requested_model=model,
        resolved_model_id=model_id,
        agent=agent,
        framework_key=framework_key,
        artifact_name=artifact_name,
        judge_models=judge_models,
        data_file_names=list(data_files or {}),
        use_skills=use_skills,
        web_fetch=web_fetch,
    )

    return result


def _run_local_generation(
    *,
    prompt: str,
    model_id: str,
    framework_key: str,
    data_files: dict[str, str] | None,
    iteration: int,
    output_path: Path | None = None,
    use_skills: bool = True,
) -> tuple[str | None, list[dict[str, object]], bool]:
    """Generate a Shiny artifact on the host via LM Studio (no Docker).

    Host-side counterpart of :func:`_run_generation` for local LM Studio
    models. Reuses the same prompt builders, skill context loader, model
    builder, and direct-artifact generation logic, but stages files in a
    host temp directory and validates the app with the project venv instead
    of a Docker sandbox.

    Returns the same ``(code, usage_rows, hit_token_limit)`` shape as
    :func:`_run_generation` so the :func:`generate_and_refine` loop is
    unchanged.
    """
    import asyncio
    import sys
    import tempfile

    from .config import find_free_port
    from .native_solver import generate_artifact_on_host
    from .prompts import build_system_prompt, build_user_prompt
    from .skills import load_skill_context_text

    fw = FRAMEWORKS[framework_key]
    artifact_name = fw["primary_artifact"]

    work_dir = Path(tempfile.mkdtemp(prefix=f"shinygen_local_{iteration}_"))
    try:
        # Stage data files into the host working directory so the model's
        # data context preview and the generated app can read them.
        if data_files:
            for fname, content in data_files.items():
                (work_dir / fname).write_text(content, encoding="utf-8")

        system_prompt = build_system_prompt(
            framework_key,
            data_files=list(data_files.keys()) if data_files else None,
        )
        user_prompt = build_user_prompt(prompt, framework_key, data_files)

        extra_instructions: str | None = None
        if use_skills:
            # Local models get the actionable skill overview without the
            # 100KB references bundle (matches the Docker path policy).
            skill_context = load_skill_context_text(
                framework_key, include_references=False
            ).strip()
            if skill_context:
                extra_instructions = (
                    "Use these additional shinygen dashboard "
                    "generation guidelines when planning and editing "
                    f"files:\n\n{skill_context}"
                )

        model = _build_lmstudio_model(model_id)
        port = find_free_port()

        try:
            code, usage_rows, hit_token_limit = asyncio.run(
                generate_artifact_on_host(
                    model=model,
                    framework=framework_key,
                    artifact=artifact_name,
                    work_dir=work_dir,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    extra_instructions=extra_instructions,
                    port=port,
                    python_executable=sys.executable,
                )
            )
        except RuntimeError as exc:
            # asyncio.run raises RuntimeError if an event loop is already
            # running (Inspect runs inside one). Fall back to a fresh loop.
            logger.warning(
                "Iteration %d: asyncio.run blocked (%s); using new loop",
                iteration,
                exc,
            )
            loop = asyncio.new_event_loop()
            try:
                code, usage_rows, hit_token_limit = loop.run_until_complete(
                    generate_artifact_on_host(
                        model=model,
                        framework=framework_key,
                        artifact=artifact_name,
                        work_dir=work_dir,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        extra_instructions=extra_instructions,
                        port=port,
                        python_executable=sys.executable,
                    )
                )
            finally:
                loop.close()

        if code and output_path is not None:
            # Mirror the Docker path: copy the generated artifact + data
            # files into the user-facing output directory so the app is
            # runnable directly from there.
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / artifact_name).write_text(code, encoding="utf-8")
            if data_files:
                for fname, content in data_files.items():
                    (output_path / fname).write_text(content, encoding="utf-8")

        return code, usage_rows, hit_token_limit
    except Exception as exc:
        logger.error("Local generation failed in iteration %d: %s", iteration, exc)
        return None, [], False
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _run_generation(
    prompt: str,
    agent: str,
    model_id: str,
    framework_key: str,
    data_files: dict[str, str] | None,
    skills: list[Skill],
    web_fetch: bool,
    iteration: int,
    screenshot: bool = False,
    output_path: Path | None = None,
    *,
    use_skills: bool = True,
) -> tuple[str | None, list[dict[str, object]], bool]:
    """Run a single generation via Inspect AI and extract the code.

    LM Studio models bypass the Docker/Inspect-Task path entirely and run
    on the host (see :func:`_run_local_generation`), since model inference
    already targets ``localhost:1234`` and the project venv provides the
    full Shiny runtime needed for validation.
    """
    if is_lmstudio_model(model_id):
        return _run_local_generation(
            prompt=prompt,
            model_id=model_id,
            framework_key=framework_key,
            data_files=data_files,
            iteration=iteration,
            output_path=output_path,
            use_skills=use_skills,
        )

    from inspect_ai import eval as inspect_eval

    from .extract import extract_from_log
    from .generate import build_generation_task, stage_docker_context

    fw = FRAMEWORKS[framework_key]
    artifact_name = fw["primary_artifact"]

    docker_dir = stage_docker_context(framework_key)
    logs_dir = docker_dir / "logs"
    log_path: Path | None = None
    generation_usage_rows: list[dict[str, object]] = []
    try:
        task = build_generation_task(
            user_prompt=prompt,
            agent=agent,
            model_id=model_id,
            framework_key=framework_key,
            docker_context_dir=docker_dir,
            data_files=data_files,
            skills=skills,
            web_fetch=web_fetch,
            screenshot=screenshot,
            use_skills=use_skills,
        )

        # Use reasoning_effort for Anthropic Claude 4.6+ models so the
        # provider sends thinking.type=adaptive instead of the deprecated
        # thinking.type=enabled.
        extra_config = _generation_extra_config(agent)

        eval_model = model_id
        if is_lmstudio_model(model_id):
            eval_model = _build_lmstudio_model(model_id)
        elif is_opencode_go_anthropic_model(model_id):
            from inspect_ai.model import get_model

            base_url = os.environ.get("OPENCODE_GO_BASE_URL", OPENCODE_GO_BASE_URL)
            if base_url.rstrip("/").endswith("/v1"):
                base_url = base_url.rstrip("/")[: -len("/v1")]
            eval_model = get_model(
                f"anthropic/{opencode_go_anthropic_model_name(model_id)}",
                base_url=base_url,
                api_key=os.environ["OPENCODE_GO_API_KEY"],
                memoize=False,
            )

        logs = inspect_eval(
            task,
            model=eval_model,
            log_dir=str(logs_dir),
            **extra_config,
        )

        if not logs:
            logger.warning("Iteration %d: No eval logs produced", iteration)
            return None, [], False

        log = logs[0]
        location = getattr(log, "location", None)
        if location:
            log_path = Path(location)
        generation_usage_rows = _extract_generation_usage_rows(log)

        # Strategy 1: Read artifact from the results volume (most reliable).
        # The scorer copies sandbox files to docker_dir/results/<sample_id>/.
        results_dir = docker_dir / "results"
        if results_dir.exists():
            for artifact_path in results_dir.rglob(artifact_name):
                code = artifact_path.read_text(encoding="utf-8")
                if code.strip():
                    logger.info(
                        "Iteration %d: Read %d chars from results volume",
                        iteration,
                        len(code),
                    )
                    return code, generation_usage_rows, False

        # Strategy 2: Extract from eval log messages (fallback).
        if log_path:
            code_map = extract_from_log(log_path)
            if code_map:
                if len(code_map) == 1:
                    return next(iter(code_map.values())), generation_usage_rows, False
                if "shinygen/generate" in code_map:
                    return code_map["shinygen/generate"], generation_usage_rows, False
                return next(iter(code_map.values())), generation_usage_rows, False

        logger.warning("Iteration %d: No code extracted", iteration)

        return None, generation_usage_rows, _log_hit_output_token_limit(log_path)

    except Exception as exc:
        logger.error("Generation failed in iteration %d: %s", iteration, exc)
        recovered_code, recovered_log_path = _recover_code_from_eval_logs(
            logs_dir,
            artifact_name,
        )
        if recovered_log_path is not None:
            log_path = recovered_log_path
        if recovered_code is not None:
            logger.warning(
                "Recovered %s from eval log after generation failure in iteration %d",
                artifact_name,
                iteration,
            )
            return (
                recovered_code,
                generation_usage_rows,
                _log_hit_output_token_limit(log_path),
            )
        return None, generation_usage_rows, _log_hit_output_token_limit(log_path)
    finally:
        if output_path is not None:
            copied_agent_screenshot = _copy_agent_screenshot_artifact(
                output_path,
                results_dir=docker_dir / "results",
                log_path=log_path,
            )
            if copied_agent_screenshot is not None:
                logger.info("Agent screenshot copied to %s", copied_agent_screenshot)

            # Copy eval logs to output directory before cleanup
            if logs_dir.exists():
                eval_logs_dest = output_path / "eval_logs"
                eval_logs_dest.mkdir(parents=True, exist_ok=True)
                for log_file in logs_dir.rglob("*"):
                    if log_file.is_file():
                        dest = eval_logs_dest / log_file.relative_to(logs_dir)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(log_file, dest)
                logger.info("Eval logs copied to %s", eval_logs_dest)
        shutil.rmtree(docker_dir, ignore_errors=True)
