"""CLI tests for presubmit command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hypo_research.cli import main
from hypo_research.presubmit.runner import CheckStageResult, PresubmitResult, PresubmitVerdict


def make_result(verdict: PresubmitVerdict) -> PresubmitResult:
    errors = 1 if verdict is PresubmitVerdict.FAIL else 0
    warnings = 1 if verdict is PresubmitVerdict.WARNING else 0
    return PresubmitResult(
        verdict=verdict,
        stages=[
            CheckStageResult(
                stage="check",
                passed=errors == 0,
                errors=errors,
                warnings=warnings,
                details=[],
                duration_seconds=0.1,
            )
        ],
        total_errors=errors,
        total_warnings=warnings,
        total_duration_seconds=0.1,
        summary="summary",
    )


def tex_file(tmp_path: Path) -> Path:
    path = tmp_path / "paper.tex"
    path.write_text("\\documentclass{article}\\begin{document}x\\end{document}\n", encoding="utf-8")
    return path


def test_presubmit_cli_basic(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("hypo_research.cli.run_presubmit", lambda *a, **k: make_result(PresubmitVerdict.PASS))
    runner = CliRunner()
    result = runner.invoke(main, ["presubmit", str(tex_file(tmp_path))])

    assert result.exit_code == 0
    assert "提交前检查报告" in result.output


def test_presubmit_cli_venue(monkeypatch, tmp_path: Path) -> None:
    seen = {}
    monkeypatch.setattr(
        "hypo_research.cli.run_presubmit",
        lambda tex_root, **kwargs: seen.update(kwargs) or make_result(PresubmitVerdict.PASS),
    )
    runner = CliRunner()
    runner.invoke(main, ["presubmit", str(tex_file(tmp_path)), "--venue", "ieee_journal"])

    assert seen["venue"] == "ieee_journal"


def test_presubmit_cli_skip_single_and_multiple(monkeypatch, tmp_path: Path) -> None:
    seen = {}
    monkeypatch.setattr(
        "hypo_research.cli.run_presubmit",
        lambda tex_root, **kwargs: seen.update(kwargs) or make_result(PresubmitVerdict.PASS),
    )
    runner = CliRunner()
    runner.invoke(
        main,
        ["presubmit", str(tex_file(tmp_path)), "--skip", "lint", "--skip", "verify"],
    )

    assert seen["skip_stages"] == ["lint", "verify"]


def test_presubmit_cli_json(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("hypo_research.cli.run_presubmit", lambda *a, **k: make_result(PresubmitVerdict.PASS))
    runner = CliRunner()
    result = runner.invoke(main, ["presubmit", str(tex_file(tmp_path)), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["verdict"] == "pass"


def test_presubmit_cli_output_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("hypo_research.cli.run_presubmit", lambda *a, **k: make_result(PresubmitVerdict.PASS))
    output = tmp_path / "report.md"
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["presubmit", str(tex_file(tmp_path)), "--output", str(output)],
    )

    assert result.exit_code == 0
    assert "提交前检查报告" in output.read_text(encoding="utf-8")


def test_presubmit_cli_return_codes(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()
    path = tex_file(tmp_path)
    for verdict, expected in [
        (PresubmitVerdict.PASS, 0),
        (PresubmitVerdict.FAIL, 1),
        (PresubmitVerdict.WARNING, 2),
    ]:
        monkeypatch.setattr("hypo_research.cli.run_presubmit", lambda *a, v=verdict, **k: make_result(v))
        result = runner.invoke(main, ["presubmit", str(path)])
        assert result.exit_code == expected
