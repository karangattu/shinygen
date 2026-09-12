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

#### Geographic task coverage

Require a map panel when both conditions hold: location materially helps answer the user's questions (for example, locating listings, comparing neighborhoods, service coverage, or regional patterns), and the data contains usable coordinates or geographic areas that can be mapped reliably. State the spatial question and the available geographic fields before applying this requirement. A location column alone does not make a map necessary for a task unrelated to geography. Do not invent coordinates, boundaries, or a geocoding result; explain unavailable or unreliable geographic data.

The map must show relevant records or aggregates with recognizable geographic context, fit the area of interest, and provide enough space to distinguish locations and interpret its encodings. Use a basemap, labeled boundaries, or equivalent geographic reference appropriate to the task. Neighborhood bars and a bare latitude/longitude scatter do not replace a map when users need to understand where places are. A decorative map, an unreadable strip, or markers lost in an unnecessarily broad extent do not satisfy the requirement.

Integrate the map into the main analytical workflow. Prefer the overview when location is central to the first question; a clearly labeled map tab is acceptable when it preserves relevant filter context and does not needlessly separate essential comparisons. Do not require a duplicate overview map merely because one exists on another usable view. For a live review, trace locating a matching record or area and relating it to the relevant metric/detail. For screenshot-only reviews, inspect all supplied views and navigation before reporting a missing map; distinguish "absent from supplied evidence" from confirmed absence, and mark unpictured map tabs or untested filter linkage as unverified.

Report a **medium-priority** geographic-coverage finding when an applicable map is missing or materially inadequate while other analysis remains useful; cap visual quality at **7/10**. Use **high priority** and the **3/10** unusable-primary-view ceiling when a broken or unusable map blocks the dashboard's primary spatial workflow. Apply a lower existing ceiling when essential labels are unreadable or outputs repeatedly fail. Group map sizing, framing, and missing context into the affected task finding rather than counting the same obstacle repeatedly. These are review rules, not validated predictions of human preference.

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

At the actual first viewport and normal viewing size, before the component checklist, ask:

- Is the subject immediately recognizable?
- Is there a clear starting point?
- Can the main analytical story be understood without opening another tab?
- Does the page feel complete, balanced, and trustworthy?

Secondary tabs can add depth, but they do not repair a weak first impression.

Record a provisional **holistic score** and the dominant element before continuing. Keep the original observation even if later evidence changes the final grade. Full-page thumbnails can reveal overall structure, but cannot establish what is simultaneously visible or readable to a user.

### Step 3: Trace tasks and relationships

Choose two or three questions from the stated audience and task, and identify the visible evidence needed to answer each. For example: compare neighborhood prices, locate matching listings, then inspect one listing. Do not invent an audience, a trend, or an unsupported conclusion. An exploratory dashboard can succeed by exposing useful questions and comparisons without asserting a single editorial takeaway.

For each task, record the starting view, scroll positions or tab changes, whether related values are visible together, and any need to remember values across screens. Report how many viewport heights the primary analysis occupies; distinguish necessary detail browsing from avoidable scrolling for a core comparison. Long pages and tables below the fold are not automatically defects.

Judge relationships, not component inventory:

- Does the space and visual emphasis given to KPIs and filters match their importance relative to the analysis?
- Do related charts use compatible units, scales where comparison requires them, and stable category colors? Are comparisons adjacent or needlessly separated?
- Do repeated cards, headings, icons, or large plots collectively overwhelm the main question, even if each looks acceptable alone?
- Do gradients, shadows, and saturated fills improve grouping or obscure text and compete with data? Neither reward nor ban decoration by itself.
- Can a chart be interpreted at normal size, rather than merely having labels? Check overlapping legends, ambiguous size encodings, misleading axes, map framing, tiny slices, and redundant charts against the task.

Describe compounding flaws as one task-level obstacle: oversized cards plus small labels plus separated comparisons may make analysis impractical. Apply the severity of that combined effect; do not turn it into several tiny deductions that polish can cancel, or double-count the same obstacle.

### Step 4: Inspect component execution

Consider each dimension explicitly before choosing the final score:

1. **Hierarchy and scanability** — the eye knows where to start and what matters.
2. **Composition and density** — space is used purposefully without crowding.
3. **Color and typography coherence** — repeated, legible, functional styling.
4. **Chart, map, and table clarity** — suitable forms, labels, units, and readable marks.
5. **Visible usability** — controls look understandable and useful details are accessible.
6. **Completeness and polish** — no broken, loading, overlapping, clipped, or stretched output.

