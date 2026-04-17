# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Pre-built sandbox images on GHCR**: New `.github/workflows/build-sandbox-images.yml` builds and publishes `ghcr.io/<owner>/shinygen-sandbox-python` and `ghcr.io/<owner>/shinygen-sandbox-r` with `claude` and `codex` standalone binaries baked in. Compose files default to pulling these (`pull_policy: missing`) and fall back to local build when missing. Switches `CODEX_CLI_VERSION` to `"auto"` so `inspect_swe` reuses the in-image binary instead of re-downloading per sample.
- **Benchmark workflows pre-pull sandbox image**: `run-benchmark-matrix.yml`, `run-shinygen.yml`, and `run-shinygen-multi.yml` log into GHCR and `docker pull` the framework-appropriate image before running, eliminating the ~10 min Dockerfile build (R) and per-sample CLI downloads. Override the image tag via `SHINYGEN_SANDBOX_PYTHON_IMAGE` / `SHINYGEN_SANDBOX_R_IMAGE`.
- **Judge requires sandbox screenshots**: Iteration judging now reuses `agent_last_screenshot.png` captured inside the sandbox and fails loudly if that artifact is missing instead of falling back to host-side or code-only judging. This keeps benchmark visual scoring tied to sandbox-captured evidence and avoids silent quality regressions.

### Fixed
- **Token truncation recovery**: Detect when Claude hits output token limits before writing artifacts; automatically retry with a focused direct-write prompt instead of repeating the full generation
- **R screenshot pipeline**: Uncomment R app launch command in visual-QA skill, add `python3` screenshot helper reference for R containers, and add `Rscript` process cleanup
- **R package baseline**: Add `scales` and `thematic` to default R install command to prevent app startup failures during visual QA

### Changed
- Lower Claude `reasoning_effort` from `high` to `medium` to reduce run duration while maintaining adaptive thinking
- Append `EXECUTION PRIORITY` directive to all system prompts, instructing the agent to write the primary artifact early and avoid excessive reconnaissance
- Ignore benchmark aggregate directories in `.gitignore`
