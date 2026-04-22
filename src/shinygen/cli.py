"""
CLI entry point for shinygen.
"""

from __future__ import annotations

from pathlib import Path

import click


@click.group()
@click.version_option(package_name="shinygen")
def main() -> None:
    """shinygen — Generate Shiny apps with LLMs."""


@main.command()
@click.option(
    "--prompt",
    "-p",
    required=True,
    help="Natural language description of the desired app.",
)
@click.option(
    "--model",
    "-m",
    default="claude-sonnet",
    show_default=True,
    help=(
        'Model alias or full ID. Aliases: "claude-opus", "claude-sonnet", '
        '"gpt54", "gpt54-mini", "codex-gpt53".'
    ),
)
@click.option(
    "--framework",
    "-f",
    default="shiny_python",
    show_default=True,
    help='Target framework: "shiny_python", "shiny_r", "python", "r".',
)
@click.option(
    "--output",
    "-o",
    default="output",
    show_default=True,
    type=click.Path(),
    help="Directory where the final app will be saved.",
)
@click.option(
    "--skills-dir",
    "-s",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Path to a directory of custom skill files to inject.",
)
@click.option(
    "--csv-file",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="CSV file to include in the sandbox.",
)
@click.option(
    "--data-file",
    "-d",
    multiple=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Data file(s) to include in the sandbox. Can be repeated.",
)
@click.option(
    "--screenshot/--no-screenshot",
    default=False,
    show_default=True,
    help="Take Playwright screenshots for visual quality evaluation.",
)
@click.option(
    "--judge-model",
    "-j",
    default=None,
    help='Model for quality evaluation (e.g., "anthropic/claude-sonnet-4-6").',
)
@click.option(
    "--max-iterations",
    "-i",
    default=3,
    show_default=True,
    type=int,
    help="Maximum number of generate-judge-refine iterations.",
)
@click.option(
    "--quality-threshold",
    "-q",
    default=7.0,
    show_default=True,
    type=float,
    help="Minimum composite quality score (1-10) to accept.",
)
@click.option(
    "--web-fetch/--no-web-fetch",
    default=True,
    show_default=True,
    help="Allow the agent to use web search tools.",
)
@click.option(
    "--skills/--no-skills",
    "use_skills",
    default=True,
    show_default=True,
    help=(
        "Inject the bundled framework skill (and any --skills-dir) into the "
        "agent context. Use --no-skills to run a vanilla baseline for "
        "control/treatment benchmarks."
    ),
)
@click.option(
    "--port",
    default=None,
    type=int,
    help="Port for running the app during screenshots.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose debug logging.",
)
def generate(
    prompt: str,
    model: str,
    framework: str,
    output: str,
    skills_dir: str | None,
    csv_file: str | None,
    data_file: tuple[str, ...],
    screenshot: bool,
    judge_model: str | None,
    max_iterations: int,
    quality_threshold: float,
    web_fetch: bool,
    use_skills: bool,
    port: int | None,
    verbose: bool,
) -> None:
    """Generate a Shiny app from a natural language prompt."""
    from .api import generate as api_generate

    # Read data files
    data_files: dict[str, str] | None = None
    if data_file:
        data_files = {}
        for fp in data_file:
            p = Path(fp)
            data_files[p.name] = p.read_text(encoding="utf-8")
    if csv_file:
        if data_files is None:
            data_files = {}
        csv_path = Path(csv_file)
        data_files[csv_path.name] = csv_path.read_text(encoding="utf-8")

    from .config import APIKeyMissingError, DockerNotAvailableError

    try:
        result = api_generate(
            prompt=prompt,
            model=model,
            framework=framework,
            output_dir=output,
            skills_dir=skills_dir,
            data_files=data_files,
            screenshot=screenshot,
            judge_model=judge_model,
            max_iterations=max_iterations,
            quality_threshold=quality_threshold,
            web_fetch=web_fetch,
            use_skills=use_skills,
            port=port,
            verbose=verbose,
        )
    except (DockerNotAvailableError, APIKeyMissingError) as exc:
        click.secho(f"\nError: {exc}", fg="red", err=True)
        raise SystemExit(1)

    if result.error:
        click.secho(f"Error: {result.error}", fg="red", err=True)
        raise SystemExit(1)

    click.secho(f"App generated successfully!", fg="green")
    click.echo(f"  Output:     {result.app_dir}")
    click.echo(f"  Score:      {result.score:.2f}")
    click.echo(f"  Iterations: {result.iterations}")
    click.echo(f"  Passed:     {result.passed}")

    # Usage stats
    usage = result.usage
    click.echo(f"  Time:       {usage.total_time_seconds:.1f}s"
               f" (generate: {usage.generation_time_seconds:.1f}s,"
               f" judge: {usage.judge_time_seconds:.1f}s)")
    if usage.total_input_tokens or usage.total_output_tokens:
        token_parts = [
            f"{usage.total_input_tokens:,} input",
            f"{usage.total_output_tokens:,} output",
        ]
        if usage.total_cache_write_tokens:
            token_parts.append(f"{usage.total_cache_write_tokens:,} cache-write")
        if usage.total_cache_read_tokens:
            token_parts.append(f"{usage.total_cache_read_tokens:,} cache-read")
        click.echo(f"  Tokens:     {', '.join(token_parts)}")

    # Per-iteration cost & token breakdown
    if usage.details:
        click.echo("  Cost breakdown:")

        # Aggregate by iteration and stage.
        iter_generate: dict[int, float] = {}
        iter_judge: dict[int, float] = {}
        iter_tokens: dict[int, dict[str, int]] = {}
        for d in usage.details:
            it = int(d.get("iteration", 0) or 0)
            c = float(d.get("cost") or 0.0)
            stage = str(d.get("stage", ""))
            if stage == "generate":
                iter_generate[it] = iter_generate.get(it, 0.0) + c
            elif stage == "judge":
                iter_judge[it] = iter_judge.get(it, 0.0) + c
            # Accumulate tokens per iteration
            if it not in iter_tokens:
                iter_tokens[it] = {
                    "input": 0, "output": 0,
                    "cache_write": 0, "cache_read": 0,
                }
            iter_tokens[it]["input"] += int(d.get("input_tokens", 0) or 0)
            iter_tokens[it]["output"] += int(d.get("output_tokens", 0) or 0)
            iter_tokens[it]["cache_write"] += int(d.get("cache_write_tokens", 0) or 0)
            iter_tokens[it]["cache_read"] += int(d.get("cache_read_tokens", 0) or 0)

        cumulative = 0.0
        all_iters = sorted(set(iter_generate) | set(iter_judge))
        for it in all_iters:
            gen_cost = iter_generate.get(it, 0.0)
            judge_cost = iter_judge.get(it, 0.0)
            subtotal = gen_cost + judge_cost
            cumulative += subtotal
            label = f"iteration {it}" if it > 0 else "setup"
            click.echo(
                f"    [{label}]  generate: ${gen_cost:.4f}, "
                f"judge: ${judge_cost:.4f}, subtotal: ${subtotal:.4f}, "
                f"cumulative: ${cumulative:.4f}"
            )
            # Token details per iteration
            toks = iter_tokens.get(it)
            if toks and (toks["input"] or toks["output"]):
                tok_parts = [
                    f"{toks['input']:,} in",
                    f"{toks['output']:,} out",
                ]
                if toks["cache_write"]:
                    tok_parts.append(f"{toks['cache_write']:,} cache-w")
                if toks["cache_read"]:
                    tok_parts.append(f"{toks['cache_read']:,} cache-r")
                click.echo(f"              tokens: {', '.join(tok_parts)}")

        total_generate = usage.generation_cost or 0.0
        total_judge = usage.judge_cost or 0.0
        total_cost = usage.total_cost if usage.total_cost is not None else (total_generate + total_judge)
        click.echo(
            f"    [total]      generate: ${total_generate:.4f}, "
            f"judge: ${total_judge:.4f}, cumulative: ${total_cost:.4f}"
        )

        if total_generate == 0.0 and any(d.get("stage") == "generate" for d in usage.details):
            click.echo(
                "    Note: generation usage was captured but cost could not "
                "be priced for one or more models."
            )
    elif usage.total_cost is not None and usage.total_cost > 0:
        click.echo(
            f"  Cost:       ${usage.total_cost:.4f}"
            f" (generate: ${usage.generation_cost or 0.0:.4f},"
            f" judge: ${usage.judge_cost or 0.0:.4f})"
        )

    if result.screenshot_paths:
        click.echo(f"  Screenshots:")
        for sp in result.screenshot_paths:
            click.echo(f"    - {sp}")


