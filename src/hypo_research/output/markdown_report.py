"""Markdown report generation helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from hypo_research.core.models import PaperResult, SurveyMeta
from hypo_research.output.ranking import (
    RankedPaper,
    compute_rankings,
    has_overall_scores,
    has_relevance_scores,
)

RankingView = Literal["all", "overall", "citations", "relevance", "time"]


def generate_report(
    papers: list[PaperResult],
    meta: SurveyMeta,
    output_path: Path,
    ranking_view: RankingView = "all",
) -> Path:
    """Generate a Markdown survey report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title = (
        "# Citation Graph Expansion Report"
        if meta.mode == "citation_graph"
        else "# Literature Survey Report"
    )

    lines: list[str] = [
        title,
        "",
        "## Search Summary",
        "",
        f'- **Query**: "{meta.query}"',
        f"- **Date**: {_format_date(meta.created_at)}",
        f"- **Sources**: {_format_sources(meta.sources_used)}",
        f"- **Results**: {len(papers)} papers ({meta.verified_count or 0} verified, {meta.single_source_count or 0} single-source)",
        *_render_mode_specific_summary(meta),
        "",
    ]

    lines.extend(_render_ranking_views(papers, ranking_view=ranking_view))
    lines.extend(["## Results by Verification Status", ""])

    groups = [
        (
            "Verified (2+ sources)",
            [
                paper
                for paper in papers
                if getattr(paper.verification, "value", paper.verification) == "verified"
            ],
        ),
        (
            "Single Source",
            [
                paper
                for paper in papers
                if getattr(paper.verification, "value", paper.verification) == "single_source"
            ],
        ),
        (
            "Unverified",
            [
                paper
                for paper in papers
                if getattr(paper.verification, "value", paper.verification) == "unverified"
            ],
        ),
    ]
    for heading, grouped_papers in groups:
        if grouped_papers:
            lines.extend(_render_paper_section(heading, grouped_papers))

    lines.extend(_render_metadata_quality(meta, papers))
    lines.extend(_render_statistics(meta, papers))

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def _render_ranking_views(
    papers: list[PaperResult],
    *,
    ranking_view: RankingView,
) -> list[str]:
    if not papers:
        return []

    rankings = compute_rankings(papers)
    has_overall = has_overall_scores(papers)
    has_relevance = has_relevance_scores(papers)
    views = _selected_views(ranking_view, has_overall=has_overall, has_relevance=has_relevance)
    lines: list[str] = []

    for view in views:
        if view == "overall":
            lines.extend(
                _render_overall_ranking(
                    rankings.overall,
                    fallback=not has_overall,
                )
            )
        elif view == "citations":
            lines.extend(_render_citation_ranking(rankings.by_citations))
        elif view == "relevance":
            if rankings.by_relevance:
                lines.extend(_render_relevance_ranking(rankings.by_relevance))
            elif ranking_view == "relevance":
                lines.extend(
                    [
                        "## 🎯 相关性排序（By Relevance）",
                        "",
                        "> 当前结果没有 Agent relevance_score，无法生成相关性排序。",
                        "",
                        "---",
                        "",
                    ]
                )
        elif view == "time":
            lines.extend(_render_timeline(rankings.by_time))

    return lines


def _selected_views(
    ranking_view: RankingView,
    *,
    has_overall: bool,
    has_relevance: bool,
) -> list[str]:
    if ranking_view == "all":
        if not has_overall and not has_relevance:
            return ["overall", "time"]
        views = ["overall", "citations"]
        if has_relevance:
            views.append("relevance")
        views.append("time")
        return views
    return [ranking_view]


