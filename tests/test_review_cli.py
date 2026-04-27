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
    result = CliRunner().invoke(main, ["review", str(tex_file(tmp_path)), "--no-literature"])

    assert result.exit_code == 0
    assert "模拟审稿报告" in result.output
    assert "贺云翔" in result.output


def test_review_cli_venue_panel_reviewers_and_severity(tmp_path: Path) -> None:
    path = tex_file(tmp_path)
    runner = CliRunner()

    venue_result = runner.invoke(main, ["review", str(path), "--venue", "dac", "--no-literature"])
    full_result = runner.invoke(main, ["review", str(path), "--panel", "full", "--json", "--no-literature"])
    custom_result = runner.invoke(main, ["review", str(path), "--reviewers", "lichaofan", "chenquanyu", "liyuxuan", "--no-literature"])
    harsh_result = runner.invoke(main, ["review", str(path), "--severity", "harsh", "--no-literature"])

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
    json_result = runner.invoke(main, ["review", str(path), "--json", "--no-literature"])
    output_result = runner.invoke(main, ["review", str(path), "--output", str(output), "--no-literature"])

    assert json_result.exit_code == 0
    assert json.loads(json_result.output)["paper_title"] == "Review CLI Paper"
    assert output_result.exit_code == 0
    assert "模拟审稿报告" in output.read_text(encoding="utf-8")


def test_review_cli_no_literature_skips_search(monkeypatch, tmp_path: Path) -> None:
    called = {"value": False}

    def fake_search(*args, **kwargs):
        called["value"] = True
        return None

    monkeypatch.setattr("hypo_research.cli.search_literature", fake_search)
    result = CliRunner().invoke(main, ["review", str(tex_file(tmp_path)), "--no-literature"])

    assert result.exit_code == 0
    assert called["value"] is False


def test_review_cli_literature_options_are_passed(monkeypatch, tmp_path: Path) -> None:
    seen = {}

    def fake_search_literature(**kwargs):
        seen.update(kwargs)
        from hypo_research.review.literature import LiteratureContext

        return LiteratureContext(
            query_terms=["query"],
            references=[],
            search_timestamp="2026-04-27T12:00:00",
            year_range=(2021, 2026),
            paper_title=kwargs["paper_title"],
        )

    monkeypatch.setattr("hypo_research.cli.search_literature", fake_search_literature)
    result = CliRunner().invoke(
        main,
        [
            "review",
            str(tex_file(tmp_path)),
            "--literature-years",
            "5",
            "--literature-count",
            "6",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert seen["year_range"] == 5
    assert seen["max_results"] == 6
