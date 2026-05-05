"""CLI tests for the check pipeline command."""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile


FIX_BUGGY = "tests/fixtures/fix_buggy.tex"


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "hypo-research", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_check_cli_basic(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    result = run_cli(["check", "--no-verify", "--no-save", str(src)])
    assert result.returncode in (0, 1)
    assert "Check Report" in result.stdout or "check" in result.stdout.lower()


def test_check_cli_zip_target(tmp_path) -> None:
    archive = tmp_path / "paper.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(
            "paper/main.tex",
            r"""
\documentclass{article}
\begin{document}
\section{Intro}
Text.
\end{document}
""",
        )

    result = run_cli(["check", "--no-verify", "--no-save", str(archive)])

    assert result.returncode in (0, 1)
    assert "Check Report" in result.stdout


def test_check_cli_json(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    result = run_cli(["check", "--json", "--no-verify", "--no-save", str(src)])
    data = json.loads(result.stdout)
    assert "lint" in data
    assert "stats" in data


def test_check_cli_full_json(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    result = run_cli(["check", "--full", "--json", "--no-verify", "--no-save", str(src)])
    data = json.loads(result.stdout)
    assert data["full_check"] is True
    assert "agent_review_checklist" in data
    assert any("figure" in item["focus"] for item in data["agent_review_checklist"])


def test_check_cli_lint_only(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    result = run_cli(["check", "--lint-only", "--no-save", str(src)])
    assert result.returncode in (0, 1)


def test_check_cli_no_fix(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    original = src.read_text(encoding="utf-8")
    run_cli(["check", "--no-fix", "--no-verify", "--no-save", str(src)])
    assert src.read_text(encoding="utf-8") == original


def test_check_cli_exit_code(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    result = run_cli(["check", "--no-fix", "--no-verify", "--no-save", str(src)])
    assert result.returncode == 1
