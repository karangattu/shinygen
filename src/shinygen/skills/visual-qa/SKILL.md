---
name: visual-qa
description: Visually verify the rendered dashboard application by running it, checking logs, and reviewing screenshots to evaluate human-perceived visual appeal, UX quality, information hierarchy, and layout correctness.
metadata:
  author: Antigravity
  version: "1.1"
  license: MIT
---

# Visual QA & UX Evaluation

Visually verify and evaluate Shiny dashboards against professional modern design standards. Dashboards should center on user empathy, ruthlessly prioritize metrics, and structure clear visual hierarchies so users can absorb critical data within five seconds. An effective dashboard is a functional, interactive story rather than a cluttered dumping ground for charts.

## Progressive Loading

Read this file to understand the verification workflow, then load only the references needed for your specific evaluation task:

| Evaluation Target | Reference Document |
| --- | --- |
| Human Preference Calibration, First-Impression Quality, and the Visual Scorecard | [references/human_visual_preferences.md](references/human_visual_preferences.md) |
| User Empathy, Ruthless Metric Prioritization, and the 5-Second Rule | [references/principles.md](references/principles.md) |
| Accessibility, Color Contrast, Legible Typography, and Graceful State Handling | [references/accessibility_and_ux.md](references/accessibility_and_ux.md) |

## Human Preference Calibration

Judge the screenshot as a human deciding whether the dashboard looks clear, useful, cohesive, and complete. Do not reward visual novelty, custom CSS, extra tabs, or unusually large components by themselves. A conventional Shiny layout can be excellent when it presents the analytical story immediately.

Human raters consistently favor **one-screen usefulness**: a compact filter rail, 3-4 concise KPIs, a prominent primary visualization such as a map or decision-relevant chart, a balanced grid of supporting charts, and a detail table. This is a strong archetype, not a mandatory template.

**Clean alone is not enough.** A tidy screenshot should not score highly when it is sparse, dominated by oversized KPI tiles, missing useful context, or forces users across several views to understand the basic story.

Apply the **render-state gate** before judging aesthetics. Repeated empty panels, unresolved output placeholders, tiny loading marks, or stuck spinners make the visible dashboard incomplete even when its code and surrounding cards look polished.

Read [references/human_visual_preferences.md](references/human_visual_preferences.md) before scoring or revising visual quality. It contains the human-aligned inspection sequence and score anchors.

## Hands-on Visual Self-Evaluation Workflow

To evaluate visual quality, layout correctness, chart visibility, text readability, colors, and styling, you must run the app and take screenshots.

After capturing screenshots:

1. Inspect the landing screenshot first at fit-to-screen size. Record what a user can understand within five seconds.
2. Check the render-state gate: every KPI, chart, map, and table must contain meaningful rendered content rather than loading marks or suspicious blank space.
3. Evaluate hierarchy, purposeful density, palette coherence, labels, and whether the primary analytical story is visible without excessive navigation.
4. Inspect secondary views for consistency and breakage, but do not let the number of views substitute for the quality of the landing view.
5. Revise the app, capture fresh screenshots, and judge the new screenshots rather than the intended code.

### Python Verification Pipeline

```bash
nohup python -m shiny run app.py --port 8000 > /tmp/app.log 2>&1 &
tail -n 80 /tmp/app.log
python /home/user/project/.tools/screenshot_helper.py
tail -n 80 /tmp/app.log
pkill -f "shiny run" || true
```

### R Verification Pipeline

```bash
nohup Rscript -e "shiny::runApp('app.R', port=8000, launch.browser=FALSE)" > /tmp/app.log 2>&1 &
tail -n 80 /tmp/app.log
python3 /home/user/project/.tools/screenshot_helper.py
tail -n 80 /tmp/app.log
pkill -f "Rscript" || true
```
