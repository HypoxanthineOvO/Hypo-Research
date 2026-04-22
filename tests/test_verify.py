"""Tests for citation verification logic."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
import respx

from hypo_research.writing.verify import title_similarity, verify_bib


S2_CINNAMON = {
    "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
    "title": "Cinnamon: A Large-Scale Hardware Accelerator for Fully Homomorphic Encryption",
    "year": 2025,
    "venue": "ASPLOS",
    "authors": [
        {"authorId": "123", "name": "Nikola Samardzic"},
        {"authorId": "456", "name": "Axel Feldmann"},
    ],
    "externalIds": {"DOI": "10.1145/3582016.3582066", "ArXiv": None},
    "citationCount": 15,
}

S2_F1 = {
    "paperId": "f1paper",
    "title": "F1: A Fast and Programmable Accelerator for Fully Homomorphic Encryption",
    "year": 2021,
    "venue": "MICRO-54",
    "authors": [{"authorId": "789", "name": "Axel Feldmann"}],
    "externalIds": {"DOI": "10.1145/3466752.3480070"},
    "citationCount": 20,
}

S2_CRATERLAKE = {
    "paperId": "craterlake",
    "title": "CraterLake: A Hardware Accelerator for Efficient Unbounded Computation on Encrypted Data",
    "year": 2022,
    "venue": "ISCA",
    "authors": [{"authorId": "999", "name": "Nikola Samardzic"}],
    "externalIds": {},
    "citationCount": 33,
}

OPENALEX_CINNAMON = {
    "id": "https://openalex.org/W2741809807",
    "title": "Cinnamon: A Large-Scale Hardware Accelerator for Fully Homomorphic Encryption",
    "publication_year": 2025,
    "primary_location": {
        "source": {
            "display_name": "Proceedings of the 28th ACM International Conference on Architectural Support for Programming Languages and Operating Systems"
        }
    },
    "authorships": [
        {"author": {"display_name": "Nikola Samardzic"}},
        {"author": {"display_name": "Axel Feldmann"}},
    ],
    "doi": "https://doi.org/10.1145/3582016.3582066",
    "cited_by_count": 18,
}

OPENALEX_F1 = {
    "id": "https://openalex.org/W34667523480070",
    "title": "F1: A Fast and Programmable Accelerator for Fully Homomorphic Encryption",
    "publication_year": 2021,
    "primary_location": {"source": {"display_name": "MICRO-54"}},
    "authorships": [{"author": {"display_name": "Axel Feldmann"}}],
    "doi": "https://doi.org/10.1145/3466752.3480070",
    "cited_by_count": 21,
}


def test_title_similarity_exact_match() -> None:
    assert (
        title_similarity(
            "Cinnamon: A Large-Scale Hardware Accelerator",
            "Cinnamon: A Large-Scale Hardware Accelerator",
        )
        == 1.0
    )


def test_title_similarity_case_insensitive() -> None:
    assert (
        title_similarity(
            "cinnamon: a large-scale hardware accelerator",
            "Cinnamon: A Large-Scale Hardware Accelerator",
        )
        == 1.0
    )


def test_title_similarity_latex_cleanup() -> None:
    similarity = title_similarity(
        "{Cinnamon}: A {Large-Scale} Hardware Accelerator",
        "Cinnamon: A Large-Scale Hardware Accelerator",
    )
    assert similarity > 0.9


def test_title_similarity_different_titles() -> None:
    similarity = title_similarity(
        "Cinnamon: A Large-Scale Hardware Accelerator",
        "CraterLake: Efficient Unbounded Computation on Encrypted Data",
    )
    assert similarity < 0.5


def test_title_similarity_minor_difference() -> None:
    similarity = title_similarity(
        "F1: A Fast and Programmable Accelerator for FHE",
        "F1: Fast and Programmable Accelerator for Fully Homomorphic Encryption",
    )
    assert similarity > 0.7


@pytest.mark.asyncio
@respx.mock
async def test_verify_real_paper_via_doi() -> None:
    _mock_default_verify_routes()
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["cinnamon2025"])
    cinnamon = report.results[0]
    assert cinnamon.status == "verified"
    assert cinnamon.remote_source == "both"


@pytest.mark.asyncio
@respx.mock
async def test_verify_fake_paper_not_found() -> None:
    _mock_default_verify_routes()
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["fakepaper2024"])
    fake = report.results[0]
    assert fake.status == "not_found"


@pytest.mark.asyncio
@respx.mock
async def test_verify_wrong_year_mismatch() -> None:
    _mock_default_verify_routes()
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["f1wrong"])
    result = report.results[0]
    assert result.status == "mismatch"
    assert any("year:" in mismatch for mismatch in result.mismatches)


@pytest.mark.asyncio
@respx.mock
async def test_verify_missing_doi_uses_title_search() -> None:
    _mock_default_verify_routes()
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["craterlake2022"])
    result = report.results[0]
    assert result.status == "verified"
    assert result.remote_source == "s2"


@pytest.mark.asyncio
@respx.mock
async def test_verify_partial_match_fuzzy_title() -> None:
    s2_payload = dict(S2_CRATERLAKE, title="CraterLake: Hardware Accelerator for Efficient Unbounded Computation on Encrypted Data")
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json={"total": 1, "data": [s2_payload]})
    )
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})
    )
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["craterlake2022"])
    result = report.results[0]
    assert result.status == "verified"
    assert result.title_similarity is not None and result.title_similarity > 0.8


@pytest.mark.asyncio
@respx.mock
async def test_verify_filters_by_tex_citations() -> None:
    _mock_default_verify_routes()
    report = await verify_bib(
        "tests/fixtures/lint_buggy.bib",
        tex_path="tests/fixtures/lint_buggy.tex",
    )
    assert [result.bib_key for result in report.results] == ["cinnamon2025"]
    assert sorted(report.skipped) == ["craterlake2022", "f1wrong", "fakepaper2024"]


@pytest.mark.asyncio
@respx.mock
async def test_verify_both_sources() -> None:
    _mock_default_verify_routes()
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["cinnamon2025"])
    assert report.results[0].remote_source == "both"


@pytest.mark.asyncio
@respx.mock
async def test_verify_handles_api_error_gracefully() -> None:
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3582016.3582066").mock(
        return_value=httpx.Response(500, json={"error": "server error"})
    )
    respx.get("https://api.openalex.org/works/https://doi.org/10.1145/3582016.3582066").mock(
        return_value=httpx.Response(500, json={"error": "server error"})
    )
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["cinnamon2025"])
    assert report.results[0].status == "error"


@pytest.mark.asyncio
@respx.mock
async def test_verify_year_tolerance() -> None:
    tolerant = dict(S2_CINNAMON, year=2024)
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3582016.3582066").mock(
        return_value=httpx.Response(200, json=tolerant)
    )
    respx.get("https://api.openalex.org/works/https://doi.org/10.1145/3582016.3582066").mock(
        return_value=httpx.Response(200, json=OPENALEX_CINNAMON)
    )
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["cinnamon2025"])
    assert report.results[0].status == "verified"


@pytest.mark.asyncio
@respx.mock
async def test_verify_report_json_output() -> None:
    _mock_default_verify_routes()
    report = await verify_bib("tests/fixtures/lint_buggy.bib")
    payload = json.loads(report.to_json())
    expected = json.loads(Path("tests/fixtures/verify_expected.json").read_text(encoding="utf-8"))
    assert payload["summary"] == expected["summary"]
    assert {result["bib_key"]: result["status"] for result in payload["results"]} == expected["statuses"]


@pytest.mark.asyncio
@respx.mock
async def test_verify_report_markdown_output() -> None:
    _mock_default_verify_routes()
    report = await verify_bib("tests/fixtures/lint_buggy.bib")
    markdown = report.to_markdown()
    assert "# Citation Verification Report" in markdown
    assert "| Status | Count |" in markdown
    assert "### ⚠️ Mismatch: f1wrong" in markdown


@pytest.mark.network
@pytest.mark.skipif(
    os.getenv("HYPO_RUN_NETWORK_TESTS") != "1",
    reason="network tests disabled by default",
)
@pytest.mark.asyncio
async def test_verify_real_cinnamon() -> None:
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["cinnamon2025"])
    cinnamon = next(result for result in report.results if result.bib_key == "cinnamon2025")
    assert cinnamon.status == "verified"
    assert cinnamon.title_similarity is not None and cinnamon.title_similarity > 0.9


@pytest.mark.network
@pytest.mark.skipif(
    os.getenv("HYPO_RUN_NETWORK_TESTS") != "1",
    reason="network tests disabled by default",
)
@pytest.mark.asyncio
async def test_verify_real_fake_paper() -> None:
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["fakepaper2024"])
    fake = next(result for result in report.results if result.bib_key == "fakepaper2024")
    assert fake.status == "not_found"


@pytest.mark.network
@pytest.mark.skipif(
    os.getenv("HYPO_RUN_NETWORK_TESTS") != "1",
    reason="network tests disabled by default",
)
@pytest.mark.asyncio
async def test_verify_real_wrong_year() -> None:
    report = await verify_bib("tests/fixtures/lint_buggy.bib", keys=["f1wrong"])
    f1 = next(result for result in report.results if result.bib_key == "f1wrong")
    assert f1.status == "mismatch"
    assert any("year" in mismatch for mismatch in f1.mismatches)


def _mock_default_verify_routes() -> None:
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3582016.3582066").mock(
        return_value=httpx.Response(200, json=S2_CINNAMON)
    )
    respx.get("https://api.openalex.org/works/https://doi.org/10.1145/3582016.3582066").mock(
        return_value=httpx.Response(200, json=OPENALEX_CINNAMON)
    )
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.9999/fake.2024.000").mock(
        return_value=httpx.Response(404, json={"error": "Paper not found"})
    )
    respx.get("https://api.openalex.org/works/https://doi.org/10.9999/fake.2024.000").mock(
        return_value=httpx.Response(404, json={"error": "Not found"})
    )
    respx.get("https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3466752.3480070").mock(
        return_value=httpx.Response(200, json=S2_F1)
    )
    respx.get("https://api.openalex.org/works/https://doi.org/10.1145/3466752.3480070").mock(
        return_value=httpx.Response(200, json=OPENALEX_F1)
    )

    def s2_search_handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params.get("query", "")
        if "CraterLake" in query:
            return httpx.Response(200, json={"total": 1, "data": [S2_CRATERLAKE]})
        return httpx.Response(200, json={"total": 0, "data": []})

    def openalex_search_handler(request: httpx.Request) -> httpx.Response:
        query = request.url.params.get("search", "")
        if "CraterLake" in query:
            return httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})
        return httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})

    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        side_effect=s2_search_handler
    )
    respx.get("https://api.openalex.org/works").mock(side_effect=openalex_search_handler)
