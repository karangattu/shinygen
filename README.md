# shinygen

Generate, evaluate, and refine Shiny apps using LLM agents (Claude Code, Codex CLI) in Docker sandboxes.

## Architecture

```mermaid
flowchart TD
    A["👤 User Prompt + flags"] --> B["shinygen CLI / API"]
    B --> C["Pre-flight checks<br/>Docker + API key"]
    C --> D["Load framework defaults,<br/>data files, and skills"]
    D --> E["Iteration loop"]

    subgraph F["Fresh Docker sandbox per iteration"]
        G["Stage Docker context<br/>+ Inspect AI task"]
        H["LLM Agent<br/>(Claude Code / Codex CLI)"]
        I["Generate app.py / app.R"]
        J{"--screenshot?"}
        K["Run app on :8000<br/>inside sandbox"]
        L["screenshot_helper.py<br/>waits 7s and captures screenshot.png"]
        M["Agent reviews screenshot<br/>and refines in sandbox"]
        N["Scorer copies project files<br/>to results volume"]
        O["Eval log + usage rows"]

        E --> G --> H --> I --> J
        J -- Yes --> K --> L --> M --> N
        J -- No --> N
        N --> O
    end

    O --> P["Extract code from results volume<br/>or eval log"]
    O --> Q["Copy agent_last_screenshot.png<br/>from results or eval attachment"]
    P --> R{"--judge-model?"}
    R -- Yes --> S["Run extracted app on host temp dir"]
    S --> T["Host Playwright screenshot"]
    T --> U["Judge panel<br/>(1+ external LLM judges)"]
    U --> Y["Average per-criterion scores<br/>+ concatenate rationales"]
    Y --> V{"Score ≥ threshold?"}
    V -- No --> W["Refinement prompt includes<br/>panel feedback + previous code"]
    W --> E
    V -- Yes --> X["✅ Output directory"]
    R -- No --> X

    Q --> X
    X --> Z["Artifacts:<br/>• app.py / app.R<br/>• data files<br/>• screenshot.png<br/>• agent_last_screenshot.png<br/>• eval_logs/*.eval<br/>• run_summary.json"]
```

For full documentation — installation, CLI, Python API, batch mode, GitHub Actions, model aliases, skills, and data inputs — see the published docs:

**[https://karangattu.github.io/shinygen/](https://karangattu.github.io/shinygen/)**
