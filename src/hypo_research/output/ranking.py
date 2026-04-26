"""Multi-dimensional ranking helpers for survey reports."""

from __future__ import annotations

from dataclasses import dataclass

from hypo_research.core.models import PaperResult


@dataclass
class RankedPaper:
    """A paper with its ranking positions across all views."""

    paper: PaperResult
    overall_rank: int | None
    citation_rank: int
    relevance_rank: int | None
    year: int | None


@dataclass
class RankingResult:
    """All four ranked views with cross-references."""

    overall: list[RankedPaper]
    by_citations: list[RankedPaper]
    by_relevance: list[RankedPaper]
    by_time: list[RankedPaper]


def compute_rankings(papers: list[PaperResult]) -> RankingResult:
    """Compute all ranked views and cross-reference ranks."""
    ranked = [
        RankedPaper(
            paper=paper,
            overall_rank=None,
            citation_rank=0,
            relevance_rank=None,
            year=paper.year,
        )
        for paper in papers
    ]
    by_original = {id(item.paper): index for index, item in enumerate(ranked)}
    by_citations = sorted(
        ranked,
        key=lambda item: (-(item.paper.citation_count or 0), by_original[id(item.paper)]),
    )
    for index, item in enumerate(by_citations, start=1):
        item.citation_rank = index

    has_overall_scores = any(item.paper.overall_score is not None for item in ranked)
    if has_overall_scores:
        overall = sorted(
            ranked,
            key=lambda item: (
                item.paper.overall_score is None,
                -(item.paper.overall_score or 0.0),
                by_original[id(item.paper)],
            ),
        )
    else:
        overall = list(by_citations)
    for index, item in enumerate(overall, start=1):
        item.overall_rank = index

    has_relevance_scores = any(item.paper.relevance_score is not None for item in ranked)
    if has_relevance_scores:
        by_relevance = sorted(
            ranked,
            key=lambda item: (
                item.paper.relevance_score is None,
                -(item.paper.relevance_score or 0.0),
                by_original[id(item.paper)],
            ),
        )
        for index, item in enumerate(by_relevance, start=1):
            item.relevance_rank = index
    else:
        by_relevance = []

    by_time = sorted(
        ranked,
        key=lambda item: (
            item.paper.year is None,
            item.paper.year or 0,
            -(item.paper.citation_count or 0),
            by_original[id(item.paper)],
        ),
    )

    return RankingResult(
        overall=overall,
        by_citations=by_citations,
        by_relevance=by_relevance,
        by_time=by_time,
    )


def has_overall_scores(papers: list[PaperResult]) -> bool:
    """Return whether at least one paper has an overall score."""
    return any(paper.overall_score is not None for paper in papers)


def has_relevance_scores(papers: list[PaperResult]) -> bool:
    """Return whether at least one paper has a relevance score."""
    return any(paper.relevance_score is not None for paper in papers)
