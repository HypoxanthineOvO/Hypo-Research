"""CLI tests for lint auto-fix mode."""

from __future__ import annotations

import json
import subprocess


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "hypo-research", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_lint_fix_dry_run() -> None:
    result = run_cli(["lint", "--fix", "tests/fixtures/fix_buggy.tex"])
    assert "dry-run" in result.stdout.lower() or "dry_run" in result.stdout.lower()
    assert result.returncode == 0


def test_lint_fix_with_rules() -> None:
    result = run_cli(["lint", "--fix", "--rules", "L01", "tests/fixtures/fix_buggy.tex"])
    assert "L01" in result.stdout
    assert "L04" not in result.stdout


def test_lint_fix_stats_json() -> None:
    result = run_cli(["lint", "--fix", "--stats", "tests/fixtures/fix_buggy.tex"])
    data = json.loads(result.stdout)
    assert "fixes" in data
    assert len(data["fixes"]) > 0
    assert all("rule" in item for item in data["fixes"])
