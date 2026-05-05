# M02 Report - Full Check Framework

## Result

PASS

## Changes

- Added `--full` to `hypo-research check`.
- Added `full_check` and `agent_review_checklist` to `CheckReport`.
- Kept simulated review separate under `review`.

## Validation

```bash
uv run pytest tests/test_check.py::test_check_full_includes_agent_checklist tests/test_check_cli.py::test_check_cli_full_json
uv run pytest tests/test_check.py tests/test_check_cli.py tests/test_presubmit.py tests/test_presubmit_cli.py
uv run hypo-research check tests/fixtures/lint_buggy.tex --full --json --no-verify --no-save
```

All M02 validations passed.
