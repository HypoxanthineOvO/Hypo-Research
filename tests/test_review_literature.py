"""Tests for literature-grounded review support."""

from __future__ import annotations

from dataclasses import asdict

import httpx
import pytest

from hypo_research.core.models import PaperResult
from hypo_research.review.literature import (
    LiteratureContext,
    LiteratureReference,
    _deduplicate_and_rank,
    _rate_limited_request,
    extract_search_queries,
    format_literature_context,
    search_literature,
)
from hypo_research.review.parser import PaperStructure
from hypo_research.review.reviewers import REVIEWERS, Severity, get_reviewer_prompt


def paper_result(
    title: str,
    paper_id: str,
    *,
    citations: int = 0,
    year: int = 2025,
    abstract: str = "abstract",
) -> PaperResult:
    return PaperResult(
        title=title,
        authors=["Alice", "Bob", "Carol", "Dave"],
        year=year,
        venue="DAC",
        abstract=abstract,
        s2_paper_id=paper_id,
        url=f"https://example.com/{paper_id}",
        citation_count=citations,
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
    )


def literature_context() -> LiteratureContext:
    return LiteratureContext(
        query_terms=["fhe accelerator", "bootstrapping hardware"],
        references=[
            LiteratureReference(
                title="Recent FHE Accelerator",
                authors=["Alice", "Bob", "Carol", "et al."],
                venue="DAC",
                year=2025,
                abstract_snippet="A recent accelerator.",
                citation_count=42,
                s2_paper_id="s2-1",
                is_cited_by_paper=False,
            )
        ],
        search_timestamp="2026-04-27T12:00:00",
        year_range=(2023, 2026),
        paper_title="Paper",
    )


def test_extract_search_queries_uses_mock_llm(monkeypatch) -> None:
    monkeypatch.setattr(
        "hypo_research.review.literature._call_llm_for_queries",
        lambda **kwargs: "fully homomorphic encryption accelerator\nbootstrapping ASIC design\nprivacy preserving ML hardware",
    )

    queries = extract_search_queries("Fast FHE", "We propose hardware.", num_queries=3)

    assert queries == [
        "fully homomorphic encryption accelerator",
        "bootstrapping ASIC design",
        "privacy preserving ML hardware",
    ]


def test_deduplicate_and_rank_filters_self_and_marks_cited() -> None:
    raw = [
        paper_result("The Reviewed Paper", "self", citations=999),
        paper_result("Recent FHE Accelerator", "p1", citations=10),
        paper_result("Recent FHE Accelerator Duplicate", "p1", citations=20),
        paper_result("Uncited Important Work", "p2", citations=5),
    ]

    refs = _deduplicate_and_rank(
        raw,
        paper_title="The Reviewed Paper",
        paper_references=["Recent FHE Accelerator"],
        max_results=10,
    )

    assert [ref.s2_paper_id for ref in refs] == ["p2", "p1"]
    assert refs[0].is_cited_by_paper is False
    assert refs[1].is_cited_by_paper is True
    assert refs[1].citation_count == 20


def test_search_literature_returns_empty_context_when_s2_unavailable(monkeypatch) -> None:
    async def failing_search(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr("hypo_research.review.literature._search_literature_async", failing_search)

    context = search_literature("Paper", "abstract", queries=["fhe accelerator"])

    assert context.references == []
    assert context.query_terms == ["fhe accelerator"]


def test_format_literature_context_output_and_empty() -> None:
    rendered = format_literature_context(literature_context())

    assert "近期相关工作参考" in rendered
    assert "⚠️ 本文未引用" in rendered
    assert format_literature_context(LiteratureContext([], [], "now", (2023, 2026), "Paper")) == ""


def test_literature_dataclasses_serialize() -> None:
    payload = asdict(literature_context())

    assert payload["references"][0]["title"] == "Recent FHE Accelerator"


def test_reviewer_prompt_injects_literature_context() -> None:
    paper = PaperStructure(
        title="Paper",
        abstract="abstract",
        sections=[],
        figures=[],
        tables=[],
        equations_count=0,
        references=[],
        claims=[],
        word_count=1,
        page_count=None,
        raw_text="raw",
        source_type="latex",
        inferred_domain=None,
    )

    with_lit = get_reviewer_prompt(REVIEWERS["lichaofan"], Severity.STANDARD, paper, literature=literature_context())
    without_lit = get_reviewer_prompt(REVIEWERS["lichaofan"], Severity.STANDARD, paper, literature=None)

    assert "近期相关工作参考" in with_lit
    assert "近期相关工作参考" not in without_lit


def test_rate_limited_request_retries_after_429(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_get(url, params, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, request=httpx.Request("GET", url))
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr("hypo_research.review.literature.time.sleep", lambda seconds: None)
    monkeypatch.setattr("hypo_research.review.literature.httpx.get", fake_get)

    assert _rate_limited_request("https://example.com", {}) == {"ok": True}
    assert calls["count"] == 2


def test_abstract_truncation() -> None:
    refs = _deduplicate_and_rank(
        [paper_result("Long Abstract Paper", "p1", abstract="x" * 500)],
        paper_title="Other Paper",
        paper_references=[],
        max_results=1,
    )

    assert len(refs[0].abstract_snippet) <= 200
    assert refs[0].abstract_snippet.endswith("...")
