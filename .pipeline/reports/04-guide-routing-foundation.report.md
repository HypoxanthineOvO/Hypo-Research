# M01 Report - Guide Routing Foundation

## Result

PASS

## Changes

- Added `src/hypo_research/guide/` with deterministic route models and router.
- Added `hypo-research guide "<request>"` CLI command.
- Added router and CLI tests in `tests/test_guide.py`.

## Validation

```bash
uv run pytest tests/test_guide.py
uv run hypo-research guide "我论文快投了，帮我检查一下"
uv run hypo-research guide "read this PDF"
uv run hypo-research --help
```

All M01 validations passed.
