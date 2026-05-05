# M03 - PDF Full-Text Reading and Conversion Capability Review

## Objective

Investigate how Hypo-Research should support paper PDF to Markdown/HTML conversion, image/table extraction, and graded full-text reading that can answer method, dataset, key figure, and claim-evidence questions.

## 需求

- Before prototype work, stop and ask the user to provide two PDF papers.
- Lightly research existing PDF-to-MD/HTML and paper parsing options, focusing on preserving structure, figures, tables, formulas, captions, and section hierarchy.
- Consider tools and approaches such as GROBID, PyMuPDF, Marker, Nougat, Docling, Unstructured, LlamaIndex readers, Pandoc/OCR pipelines, or other current candidates discovered during research.
- Design a graded full-text reading model:
  - L0 metadata and abstract
  - L1 introduction and conclusion
  - L2 methods, datasets, experiments, key figures
  - L3 structured full-paper notes
  - L4 multi-paper evidence matrix
- Prioritize questions:
  - What method does the paper use?
  - What data or benchmarks does it run?
  - What do key figures show?
  - Are claims supported by experiments?

## Boundaries

- In scope: tool research, interface design, optional local prototype over two PDFs, risk assessment.
- In scope: output format sketch for Markdown/HTML plus extracted assets.
- Out of scope: production-grade parser integration, large-scale OCR benchmark, full UI.

## Non-Goals

- Do not promise perfect formula, table, or figure extraction.
- Do not attempt exhaustive market research.
- Do not run remote or expensive processing without explicit user approval when needed.

## 预期测试

- The report compares candidate tool chains against paper-specific needs.
- If PDFs are provided, the prototype records what can be extracted and what fails.
- The interface sketch supports method/data/figure/claim queries.
- The design includes fallback behavior for poor extraction quality.

## Validation Commands

- Ask user for two PDF files before prototype validation.
- Inspect available local tools with safe commands as needed.
- If dependencies already exist, run a minimal extraction experiment and record commands used.

## Evidence

- Write `.pipeline/reports/02-pdf-full-text-reading-and-conversion-capability-review.report.md`.
- If prototype runs, save extracted sample outputs under `.pipeline/reports/pdf-prototype/` or another clearly named report subdirectory.
- Include candidate matrix, extraction observations, and recommended pipeline.

## Human QA

- User provides two PDFs before prototype work.
- User reviews whether extraction quality is sufficient for the next implementation Cycle.

## 预期产出

- `.pipeline/reports/02-pdf-full-text-reading-and-conversion-capability-review.report.md`
- PDF/HTML/Markdown conversion pipeline recommendation.
- Graded reading API/interface sketch.
- Prototype evidence if PDF samples are available.