def _print_result_summary(result, label: str | None = None) -> None:
    """Print a compact summary line for one generation result."""
    prefix = f"  [{label}] " if label else "  "
    if result.error:
        click.secho(f"{prefix}ERROR: {result.error}", fg="red")
        return
    score = f"{result.score:.2f}" if result.score else "n/a"
    click.echo(
        f"{prefix}{result.app_dir}  score={score}  "
        f"iterations={result.iterations}  passed={result.passed}"
    )


def _resolve_batch_job_paths(job: dict, base_dir: Path) -> dict:
    """Resolve config file paths relative to the config directory."""
    resolved = dict(job)

    for key in ("csv_file", "data_csv", "skills_dir", "output", "output_dir"):
        value = resolved.get(key)
        if isinstance(value, str) and value:
            path = Path(value)
            if not path.is_absolute():
                resolved[key] = str(base_dir / path)

    data_file = resolved.get("data_file")
    if isinstance(data_file, str) and data_file:
        path = Path(data_file)
        if not path.is_absolute():
            resolved["data_file"] = str(base_dir / path)
    elif isinstance(data_file, list):
        resolved["data_file"] = [
            str(base_dir / Path(path)) if not Path(path).is_absolute() else path
            for path in data_file
        ]

    return resolved


@main.command()
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="JSON file containing an array of job objects.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose debug logging.",
)
def batch(config: str, verbose: bool) -> None:
    """Run multiple generation jobs from a JSON config file.

    The config file must contain a JSON array of objects. Each object
    accepts the same keys as the ``generate`` command's options
    (using underscores, e.g. ``output_dir`` not ``--output``).

    Required key per job: ``prompt``.

    Example config file::

        [
          {
            "prompt": "Sales dashboard",
            "model": "claude-sonnet",
            "output_dir": "./run-sonnet",
            "screenshot": true
          },
          {
            "prompt": "Sales dashboard",
            "model": "gpt54",
            "output_dir": "./run-gpt54",
            "screenshot": true
          }
        ]
    """
    import json
    import logging

    from .api import batch as api_batch

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    config_path = Path(config)
    try:
        jobs = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        click.secho(f"Invalid JSON in {config}: {exc}", fg="red", err=True)
        raise SystemExit(1)

    if not isinstance(jobs, list):
        click.secho(
            "Config file must contain a JSON array of job objects.",
            fg="red",
            err=True,
        )
        raise SystemExit(1)

    jobs = [_resolve_batch_job_paths(job, config_path.parent) for job in jobs]

    # Propagate verbose to every job
    if verbose:
        for job in jobs:
            job.setdefault("verbose", True)

    click.echo(f"Starting batch run with {len(jobs)} job(s)...")

    from .config import APIKeyMissingError, DockerNotAvailableError

    try:
        batch_result = api_batch(jobs)
    except (DockerNotAvailableError, APIKeyMissingError) as exc:
        click.secho(f"\nError: {exc}", fg="red", err=True)
        raise SystemExit(1)

    click.echo()
    click.secho(
        f"Batch complete: {batch_result.succeeded} succeeded, "
        f"{batch_result.failed} failed",
        fg="green" if batch_result.failed == 0 else "yellow",
    )
    for idx, result in enumerate(batch_result.results, start=1):
        _print_result_summary(result, label=f"job {idx}")