Do not give a high score based on only one dimension.

Record component execution separately from the holistic score. Presence of filters, KPIs, charts, and a table establishes inventory, not design quality. Do not mechanically average these six dimensions into a visual grade.

### Step 5: Inspect secondary views and interaction evidence

Check additional screenshots for consistent styling and render quality. Reward useful depth, but do not award points simply because an app has more screenshots or navigation.

When a live app is available, test a representative filter, reset, empty result, and relevant navigation. Check browser and server errors and confirm that outputs settle before scoring. Distinguish an initial loading capture from a persistent failure; preserve the failed evidence and recapture after a bounded wait. Test a narrower viewport when responsive behavior is in scope. Mark anything unavailable as untested, including keyboard access or contrast ratios that were not actually checked.

### Step 6: Calibrate and challenge the grade

For comparison tasks, use supplied reference dashboards or an agreed anchor set at the same viewport, task, and data scope. Hide model/arm labels where possible. Compare pairs on the same questions, allow ties, and reverse presentation order when practical to check order bias. Explain wins with visible evidence. Do not claim pairwise judging is proven more accurate for this dataset, invent anchor images, or treat past AI scores as human ground truth.

Use actual examples at weak, competent, and strong levels when available; otherwise explicitly use the text anchors below. Pairwise losses against lower-scored references are a reason to revisit calibration. Keep ties in reported ranks and separate AI estimates from crowd results.

Before finalizing, give the strongest evidence that the proposed grade is too generous and too harsh. Reconcile both without forcing a reduction or inventing faults. If the final score differs materially from the first impression (about two points on the 10-point scale), explain which newly observed evidence justifies it. Component polish cannot overwrite a weak holistic judgment without that explanation.

## Core-problem ceilings and evidence

These are review calibration rules, not empirically validated predictors of human scores. Apply only when observed at the intended viewport and relevant to the user's primary task:

| Observed obstacle | Maximum visual score |
| --- | --- |
| Repeated unresolved outputs or an unusable primary view | 3/10 |
| Essential labels unreadable at normal size, preventing interpretation | 6/10 |
| An applicable map is missing or materially inadequate, while other analysis remains useful | 7/10 |
| Severe hierarchy failure or avoidable scrolling that separates essential comparisons | 7/10 |

The lowest applicable ceiling wins; a ceiling is not a target score. Explain the affected task and screenshot region. A single broken primary output may be severe even when other cards render; an explained intentional empty state is different. Missing capture evidence lowers confidence rather than proving a defect.

## Review output

Include the app/run identity and evidence inspected; viewport, zoom, tab/filter state; provisional holistic score; brief component assessment; two or three task outcomes; prioritized issues with screenshot location, user impact, and concrete fix; applicable ceiling; and final score with confidence and untested behavior. Report the strongest supporting and opposing evidence for the grade. Scale the report to the request.

Use 1–10 as the native visual scale. If a 15-point presentation is requested, show `visual / 10 × 15` and label it a rescaling, not a new evaluation or a human score. Keep functional completeness, code quality, and visual judgment separate. A pass flag, unjudged pipeline default, or score from a different run is not visual evidence.

This workflow incorporates the proposals in [Dashboard Grading Analysis](https://chatgpt.com/share/6a9e2b6a-88b4-83e8-880c-31ed20a24eb7). Treat those proposals as evaluation hypotheses to validate against held-out human ratings, not measured improvements in agreement.

## Score Anchors

- **9** — An immediate human favorite: cohesive, information-rich, highly legible, and visually complete with excellent first-impression quality.
- **8** — Strong professional dashboard: clear hierarchy, purposeful density, coherent palette, useful primary view, and only minor rough edges.
- **7** — Good and trustworthy: conventional styling is acceptable; the dashboard tells its story clearly but lacks some refinement.
- **6** — Tidy but basic: functional and readable, yet sparse, weakly prioritized, or visually generic.
- **5** — Mixed: some useful content, but hierarchy, density, chart choice, or coherence noticeably limits comprehension.
- **4** — Weak: confusing, cramped, patchwork, poorly sized, or substantially incomplete.
- **1-3** — Broken or unusable: repeated blank outputs, stuck loading states, severe overlap, unreadable content, or failed rendering.

Reserve high scores for screenshots that succeed across the full scorecard. Do not require novelty or custom framework styling.
