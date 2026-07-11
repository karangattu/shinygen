"""
Public Python API for shinygen.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .iterate import GenerationResult, _safe_data_filename, generate_and_refine


def read_data_files(
    data_files: dict[str, str] | None = None,
    data_file_paths: Sequence[str | Path] | None = None,
    data_csv: str | Path | None = None,
) -> dict[str, str] | None:
    """Read and merge data files from various sources.

    Args:
        data_files: Dict mapping filenames to content strings.
        data_file_paths: Optional sequence of file paths to read.
        data_csv: Optional path to a CSV file (added by basename, overrides
            any same-named file from data_file_paths).

    Returns:
        Merged dict of filename -> content, or None if no files provided.
    """
    merged: dict[str, str] | None = None

    if data_files:
        merged = {}
        for filename, content in data_files.items():
            merged[_safe_data_filename(filename)] = content

    if data_file_paths:
        if merged is None:
            merged = {}
        for fp in data_file_paths:
            p = Path(fp)
            merged[p.name] = p.read_text(encoding="utf-8")

    if data_csv:
        csv_path = Path(data_csv)
        if merged is None:
            merged = {}
        merged[csv_path.name] = csv_path.read_text(encoding="utf-8")

    return merged


def generate(
    prompt: str,
    *,
    model: str = "claude-sonnet",
    framework: str = "shiny_python",
    output_dir: str | Path = "output",
    skills_dir: str | Path | None = None,
    data_csv: str | Path | None = None,
    data_files: dict[str, str] | None = None,
    screenshot: bool = False,
    judge_model: str | Sequence[str] | None = None,
    max_iterations: int = 3,
    quality_threshold: float = 7.0,
    web_fetch: bool = True,
    use_skills: bool = True,
    port: int | None = None,
    verbose: bool = False,
) -> GenerationResult:
    """Generate a Shiny app from a natural language prompt.

    This is the main entry point for programmatic usage. It generates a Shiny
    app using an LLM agent (Claude Code or Codex CLI) running in a Docker
    sandbox, optionally takes screenshots, judges quality, and iterates.

    Args:
        prompt: Description of the desired Shiny app.
        model: Model alias or full model ID.
            Aliases: "claude-opus", "claude-opus-4-8", "claude-sonnet", "gpt55",
            "gpt54", "gpt54-mini", "gpt56-sol", "gpt56-terra", "gpt56-luna".
            Or pass a full model ID like "anthropic/claude-sonnet-5".
        framework: Target framework.
            Options: "shiny_python" (default), "shiny_r", "python", "r".
        output_dir: Directory where the final app will be written.
        skills_dir: Path to a directory of custom skill files to inject.
        data_csv: Optional path to a CSV file to include in the sandbox.
            The file is loaded and added by basename (e.g. "sales.csv").
            If it conflicts with an entry in data_files, this value wins.
        data_files: Dict mapping filenames to content strings for data files
            that should be available in the sandbox.
        screenshot: If True, take Playwright screenshots of the running app
            for visual quality evaluation.
        judge_model: Model(s) to use for quality evaluation. If ``None``,
            the app is accepted on first successful generation without
            judging. Pass a single model ID/alias for the classic
            single-judge flow, or a sequence (e.g.
            ``["anthropic/claude-sonnet-5", "openai/gpt-5.4-mini-2026-03-17"]``)
            to run a panel of judges and average their scores.
        max_iterations: Maximum number of generate-judge-refine cycles.
        quality_threshold: Minimum value-adjusted score (1-10) to accept when
            judging is enabled. Raw judge quality is still returned as
            ``quality_score``.
        web_fetch: If True (default), allow the agent to use web search tools.
        use_skills: If True (default), inject the bundled framework skill
            (and any ``skills_dir``) into the agent context. Set to False to
            run a vanilla baseline with no skills loaded — used to compare
            skill gains against the un-augmented model in benchmarks.
        port: Port for running the app during screenshots.
        verbose: If True, enable debug logging.

    Returns:
        A GenerationResult containing the app path, source code,
        value-adjusted score, raw quality score, number of iterations, and
        any screenshots.

    Examples:
        Basic generation::

            import shinygen

            result = shinygen.generate(
                "Create a penguin species explorer dashboard",
                model="claude-sonnet",
            )
            print(result.app_dir)

        With quality evaluation::

            result = shinygen.generate(
                "Interactive stock price tracker",
                model="claude-sonnet",
                screenshot=True,
                judge_model="anthropic/claude-sonnet-5",
                max_iterations=3,
                quality_threshold=7.0,
            )
            print(f"Score: {result.score}, Passed: {result.passed}")

        R app generation::

            result = shinygen.generate(
                "Shiny dashboard for mtcars analysis",
                model="claude-opus",
                framework="shiny_r",
            )
    """
    merged_data_files = read_data_files(
        data_files=data_files,
        data_csv=data_csv,
    )

    return generate_and_refine(
        prompt=prompt,
        model=model,
        framework=framework,
        output_dir=output_dir,
        skills_dir=skills_dir,
        data_files=merged_data_files,
        screenshot=screenshot,
        judge_model=judge_model,
        max_iterations=max_iterations,
        quality_threshold=quality_threshold,
        web_fetch=web_fetch,
        use_skills=use_skills,
        port=port,
        verbose=verbose,
    )


@dataclass
class BatchJob:
    """Specification for a single job within a batch run."""

    prompt: str
    model: str = "claude-sonnet"
    framework: str = "shiny_python"
    output_dir: str | Path = "output"
    skills_dir: str | Path | None = None
    data_csv: str | Path | None = None
    data_files: dict[str, str] | None = None
    screenshot: bool = False
    judge_model: str | Sequence[str] | None = None
    max_iterations: int = 3
    quality_threshold: float = 7.0
    web_fetch: bool = True
    use_skills: bool = True
    port: int | None = None
    verbose: bool = False


@dataclass
class BatchResult:
    """Collected results from a batch run."""

    results: list[GenerationResult]
    succeeded: int = 0
    failed: int = 0


def _normalize_batch_job(job: BatchJob | dict[str, object]) -> BatchJob:
    """Normalize dict batch jobs to BatchJob.

    Supports both API-style keys (``data_csv``) and CLI-style keys
    (``csv_file`` / ``data_file``) for convenience.
    """
    if isinstance(job, BatchJob):
        return job

    spec = dict(job)

    if "csv_file" in spec and "data_csv" not in spec:
        spec["data_csv"] = spec.pop("csv_file")

    if "output" in spec and "output_dir" not in spec:
        spec["output_dir"] = spec.pop("output")

    if "data_file" in spec:
        raw_paths = spec.pop("data_file")
        if isinstance(raw_paths, (str, Path)):
            paths = [raw_paths]
        else:
            paths = list(raw_paths or [])

        merged_data_files = dict(spec.get("data_files") or {})
        for file_path in paths:
            path = Path(file_path)
            merged_data_files[path.name] = path.read_text(encoding="utf-8")
        spec["data_files"] = merged_data_files

    return BatchJob(**spec)


def batch(jobs: list[BatchJob | dict]) -> BatchResult:
    """Run multiple generation jobs sequentially.

    Each job is an independent generation with its own model, prompt,
    output directory, and settings. Jobs run one at a time so they do
    not compete for Docker resources.

    Args:
        jobs: A list of :class:`BatchJob` instances or dicts with the
            same fields. Dict keys match :func:`generate` keyword
            arguments.

    Returns:
        A :class:`BatchResult` with per-job results and a success/fail
        summary.

    Examples:
        Using dicts::

            results = shinygen.batch([
                {
                    "prompt": "Sales dashboard",
                    "model": "claude-sonnet",
                    "output_dir": "./run-sonnet",
                    "screenshot": True,
                },
                {
                    "prompt": "Sales dashboard",
                    "model": "gpt55",
                    "output_dir": "./run-gpt55",
                    "screenshot": True,
                },
            ])
            for r in results.results:
                print(r.app_dir, r.score)

        Using BatchJob::

            from shinygen.api import BatchJob
            jobs = [
                BatchJob(prompt="Dashboard", model="claude-sonnet",
                         output_dir="./out-sonnet"),
                BatchJob(prompt="Dashboard", model="gpt55",
                         output_dir="./out-gpt55"),
            ]
            results = shinygen.batch(jobs)
    """
    import logging

    logger = logging.getLogger(__name__)
    batch_result = BatchResult(results=[])

    for idx, job in enumerate(jobs, start=1):
        job = _normalize_batch_job(job)
        logger.info(
            "Batch job %d/%d: model=%s output_dir=%s",
            idx,
            len(jobs),
            job.model,
            job.output_dir,
        )
        try:
            result = generate(
                prompt=job.prompt,
                model=job.model,
                framework=job.framework,
                output_dir=job.output_dir,
                skills_dir=job.skills_dir,
                data_csv=job.data_csv,
                data_files=job.data_files,
                screenshot=job.screenshot,
                judge_model=job.judge_model,
                max_iterations=job.max_iterations,
                quality_threshold=job.quality_threshold,
                web_fetch=job.web_fetch,
                use_skills=job.use_skills,
                port=job.port,
                verbose=job.verbose,
            )
            batch_result.results.append(result)
            if result.error:
                batch_result.failed += 1
            else:
                batch_result.succeeded += 1
        except Exception as exc:
            logger.error("Batch job %d failed: %s", idx, exc)
            err = GenerationResult(error=str(exc))
            batch_result.results.append(err)
            batch_result.failed += 1

    return batch_result


__all__ = ["generate", "batch", "GenerationResult", "BatchJob", "BatchResult"]