def _render_overall_ranking(
    ranked: list[RankedPaper],
    *,
    fallback: bool,
) -> list[str]:
    heading = (
        "## 📊 综合排序（按引用数 fallback）"
        if fallback
        else "## 📊 综合排序（Overall Ranking）"
    )
    lines = [
        heading,
        "",
    ]
    if fallback:
        lines.extend(["> 当前结果没有 Agent overall_score，综合排序按引用数降序回退。", ""])
    lines.extend(
        [
            "| # | 论文 | 综合分 | 📈引用 | 🎯相关 | 📅年份 |",
            "|---|------|--------|--------|--------|--------|",
        ]
    )
    for index, item in enumerate(ranked, start=1):
        lines.append(
            "| "
            f"{index} | {_escape_table(_short_title(item.paper.title))} | "
            f"{_format_score(item.paper.overall_score)} | "
            f"{_format_citation_ref(item)} | "
            f"{_format_rank(item.relevance_rank)} | "
            f"{_format_year(item.year)} |"
        )
    lines.extend(["", "---", ""])
    return lines


def _render_citation_ranking(ranked: list[RankedPaper]) -> list[str]:
    lines = [
        "## 📈 引用数排序（By Citations）",
        "",
        "| # | 论文 | 被引数 | 📊综合 | 🎯相关 | 📅年份 |",
        "|---|------|--------|--------|--------|--------|",
    ]
    for index, item in enumerate(ranked, start=1):
        lines.append(
            "| "
            f"{index} | {_escape_table(_short_title(item.paper.title))} | "
            f"{item.paper.citation_count or 0} | "
            f"{_format_rank(item.overall_rank)} | "
            f"{_format_rank(item.relevance_rank)} | "
            f"{_format_year(item.year)} |"
        )
    lines.extend(["", "---", ""])
    return lines


def _render_relevance_ranking(ranked: list[RankedPaper]) -> list[str]:
    lines = [
        "## 🎯 相关性排序（By Relevance）",
        "",
        "| # | 论文 | 相关分 | 📊综合 | 📈引用 | 📅年份 |",
        "|---|------|--------|--------|--------|--------|",
    ]
    for index, item in enumerate(ranked, start=1):
        lines.append(
            "| "
            f"{index} | {_escape_table(_short_title(item.paper.title))} | "
            f"{_format_score(item.paper.relevance_score)} | "
            f"{_format_rank(item.overall_rank)} | "
            f"{_format_citation_ref(item)} | "
            f"{_format_year(item.year)} |"
        )
    lines.extend(["", "---", ""])
    return lines


def _render_timeline(ranked: list[RankedPaper]) -> list[str]:
    lines = ["## 📅 时间线（Timeline）", ""]
    current_year: int | None | object = object()
    for item in ranked:
        if item.year != current_year:
            current_year = item.year
            if lines[-1] != "":
                lines.append("")
            lines.extend([f"### {_format_year(item.year)}", ""])
        refs = " | ".join(
            [
                f"📊综合 {_format_rank(item.overall_rank)}",
                f"📈引用 {_format_citation_ref(item)}",
                f"🎯相关 {_format_rank(item.relevance_rank)}",
            ]
        )
        lines.append(f"- {_short_title(item.paper.title)} — {refs}")
    lines.extend(["", "---", ""])
    return lines


def _render_paper_section(title: str, papers: list[PaperResult]) -> list[str]:
    lines = [f"### {title}", ""]
    for index, paper in enumerate(papers, start=1):
        authors = ", ".join(paper.authors) or "Unknown authors"
        venue = paper.venue or "Unknown venue"
        doi = paper.doi or "N/A"
        sources = ", ".join(_pretty_source_name(source) for source in paper.sources)
        abstract_excerpt = _truncate_abstract(paper.abstract)

        lines.append(f"{index}. **{paper.title}** ({paper.year or 'Unknown year'})")
        lines.append(f"   {authors} — {venue}")
        lines.append(f"   DOI: {doi} | Sources: {sources}")
        if abstract_excerpt:
            lines.append(f"   **Abstract**: {abstract_excerpt}")
        lines.append("")
    return lines


