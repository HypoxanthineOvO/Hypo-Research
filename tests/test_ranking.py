"""Tests for multi-dimensional survey rankings."""

from __future__ import annotations

from hypo_research.core.models import PaperResult
from hypo_research.output.ranking import compute_rankings


def make_paper(
    title: str,
    *,
    citation_count: int | None = None,
    year: int | None = 2024,
    overall_score: float | None = None,
    relevance_score: float | None = None,
) -> PaperResult:
    return PaperResult(
        title=title,
        authors=["Alice"],
        year=year,
        venue="ICLR",
        url=f"https://example.com/{title}",
        citation_count=citation_count,
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
        overall_score=overall_score,
        relevance_score=relevance_score,
    )


def test_compute_rankings_basic_sorting() -> None:
    papers = [
        make_paper("A", citation_count=10, overall_score=7.0, relevance_score=9.0),
        make_paper("B", citation_count=30, overall_score=8.0, relevance_score=6.0),
        make_paper("C", citation_count=20, overall_score=9.0, relevance_score=8.0),
    ]

    rankings = compute_rankings(papers)

    assert [item.paper.title for item in rankings.overall] == ["C", "B", "A"]
    assert [item.paper.title for item in rankings.by_citations] == ["B", "C", "A"]
    assert [item.paper.title for item in rankings.by_relevance] == ["A", "C", "B"]


def test_citation_sort_treats_none_as_zero() -> None:
    papers = [
        make_paper("A", citation_count=None),
        make_paper("B", citation_count=5),
        make_paper("C", citation_count=0),
    ]

    rankings = compute_rankings(papers)

    assert [item.paper.title for item in rankings.by_citations] == ["B", "A", "C"]


def test_time_sort_uses_year_ascending_then_citations() -> None:
    papers = [
        make_paper("A", year=2024, citation_count=10),
        make_paper("B", year=2022, citation_count=5),
        make_paper("C", year=2024, citation_count=20),
        make_paper("D", year=None, citation_count=100),
    ]

    rankings = compute_rankings(papers)

    assert [item.paper.title for item in rankings.by_time] == ["B", "C", "A", "D"]


def test_overall_sort_uses_scores_descending() -> None:
    papers = [
        make_paper("A", overall_score=7.0),
        make_paper("B", overall_score=None),
        make_paper("C", overall_score=9.0),
    ]

    rankings = compute_rankings(papers)

    assert [item.paper.title for item in rankings.overall] == ["C", "A", "B"]


def test_overall_fallback_to_citations_when_all_scores_missing() -> None:
    papers = [
        make_paper("A", citation_count=1),
        make_paper("B", citation_count=3),
        make_paper("C", citation_count=2),
    ]

    rankings = compute_rankings(papers)

    assert [item.paper.title for item in rankings.overall] == ["B", "C", "A"]


def test_relevance_view_empty_when_all_scores_missing() -> None:
    rankings = compute_rankings([make_paper("A"), make_paper("B")])

    assert rankings.by_relevance == []


def test_cross_reference_ranks_are_accurate() -> None:
    papers = [
        make_paper("A", citation_count=10, overall_score=9.0, relevance_score=6.0),
        make_paper("B", citation_count=30, overall_score=7.0, relevance_score=8.0),
        make_paper("C", citation_count=20, overall_score=8.0, relevance_score=9.0),
    ]

    rankings = compute_rankings(papers)
    by_title = {item.paper.title: item for item in rankings.overall}

    assert by_title["A"].overall_rank == 1
    assert by_title["A"].citation_rank == 3
    assert by_title["A"].relevance_rank == 3
    assert by_title["B"].overall_rank == 3
    assert by_title["B"].citation_rank == 1
    assert by_title["B"].relevance_rank == 2


def test_stable_sort_for_equal_values() -> None:
    papers = [
        make_paper("A", citation_count=10, overall_score=8.0, relevance_score=7.0),
        make_paper("B", citation_count=10, overall_score=8.0, relevance_score=7.0),
    ]

    rankings = compute_rankings(papers)

    assert [item.paper.title for item in rankings.overall] == ["A", "B"]
    assert [item.paper.title for item in rankings.by_citations] == ["A", "B"]
    assert [item.paper.title for item in rankings.by_relevance] == ["A", "B"]


def test_single_paper_boundary_case() -> None:
    rankings = compute_rankings(
        [make_paper("Only", citation_count=1, overall_score=10, relevance_score=10)]
    )

    assert rankings.overall[0].overall_rank == 1
    assert rankings.by_citations[0].citation_rank == 1
    assert rankings.by_relevance[0].relevance_rank == 1
    assert rankings.by_time[0].paper.title == "Only"


def test_empty_list() -> None:
    rankings = compute_rankings([])

    assert rankings.overall == []
    assert rankings.by_citations == []
    assert rankings.by_relevance == []
    assert rankings.by_time == []
