# M05 - Read L2 Evidence Cards

## Objective

Add initial L2 evidence-card extraction for methods, datasets/benchmarks, figures/tables, and claims from `PaperReadArtifact`.

## 需求

- Extend read package with evidence card models:
  - `MethodCard`
  - `DatasetCard`
  - `FigureCard`
  - `ClaimCard`
- Add `read extract <artifact> --focus methods,datasets,figures,claims --out <dir>`.
- Use deterministic heuristics first:
  - method sections and "we propose/present/introduce" sentences
  - experiment/evaluation sections for datasets/benchmarks
  - figure/table captions and page references
  - claim sentences and nearby evidence candidates
- Generate JSON and Markdown summary.
- Include confidence/uncertainty fields.
- Generate Agent prompt/checklist for deeper paper reading based on cards.

## Boundaries

- In scope: schema, heuristic extraction, CLI, tests.
- In scope: explicit uncertainty and low-confidence notes.
- Out of scope: VLM image understanding, full table parsing, citation graph integration.

## Non-Goals

- Do not claim that heuristic cards are complete or peer-review-grade.
- Do not require external services.
- Do not block if only partial cards are found.

## 预期测试

- Unit tests for card extraction from controlled text fixture.
- CLI smoke using artifact from M04.
- Markdown summary includes methods/datasets/figures/claims sections.

## Validation Commands

```bash
uv run pytest tests/test_read*.py
uv run hypo-research read ingest data/reviews/FRR/FRRPaper.pdf --out /tmp/hypo-read-frr
uv run hypo-research read extract /tmp/hypo-read-frr/artifact.json --out /tmp/hypo-read-frr/cards
```

## Evidence

- Cards JSON and Markdown summary are generated.
- Low-confidence cases are explicit.
- Agent prompt is included for subjective follow-up.

## Human QA

- Inspect whether method/data/figure/claim cards are useful enough for next implementation cycle.

## 预期产出

- Evidence card schemas.
- `read extract` CLI.
- JSON/Markdown card outputs.
- Tests and smoke evidence.
