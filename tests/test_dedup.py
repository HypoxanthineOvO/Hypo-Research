"""Tests for cross-source deduplication."""

from __future__ import annotations

from hypo_research.core.dedup import Deduplicator
from hypo_research.core.models import PaperResult


def make_paper(
    *,
    title: str,
    authors: list[str],
    year: int,
    source_api: str,
    doi: str | None = None,
    s2_paper_id: str | None = None,
    arxiv_id: str | None = None,
    openalex_id: str | None = None,
    citation_count: int | None = None,
    matched_queries: list[str] | None = None,
) -> PaperResult:
    return PaperResult(
        title=title,
        authors=authors,
        year=year,
        venue="ISSCC",
        abstract=f"Abstract for {title}",
        doi=doi,
        s2_paper_id=s2_paper_id,
        arxiv_id=arxiv_id,
        openalex_id=openalex_id,
        url="https://example.com",
        citation_count=citation_count,
        reference_count=5,
        source_api=source_api,
        sources=[source_api],
        matched_queries=matched_queries,
    )


def test_dedup_by_doi_exact_match() -> None:
    deduplicator = Deduplicator()
    papers = [
        make_paper(
            title="Paper",
            authors=["Alice Smith"],
            year=2024,
            source_api="semantic_scholar",
            doi="10.1234/Example",
        ),
        make_paper(
            title="Paper",
            authors=["Alice Smith"],
            year=2024,
            source_api="openalex",
            doi="https://doi.org/10.1234/example",
        ),
    ]

    deduped = deduplicator.dedup(papers)

    assert len(deduped) == 1
    assert deduped[0].sources == ["semantic_scholar", "openalex"]


def test_dedup_by_title_author_year() -> None:
    deduplicator = Deduplicator()
    papers = [
        make_paper(
            title="Cryogenic CMOS for Quantum Computing",
            authors=["Alice Smith"],
            year=2023,
            source_api="openalex",
        ),
        make_paper(
            title="Cryogenic CMOS for Quantum Computing",
            authors=["Alice B. Smith"],
            year=2023,
            source_api="arxiv",
        ),
    ]

    deduped = deduplicator.dedup(papers)

    assert len(deduped) == 1


def test_dedup_by_jaccard_fuzzy_title() -> None:
    deduplicator = Deduplicator()
    papers = [
        make_paper(
            title="Cryogenic CMOS: for Quantum Computing",
            authors=["Alice Smith"],
            year=2023,
            source_api="openalex",
        ),
        make_paper(
            title="Cryogenic CMOS for Quantum Computing",
            authors=["Alice Smith"],
            year=2023,
            source_api="arxiv",
        ),
    ]

    deduped = deduplicator.dedup(papers)

    assert len(deduped) == 1


def test_dedup_merge_preserves_richer_metadata() -> None:
    deduplicator = Deduplicator()
    papers = [
        make_paper(
            title="Paper",
            authors=["Alice Smith"],
            year=2024,
            source_api="arxiv",
            arxiv_id="2301.12345",
            citation_count=2,
            matched_queries=["q1"],
        ),
        make_paper(
            title="Paper",
            authors=["Alice Smith"],
            year=2024,
            source_api="semantic_scholar",
            doi="10.1234/example",
            s2_paper_id="s2-1",
            citation_count=42,
            matched_queries=["q2"],
        ),
    ]

    deduped = deduplicator.dedup(papers)

    assert len(deduped) == 1
    paper = deduped[0]
    assert paper.source_api == "semantic_scholar"
    assert paper.arxiv_id == "2301.12345"
    assert paper.s2_paper_id == "s2-1"
    assert paper.citation_count == 42
    assert paper.matched_queries == ["q1", "q2"] or paper.matched_queries == ["q2", "q1"]


def test_dedup_keeps_distinct_papers() -> None:
    deduplicator = Deduplicator()
    papers = [
        make_paper(
            title="Paper One",
            authors=["Alice Smith"],
            year=2024,
            source_api="semantic_scholar",
        ),
        make_paper(
            title="Paper Two",
            authors=["Bob Jones"],
            year=2024,
            source_api="openalex",
        ),
    ]

    deduped = deduplicator.dedup(papers)

    assert len(deduped) == 2


def test_dedup_merges_matched_queries() -> None:
    deduplicator = Deduplicator()
    papers = [
        make_paper(
            title="Paper",
            authors=["Alice Smith"],
            year=2024,
            source_api="semantic_scholar",
            doi="10.1234/example",
            matched_queries=["query-a"],
        ),
        make_paper(
            title="Paper",
            authors=["Alice Smith"],
            year=2024,
            source_api="openalex",
            doi="10.1234/example",
            matched_queries=["query-b"],
        ),
    ]

    deduped = deduplicator.dedup(papers)

    assert len(deduped) == 1
    assert set(deduped[0].matched_queries or []) == {"query-a", "query-b"}
