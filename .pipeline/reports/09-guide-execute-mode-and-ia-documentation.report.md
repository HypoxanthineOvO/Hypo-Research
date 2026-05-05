# M06 Report - Guide Execute Mode and IA Documentation

## Result

PASS

## Changes

- Added `hypo-research guide --execute` with conservative execution paths.
- Implemented safe execution for:
  - check requests: `check --full` behavior through the local check pipeline.
  - read requests: `read ingest` followed by `read outline`.
  - review requests: execute only when `--target` and `--venue` are provided; otherwise suggest the direct command.
  - search requests: execute only with explicit `--query`.
- Kept direct `check`, `read`, `review`, and `search` subcommands first-class.
- Updated README first-use IA around `guide`, `check`, `review`, and `read`.
- Added `hypo-guide` and `hypo-read` Skill docs.
- Updated `hypo-check` and `hypo-presubmit` docs to clarify `check --full` as the daily paper check path and `presubmit` as compatibility/legacy wrapper.
- Synchronized source, Codex bundle, and plugin skill mirrors.

## Validation

```bash
uv run pytest tests/test_guide.py tests/test_read.py tests/test_check.py tests/test_check_cli.py
uv run pytest
uv run hypo-research guide "我论文快投了，帮我检查一下"
uv run hypo-research guide "我论文快投了，帮我检查一下" --execute --target tests/fixtures/lint_buggy.tex
uv run hypo-research read ingest data/reviews/FRR/FRRPaper.pdf --out /tmp/hypo-read-frr-m6
uv run hypo-research check tests/fixtures/lint_buggy.tex --full --no-save
```

Focused validation passed: 30 tests.

Full regression passed: 482 passed, 3 skipped, 2 warnings.

The buggy fixture check returned code 1 as expected because it reports blocking issues; the guide execute path completed and rendered the report without treating findings as a runtime failure.
