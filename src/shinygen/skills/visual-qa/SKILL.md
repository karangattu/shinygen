---
name: visual-qa
description: Visually verify a generated Shiny app by capturing every tab/view, reviewing the rendered UI across the whole app, and iterating on layout or styling problems before finishing.
---

# Visual Self-Evaluation Skill

After creating your Shiny app, you MUST visually verify it by capturing
**every tab and panel** (not just the landing page) and evaluating the
result. Playwright and Chromium are pre-installed in this environment.

## Workflow

1. **Create the app** — Write your `app.py` (or `app.R`) as normal.
2. **Start the app** in the background on port 8000:
   ```bash
   cd /home/user/project
   # Python
   nohup python -m shiny run app.py --port 8000 > /tmp/app.log 2>&1 &
   # R
   nohup Rscript -e "shiny::runApp('app.R', port=8000, launch.browser=FALSE)" > /tmp/app.log 2>&1 &
   ```
3. **Capture every view** once the server is up:
   ```bash
   # Python
   python /home/user/project/.tools/screenshot_helper.py
   # R
   python3 /home/user/project/.tools/screenshot_helper.py
   ```
   The helper writes a numbered series into `/home/user/project/`:

   ```
   screenshot_01_landing.png
   screenshot_02_<tab-slug>.png
   screenshot_03_<tab-slug>.png
   ...
   ```

   It auto-detects tab/nav links from `ui.navset_*`, `ui.page_navbar`, and
   any `[role="tab"]` / `data-bs-toggle="tab"` element, clicks each one,
   waits for Shiny to settle, then captures a full-page screenshot. The
   landing capture is also copied to `/home/user/project/screenshot.png`
   for backwards compatibility — but **all numbered files must remain in
   place** so the judge can score the whole app, not just the first tab.

4. **View every screenshot** to evaluate the visual output across the app.
   Multi-tab dashboards are scored against the *combined* set of views, not
   just the landing page. A polished landing page with broken tabs is
   worse than a uniformly polished multi-tab app.
5. **Evaluate** every screenshot against these criteria:
   - Does each tab render correctly (no blank panels, no overlapping elements)?
   - Are charts/plots visible and properly sized **on every tab**?
   - Are titles, labels, and text readable on every view?
   - Does the colour scheme stay consistent across tabs?
   - Is the sidebar/navigation functional-looking and consistent?
   - Are value boxes, cards, and UI components properly styled on every view?
   - **Coverage**: do all tabs feel intentional, or is one a near-empty placeholder?
6. **Fix any issues** you spot and repeat steps 2-5. Pay extra attention to
   tabs that look thin compared to the landing page — fill them out instead
   of leaving them as stubs.
7. **Stop the app** when done:
   ```bash
   pkill -f "Rscript" || true
   pkill -f "shiny run" || true
   ```

## Important

- Always kill any previous app process before restarting.
- If a screenshot shows a blank page, check `/tmp/app.log` for errors.
- **Do not delete the numbered `screenshot_NN_*.png` files** — they are
  the artifacts the judge uses to score the app fairly across all tabs.
- Aim for a polished, production-quality visual appearance on every tab,
  not just the landing page.
- You may iterate up to 3 times on visual fixes.
