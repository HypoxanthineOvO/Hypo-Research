"""Markdown report generation helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from hypo_research.core.models import PaperResult, SurveyMeta


def generate_report(
    papers: list[PaperResult],
    meta: SurveyMeta,
    output_path: Path,
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
        "## Results by Verification Status",
        "",
    ]

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
