# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- **Token truncation recovery**: Detect when Claude hits output token limits before writing artifacts; automatically retry with a focused direct-write prompt instead of repeating the full generation
- **R screenshot pipeline**: Uncomment R app launch command in visual-QA skill, add `python3` screenshot helper reference for R containers, and add `Rscript` process cleanup
- **R package baseline**: Add `scales` and `thematic` to default R install command to prevent app startup failures during visual QA

### Changed
- Lower Claude `reasoning_effort` from `high` to `medium` to reduce run duration while maintaining adaptive thinking
- Append `EXECUTION PRIORITY` directive to all system prompts, instructing the agent to write the primary artifact early and avoid excessive reconnaissance
- Ignore benchmark aggregate directories in `.gitignore`