def _render_metadata_quality(meta: SurveyMeta, papers: list[PaperResult]) -> list[str]:
    lines = [
        "## Metadata Quality",
        "",
        f"- Papers with issues: {meta.papers_with_issues_count or 0}",
        f"- Warnings: {meta.metadata_warnings_count or 0}",
        f"- Errors: {meta.metadata_errors_count or 0}",
    ]

    issue_lines: list[str] = []
    for paper in papers:
        for issue in paper.metadata_issues or []:
            issue_lines.append(
                f"- {paper.title}: {issue.severity} on `{issue.field}` ({issue.message})"
            )

    if issue_lines:
        lines.append("")
        lines.extend(issue_lines)

    lines.append("")
    return lines


def _render_statistics(meta: SurveyMeta, papers: list[PaperResult]) -> list[str]:
    lines = [
        "## Statistics",
        "",
        "| Source | Papers |",
        "|--------|--------|",
    ]
    source_counts = meta.source_contributions or meta.per_source_counts or {}
    for source_name, count in source_counts.items():
        lines.append(f"| {_pretty_source_name(source_name)} | {count} |")
    lines.append(f"| **After dedup** | **{len(papers)}** |")
    if meta.depth_stats:
        lines.extend(
            [
                "",
                "### Depth Breakdown",
                "",
                "| Depth | Papers |",
                "|-------|--------|",
            ]
        )
        for depth, count in meta.depth_stats.items():
            lines.append(f"| {depth} | {count} |")
    if meta.relationship_contributions:
        lines.extend(
            [
                "",
                "### Relationship Breakdown",
                "",
                "| Relationship | Papers |",
                "|--------------|--------|",
            ]
        )
        for relationship, count in meta.relationship_contributions.items():
            lines.append(f"| {relationship} | {count} |")
    lines.append("")
    return lines


def _format_date(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


def _format_sources(sources: list[str]) -> str:
    if not sources:
        return "Unknown"
    return ", ".join(_pretty_source_name(source) for source in sources)


def _format_expansion(meta: SurveyMeta) -> str:
    if meta.expansion is None:
        return "0 variants used"
    count = len(meta.expansion.variants)
    if count == 0:
        return "0 variants used"
    variants = ", ".join(variant.query for variant in meta.expansion.variants)
    return f"{count} variants used ({variants})"


def _pretty_source_name(source: str) -> str:
    mapping = {
        "semantic_scholar": "Semantic Scholar",
        "openalex": "OpenAlex",
        "arxiv": "arXiv",
    }
    return mapping.get(source, source)


def _truncate_abstract(abstract: str | None, limit: int = 500) -> str:
    """Return a Markdown-sized abstract excerpt."""
    if not abstract:
        return ""
    cleaned = " ".join(abstract.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def _short_title(title: str, limit: int = 60) -> str:
    """Return a compact title for ranking tables."""
    if len(title) <= limit:
        return title
    return f"{title[:limit]}..."


def _format_score(score: float | None) -> str:
    if score is None:
        return "-"
    return f"{score:.1f}"


def _format_rank(rank: int | None) -> str:
    if rank is None:
        return "-"
    return f"#{rank}"


def _format_citation_ref(item: RankedPaper) -> str:
    return f"#{item.citation_rank} ({item.paper.citation_count or 0})"


def _format_year(year: int | None) -> str:
    if year is None:
        return "Unknown year"
    return str(year)


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|")


def _render_mode_specific_summary(meta: SurveyMeta) -> list[str]:
    if meta.mode != "citation_graph":
        return [f"- **Query Expansion**: {_format_expansion(meta)}"]

    seed_summary = ", ".join(meta.seed_identifiers or []) or "N/A"
    failed_seeds = ", ".join(meta.failed_seeds or []) or "None"
    return [
        "- **Mode**: Citation graph traversal",
        f"- **Seeds**: {seed_summary}",
        f"- **Traversal Settings**: depth={meta.depth or 1}, direction={meta.direction or 'both'}",
        f"- **Seed Resolution**: {meta.seed_resolved_count or 0} resolved, {len(meta.failed_seeds or [])} failed",
        f"- **Failed Seeds**: {failed_seeds}",
        f"- **Traversal Raw Results**: {meta.total_raw_results or len(meta.per_source_counts or {})}",
    ]
