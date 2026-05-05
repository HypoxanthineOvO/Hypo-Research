# M04 Report - Read PDF Ingestion Prototype

## Result

PASS

## Changes

- Added `src/hypo_research/read/` with `PaperReadArtifact` v0.
- Added PDF ingestion using PyMuPDF when available and `pdftotext/pdfimages` fallback.
- Added CLI commands `read ingest` and `read outline`.
- Added `tests/test_read.py`.

## Validation

```bash
uv run pytest tests/test_read.py
uv run hypo-research read ingest data/reviews/FRR/FRRPaper.pdf --out /tmp/hypo-read-frr
uv run hypo-research read outline /tmp/hypo-read-frr/artifact.json
```

All M04 validations passed.
