# shinygen

Generate, evaluate, and refine Shiny apps using LLM agents (Claude Code, Codex CLI) in Docker sandboxes.

## Architecture

```mermaid
flowchart TD
    A["👤 User Prompt + flags"] --> B["shinygen CLI / API"]
    B --> C["Pre-flight checks\nDocker + API key"]
    C --> D["Load framework defaults,\ndata files, and skills"]
    D --> E["Iteration loop"]

    subgraph F["Fresh Docker sandbox per iteration"]
        G["Stage Docker context\n+ Inspect AI task"]
        H["LLM Agent\n(Claude Code / Codex CLI)"]
        I["Generate app.py / app.R"]
        J{"--screenshot?"}
        K["Run app on :8000\ninside sandbox"]
        L["screenshot_helper.py\nwaits 7s and captures screenshot.png"]
        M["Agent reviews screenshot\nand refines in sandbox"]
        N["Scorer copies project files\nto results volume"]
        O["Eval log + usage rows"]

        E --> G --> H --> I --> J
        J -- Yes --> K --> L --> M --> N
        J -- No --> N
        N --> O
    end

    O --> P["Extract code from results volume\nor eval log"]
    O --> Q["Copy agent_last_screenshot.png\nfrom results or eval attachment"]
    P --> R{"--judge-model?"}
    R -- Yes --> S["Run extracted app on host temp dir"]
    S --> T["Host Playwright screenshot"]
    T --> U["External LLM judge\n(scores 4 criteria)"]
    U --> V{"Score ≥ threshold?"}
    V -- No --> W["Refinement prompt includes\njudge feedback + previous code"]
    W --> E
    V -- Yes --> X["✅ Output directory"]
    R -- No --> X

    Q --> X
    X --> Y["Artifacts:\n• app.py / app.R\n• data files\n• screenshot.png\n• agent_last_screenshot.png\n• eval_logs/*.eval\n• run_summary.json"]
```

### How It Works

1. **You run a command** — provide a prompt, pick a model, and optionally enable `--screenshot` and `--judge-model`.
2. **Pre-flight + setup** — shinygen checks Docker/API access, resolves the framework and model, and loads bundled skills, custom skills, and any data files.
3. **Fresh sandbox generation** — each iteration stages a fresh Docker sandbox, installs agent skills in the agent's native home, and asks Claude Code or Codex CLI to generate `app.py` or `app.R`.
4. **Agent self-evaluation** (when `--screenshot` is enabled) — inside the sandbox, the agent runs the app, uses `screenshot_helper.py`, waits 7 seconds before capture, reviews the screenshot, and refines visually before submission.
5. **Extraction + optional external judge** — shinygen extracts the app from the results volume or eval log, preserves the final in-agent screenshot as `agent_last_screenshot.png`, and, if `--judge-model` is set, runs the extracted app on the host for a separate Playwright screenshot and external LLM score. Failed scores feed a refinement prompt that includes both judge feedback and the previous code.
6. **Final output** — the final app, screenshots, eval logs, and structured run summary are written to your output directory.

### What You Get

```
my-dashboard/
├── app.py                  # Or app.R for Shiny for R
├── data.csv                # Your data file (if provided)
├── screenshot.png          # Host-side screenshot used by the external judge
├── agent_last_screenshot.png
├── eval_logs/
│   └── *.eval
└── run_summary.json        # Structured score, usage, and artifact metadata
```

The CLI also prints a summary:

```
Score: 8.25 / 10.00 (after 2 iterations)
Time:  45.2s total (38.1s generate, 7.1s judge)
Tokens: 12,340 input / 3,210 output
Cost:  $0.1842
```

## Installation

```bash
# from a local checkout of this repo
cd /path/to/shinygen
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If you only need the runtime dependencies, use `python -m pip install -e .` instead of the editable dev install above.

## Quick Start

### CLI

```bash
# Generate a Shiny for Python app with Claude Sonnet
shinygen generate \
    --prompt "Create a sales dashboard with filters by region and product category" \
    --model claude-sonnet \
    --output ./my-dashboard

# With screenshot-based quality evaluation and iteration
shinygen generate \
    --prompt "Create a clinical trials dashboard" \
    --model claude-opus \
    --output ./trials-app \
    --screenshot \
    --judge-model claude-sonnet \
    --max-iterations 5

# Shiny for R
shinygen generate \
    --prompt "Create an interactive data explorer" \
    --model claude-sonnet \
    --framework shiny-r \
    --output ./r-app

# With custom skills and data files
shinygen generate \
    --prompt "Build a dashboard for this dataset" \
    --model gpt54 \
    --output ./my-app \
    --skills-dir ./my-skills/ \
    --csv-file ./sales.csv
```

`web_fetch` is enabled by default. Use `--no-web-fetch` to disable web search.

### Python API

```python
import shinygen

result = shinygen.generate(
    prompt="Create a sales dashboard with regional filters",
    model="claude-sonnet",
    output_dir="./my-dashboard",
    framework="shiny-python",
    data_csv="./sales.csv",
    screenshot=True,
    judge_model="claude-sonnet",
    max_iterations=5,
)

