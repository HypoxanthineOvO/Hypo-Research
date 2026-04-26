"""Tests for JSON survey output."""

from __future__ import annotations

import json
from pathlib import Path

from hypo_research.core.models import PaperResult, SearchParams, SurveyMeta
from hypo_research.output.json_output import write_search_output


def test_json_output_includes_full_abstract(tmp_path: Path) -> None:
    abstract = "A" * 800
    paper = PaperResult(
        title="Paper",
        authors=["Alice"],
        year=2024,
        venue="ICLR",
        abstract=abstract,
        url="https://example.com",
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
    )
    meta = SurveyMeta(
        query="test",
        params=SearchParams(query="test"),
        sources_used=["semantic_scholar"],
    )

    write_search_output(tmp_path, meta, [paper])

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert payload[0]["abstract"] == abstract


def test_json_output_includes_per_paper_rankings(tmp_path: Path) -> None:
    papers = [
        PaperResult(
            title="A",
            authors=["Alice"],
            year=2024,
            url="https://example.com/a",
            citation_count=10,
            overall_score=8.0,
            relevance_score=9.0,
            source_api="semantic_scholar",
            sources=["semantic_scholar"],
        ),
        PaperResult(
            title="B",
            authors=["Bob"],
            year=2023,
            url="https://example.com/b",
            citation_count=20,
            overall_score=9.0,
            relevance_score=7.0,
            source_api="semantic_scholar",
            sources=["semantic_scholar"],
        ),
    ]
    meta = SurveyMeta(
        query="test",
        params=SearchParams(query="test"),
        sources_used=["semantic_scholar"],
    )

    write_search_output(tmp_path, meta, papers)

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    by_title = {paper["title"]: paper for paper in payload}
    assert by_title["A"]["rankings"]["overall"] == 2
    assert by_title["A"]["rankings"]["by_citations"] == 2
    assert by_title["A"]["rankings"]["by_relevance"] == 1
    assert by_title["A"]["rankings"]["by_time_position"] == "2024-1"


def test_json_output_writes_top_level_ranking_views(tmp_path: Path) -> None:
    papers = [
        PaperResult(
            title="A",
            authors=["Alice"],
            year=2024,
            url="https://example.com/a",
            citation_count=1,
            overall_score=9,
            relevance_score=8,
            source_api="semantic_scholar",
            sources=["semantic_scholar"],
        )
    ]
    meta = SurveyMeta(
        query="test",
        params=SearchParams(query="test"),
        sources_used=["semantic_scholar"],
    )

    write_search_output(tmp_path, meta, papers)

    payload = json.loads((tmp_path / "ranked_results.json").read_text(encoding="utf-8"))
    assert "papers" in payload
    assert "ranking_views" in payload
    assert payload["ranking_views"]["overall"] == ["https://example.com/a"]
    assert payload["ranking_views"]["by_time"]["2024"] == ["https://example.com/a"]


def test_json_output_omits_none_scores(tmp_path: Path) -> None:
    paper = PaperResult(
        title="Paper",
        authors=["Alice"],
        year=2024,
        url="https://example.com",
        citation_count=1,
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
    )
    meta = SurveyMeta(
        query="test",
        params=SearchParams(query="test"),
        sources_used=["semantic_scholar"],
    )

    write_search_output(tmp_path, meta, [paper])

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert "overall_score" not in payload[0]
    assert "relevance_score" not in payload[0]


def test_json_output_keeps_results_json_as_list_for_compatibility(tmp_path: Path) -> None:
    paper = PaperResult(
        title="Paper",
        authors=["Alice"],
        year=2024,
        url="https://example.com",
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
    )
    meta = SurveyMeta(
        query="test",
        params=SearchParams(query="test"),
        sources_used=["semantic_scholar"],
    )

    write_search_output(tmp_path, meta, [paper])

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert payload[0]["title"] == "Paper"
