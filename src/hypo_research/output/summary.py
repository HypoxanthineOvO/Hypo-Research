"""Survey overview and reading recommendation helpers."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from statistics import median

from hypo_research.core.models import PaperResult
from hypo_research.output.ranking import RankedPaper, compute_rankings, has_overall_scores


@dataclass
class ScoreDistribution:
    """Summary of Agent overall scores."""

    max_score: float
    min_score: float
    avg_score: float


@dataclass
class ReadingPlan:
    """Recommended reading order groups."""

    top_overall: list[PaperResult] = field(default_factory=list)
    latest: list[PaperResult] = field(default_factory=list)
    high_citation_remaining: list[PaperResult] = field(default_factory=list)


@dataclass
class SurveySummary:
    """High-level survey summary for reports and JSON output."""

    total: int
    min_year: int | None
    max_year: int | None
    score_distribution: ScoreDistribution | None
    high_citation_count: int
    overview_limit: int
    must_read: list[PaperResult]
    reading_plan: ReadingPlan
    statistical_summary: str


def build_survey_summary(papers: list[PaperResult]) -> SurveySummary:
    """Build a survey overview with stats, must-read papers, and reading plan."""
    years = [paper.year for paper in papers if paper.year is not None]
    scores = [paper.overall_score for paper in papers if paper.overall_score is not None]
    citations = [paper.citation_count or 0 for paper in papers]
    rankings = compute_rankings(papers)
    has_scores = has_overall_scores(papers)
    score_distribution = (
        ScoreDistribution(
            max_score=max(scores),
            min_score=min(scores),
            avg_score=sum(scores) / len(scores),
        )
        if scores
        else None
    )
    must_read = _must_read_papers(rankings.overall, has_scores=has_scores)
    reading_plan = _reading_plan(rankings.overall, rankings.by_time, rankings.by_citations, has_scores=has_scores)
    return SurveySummary(
        total=len(papers),
        min_year=min(years) if years else None,
        max_year=max(years) if years else None,
        score_distribution=score_distribution,
        high_citation_count=sum(1 for citation in citations if citation >= 100),
        overview_limit=_overview_limit(len(papers)),
        must_read=must_read,
        reading_plan=reading_plan,
        statistical_summary=_statistical_summary(papers),
    )


def abstract_brief(abstract: str | None) -> str:
    """Return a compact abstract brief for overview tables."""
    if not abstract:
        return "—"
    cleaned = " ".join(abstract.split())
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        return _truncate(cleaned, 30)
    first_sentence = re.split(r"(?<=\.)\s+", cleaned, maxsplit=1)[0]
    return _truncate(first_sentence, 80)


def summary_to_payload(summary: SurveySummary, papers: list[PaperResult]) -> dict[str, object]:
    """Convert a SurveySummary to JSON-serializable payload."""
    return {
        "total": summary.total,
        "year_span": {
            "min": summary.min_year,
            "max": summary.max_year,
        },
        "score_distribution": (
            {
                "max": round(summary.score_distribution.max_score, 2),
                "min": round(summary.score_distribution.min_score, 2),
                "avg": round(summary.score_distribution.avg_score, 2),
            }
            if summary.score_distribution is not None
            else None
        ),
        "high_citation_count": summary.high_citation_count,
        "overview_limit": summary.overview_limit,
        "must_read": [_paper_identifier(papers, paper) for paper in summary.must_read],
        "reading_order": {
            "top_overall": [
                _paper_identifier(papers, paper) for paper in summary.reading_plan.top_overall
            ],
            "latest": [
                _paper_identifier(papers, paper) for paper in summary.reading_plan.latest
            ],
            "high_citation_remaining": [
                _paper_identifier(papers, paper)
                for paper in summary.reading_plan.high_citation_remaining
            ],
        },
        "statistical_summary": summary.statistical_summary,
    }


def _must_read_papers(ranked: list[RankedPaper], *, has_scores: bool) -> list[PaperResult]:
    selected: list[PaperResult] = []
    seen: set[int] = set()
    for item in ranked:
        citation_count = item.paper.citation_count or 0
        if has_scores:
            include = (item.paper.overall_score or 0) >= 8.0 or citation_count >= 200
        else:
            include = citation_count >= 200
        if include and id(item.paper) not in seen:
            selected.append(item.paper)
            seen.add(id(item.paper))
    return selected


def _reading_plan(
    overall: list[RankedPaper],
    by_time: list[RankedPaper],
    by_citations: list[RankedPaper],
    *,
    has_scores: bool,
) -> ReadingPlan:
    top_overall = [item.paper for item in overall[:3]]
    known_years = [item.year for item in by_time if item.year is not None]
    latest_year = max(known_years) if known_years else None
    latest = [
        item.paper for item in by_time if item.year == latest_year
    ][:3] if latest_year is not None else []
    seen = set(id(paper) for paper in [*top_overall, *latest])
    high_citation_remaining = [
        item.paper
        for item in by_citations
        if (item.paper.citation_count or 0) >= 100 and id(item.paper) not in seen
    ][:3]
    if not has_scores:
        top_overall = [item.paper for item in by_citations[:3]]
        seen = set(id(paper) for paper in [*top_overall, *latest])
        high_citation_remaining = [
            item.paper
            for item in by_citations
            if id(item.paper) not in seen
        ][:3]
    return ReadingPlan(
        top_overall=top_overall,
        latest=latest,
        high_citation_remaining=high_citation_remaining,
    )


def _statistical_summary(papers: list[PaperResult]) -> str:
    if not papers:
        return "本次检索未返回论文。"
    year_counts = Counter(paper.year for paper in papers if paper.year is not None)
    citations = sorted(paper.citation_count or 0 for paper in papers)
    median_citation = int(median(citations)) if citations else 0
    if year_counts:
        most_common_year, most_common_count = year_counts.most_common(1)[0]
        latest_year = max(year_counts)
        recent_count = sum(
            count for year, count in year_counts.items() if year >= latest_year - 1
        )
        recent_ratio = round(recent_count / len(papers) * 100)
        return (
            f"该候选池覆盖 {min(year_counts)}–{max(year_counts)} 年，"
            f"{most_common_year} 年论文最多（{most_common_count} 篇），"
            f"近两年占比约 {recent_ratio}%，引用中位数 {median_citation}。"
        )
    return f"该候选池缺少年份信息，引用中位数 {median_citation}。"


def _overview_limit(total: int) -> int:
    if total <= 10:
        return total
    if total <= 30:
        return 10
    return 20


def _paper_identifier(papers: list[PaperResult], paper: PaperResult) -> str:
    if paper.url:
        return paper.url
    return f"paper_{papers.index(paper) + 1}"


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}..."
