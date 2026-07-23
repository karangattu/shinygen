# Human-Aligned Dashboard Visual Evaluation

Use this reference when judging or revising a dashboard screenshot. It calibrates visual QA to the qualities people consistently rate highly instead of to novelty, framework customization, or feature count.

## What Human Raters Reward

### 1. Immediate analytical usefulness

The landing view should communicate its purpose within five seconds. Strong dashboards usually expose a clear sequence:

1. compact global filters,
2. three or four meaningful KPIs,
3. one prominent primary visualization,
4. a balanced set of supporting comparisons, and
5. detailed records for inspection.

This sequence matters more than whether the dashboard uses custom CSS or recognizable framework defaults.

### 2. Purposeful information density

People favor dashboards that use the available canvas well. Reward layouts that feel complete without feeling crowded.

- Treat large empty regions, oversized KPI cards, and under-filled panels as lost analytical space.
- Treat tiny charts, excessive card grids, and cramped labels as overload.
- Prefer consistent alignment and card dimensions that make the page easy to scan.
- Do not mistake minimalism for quality when the page omits useful context.

### 3. Cohesive, functional color

Reward a restrained palette repeated across KPIs and charts. Color should connect related concepts, establish hierarchy, or encode data—not make every panel compete for attention.

Penalize patchwork palettes, abrupt light/dark transitions, poor contrast, and chart colors that change meaning between panels.

### 4. A compelling primary view

Maps often rate highly for geographic data because they make the domain immediately recognizable. More generally, the strongest chart should answer an important question and receive enough space to be legible.

Do not reward a map or large chart merely for existing. It must be populated, well-framed, readable, and integrated with the surrounding analysis.

### 5. Familiar controls and visible detail

Humans value filters in expected locations, clear reset behavior, understandable labels, and a table or detail view that makes the analysis feel trustworthy. A screenshot should make exploration look obvious even when the evaluator cannot interact with it.

## Common LLM Misratings

- Over-rewarding custom styling, extra tabs, animations, or feature breadth.
- Penalizing a conventional Shiny or BI layout even when it is the clearest design.
- Calling a sparse page "clean" when it is actually basic or incomplete.
- Giving oversized KPI tiles too much credit for visual hierarchy.
- Ignoring loading dots, unresolved outputs, blank chart regions, or stretched plots.
- Judging what the code intends to render instead of what the screenshot shows.
- Averaging a weak landing page with several secondary views and calling the whole app polished.

## Human-Aligned Inspection Sequence

### Step 1: Apply the render-state gate

Inspect every visible output before considering aesthetics.

- Repeated empty cards, stuck loading indicators, unresolved placeholders, or obviously unpopulated plots cap visual quality at 3/10.
- A single intentional empty state is acceptable only when it is clearly explained and styled.
- Trust screenshot evidence over code intent.

### Step 2: Judge the landing view independently

At fit-to-screen size, ask:

- Is the subject immediately recognizable?
- Is there a clear starting point?
- Can the main analytical story be understood without opening another tab?
- Does the page feel complete, balanced, and trustworthy?

Secondary tabs can add depth, but they do not repair a weak first impression.

### Step 3: Score observable visual qualities

Consider each dimension explicitly before choosing the final score:

1. **Hierarchy and scanability** — the eye knows where to start and what matters.
2. **Composition and density** — space is used purposefully without crowding.
3. **Color and typography coherence** — repeated, legible, functional styling.
4. **Chart, map, and table clarity** — suitable forms, labels, units, and readable marks.
5. **Visible usability** — controls look understandable and useful details are accessible.
6. **Completeness and polish** — no broken, loading, overlapping, clipped, or stretched output.

Do not give a high score based on only one dimension.

### Step 4: Inspect secondary views

Check additional screenshots for consistent styling and render quality. Reward useful depth, but do not award points simply because an app has more screenshots or navigation.

## Score Anchors

- **9** — An immediate human favorite: cohesive, information-rich, highly legible, and visually complete with excellent first-impression quality.
- **8** — Strong professional dashboard: clear hierarchy, purposeful density, coherent palette, useful primary view, and only minor rough edges.
- **7** — Good and trustworthy: conventional styling is acceptable; the dashboard tells its story clearly but lacks some refinement.
- **6** — Tidy but basic: functional and readable, yet sparse, weakly prioritized, or visually generic.
- **5** — Mixed: some useful content, but hierarchy, density, chart choice, or coherence noticeably limits comprehension.
- **4** — Weak: confusing, cramped, patchwork, poorly sized, or substantially incomplete.
- **1-3** — Broken or unusable: repeated blank outputs, stuck loading states, severe overlap, unreadable content, or failed rendering.

Reserve high scores for screenshots that succeed across the full scorecard. Do not require novelty or custom framework styling.
