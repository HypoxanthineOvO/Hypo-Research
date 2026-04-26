"""JSON output helpers for search results and provenance metadata."""

from __future__ import annotations

import json
from pathlib import Path

from hypo_research.core.models import PaperResult, SurveyMeta
from hypo_research.output.ranking import RankingResult, compute_rankings
from hypo_research.output.summary import build_survey_summary, summary_to_payload


def write_search_output(
    output_dir: Path,
    meta: SurveyMeta,
    papers: list[PaperResult],
) -> None:
    """Write survey metadata, normalized results, and raw responses."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    meta_payload = meta.model_dump(mode="json")
    rankings = compute_rankings(papers)
    summary = build_survey_summary(papers)
    rankings_by_paper = _rankings_by_paper(rankings)
    results_payload = [
        _paper_payload(paper, rankings_by_paper[id(paper)]) for paper in papers
    ]
    ranked_payload = {
        "papers": results_payload,
        "summary": summary_to_payload(summary, papers),
        "ranking_views": _ranking_views_payload(rankings, papers, summary.must_read),
    }

    _write_json(output_dir / "meta.json", meta_payload)
    _write_json(output_dir / "results.json", results_payload)
    _write_json(output_dir / "ranked_results.json", ranked_payload)

    grouped: dict[str, list[dict]] = {source_name: [] for source_name in meta.sources_used}
    for paper in papers:
        grouped.setdefault(paper.source_api, []).append(paper.model_dump(mode="json"))

    for source_name, payload in grouped.items():
        raw_payload = {
            "source": source_name,
            "count": len(payload),
            "papers": payload,
        }
        _write_json(raw_dir / f"{source_name}.json", raw_payload)


def _write_json(path: Path, payload: dict | list[dict]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _paper_payload(paper: PaperResult, rankings: dict[str, object]) -> dict:
    payload = paper.model_dump(mode="json", exclude={"raw_response"})
    if paper.overall_score is None:
        payload.pop("overall_score", None)
    if paper.relevance_score is None:
        payload.pop("relevance_score", None)
    payload["rankings"] = rankings
    return payload


def _rankings_by_paper(rankings: RankingResult) -> dict[int, dict[str, object]]:
    by_time_position = _time_positions(rankings)
    all_ranked = {
        id(item.paper): item
        for view in (
            rankings.overall,
            rankings.by_citations,
            rankings.by_relevance,
            rankings.by_time,
        )
        for item in view
    }
    return {
        paper_id: {
            "overall": item.overall_rank,
            "by_citations": item.citation_rank,
            "by_relevance": item.relevance_rank,
            "by_time_position": by_time_position.get(paper_id),
        }
        for paper_id, item in all_ranked.items()
    }


def _ranking_views_payload(
    rankings: RankingResult,
    papers: list[PaperResult],
    must_read: list[PaperResult],
) -> dict[str, object]:
    identifiers = {id(paper): _paper_identifier(index, paper) for index, paper in enumerate(papers, start=1)}
    by_time: dict[str, list[str]] = {}
    for item in rankings.by_time:
        year_key = str(item.paper.year) if item.paper.year is not None else "unknown"
        by_time.setdefault(year_key, []).append(identifiers[id(item.paper)])

    return {
        "overall": [identifiers[id(item.paper)] for item in rankings.overall],
        "by_citations": [identifiers[id(item.paper)] for item in rankings.by_citations],
        "by_relevance": [identifiers[id(item.paper)] for item in rankings.by_relevance],
        "by_time": by_time,
        "must_read": [_paper_identifier(papers.index(paper) + 1, paper) for paper in must_read],
    }


def _time_positions(rankings: RankingResult) -> dict[int, str]:
    counters: dict[str, int] = {}
    positions: dict[int, str] = {}
    for item in rankings.by_time:
        year_key = str(item.paper.year) if item.paper.year is not None else "unknown"
        counters[year_key] = counters.get(year_key, 0) + 1
        positions[id(item.paper)] = f"{year_key}-{counters[year_key]}"
    return positions


def _paper_identifier(index: int, paper: PaperResult) -> str:
    return paper.url or f"paper_{index}"
