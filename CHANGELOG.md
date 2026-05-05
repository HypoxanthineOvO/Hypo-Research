# Changelog

## v0.7.1 - 2026-05-05

### Fixes

- Fixed plugin manifest: `author` field changed from string to object `{name}` format, resolving installation failure on Claude Code plugin validation.

### Tests

- Full regression: `492 passed, 3 skipped, 2 warnings`.

## v0.7.0 - 2026-05-05

### Features

- Added `guide` as a first-line natural-language router with conservative `--execute` support.
- Added PDF reading workflows: `read ingest`, `read outline`, and `read extract` evidence cards.
- Added `check --full` with Agent-facing submission-readiness review checklist.
- Added Research Brief V2 sections to literature Markdown reports.
- Added paper target resolution for files, folders, and `.zip` / `.tar*` archives.
- Added `hypo-guide` and `hypo-read` skills and updated skill IA around guide/check/review/read.

### Fixes

- Clarified `presubmit` as a compatibility/legacy wrapper while keeping direct `check --full` as the primary paper check.
- Repaired stale workflow lock and accepted Cycle C2 state before release.

### Tests

- Full regression: `492 passed, 3 skipped, 2 warnings`.
