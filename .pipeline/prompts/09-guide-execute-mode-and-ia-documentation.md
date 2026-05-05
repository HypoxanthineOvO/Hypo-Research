# M06 - Guide Execute Mode and IA Documentation

## Objective

Connect the new Guide, Check, Report, and Read slices into usable user workflows, then update documentation and skill IA around the large categories `guide/check/review/read`.

## 需求

- Add `guide --execute` for safe execution paths:
  - paper checking request -> `check --full`
  - read PDF request -> `read ingest` and `read outline`
  - simulated review request -> route to `review` command or suggest command when execution requires additional parameters
  - search/survey request -> suggest or execute safe search when enough input is present
- Ensure direct subcommands remain first-class.
- Update README first-use flow around:
  - `guide`
  - `check`
  - `review`
  - `read`
  - plus existing expert skills
- Add or update Skill documentation for guide/read/check semantics.
- Clarify `presubmit` as compatibility/legacy thin wrapper in docs if applicable.

## Boundaries

- In scope: CLI execution mode, docs, skill IA, end-to-end smoke tests.
- In scope: small updates to README and selected SKILL.md.
- Out of scope: removing old skills, full docs site rewrite.

## Non-Goals

- Do not execute destructive operations from guide.
- Do not hide direct commands.
- Do not make `guide --execute` require LLM.

## 预期测试

- CLI integration tests for guide execute paths.
- Smoke commands:
  - `guide "我论文快投了" --execute ...`
  - `read ingest <sample.pdf>`
  - `check --full <fixture.tex>`
- README examples match implemented commands.

## Validation Commands

```bash
uv run pytest
uv run hypo-research guide "我论文快投了，帮我检查一下"
uv run hypo-research guide "我论文快投了，帮我检查一下" --execute --target tests/fixtures/lint_buggy.tex
uv run hypo-research read ingest data/reviews/FRR/FRRPaper.pdf --out /tmp/hypo-read-frr
uv run hypo-research check tests/fixtures/lint_buggy.tex --full
```

## Evidence

- Full test suite or focused equivalent passes.
- README and Skill docs reflect large-category IA.
- Guide execute mode demonstrates at least check and read paths.

## Human QA

- Validate that user-facing docs no longer require memorizing 19 skill names for common paths.

## 预期产出

- `guide --execute`.
- Updated README/Skill IA.
- End-to-end tests.
- Final implementation report.
