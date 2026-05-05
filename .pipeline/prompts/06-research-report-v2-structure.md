# M03 - Research Report V2 Structure

## Objective

Upgrade the search/survey Markdown report structure so it can support research briefs rather than only ranked paper lists.

## 需求

- Extend report generation with a v2 profile or structured sections:
  - field familiarity / task setting
  - primer placeholder
  - paper map placeholder
  - evidence depth
  - method/dataset/claim matrix placeholders
  - enhanced reading order
  - uncertainty/metadata quality notes
- Preserve compatibility with existing `results.md` consumers.
- Add configuration or CLI option only if needed; default can remain compatible while v2 structure is testable.
- Do not require LLM generation for primer content in this milestone; stable report slots are enough.

## Boundaries

- In scope: output renderer, summary payload additions, tests.
- In scope: `SearchResult`/`SurveyMeta` metadata additions if low-risk.
- Out of scope: actual deep full-text extraction; M04-M05 own read artifacts.

## Non-Goals

- Do not remove current ranking tables.
- Do not make the report verbose for tiny searches without need.
- Do not add remote calls.

## 预期测试

- Golden Markdown test for report v2 sections.
- Existing report tests pass.
- Search CLI still writes results.md.

## Validation Commands

```bash
uv run pytest tests/test_markdown_report.py tests/test_survey_cli.py tests/test_json_output.py
uv run hypo-research search "LLM for code generation" --max-results 2 --source arxiv --output-dir /tmp/hypo-report-v2-smoke
```

## Evidence

- Generated report contains v2 sections or profile.
- Backward-compatible ranking and verification sections remain.

## Human QA

- Check report outline against M04 previous analysis report.

## 预期产出

- Updated Markdown report renderer.
- Tests for v2 report structure.
- Optional metadata fields for evidence depth/report profile.
