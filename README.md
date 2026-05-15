# shinygen

Generate, evaluate, and refine Shiny apps using LLM agents (Claude Code, Codex CLI) in Docker sandboxes.

## Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontFamily': 'Inter, Arial, sans-serif'}}}%%
flowchart TD
    %% Color Palette Definitions
    classDef input fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e,rx:8
    classDef core fill:#f1f5f9,stroke:#64748b,stroke-width:2px,color:#0f172a,rx:8
    classDef agent fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#581c87,rx:8
    classDef validation fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f,rx:8
    classDef judge fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#881337,rx:8
    classDef output fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d,rx:8

    A["👤 User Request<br/>(Prompt + Dataset + Flags)"]:::input --> B["shinygen API / CLI"]:::core
    
    B --> C["Start Iteration Loop"]:::core
    
    subgraph Sandbox["Docker Sandbox Execution"]
        direction TB
        C --> D["Inject Framework Skills & Context"]:::agent
        D --> E["LLM Agent Writes Code<br/>(Claude Code / Codex / OpenCode Go)"]:::agent
    end
    
    E --> F["Host-side Runtime Validation<br/>(Unconditionally Starts App & Captures Logs)"]:::validation
    
    F --> G{"Screenshots<br/>Enabled?"}:::validation
    G -- Yes --> H["Host Playwright Captures UI"]:::validation
    G -- No --> I{"Judge Model<br/>Enabled?"}:::judge
    H --> I
    
    I -- Yes --> J["LLM Judge Panel Evaluates<br/>(Scores Code + Visuals 1-10)"]:::judge
    J --> K{"Meets Quality<br/>Threshold?"}:::judge
    
    I -- No --> L{"App Started<br/>Successfully?"}:::validation
    
    K -- No --> M["Construct Refinement Feedback<br/>(Judge Critiques + Server Error Logs)"]:::core
    L -- No --> M
    M --> C
    
    K -- Yes --> N["✅ Save Artifacts<br/>(Code, Logs, Screenshots, Summary)"]:::output
    L -- Yes --> N
```

For full documentation — installation, CLI, Python API, batch mode, GitHub Actions, model aliases, skills, and data inputs — see the published docs:

**[https://karangattu.github.io/shinygen/](https://karangattu.github.io/shinygen/)**

## Value scoring

When a judge model is enabled, shinygen now records both raw `quality_score` and value-adjusted `score` / `value_score` in `run_summary.json`. The value score deducts for extra generation iterations and generation cost, so a similarly good app that completes in one cheap attempt ranks above a costly multi-iteration run.

## OpenCode Go models

OpenCode Go models can be tested through Inspect and the `mini_swe_agent` sandbox solver. Most route through Inspect's `openai-api` provider; MiniMax M2.5/M2.7 route through OpenCode Go's Anthropic-compatible messages endpoint.

```bash
export OPENCODE_GO_API_KEY="sk-..."

shinygen generate \
    --prompt "Build a polished dashboard for this dataset" \
    --model opencode-go/kimi-k2.6 \
    --csv-file ./test_data_csv_files/airbnb-asheville-short.csv \
    --screenshot \
    --judge-model anthropic/claude-opus-4-7
```

Supported OpenCode Go aliases include `glm-5.1`, `glm-5`, `kimi-k2.5`, `kimi-k2.6`, `mimo-v2.5`, `mimo-v2.5-pro`, `minimax-m2.5`, `minimax-m2.7`, `qwen3.5-plus`, `qwen3.6-plus`, `deepseek-v4-pro`, and `deepseek-v4-flash`.

See `batch-opencode-go.json` for a ready-to-edit local benchmark template that compares frontier US models and OpenCode Go models across `skills` and `vanilla` arms.
