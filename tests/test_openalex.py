"""Tests for the OpenAlex adapter."""

from __future__ import annotations

import httpx
import pytest
import respx

from hypo_research.core.models import SearchParams
from hypo_research.core.sources.openalex import OpenAlexSource, restore_abstract

SAMPLE_OPENALEX_WORK = {
    "id": "https://openalex.org/W1234567890",
    "doi": "https://doi.org/10.1234/example",
    "title": "Cryogenic CMOS for Quantum Computing",
    "authorships": [
        {"author": {"display_name": "Alice Smith"}},
        {"author": {"display_name": "Bob Jones"}},
    ],
    "publication_year": 2023,
    "primary_location": {
        "landing_page_url": "https://example.org/paper",
        "source": {"display_name": "ISSCC"},
    },
    "cited_by_count": 42,
    "abstract_inverted_index": {
        "Cryogenic": [0],
        "CMOS": [1],
        "design": [2],
    },
    "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W2"],
    "type": "article",
}


@pytest.mark.asyncio
@respx.mock
async def test_openalex_search_maps_fields() -> None:
    source = OpenAlexSource()
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(
            200,
            json={"results": [SAMPLE_OPENALEX_WORK], "meta": {"next_cursor": None}},
        )
    )

    papers = await source.search(SearchParams(query="cryogenic computing", max_results=5))
    await source.close()

    assert len(papers) == 1
    paper = papers[0]
    assert paper.title == SAMPLE_OPENALEX_WORK["title"]
    assert paper.authors == ["Alice Smith", "Bob Jones"]
    assert paper.year == 2023
    assert paper.venue == "ISSCC"
    assert paper.abstract == "Cryogenic CMOS design"
    assert paper.doi == "10.1234/example"
    assert paper.openalex_id == "W1234567890"
    assert paper.citation_count == 42
    assert paper.reference_count == 2
    assert paper.sources == ["openalex"]


def test_restore_abstract_from_inverted_index() -> None:
    restored = restore_abstract({"Abstract": [0], "of": [1, 5], "paper": [2, 6]})
    assert restored == "Abstract of paper of paper"


@pytest.mark.asyncio
@respx.mock
async def test_openalex_search_includes_year_filter() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={"results": [SAMPLE_OPENALEX_WORK], "meta": {"next_cursor": None}},
        )

    source = OpenAlexSource()
    respx.get("https://api.openalex.org/works").mock(side_effect=handler)

    await source.search(SearchParams(query="cryogenic", year_range=(2020, 2026)))
    await source.close()

    assert captured_requests
    assert captured_requests[0].url.params["filter"] == "publication_year:2020-2026"


@pytest.mark.asyncio
@respx.mock
async def test_openalex_search_handles_pagination() -> None:
    source = OpenAlexSource()
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        cursor = request.url.params["cursor"]
        if cursor == "*":
            return httpx.Response(
                200,
                json={
                    "results": [dict(SAMPLE_OPENALEX_WORK, id=f"https://openalex.org/W{i}") for i in range(50)],
                    "meta": {"next_cursor": "cursor-2"},
                },
            )
        return httpx.Response(
            200,
            json={
                "results": [dict(SAMPLE_OPENALEX_WORK, id="https://openalex.org/W999")],
                "meta": {"next_cursor": None},
            },
        )

    respx.get("https://api.openalex.org/works").mock(side_effect=handler)

    papers = await source.search(SearchParams(query="cryogenic", max_results=51))
    await source.close()

    assert len(papers) == 51
    assert len(calls) == 2


@pytest.mark.asyncio
@respx.mock
async def test_openalex_retries_after_429() -> None:
    source = OpenAlexSource()
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={"results": [SAMPLE_OPENALEX_WORK], "meta": {"next_cursor": None}},
        )

    respx.get("https://api.openalex.org/works").mock(side_effect=handler)

    papers = await source.search(SearchParams(query="cryogenic"))
    await source.close()

    assert call_count == 2
    assert len(papers) == 1


@pytest.mark.asyncio
@respx.mock
async def test_openalex_polite_pool_headers_include_mailto() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(
            200,
            json={"results": [SAMPLE_OPENALEX_WORK], "meta": {"next_cursor": None}},
        )

    source = OpenAlexSource(email="research@example.com")
    respx.get("https://api.openalex.org/works").mock(side_effect=handler)

    await source.search(SearchParams(query="cryogenic"))
    await source.close()

    assert captured_requests
    assert "mailto:research@example.com" in captured_requests[0].headers["User-Agent"]
