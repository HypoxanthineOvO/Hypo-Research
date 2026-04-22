"""Tests for metadata serialization and CLI threshold filtering."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from hypo_research.cli import main
from hypo_research.core.models import (
    ExpansionTrace,
    PaperResult,
    QueryVariant,
    SearchParams,
    SearchResult,
    SurveyMeta,
)
from hypo_research.output.json_output import write_search_output


def make_paper(
    title: str,
    *,
    matched_queries: list[str] | None = None,
    relevance_score: int | None = None,
    relevance_reason: str | None = None,
) -> PaperResult:
    return PaperResult(
        title=title,
        authors=["Alice Smith"],
        year=2024,
        venue="ISSCC",
        abstract=f"Abstract for {title}",
        doi=f"10.1234/{title.lower().replace(' ', '-')}",
        s2_paper_id=title.lower().replace(" ", "-"),
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        citation_count=7,
        reference_count=3,
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
        matched_queries=matched_queries,
        relevance_score=relevance_score,
        relevance_reason=relevance_reason,
    )


def make_meta(output_dir: Path) -> SurveyMeta:
    params = SearchParams(query="cryogenic computing GPU")
    return SurveyMeta(
        query=params.query,
        params=params,
        sources_used=["semantic_scholar"],
        output_dir=str(output_dir),
    )


def test_paper_result_new_fields_serialize(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"
    meta = make_meta(output_dir)
    paper = make_paper(
        "Paper One",
        matched_queries=["q1", "q2"],
        relevance_score=4,
        relevance_reason="Highly relevant",
    )

    write_search_output(output_dir, meta, [paper])

    payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    assert payload[0]["matched_queries"] == ["q1", "q2"]
    assert payload[0]["relevance_score"] == 4
    assert payload[0]["relevance_reason"] == "Highly relevant"


def test_survey_meta_new_fields_serialize(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"
    params = SearchParams(query="cryogenic computing GPU")
    trace = ExpansionTrace(
        original_query="cryogenic computing GPU",
        variants=[
            QueryVariant(
                query="cryo-CMOS accelerator",
                strategy="synonym",
                rationale="Alternative terminology",
            )
        ],
        all_queries=["cryogenic computing GPU", "cryo-CMOS accelerator"],
    )
    meta = SurveyMeta(
        query=params.query,
        params=params,
        sources_used=["semantic_scholar"],
        output_dir=str(output_dir),
        expansion=trace,
        pre_filter_count=5,
        post_filter_count=3,
        relevance_threshold=3,
    )

    write_search_output(output_dir, meta, [make_paper("Paper One")])

    payload = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
    assert payload["expansion"]["original_query"] == "cryogenic computing GPU"
    assert payload["pre_filter_count"] == 5
    assert payload["post_filter_count"] == 3
    assert payload["relevance_threshold"] == 3


def test_new_fields_default_values_serialize_as_null_or_absent(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"
    meta = make_meta(output_dir)
    paper = make_paper("Paper One")
    paper.matched_queries = None
    paper.relevance_score = None
    paper.relevance_reason = None

    write_search_output(output_dir, meta, [paper])

    results_payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    meta_payload = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))

    assert results_payload[0].get("matched_queries") is None
    assert results_payload[0].get("relevance_score") is None
    assert results_payload[0].get("relevance_reason") is None
    assert meta_payload.get("expansion") is None
    assert meta_payload.get("pre_filter_count") is None
    assert meta_payload.get("post_filter_count") is None
    assert meta_payload.get("relevance_threshold") is None


def test_cli_relevance_threshold_filters_results(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"

    async def fake_run_single_search(
        params: SearchParams,
        output_dir: str | None,
        s2_api_key: str | None,
    ) -> SearchResult:
        papers = [
            make_paper("Keep Paper", relevance_score=4, relevance_reason="Relevant"),
            make_paper("Drop Paper", relevance_score=2, relevance_reason="Too broad"),
            make_paper("Unscored Paper"),
        ]
        meta = SurveyMeta(
            query=params.query,
            params=params,
            sources_used=["semantic_scholar"],
            output_dir=str(output_dir),
            total_results=len(papers),
        )
        return SearchResult(meta=meta, papers=papers, output_dir=str(output_dir))

    runner = CliRunner()
    with patch("hypo_research.cli._run_single_search", side_effect=fake_run_single_search):
        result = runner.invoke(
            main,
            [
                "search",
                "cryogenic computing GPU",
                "--relevance-threshold",
                "3",
                "--output-dir",
                str(output_dir),
            ],
        )

    assert result.exit_code == 0
    assert "Relevance filter: 3 -> 2 (threshold=3)" in result.output

    results_payload = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
    meta_payload = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))

    assert len(results_payload) == 2
    assert {paper["title"] for paper in results_payload} == {
        "Keep Paper",
        "Unscored Paper",
    }
    assert meta_payload["pre_filter_count"] == 3
    assert meta_payload["post_filter_count"] == 2
    assert meta_payload["relevance_threshold"] == 3
