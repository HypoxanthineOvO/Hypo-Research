# M01 - Guide Routing Foundation

## Objective

Add a runnable `hypo-research guide` foundation that routes natural-language research requests into the main command categories without forcing users to memorize individual skill names.

## 需求

- Add a `src/hypo_research/guide/` package with typed route/intent/scenario models.
- Add a deterministic router that recognizes at least these top-level categories:
  - `guide`
  - `check`
  - `review`
  - `read`
  - `search`
  - `project`
  - `idea`
- Add CLI command `hypo-research guide "<request>"`.
- Default output should be route advice, confidence, rationale, follow-up questions, and suggested next commands.
- Cover common utterances:
  - "我论文快投了，帮我检查一下"
  - "帮我读这篇 PDF"
  - "调研一个陌生方向"
  - "帮我模拟审稿"
  - "帮我管理这个研究项目"
- Preserve direct subcommand usage; guide is a convenience layer, not a forced path.

## Boundaries

- In scope: router models, simple deterministic rule-based router, CLI output, tests.
- Out of scope: executing child commands; `--execute` belongs to M06.
- Out of scope: rewriting existing skills or README.

## Non-Goals

- Do not introduce LLM calls for routing in this milestone.
- Do not remove or rename existing commands.
- Do not overfit only Chinese phrases; include a small set of English cases.

## 预期测试

- Unit tests for route classification, confidence, and suggested commands.
- CLI test for `uv run hypo-research guide "我论文快投了，帮我检查一下"`.
- Existing `uv run hypo-research --help` still works.

## Validation Commands

```bash
uv run pytest tests/test_guide*.py
uv run hypo-research guide "我论文快投了，帮我检查一下"
uv run hypo-research guide "read this PDF"
uv run hypo-research --help
```

## Evidence

- Tests pass.
- CLI output includes route, rationale, next command, and follow-up questions.
- No existing top-level command is removed.

## Human QA

- Check whether route wording matches the intended large categories: guide/check/review/read.

## 预期产出

- `src/hypo_research/guide/`
- CLI `guide` command.
- Tests for router and CLI output.
