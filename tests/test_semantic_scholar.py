"""Tests for the Semantic Scholar adapter."""

from __future__ import annotations

import asyncio
import httpx
import pytest
import respx

from hypo_research.core.models import SearchParams, VerificationLevel
from hypo_research.core.sources.semantic_scholar import SemanticScholarSource

SAMPLE_S2_PAPER = {
    "paperId": "abc123",
    "title": "Cryogenic CMOS for Quantum Computing",
    "authors": [
        {"authorId": "1", "name": "Alice Smith"},
        {"authorId": "2", "name": "Bob Jones"},
    ],
    "year": 2023,
    "venue": "ISSCC",
    "abstract": "We present a cryogenic CMOS design...",
    "externalIds": {"DOI": "10.1234/example", "ArXiv": "2301.00001"},
    "citationCount": 42,
    "referenceCount": 30,
    "url": "https://www.semanticscholar.org/paper/abc123",
}

SAMPLE_S2_SEARCH_RESPONSE = {
    "total": 1,
    "offset": 0,
    "next": None,
    "data": [SAMPLE_S2_PAPER],
}


def make_paper(index: int) -> dict:
    paper = dict(SAMPLE_S2_PAPER)
    paper["paperId"] = f"paper-{index}"
    paper["title"] = f"Paper {index}"
    paper["url"] = f"https://www.semanticscholar.org/paper/paper-{index}"
    paper["externalIds"] = {"DOI": f"10.1234/{index}"}
    return paper


@pytest.mark.asyncio
@respx.mock
async def test_search_maps_paper_fields() -> None:
    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json=SAMPLE_S2_SEARCH_RESPONSE)
    )

    papers = await source.search(SearchParams(query="cryogenic computing", max_results=3))
    await source.close()

    assert len(papers) == 1
    paper = papers[0]
    assert paper.title == SAMPLE_S2_PAPER["title"]
    assert paper.authors == ["Alice Smith", "Bob Jones"]
    assert paper.doi == "10.1234/example"
    assert paper.arxiv_id == "2301.00001"
    assert paper.source_api == "semantic_scholar"
    assert paper.sources == ["semantic_scholar"]
    assert paper.verification is VerificationLevel.SINGLE_SOURCE
    assert paper.raw_response["paperId"] == "abc123"


@pytest.mark.asyncio
@respx.mock
async def test_search_handles_pagination() -> None:
    source = SemanticScholarSource()
    calls: list[httpx.Request] = []
    first_page = {
        "total": 105,
        "offset": 0,
        "data": [make_paper(index) for index in range(100)],
    }
    second_page = {
        "total": 105,
        "offset": 100,
        "data": [make_paper(index) for index in range(100, 105)],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        offset = int(request.url.params["offset"])
        if offset == 0:
            return httpx.Response(200, json=first_page)
        if offset == 100:
            return httpx.Response(200, json=second_page)
        return httpx.Response(500)

    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        side_effect=handler
    )

    papers = await source.search(SearchParams(query="cryogenic computing", max_results=105))
    await source.close()

    assert len(papers) == 105
    assert len(calls) == 2
    assert calls[0].url.params["offset"] == "0"
    assert calls[1].url.params["offset"] == "100"


@pytest.mark.asyncio
@respx.mock
async def test_search_includes_year_filter() -> None:
    source = SemanticScholarSource()
    captured_request: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request.append(request)
        return httpx.Response(200, json=SAMPLE_S2_SEARCH_RESPONSE)

    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        side_effect=handler
    )

    await source.search(
        SearchParams(query="cryogenic computing", year_range=(2020, 2026))
    )
    await source.close()

    assert captured_request
    assert captured_request[0].url.params["year"] == "2020-2026"


@pytest.mark.asyncio
@respx.mock
async def test_search_retries_after_429() -> None:
    source = SemanticScholarSource()
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json=SAMPLE_S2_SEARCH_RESPONSE)

    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        side_effect=handler
    )

    papers = await source.search(SearchParams(query="cryogenic computing"))
    await source.close()

    assert call_count == 2
    assert len(papers) == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_paper_returns_single_record() -> None:
    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/abc123").mock(
        return_value=httpx.Response(200, json=SAMPLE_S2_PAPER)
    )

    paper = await source.get_paper("abc123")
    await source.close()

    assert paper is not None
    assert paper.s2_paper_id == "abc123"
    assert paper.title == SAMPLE_S2_PAPER["title"]


def test_s2_uses_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key-123")

    source = SemanticScholarSource()

    assert source.api_key == "test-key-123"
    assert source.headers["x-api-key"] == "test-key-123"
    asyncio.run(source.close())


def test_s2_works_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)

    source = SemanticScholarSource()

    assert source.api_key is None
    assert "x-api-key" not in source.headers
    asyncio.run(source.close())


def test_s2_rate_limiter_adjusts_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key")

    source = SemanticScholarSource()

    assert source.rate_limiter.max_requests >= 10
    asyncio.run(source.close())
