"""CLI tests for survey ranking views."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from hypo_research.cli import main
from hypo_research.core.models import PaperResult, SearchParams, SearchResult, SurveyMeta


def make_result(output_dir: Path, *, scored: bool = True) -> SearchResult:
    papers = [
        PaperResult(
            title="A",
            authors=["Alice"],
            year=2024,
            url="https://example.com/a",
            citation_count=10,
            overall_score=8.0 if scored else None,
            relevance_score=9.0 if scored else None,
            source_api="semantic_scholar",
            sources=["semantic_scholar"],
        ),
        PaperResult(
            title="B",
            authors=["Bob"],
            year=2023,
            url="https://example.com/b",
            citation_count=20,
            overall_score=9.0 if scored else None,
            relevance_score=7.0 if scored else None,
            source_api="semantic_scholar",
            sources=["semantic_scholar"],
        ),
    ]
    meta = SurveyMeta(
        query="ranking test",
        params=SearchParams(query="ranking test"),
        sources_used=["semantic_scholar"],
        output_dir=str(output_dir),
        total_results=len(papers),
    )
    return SearchResult(meta=meta, papers=papers, output_dir=str(output_dir))


def test_search_sort_all_default_writes_all_views(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"

    async def fake_run_single_search(*args, **kwargs):
        return make_result(output_dir, scored=True)

    runner = CliRunner()
    with patch("hypo_research.cli._run_single_search", side_effect=fake_run_single_search):
        result = runner.invoke(
            main,
            ["search", "ranking test", "--output-dir", str(output_dir)],
        )

    assert result.exit_code == 0
    content = (output_dir / "results.md").read_text(encoding="utf-8")
    assert "## 📊 综合排序（Overall Ranking）" in content
    assert "## 📈 引用数排序（By Citations）" in content
    assert "## 🎯 相关性排序（By Relevance）" in content
    assert "## 📅 时间线（Timeline）" in content


def test_search_sort_citations_writes_single_view(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"

    async def fake_run_single_search(*args, **kwargs):
        return make_result(output_dir, scored=True)

    runner = CliRunner()
    with patch("hypo_research.cli._run_single_search", side_effect=fake_run_single_search):
        result = runner.invoke(
            main,
            ["search", "ranking test", "--sort", "citations", "--output-dir", str(output_dir)],
        )

    assert result.exit_code == 0
    content = (output_dir / "results.md").read_text(encoding="utf-8")
    assert "## 📈 引用数排序（By Citations）" in content
    assert "## 📊 综合排序（Overall Ranking）" not in content


def test_search_sort_time_writes_timeline(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"

    async def fake_run_single_search(*args, **kwargs):
        return make_result(output_dir, scored=True)

    runner = CliRunner()
    with patch("hypo_research.cli._run_single_search", side_effect=fake_run_single_search):
        result = runner.invoke(
            main,
            ["search", "ranking test", "--sort", "time", "--output-dir", str(output_dir)],
        )

    assert result.exit_code == 0
    content = (output_dir / "results.md").read_text(encoding="utf-8")
    assert "## 📅 时间线（Timeline）" in content
    assert "### 2023" in content
    assert "### 2024" in content


def test_search_sort_overall_fallback_message(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"

    async def fake_run_single_search(*args, **kwargs):
        return make_result(output_dir, scored=False)

    runner = CliRunner()
    with patch("hypo_research.cli._run_single_search", side_effect=fake_run_single_search):
        result = runner.invoke(
            main,
            ["search", "ranking test", "--sort", "overall", "--output-dir", str(output_dir)],
        )

    assert result.exit_code == 0
    assert "Overall ranking has no Agent scores; falling back to citations." in result.output
    content = (output_dir / "results.md").read_text(encoding="utf-8")
    assert "## 📊 综合排序（按引用数 fallback）" in content
