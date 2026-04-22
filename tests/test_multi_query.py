"""Tests for multi-query targeted search."""

from __future__ import annotations

import httpx
import pytest
import respx

from hypo_research.core.models import ExpansionTrace, QueryVariant, SearchParams
from hypo_research.core.sources.semantic_scholar import SemanticScholarSource
from hypo_research.survey.targeted import TargetedSearch


def make_paper(paper_id: str, title: str, doi: str | None = None) -> dict:
    external_ids = {"DOI": doi} if doi else {}
    return {
        "paperId": paper_id,
        "title": title,
        "authors": [{"authorId": "1", "name": "Alice Smith"}],
        "year": 2024,
        "venue": "ISSCC",
        "abstract": f"Abstract for {title}",
        "externalIds": external_ids,
        "citationCount": 10,
        "referenceCount": 5,
        "url": f"https://www.semanticscholar.org/paper/{paper_id}",
    }


def make_search_response(papers: list[dict]) -> dict:
    return {
        "total": len(papers),
        "offset": 0,
        "next": None,
        "data": papers,
    }


@pytest.mark.asyncio
@respx.mock
async def test_multi_query_search_merges_all_results(tmp_path) -> None:
    query_map = {
        "cryogenic computing GPU": [make_paper("p1", "Paper One")],
        "cryo-CMOS accelerator": [make_paper("p2", "Paper Two")],
        "low temperature VLSI GPU": [make_paper("p3", "Paper Three")],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params["query"]
        return httpx.Response(200, json=make_search_response(query_map[query]))

    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        side_effect=handler
    )

    searcher = TargetedSearch(sources=[source])
    result = await searcher.multi_query_search(
        queries=list(query_map.keys()),
        base_params=SearchParams(query="cryogenic computing GPU", max_results=10),
        output_dir=str(tmp_path / "survey"),
    )
    await searcher.close()

    assert len(result.papers) == 3
    assert {paper.title for paper in result.papers} == {
        "Paper One",
        "Paper Two",
        "Paper Three",
    }
    assert result.meta.pre_filter_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_multi_query_search_deduplicates_duplicate_papers(tmp_path) -> None:
    shared_paper = make_paper("shared", "Shared Paper", doi="10.1234/shared")
    query_map = {
        "q1": [shared_paper],
        "q2": [shared_paper],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=make_search_response(query_map[request.url.params["query"]]),
        )

    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        side_effect=handler
    )

    searcher = TargetedSearch(sources=[source])
    result = await searcher.multi_query_search(
        queries=["q1", "q2"],
        base_params=SearchParams(query="q1", max_results=10),
        output_dir=str(tmp_path / "survey"),
    )
    await searcher.close()

    assert len(result.papers) == 1
    assert result.papers[0].s2_paper_id == "shared"


@pytest.mark.asyncio
@respx.mock
async def test_multi_query_search_records_matched_queries(tmp_path) -> None:
    shared_paper = make_paper("shared", "Shared Paper")
    unique_paper = make_paper("unique", "Unique Paper")
    query_map = {
        "q1": [shared_paper],
        "q2": [shared_paper],
        "q3": [unique_paper],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=make_search_response(query_map[request.url.params["query"]]),
        )

    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        side_effect=handler
    )

    searcher = TargetedSearch(sources=[source])
    result = await searcher.multi_query_search(
        queries=["q1", "q2", "q3"],
        base_params=SearchParams(query="q1", max_results=10),
        output_dir=str(tmp_path / "survey"),
    )
    await searcher.close()

    papers_by_id = {paper.s2_paper_id: paper for paper in result.papers}
    assert papers_by_id["shared"].matched_queries == ["q1", "q2"]
    assert papers_by_id["unique"].matched_queries == ["q3"]


@pytest.mark.asyncio
@respx.mock
async def test_multi_query_single_query_matches_search_behavior(tmp_path) -> None:
    query = "cryogenic computing GPU"
    response_payload = make_search_response([make_paper("p1", "Paper One")])
    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json=response_payload)
    )

    searcher = TargetedSearch(sources=[source])
    single_result = await searcher.search(
        SearchParams(query=query, max_results=10),
        output_dir=str(tmp_path / "single"),
    )
    multi_result = await searcher.multi_query_search(
        queries=[query],
        base_params=SearchParams(query=query, max_results=10),
        output_dir=str(tmp_path / "multi"),
    )
    await searcher.close()

    assert single_result.meta.total_results == multi_result.meta.total_results
    assert [paper.title for paper in single_result.papers] == [
        paper.title for paper in multi_result.papers
    ]


@pytest.mark.asyncio
@respx.mock
async def test_multi_query_search_records_expansion_trace(tmp_path) -> None:
    trace = ExpansionTrace(
        original_query="cryogenic computing GPU",
        variants=[
            QueryVariant(
                query="cryo-CMOS accelerator",
                strategy="synonym",
                rationale="Uses cryo-CMOS wording",
            )
        ],
        all_queries=["cryogenic computing GPU", "cryo-CMOS accelerator"],
    )
    query_map = {
        "cryogenic computing GPU": [make_paper("p1", "Paper One")],
        "cryo-CMOS accelerator": [make_paper("p2", "Paper Two")],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=make_search_response(query_map[request.url.params["query"]]),
        )

    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        side_effect=handler
    )

    searcher = TargetedSearch(sources=[source])
    result = await searcher.multi_query_search(
        queries=trace.all_queries,
        base_params=SearchParams(query=trace.original_query, max_results=10),
        expansion_trace=trace,
        output_dir=str(tmp_path / "survey"),
    )
    await searcher.close()

    assert result.meta.expansion == trace
