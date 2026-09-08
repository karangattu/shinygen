# shinygen

Generate, evaluate, and refine Shiny apps using LLM agents (Claude Code, Codex CLI) in Docker sandboxes.

## Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontFamily': 'Inter, system-ui, -apple-system, sans-serif' }}}%%
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
    User(["👤 <b>User Request</b><br/>Dataset CSV + Prompt"]):::input
    User --> Setup["⚙️ <b>shinygen Setup</b><br/>Selects framework (Python/R), AI model & evaluation flags"]:::setup

    %% 2. Docker Sandbox Generation
    subgraph Sandbox["🐳 Isolated Docker Sandbox"]
        direction TB
        Skills("✨ <b>Design Skills & Guidelines</b><br/>UI layout patterns, thematic palettes & data schema"):::agent
        Coder("🤖 <b>AI Coding Agent</b><br/>Generates Shiny Python or R code inside sandbox"):::agent
        Skills --> Coder
    end
    Setup --> Skills

    %% 3. Automated Health Check & Visuals
    subgraph Verify["⚡ Live Verification & Screenshots"]
        direction TB
        Launch("🚀 <b>Live App Health Check</b><br/>Boots Shiny server to test syntax & capture runtime logs"):::test
        Snap("📸 <b>Capture Live UI Visuals</b><br/>Headless browser captures full-page dashboard screenshots"):::test
        Launch -->|"App Runs Clean"| Snap
    end
    Coder --> Launch

    %% 4. Multimodal AI Judge
    subgraph Quality["⚖️ Quality Evaluation"]
        direction TB
        Judge("🎨 <b>Multimodal AI Judge</b><br/>Evaluates visual polish, charts & code quality (1–10)"):::judge
        Check{"Quality Meets<br/>Target Score?"}:::judge
        Judge --> Check
    end
    Snap --> Judge

    %% 5. Self-Healing Refinement Loop or Success
    Feedback("🔄 <b>Auto-Fix & Refine Loop</b><br/>Feeds console errors & judge feedback into next attempt"):::loop
    Launch -->|"App Crashed"| Feedback
    Check -- "❌ Needs Polish" --> Feedback
    Feedback -.->|"Retry in Sandbox"| Coder

    Success(["✅ <b>Production-Ready Shiny Dashboard</b><br/>Tested app code (app.py / app.R) • Screenshots • Cost & Quality Report"]):::done
    Check -- "✔️ Quality Passed" --> Success
    Snap -->|"Judging Disabled"| Success
```

For full documentation — installation, CLI, Python API, batch mode, GitHub Actions, model aliases, skills, and data inputs — see the published docs:

**[https://karangattu.github.io/shinygen/](https://karangattu.github.io/shinygen/)**

Give your inputs in this survey to help us what kinds of dashboards we want AI to be able to generate:
**[DashSwipe Survey](https://usertestingapp.vercel.app)**
