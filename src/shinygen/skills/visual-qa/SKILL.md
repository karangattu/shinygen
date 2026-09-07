---
name: visual-qa
description: Visually verify the rendered dashboard application by running it, checking logs, and reviewing screenshots to evaluate human-perceived visual appeal, UX quality, information hierarchy, and layout correctness.
metadata:
  author: Antigravity
  version: "1.2"
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

The dashboard study suggests **one-screen usefulness** matters: compact filters, concise KPIs, a prominent decision-relevant visualization, supporting comparisons, and accessible detail. This is a candidate archetype, not a mandatory template or evidence that every audience prefers it. Judge whether those parts work together for the actual task, not whether they exist.

**Clean alone is not enough.** A tidy screenshot should not score highly when it is sparse, dominated by oversized KPI tiles, missing useful context, or forces users across several views to understand the basic story.

Apply the **render-state gate** before judging aesthetics. Repeated empty panels, unresolved output placeholders, tiny loading marks, or stuck spinners make the visible dashboard incomplete even when its code and surrounding cards look polished.

Read [references/human_visual_preferences.md](references/human_visual_preferences.md) before scoring or revising visual quality. It contains the human-aligned inspection sequence and score anchors.

## Hands-on Visual Self-Evaluation Workflow

For a live-app review, run the app and take screenshots. For a screenshot-only request, inspect the supplied evidence and report untested behavior; do not infer working interactions or responsive layouts from code or one image. Review requests authorize findings; revise the app only when building or fixing it is in scope.

After capturing screenshots:

1. Capture the first real viewport at the intended display size (for example 1440×900 CSS pixels, normal browser zoom), subsequent scroll positions, and a full-page image for context. Record viewport, zoom, scroll offsets, and filter/tab state. Read labels at normal viewing size; a tall image shrunk to fit the screen is not evidence of readability. The helper below produces full-page images; supplement it with browser screenshots using `full_page=False` at actual scroll positions. A crop of an existing full-page image is only an approximation and cannot prove sticky behavior or reflow.
2. Before inspecting component details or source code, record the first impression: what dominates, the apparent purpose, the first useful question to investigate, and a provisional holistic score. Preserve this observation. This simulates a brief glance; it is not a measured human five-second test. A genuinely blinded first pass needs a separate evaluation context that has not seen the detailed rubric.
3. Apply the render-state gate and trace two or three relevant user questions through the views. Record scrolling, tab changes, and comparisons that require remembering information from another screen. See the reference for the relationship and task checks.
4. Inspect component execution and secondary views, then challenge both an overly generous and an overly harsh grade. Reconcile the holistic impression, task evidence, and component findings before assigning a final score. Do not average away major usability failures.
5. When revisions are authorized, fix the highest-impact obstacles, capture fresh screenshots at the same viewport and state, and repeat the task checks. Otherwise report the findings and recommended changes.

Use the evidence and reporting format in [references/human_visual_preferences.md](references/human_visual_preferences.md), including its score ceilings and optional pairwise calibration for ranking tasks.

### Python Verification Pipeline

```bash
nohup python -m shiny run app.py --port 8000 > /tmp/app.log 2>&1 &
printf '%s\n' "$!" > /tmp/shinygen_app.pid
tail -n 80 /tmp/app.log
python /home/user/project/.tools/screenshot_helper.py
tail -n 80 /tmp/app.log
if [ -s /tmp/shinygen_app.pid ]; then
  read -r app_pid < /tmp/shinygen_app.pid
  kill "$app_pid" 2>/dev/null || true
  rm -f /tmp/shinygen_app.pid
fi
```

Use the recorded PID for restarts too. Never use `pkill`, `killall`, or another
pattern-based process command because it can terminate the agent itself.

### R Verification Pipeline

```bash
nohup Rscript -e "shiny::runApp('app.R', port=8000, launch.browser=FALSE)" > /tmp/app.log 2>&1 &
printf '%s\n' "$!" > /tmp/shinygen_app.pid
tail -n 80 /tmp/app.log
python3 /home/user/project/.tools/screenshot_helper.py
tail -n 80 /tmp/app.log
if [ -s /tmp/shinygen_app.pid ]; then
  read -r app_pid < /tmp/shinygen_app.pid
  kill "$app_pid" 2>/dev/null || true
  rm -f /tmp/shinygen_app.pid
fi
```
