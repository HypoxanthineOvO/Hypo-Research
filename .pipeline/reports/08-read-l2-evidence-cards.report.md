# M05 Report - Read L2 Evidence Cards

## Result

PASS

## Changes

- Added heuristic L2 evidence-card extraction for read artifacts.
- Added `read extract <artifact.json> --out <dir>`.
- Added JSON and Markdown evidence-card outputs for methods, datasets, figures, and claims.
- Added Agent-facing deep-read prompt text in the extraction result.
- Extended read tests for extraction API and CLI behavior.

## Validation

```bash
uv run pytest tests/test_read.py
uv run hypo-research read ingest data/reviews/FRR/FRRPaper.pdf --out /tmp/hypo-read-frr
uv run hypo-research read extract /tmp/hypo-read-frr/artifact.json --out /tmp/hypo-read-frr/cards
```

All M05 validations passed.
