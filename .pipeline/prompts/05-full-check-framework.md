# M02 - Full Check Framework

## Objective

Make `check --full` the strong paper-checking path for format/structure/citation and writing-quality review prompts, while keeping simulated peer review separate under `review`.

## 需求

- Add or refine `check --full` semantics.
- `check --full` should include:
  - existing lint/fix/verify/stats behavior
  - writing-quality signals suitable for deterministic checks where possible
  - Agent-facing checklist/prompt for subjective review items
- Keep `review` independent for simulated peer review.
- Clarify `presubmit` as compatibility wrapper or thin aggregation layer; do not make it the primary concept.
- Ensure full check output can be consumed by Guide and future paper-ready workflows.
- The Agent checklist should cover at least:
  - contribution clarity
  - figure/table explanation adequacy
  - claim/evidence support
  - related-work coverage prompt
  - terminology consistency prompt

## Boundaries

- In scope: check data model/report output, CLI flags, tests.
- In scope: deterministic signals already available from stats/lint and new lightweight writing stats if practical.
- Out of scope: automatic simulated review; `review` remains separate.
- Out of scope: full rewrite of presubmit internals unless needed for compatibility.

## Non-Goals

- Do not make subjective Agent checklist look like deterministic PASS/FAIL.
- Do not break existing `check` default behavior.
- Do not remove `presubmit` command.

## 预期测试

- `check --full --json` includes deterministic check summary and Agent checklist fields.
- Existing check tests still pass.
- Fixture-based report has stable expected fields.

## Validation Commands

```bash
uv run pytest tests/test_check*.py tests/test_presubmit*.py
uv run hypo-research check tests/fixtures/lint_buggy.tex --full --json
uv run hypo-research check tests/fixtures/lint_buggy.tex --full
```

## Evidence

- JSON output demonstrates `full` mode.
- Markdown/text output clearly separates automatic checks from Agent review checklist.
- Presubmit compatibility remains intact.

## Human QA

- Verify that `check` feels like strong paper checking and `review` remains academic simulated review.

## 预期产出

- Updated check model/rendering.
- `--full` CLI behavior.
- Tests covering full check output.
