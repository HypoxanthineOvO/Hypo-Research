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
from hypo_research.output.summary import abstract_brief, build_survey_summary


def make_paper(
    *,
    title: str,
    verification: VerificationLevel,
    metadata_issues: list[MetadataIssue] | None = None,
    abstract: str | None = None,
    year: int | None = 2023,
    citation_count: int | None = None,
    overall_score: float | None = None,
    relevance_score: float | None = None,
) -> PaperResult:
    return PaperResult(
        title=title,
        authors=["Alice Smith"],
        year=year,
        venue="ISSCC",
        abstract=abstract if abstract is not None else f"Abstract for {title}",
        doi="10.1234/example",
        url="https://example.com",
        citation_count=citation_count,
        overall_score=overall_score,
        relevance_score=relevance_score,
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
    assert "# Survey Report: cryogenic computing GPU" in content
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


def test_generate_report_overview_contains_count_and_year_span(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="Paper 2022",
            verification=VerificationLevel.VERIFIED,
            year=2022,
        ),
        make_paper(
            title="Paper 2024",
            verification=VerificationLevel.VERIFIED,
            year=2024,
        ),
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "## 📋 概览" in content
    assert "- **检索论文数**：2 篇" in content
    assert "- **时间跨度**：2022 – 2024" in content


def test_generate_report_overview_score_distribution_when_scored(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="High Score",
            verification=VerificationLevel.VERIFIED,
            overall_score=9.0,
        ),
        make_paper(
            title="Low Score",
            verification=VerificationLevel.VERIFIED,
            overall_score=7.0,
        ),
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "- **综合评分分布**：最高 9.0 / 最低 7.0 / 平均 8.0" in content


def test_generate_report_overview_skips_score_distribution_without_scores(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(title="No Score", verification=VerificationLevel.VERIFIED),
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "综合评分分布" not in content


def test_generate_report_overview_tables_and_timeline(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="Overall First",
            verification=VerificationLevel.VERIFIED,
            year=2023,
            citation_count=10,
            overall_score=9.0,
            abstract="This paper builds a fast accelerator. It has more details.",
        ),
        make_paper(
            title="Citation First",
            verification=VerificationLevel.VERIFIED,
            year=2024,
            citation_count=300,
            overall_score=8.0,
            abstract="This paper is highly cited.",
        ),
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "## 🏆 全部论文速览" in content
    assert "## 📈 全部论文速览" in content
    assert "## 📅 时间线速览" in content
    assert "| 1 | Overall First | 9.0 | 10 | 2023 | This paper builds a fast accelerator. |" in content
    assert "| 1 | Citation First | 300 | 8.0 | 2024 | This paper is highly cited. |" in content
    assert "### 2024 (1 篇)" in content


def test_abstract_brief_truncates_and_handles_empty() -> None:
    assert abstract_brief(None) == "—"
    assert abstract_brief("中" * 31) == f"{'中' * 30}..."
    english = "A" * 90 + ". Second sentence."
    assert abstract_brief(english) == f"{'A' * 80}..."


def test_survey_summary_must_read_with_scores() -> None:
    papers = [
        make_paper(
            title="High Score",
            verification=VerificationLevel.VERIFIED,
            citation_count=10,
            overall_score=8.1,
        ),
        make_paper(
            title="High Citation",
            verification=VerificationLevel.VERIFIED,
            citation_count=250,
            overall_score=6.0,
        ),
        make_paper(
            title="Normal",
            verification=VerificationLevel.VERIFIED,
            citation_count=50,
            overall_score=7.0,
        ),
    ]

    summary = build_survey_summary(papers)

    assert {paper.title for paper in summary.must_read} == {"High Score", "High Citation"}


def test_survey_summary_must_read_without_scores_uses_citation_threshold() -> None:
    papers = [
        make_paper(
            title="High Citation",
            verification=VerificationLevel.VERIFIED,
            citation_count=250,
        ),
        make_paper(
            title="Low Citation",
            verification=VerificationLevel.VERIFIED,
            citation_count=199,
        ),
    ]

    summary = build_survey_summary(papers)

    assert [paper.title for paper in summary.must_read] == ["High Citation"]


def test_generate_report_reading_advice_changes_without_scores(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="High Citation",
            verification=VerificationLevel.VERIFIED,
            citation_count=250,
        )
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "## 📖 阅读建议" in content
    assert "必读论文（引用 ≥ 200）" in content
    assert "1. 先读高引 Top 3，建立领域整体认知" in content


def test_survey_summary_overview_limit_adapts_to_total() -> None:
    small = [
        make_paper(title=f"Small {index}", verification=VerificationLevel.VERIFIED)
        for index in range(10)
    ]
    medium = [
        make_paper(title=f"Medium {index}", verification=VerificationLevel.VERIFIED)
        for index in range(11)
    ]
    large = [
        make_paper(title=f"Large {index}", verification=VerificationLevel.VERIFIED)
        for index in range(31)
    ]

    assert build_survey_summary(small).overview_limit == 10
    assert build_survey_summary(medium).overview_limit == 10
    assert build_survey_summary(large).overview_limit == 20


def test_survey_summary_statistical_summary_mentions_years_and_median() -> None:
    papers = [
        make_paper(
            title="Paper 2022",
            verification=VerificationLevel.VERIFIED,
            year=2022,
            citation_count=10,
        ),
        make_paper(
            title="Paper 2024",
            verification=VerificationLevel.VERIFIED,
            year=2024,
            citation_count=30,
        ),
    ]

    summary = build_survey_summary(papers)

    assert "2022–2024 年" in summary.statistical_summary
    assert "引用中位数 20" in summary.statistical_summary


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


def test_generate_report_includes_all_ranking_sections_with_scores(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="TFHE-rs: A Pure-Rust Implementation of Fully Homomorphic Encryption",
            verification=VerificationLevel.VERIFIED,
            year=2022,
            citation_count=180,
            overall_score=9.2,
            relevance_score=7.1,
        ),
        make_paper(
            title="CryptoNAS: Private Inference on a Budget",
            verification=VerificationLevel.VERIFIED,
            year=2024,
            citation_count=245,
            overall_score=8.7,
            relevance_score=9.5,
        ),
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "## 📊 综合排序（Overall Ranking）" in content
    assert "## 📈 引用数排序（By Citations）" in content
    assert "## 🎯 相关性排序（By Relevance）" in content
    assert "## 📅 时间线（Timeline）" in content
    assert "| 1 | TFHE-rs" in content
    assert "#2 (180)" in content
    assert "#1 (245)" in content


def test_generate_report_fallback_outputs_overall_and_timeline(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="Low Citation",
            verification=VerificationLevel.SINGLE_SOURCE,
            citation_count=1,
        ),
        make_paper(
            title="High Citation",
            verification=VerificationLevel.SINGLE_SOURCE,
            citation_count=9,
        ),
    ]

    generate_report(papers, make_meta(), output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "## 📊 综合排序（按引用数 fallback）" in content
    assert "## 📅 时间线（Timeline）" in content
    assert "## 📈 引用数排序（By Citations）" not in content
    assert "## 🎯 相关性排序（By Relevance）" not in content


def test_generate_report_timeline_groups_by_year(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="Paper 2024",
            verification=VerificationLevel.VERIFIED,
            year=2024,
            citation_count=1,
        ),
        make_paper(
            title="Paper 2022",
            verification=VerificationLevel.VERIFIED,
            year=2022,
            citation_count=1,
        ),
    ]

    generate_report(papers, make_meta(), output_path, ranking_view="time")

    content = output_path.read_text(encoding="utf-8")
    assert "### 2022" in content
    assert "### 2024" in content
    assert content.index("### 2022") < content.index("### 2024")


def test_generate_report_internal_references_format(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    papers = [
        make_paper(
            title="Overall First",
            verification=VerificationLevel.VERIFIED,
            citation_count=10,
            overall_score=10,
            relevance_score=5,
        ),
        make_paper(
            title="Citation First",
            verification=VerificationLevel.VERIFIED,
            citation_count=20,
            overall_score=9,
            relevance_score=8,
        ),
    ]

    generate_report(papers, make_meta(), output_path, ranking_view="citations")

    content = output_path.read_text(encoding="utf-8")
    assert "| 1 | Citation First | 20 | #2 | #1 | 2023 |" in content


def test_generate_report_truncates_ranking_title(tmp_path: Path) -> None:
    output_path = tmp_path / "results.md"
    long_title = "A" * 70
    generate_report(
        [
            make_paper(
                title=long_title,
                verification=VerificationLevel.VERIFIED,
                citation_count=1,
                overall_score=8,
            )
        ],
        make_meta(),
        output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert f"{'A' * 60}..." in content
