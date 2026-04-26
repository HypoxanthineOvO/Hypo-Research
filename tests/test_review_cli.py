"""CLI tests for the review command."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hypo_research.cli import main


def tex_file(tmp_path: Path) -> Path:
    path = tmp_path / "paper.tex"
    path.write_text(
        r"""
\documentclass{article}
\title{Review CLI Paper}
\begin{document}
\begin{abstract}We propose a method.\end{abstract}
\section{Intro}
Our method outperforms baselines.
\end{document}
""",
        encoding="utf-8",
    )
    return path


def test_review_cli_basic(tmp_path: Path) -> None:
    result = CliRunner().invoke(main, ["review", str(tex_file(tmp_path))])

    assert result.exit_code == 0
    assert "模拟审稿报告" in result.output
    assert "贺云翔" in result.output


def test_review_cli_venue_panel_reviewers_and_severity(tmp_path: Path) -> None:
    path = tex_file(tmp_path)
    runner = CliRunner()

    venue_result = runner.invoke(main, ["review", str(path), "--venue", "dac"])
    full_result = runner.invoke(main, ["review", str(path), "--panel", "full", "--json"])
    custom_result = runner.invoke(main, ["review", str(path), "--reviewers", "lichaofan", "chenquanyu", "liyuxuan"])
    harsh_result = runner.invoke(main, ["review", str(path), "--severity", "harsh"])

    assert venue_result.exit_code == 0
    assert json.loads(full_result.output)["panel"] == [
        "heyunxiang",
        "lichaofan",
        "wuhaoyu",
        "chenquanyu",
        "jiangye",
        "liyuxuan",
        "dingqihan",
    ]
    assert "李宇轩" in custom_result.output
    assert "地狱版" in harsh_result.output


def test_review_cli_list_reviewers_and_venues() -> None:
    runner = CliRunner()
    reviewers = runner.invoke(main, ["review", "--list-reviewers"])
    venues = runner.invoke(main, ["review", "--list-venues"])

    assert reviewers.exit_code == 0
    assert "lichaofan" in reviewers.output
    assert venues.exit_code == 0
    assert "dac" in venues.output


def test_review_cli_json_and_output(tmp_path: Path) -> None:
    path = tex_file(tmp_path)
    output = tmp_path / "review.md"
    runner = CliRunner()
    json_result = runner.invoke(main, ["review", str(path), "--json"])
    output_result = runner.invoke(main, ["review", str(path), "--output", str(output)])

    assert json_result.exit_code == 0
    assert json.loads(json_result.output)["paper_title"] == "Review CLI Paper"
    assert output_result.exit_code == 0
    assert "模拟审稿报告" in output.read_text(encoding="utf-8")
