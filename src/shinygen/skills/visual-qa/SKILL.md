---
name: visual-qa
description: Visually verify the rendered dashboard application by running it, checking logs, and reviewing screenshots to evaluate visual appeal, UX quality, and layout correctness.
metadata:
  author: Antigravity
  version: "1.0"
  license: MIT
---

# Visual QA & UX Evaluation

Visually verify and evaluate Shiny dashboards against professional modern design standards. Dashboards should center on user empathy, ruthlessly prioritize metrics, and structure clear visual hierarchies so users can absorb critical data within five seconds. An effective dashboard is a functional, interactive story rather than a cluttered dumping ground for charts.

## Progressive Loading

Read this file to understand the verification workflow, then load only the references needed for your specific evaluation task:

| Evaluation Target | Reference Document |
| --- | --- |
| User Empathy, Ruthless Metric Prioritization, and the 5-Second Rule | [references/principles.md](references/principles.md) |
| Accessibility, Color Contrast, Legible Typography, and Graceful State Handling | [references/accessibility_and_ux.md](references/accessibility_and_ux.md) |

## Hands-on Visual Self-Evaluation Workflow

To evaluate visual quality, layout correctness, chart visibility, text readability, colors, and styling, you must run the app and take screenshots.

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
