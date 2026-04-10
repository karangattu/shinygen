---
name: visual-qa
description: Visually verify a generated Shiny app by taking a screenshot, reviewing the rendered UI, and iterating on layout or styling problems before finishing.
---

# Visual Self-Evaluation Skill

After creating your Shiny app, you MUST visually verify it by taking a
screenshot and evaluating the result. Playwright and Chromium are
pre-installed in this environment.

## Workflow

1. **Create the app** — Write your `app.py` (or `app.R`) as normal.
2. **Start the app** in the background on port 8000:
   ```bash
   cd /home/user/project
   # Python
   nohup python -m shiny run app.py --port 8000 > /tmp/app.log 2>&1 &
   # R
   # nohup Rscript -e "shiny::runApp('app.R', port=8000, launch.browser=FALSE)" > /tmp/app.log 2>&1 &
   ```
3. **Wait** a few seconds for the server to start, then **take a screenshot**:
   ```bash
   python /home/user/project/.tools/screenshot_helper.py
   ```
   This saves a full-page screenshot to `/home/user/project/screenshot.png`.
4. **View the screenshot** to evaluate the visual output.
5. **Evaluate** the screenshot against these criteria:
   - Does the layout render correctly (no blank pages, no overlapping elements)?
   - Are charts/plots visible and properly sized?
   - Are titles, labels, and text readable?
   - Does the colour scheme look professional?
   - Is the sidebar/navigation functional-looking?
   - Are value boxes, cards, and UI components properly styled?
6. **Fix any issues** you spot and repeat steps 2-5.
7. **Stop the app** when done:
   ```bash
   pkill -f "shiny run" || true
   ```

## Important

- Always kill any previous app process before restarting.
- If the screenshot shows a blank page, check `/tmp/app.log` for errors.
- Aim for a polished, production-quality visual appearance.
- You may iterate up to 3 times on visual fixes.
