# Changelog

## 0.2.0 - 2026-06-08

- Added `export --format handoff` for new-thread agent handoffs.
- Handoff exports include project snapshot, operating constraints, recent work, decisions, verification commands, test evidence, ownership, and a next-agent prompt.
- Added renderer and CLI tests for handoff exports.
- Expanded Chinese and English README docs with Codex / Claude Code handoff workflows.
- Added CI smoke coverage for handoff export generation.

## 0.1.0 - 2026-06-08

- Initial release of `agent-memory-briefcase`
- Added offline CLI commands for initialization, decisions, sessions, briefs, linting, exports, and CI checks
- Added mirrored Markdown and JSON storage for decisions and sessions
- Added stale-memory detection and budget-aware brief truncation
- Added examples, documentation, and GitHub Actions CI
- Added unittest coverage for storage, linting, export, truncation, stale detection, and CLI behavior
