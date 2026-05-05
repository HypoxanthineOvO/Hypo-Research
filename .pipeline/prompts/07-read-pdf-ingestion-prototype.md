# M04 - Read PDF Ingestion Prototype

## Objective

Add `hypo-research read ingest/outline` with `PaperReadArtifact` v0, using PyMuPDF as the primary local parser and a clean adapter boundary for future Docling/Marker/GROBID support.

## 需求

- Add optional dependency for PDF reading, with PyMuPDF as the first backend.
- Add `src/hypo_research/read/` package.
- Define `PaperReadArtifact` v0 with:
  - source path/hash
  - page count
  - metadata
  - raw text
  - rough sections
  - figure/image metadata
  - extraction quality
  - backend info
- Add CLI group `read` with:
  - `read ingest <pdf> --out <dir>`
  - `read outline <artifact>`
- Use local sample PDFs under `data/reviews/` for smoke validation.
- Predefine adapter interface for Docling or other parsers, but do not implement heavy adapters yet.

## Boundaries

- In scope: local PDF parsing, artifact JSON, outline rendering, tests.
- Out of scope: L2 evidence cards; M05 owns extraction.
- Out of scope: OCR-heavy handling and production-quality table parsing.

## Non-Goals

- Do not require network.
- Do not make PyMuPDF a mandatory base dependency if optional extra is sufficient.
- Do not change existing `review.parser` behavior unless a safe shared helper emerges.

## 预期测试

- Unit tests for artifact model serialization.
- CLI smoke with sample PDF.
- Graceful error when PDF backend is unavailable.

## Validation Commands

```bash
uv run pytest tests/test_read*.py
uv run hypo-research read ingest data/reviews/FRR/FRRPaper.pdf --out /tmp/hypo-read-frr
uv run hypo-research read outline /tmp/hypo-read-frr/artifact.json
```

## Evidence

- Artifact JSON contains pages, text summary, rough sections, and image metadata.
- CLI outline is readable and includes extraction quality.

## Human QA

- Inspect artifact and outline for one real paper.

## 预期产出

- `src/hypo_research/read/`
- CLI `read ingest` and `read outline`.
- Optional dependency metadata.
- Tests and sample artifact smoke.