print(result.app_dir)       # ./my-dashboard
print(result.score)          # 4.5
print(result.iterations)    # 2
```

### Batch over a CSV

If you want one generated app per row in a dataset, loop over the CSV and call the Python API for each record. The example below uses the checked-in `trials_short_50.csv`, enables screenshot mode, and writes each run to its own output directory.

```python
from csv import DictReader
from pathlib import Path
import re

import shinygen


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or "row"


csv_path = Path("test_data_csv_files/trials_short_50.csv")
output_root = Path("batch_outputs")
output_root.mkdir(parents=True, exist_ok=True)

with csv_path.open(newline="", encoding="utf-8") as handle:
    for row in DictReader(handle):
        prompt = (
            "Create a Shiny dashboard for this clinical trial record.\n"
            f"Title: {row['Title']}\n"
            f"Acronym: {row['Acronym']}\n"
            f"Conditions: {row['Conditions']}\n"
            f"Interventions: {row['Interventions']}\n"
            f"Outcome Measures: {row['Outcome Measures']}\n"
            f"Study Type: {row['Study Type']}\n"
        )

        output_dir = output_root / f"{row['Rank']}_{slugify(row['NCT Number'])}"

        shinygen.generate(
            prompt=prompt,
            model="claude-sonnet",
            framework="shiny_python",
            output_dir=output_dir,
            data_csv=csv_path,
            screenshot=True,
            judge_model="claude-sonnet",
            max_iterations=3,
        )
```

If you want to parallelize the dataset later, keep the same prompt pattern and split the CSV into chunks first; each chunk can still pass `screenshot=True`.

## Run from GitHub Actions

Use the manual workflow at `.github/workflows/run-shinygen.yml` to run one `shinygen generate` job from the Actions UI and download the generated outputs as an artifact.

1. Add repository secrets:
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`
2. In GitHub, open **Actions** → **Run shinygen** → **Run workflow**.
3. Fill the typed inputs (`prompt`, `model`, `framework`, screenshot/judge options, and iteration settings), then start the run.
4. After completion, open the run summary and download artifact `shinygen-run-<run_id>`.

The artifact contains the full run output directory (`gha_runs/run-<run_id>`), including the generated app file (`app.py` or `app.R`), screenshots when enabled, `eval_logs/`, raw CLI output in `run.log`, and extracted timing/cost/token summary in `run_metrics.txt`.

### Parallel Multi-Model Runs (up to 8 runners)

Use `.github/workflows/run-shinygen-multi.yml` when you want to evaluate the **same prompt** across multiple models in parallel.

1. Open **Actions** → **Run shinygen (multi-model parallel)** → **Run workflow**.
2. Set `models` as a comma-separated or newline-separated list (max 8), for example:
   - `claude-opus, claude-sonnet, gpt54, gpt54-mini, codex-gpt53`
3. Keep the same shared settings (`prompt`, `framework`, screenshot/judge options, thresholds).
4. Start the run. GitHub fans out one matrix job per model with `max-parallel: 8`.
5. Download either:
   - per-model artifacts (`shinygen-run-<run_id>-<idx>-<model-slug>`), or
   - a combined aggregate artifact (`shinygen-run-<run_id>-aggregate`).

Each per-model artifact includes generated app outputs, `eval_logs/`, `run.log`, and `run_metrics.txt` for timing/cost/tokens. The aggregate artifact contains all per-model artifact directories plus an `INDEX.txt`.

## Features

- **Multiple LLM agents**: Claude Code (Anthropic) and Codex CLI (OpenAI)
- **Docker sandboxes**: Isolated generation via Inspect AI
- **R and Python**: Generate Shiny for Python (`app.py`) or Shiny for R (`app.R`)
- **Visual self-evaluation**: Agent takes Playwright screenshots *inside* the sandbox, reviews them, and self-corrects layout/styling issues before returning
- **External LLM judge**: Optional quality gate — a separate LLM scores the app on functionality, design, code quality, and UX
- **Iterative refinement**: Automatically re-generate until quality threshold is met
- **Skills injection**: Pass custom skill files into the sandbox
- **Web fetch (default on)**: Allow the agent to search the web during generation (`--no-web-fetch` to disable)
- **Data files**: Include CSV/data files in the sandbox
- **Cost & time tracking**: Token usage and dollar costs reported per run

## Data Inputs

- Use `--csv-file` (CLI) or `data_csv` (Python API) for a single primary CSV.
- Use `--data-file` (CLI, repeatable) or `data_files` (Python API) for multiple or non-CSV files.
- If both are provided with the same filename, the CSV convenience argument wins.

## Models

| Alias | Agent | Model ID |
|-------|-------|----------|
| `claude-opus` | Claude Code | `anthropic/claude-opus-4-6` |
| `claude-sonnet` | Claude Code | `anthropic/claude-sonnet-4-6` |
| `gpt54` | Codex CLI | `openai/gpt-5.4` |
| `gpt54-mini` | Codex CLI | `openai/gpt-5.4-mini-2026-03-17` |
| `codex-gpt53` | Codex CLI | `openai/gpt-5.3-codex` |

## Requirements

- Python 3.10+
- Docker (for sandbox execution)
- API key for your chosen model (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
- Playwright browsers are pre-installed inside the Docker sandbox — no host installation needed for `--screenshot`

## License

MIT
