# shinygen

Generate, evaluate, and refine Shiny apps using LLM agents (Claude Code, Codex CLI) in Docker sandboxes.

## Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontFamily': 'Inter, system-ui, -apple-system, sans-serif', 'fontSize': '15px', 'lineColor': '#475569', 'edgeLabelBackground': '#ffffff' }, 'flowchart': { 'padding': 8, 'nodeSpacing': 30, 'rankSpacing': 35, 'curve': 'linear', 'htmlLabels': true, 'useMaxWidth': true }}}%%
flowchart TD
    %% Color Palette Definitions
    classDef input fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e
    classDef setup fill:#f8fafc,stroke:#64748b,stroke-width:2px,color:#334155
    classDef agent fill:#f3e8ff,stroke:#9333ea,stroke-width:2px,color:#581c87
    classDef test fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f
    classDef judge fill:#ffe4e6,stroke:#e11d48,stroke-width:2px,color:#881337
    classDef loop fill:#f1f5f9,stroke:#475569,stroke-width:2px,color:#1e293b
    classDef done fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d

    %% 1. User Input & Setup
    User(["User Request<br/>CSV data + prompt"]):::input
    User --> Setup["shinygen Setup<br/>Python/R, model, flags"]:::setup

    %% 2. Docker Sandbox Generation
    subgraph Sandbox["Docker Sandbox"]
        direction TB
        Skills["Design Skills<br/>layouts, palettes, schema"]:::agent
        Coder["AI Coding Agent<br/>writes Shiny code"]:::agent
        Skills --> Coder
    end
    Setup --> Skills

    %% 3. Automated Health Check & Visuals
    subgraph Verify["Live Verification"]
        direction TB
        Launch["Health Check<br/>boot app, read logs"]:::test
        Snap["Screenshots<br/>full-page capture"]:::test
        Launch --> Snap
    end
    Coder --> Launch

    %% 4. Multimodal AI Judge
    subgraph Quality["Quality Evaluation"]
        direction TB
        Judge["AI Judge<br/>design + code<br/>scores 1 to 10"]:::judge
        Check{"Score OK?"}:::judge
        Judge --> Check
    end
    Snap --> Judge

    %% 5. Self-Healing Refinement Loop or Success
    Feedback["Auto-Fix Loop<br/>retry with feedback"]:::loop
    Success(["Dashboard Ready<br/>app code, screenshots<br/>cost + quality report"]):::done
    Launch -- crashed --> Feedback
    Check -- no --> Feedback
    Check -- yes --> Success
    Snap -- no judge --> Success
    Feedback -. retry .-> Coder
```

For full documentation — installation, CLI, Python API, batch mode, GitHub Actions, model aliases, skills, and data inputs — see the published docs:

**[https://karangattu.github.io/shinygen/](https://karangattu.github.io/shinygen/)**

Give your inputs in this survey to help us what kinds of dashboards we want AI to be able to generate:
**[DashSwipe Survey](https://usertestingapp.vercel.app)**
