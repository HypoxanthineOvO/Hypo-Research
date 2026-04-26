"""Tests for Markdown report generation."""

from __future__ import annotations

from pathlib import Path

from hypo_research.core.models import (
    ExpansionTrace,
    MetadataIssue,
    PaperResult,
    QueryVariant,
    SearchParams,
    SurveyMeta,
    VerificationLevel,
)
from hypo_research.output.markdown_report import generate_report


def make_paper(
    *,
    title: str,
    verification: VerificationLevel,
    metadata_issues: list[MetadataIssue] | None = None,
    abstract: str | None = None,
) -> PaperResult:
    return PaperResult(
        title=title,
        authors=["Alice Smith"],
        year=2023,
        venue="ISSCC",
        abstract=abstract if abstract is not None else f"Abstract for {title}",
        doi="10.1234/example",
        url="https://example.com",
        source_api="semantic_scholar",
        sources=["semantic_scholar", "openalex"] if verification is VerificationLevel.VERIFIED else ["semantic_scholar"],
        verification=verification,
        metadata_issues=metadata_issues,
    )


def make_meta() -> SurveyMeta:
    return SurveyMeta(
        query="cryogenic computing GPU",
        params=SearchParams(query="cryogenic computing GPU"),
        sources_used=["semantic_scholar", "openalex", "arxiv"],
        per_source_counts={"semantic_scholar": 4, "openalex": 3, "arxiv": 2},
        verified_count=1,
        single_source_count=1,
        expansion=ExpansionTrace(
            original_query="cryogenic computing GPU",
            variants=[
                QueryVariant(
                    query="cryo-CMOS accelerator",
                    strategy="synonym",
                    rationale="Alternative terminology",
                )
            ],
            all_queries=["cryogenic computing GPU", "cryo-CMOS accelerator"],
        ),
        metadata_warnings_count=1,
        metadata_errors_count=1,
        papers_with_issues_count=1,
    )


def test_generate_report_basic_content(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(title="Verified Paper", verification=VerificationLevel.VERIFIED),
        make_paper(title="Single Source Paper", verification=VerificationLevel.SINGLE_SOURCE),
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "# Literature Survey Report" in content
    assert "Verified Paper" in content
    assert "Single Source Paper" in content
    assert "Semantic Scholar, OpenAlex, arXiv" in content


def test_generate_report_groups_by_verification() -> None:
    output_path = Path("/tmp/test_report.md")
    papers = [
        make_paper(title="Verified Paper", verification=VerificationLevel.VERIFIED),
        make_paper(title="Single Source Paper", verification=VerificationLevel.SINGLE_SOURCE),
    ]

    generate_report(papers, make_meta(), output_path)
    content = output_path.read_text(encoding="utf-8")

    assert "### Verified (2+ sources)" in content
    assert "### Single Source" in content


def test_generate_report_includes_statistics_table(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    generate_report(
        [make_paper(title="Verified Paper", verification=VerificationLevel.VERIFIED)],
        make_meta(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "| Source | Papers |" in content
    assert "| Semantic Scholar | 4 |" in content
    assert "| **After dedup** | **1** |" in content


def test_generate_report_includes_expansion_info(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    generate_report(
        [make_paper(title="Verified Paper", verification=VerificationLevel.VERIFIED)],
        make_meta(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "1 variants used (cryo-CMOS accelerator)" in content


def test_generate_report_includes_metadata_quality_summary(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="Problematic Paper",
            verification=VerificationLevel.SINGLE_SOURCE,
            metadata_issues=[
                MetadataIssue(field="authors", severity="error", message="No authors listed")
            ],
        )
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "## Metadata Quality" in content
    assert "Warnings: 1" in content
    assert "Errors: 1" in content
    assert "Problematic Paper: error on `authors`" in content


def test_generate_report_truncates_long_abstract(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    long_abstract = "A" * 520
    generate_report(
        [
            make_paper(
                title="Long Abstract Paper",
                verification=VerificationLevel.VERIFIED,
                abstract=long_abstract,
            )
        ],
        make_meta(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "**Abstract**: " in content
    assert f"{'A' * 500}..." in content
    assert long_abstract not in content


def test_generate_report_for_citation_graph_mode(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    meta = make_meta().model_copy(
        update={
            "mode": "citation_graph",
            "seed_identifiers": ["Cinnamon", "CraterLake"],
            "seed_resolved_count": 2,
            "failed_seeds": ["Unknown Seed"],
            "total_raw_results": 12,
            "depth": 1,
            "direction": "both",
            "depth_stats": {"1": 5},
            "relationship_contributions": {"citations": 7, "references": 5},
            "source_contributions": {"semantic_scholar": 7, "openalex": 5},
        }
    )

    generate_report(
        [make_paper(title="Verified Paper", verification=VerificationLevel.VERIFIED)],
        meta,
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "# Citation Graph Expansion Report" in content
    assert "Mode**: Citation graph traversal" in content
    assert "Seeds**: Cinnamon, CraterLake" in content
    assert "| citations | 7 |" in content
