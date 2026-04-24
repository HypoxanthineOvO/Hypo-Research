"""CLI tests for multi-file LaTeX projects."""

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


def test_lint_multifile_default() -> None:
    result = run_cli(["lint", "tests/fixtures/multifile/main.tex"])
    assert "sections/" in result.stdout or "eval.tex" in result.stdout


def test_lint_multifile_stats() -> None:
    result = run_cli(["lint", "--stats", "tests/fixtures/multifile/main.tex"])
    data = json.loads(result.stdout)
    assert "project" in data
    assert data["project"] is not None
    assert "main.tex" in data["project"]["root_file"]
    if data.get("labels"):
        assert any(label["file"] != "" for label in data["labels"])


def test_lint_single_file_unchanged() -> None:
    result = run_cli(["lint", "tests/fixtures/lint_buggy.tex"])
    assert "sections/" not in result.stdout


def test_lint_from_subfile() -> None:
    result = run_cli(["lint", "tests/fixtures/multifile/sections/intro.tex"])
    assert result.returncode == 1
    assert "eval.tex" in result.stdout


def test_verify_multifile_auto_bib() -> None:
    result = run_cli(["verify", "--tex", "tests/fixtures/multifile/main.tex", "--keys", "craterlake2022"])
    assert result.returncode in {0, 1}
    assert "craterlake2022" in (result.stdout + result.stderr)
