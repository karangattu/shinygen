# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Pre-built sandbox images on GHCR**: New `.github/workflows/build-sandbox-images.yml` builds and publishes `ghcr.io/<owner>/shinygen-sandbox-python` and `ghcr.io/<owner>/shinygen-sandbox-r` with `claude` and `codex` standalone binaries baked in. Compose files default to pulling these (`pull_policy: missing`) and fall back to local build when missing. Switches `CODEX_CLI_VERSION` to `"auto"` so `inspect_swe` reuses the in-image binary instead of re-downloading per sample.
- **Benchmark workflows pre-pull sandbox image**: `run-benchmark-matrix.yml`, `run-shinygen.yml`, and `run-shinygen-multi.yml` log into GHCR and `docker pull` the framework-appropriate image before running, eliminating the ~10 min Dockerfile build (R) and per-sample CLI downloads. Override the image tag via `SHINYGEN_SANDBOX_PYTHON_IMAGE` / `SHINYGEN_SANDBOX_R_IMAGE`.
- **Judge requires sandbox screenshots**: Iteration judging now reuses `agent_last_screenshot.png` captured inside the sandbox and fails loudly if that artifact is missing instead of falling back to host-side or code-only judging. This keeps benchmark visual scoring tied to sandbox-captured evidence and avoids silent quality regressions.

### Fixed
- **Restore host-side screenshot deps on benchmark runner**: `run-benchmark-matrix.yml` now reinstalls `shinygen[screenshot]` + `playwright install chromium` + Python Shiny runtime packages (`shiny plotly faicons pandas matplotlib seaborn shinywidgets`). The earlier optimization that dropped these assumed the in-sandbox screenshot would always succeed, but agents that get SIGTERMed mid-run leave no `agent_last_screenshot.png` and the host-side fallback then fails with `No module named 'playwright'`. Reinstalling adds ~30s per job and lets the fallback in `iterate.py` actually capture an image. Also demoted the iteration-1 "ERROR" log to "WARNING" since the loop already recovers on the final iteration.
- **Python dashboards no longer render with cards glued together**: Python Shiny's `ui.layout_columns()` and `ui.layout_column_wrap()` produce `<div class="bslib-grid">` with `gap: 0` by default unless `gap=` is passed explicitly (unlike R bslib). Agents frequently forget the `gap` argument, producing dashboards where every value box and card visibly touches. The Python system prompt now requires creating a `styles.css` with `.bslib-grid { gap: 1rem !important; ... }` plus margin rules for bare card sequences, and loading it via `ui.include_css(...)`. The shiny-python-dashboard skill, its styling reference, and the Quick Start example are aligned with the same safety net. R dashboards are unaffected because R bslib defaults to a non-zero Bootstrap gap.
- **Benchmark resilience when agent SIGTERMs**: When the in-sandbox `agent_last_screenshot.png` is missing (e.g. the codex/claude CLI is killed mid-run before reaching its screenshot step), `_resolve_judge_screenshot_paths` now attempts a host-side capture against the recovered code instead of immediately raising. If host-side capture also fails on the final iteration, the loop proceeds with code-only judging rather than failing the entire run. Set `SHINYGEN_STRICT_SANDBOX_SCREENSHOT=1` to restore the previous strict behavior.
- **Token truncation recovery**: Detect when Claude hits output token limits before writing artifacts; automatically retry with a focused direct-write prompt instead of repeating the full generation
- **R screenshot pipeline**: Uncomment R app launch command in visual-QA skill, add `python3` screenshot helper reference for R containers, and add `Rscript` process cleanup
- **R package baseline**: Add `scales` and `thematic` to default R install command to prevent app startup failures during visual QA

### Changed
- Lower Claude `reasoning_effort` from `high` to `medium` to reduce run duration while maintaining adaptive thinking
- Append `EXECUTION PRIORITY` directive to all system prompts, instructing the agent to write the primary artifact early and avoid excessive reconnaissance
- Ignore benchmark aggregate directories in `.gitignore`
