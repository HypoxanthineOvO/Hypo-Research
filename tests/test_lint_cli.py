"""CLI tests for the LaTeX lint command."""

from __future__ import annotations

import json
import subprocess


def test_lint_cli_default_mode() -> None:
    result = subprocess.run(
        ["uv", "run", "hypo-research", "lint", "tests/fixtures/lint_buggy.tex"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "[L01]" in result.stdout
    assert result.returncode == 1


def test_lint_cli_stats_mode() -> None:
    result = subprocess.run(
        ["uv", "run", "hypo-research", "lint", "--stats", "tests/fixtures/lint_buggy.tex"],
        capture_output=True,
        text=True,
        check=False,
    )
    data = json.loads(result.stdout)
    assert "summary" in data
    assert "issues" in data
    assert data["summary"]["issues_found"] > 0


def test_lint_cli_clean_file() -> None:
    result = subprocess.run(
        ["uv", "run", "hypo-research", "lint", "tests/fixtures/lint_fixed.tex"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_lint_cli_with_bib() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "hypo-research",
            "lint",
            "--bib",
            "tests/fixtures/lint_buggy.bib",
            "tests/fixtures/lint_buggy.tex",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "[L12]" in result.stdout


def test_lint_cli_rule_filter() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "hypo-research",
            "lint",
            "--rules",
            "L01,L04",
            "tests/fixtures/lint_buggy.tex",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "[L01]" in result.stdout
    assert "[L07]" not in result.stdout
