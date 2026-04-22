"""Tests for metadata auto verification hook."""

from __future__ import annotations

from pathlib import Path

from hypo_research.core.models import PaperResult, SearchParams, SurveyMeta, VerificationLevel
from hypo_research.hooks.auto_verify import AutoVerifyHook
from hypo_research.hooks.base import HookContext, HookEvent


def make_paper(
    *,
    doi: str | None = "10.1234/example",
    abstract: str | None = "Abstract",
    year: int | None = 2024,
    authors: list[str] | None = None,
    title: str = "Cryogenic CMOS for Quantum Computing",
    verification: VerificationLevel = VerificationLevel.SINGLE_SOURCE,
) -> PaperResult:
    return PaperResult(
        title=title,
        authors=authors if authors is not None else ["Alice Smith"],
        year=year,
        venue="ISSCC",
        abstract=abstract,
        doi=doi,
        url="https://example.com",
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
        verification=verification,
    )


def make_context(papers: list[PaperResult]) -> HookContext:
    meta = SurveyMeta(
        query="cryogenic computing GPU",
        params=SearchParams(query="cryogenic computing GPU"),
        output_dir="/tmp/out",
    )
    return HookContext(
        papers=papers,
        meta=meta,
        output_dir=Path("/tmp/out"),
        event=HookEvent.POST_VERIFY,
    )


def test_auto_verify_warns_on_missing_doi() -> None:
    paper = make_paper(doi=None)
    ctx = make_context([paper])

    AutoVerifyHook()(ctx)

    assert any(issue.message == "No DOI available" for issue in paper.metadata_issues or [])


def test_auto_verify_errors_on_missing_authors() -> None:
    paper = make_paper(authors=[])
    ctx = make_context([paper])

    AutoVerifyHook()(ctx)

    assert any(issue.message == "No authors listed" for issue in paper.metadata_issues or [])


def test_auto_verify_detects_multiple_issues() -> None:
    paper = make_paper(doi=None, abstract=None, year=0, authors=[], title="Short")
    ctx = make_context([paper])

    AutoVerifyHook()(ctx)

    messages = {issue.message for issue in paper.metadata_issues or []}
    assert "No DOI available" in messages
    assert "No abstract available" in messages
    assert "Invalid publication year" in messages
    assert "No authors listed" in messages
    assert "Suspiciously short title" in messages


def test_auto_verify_no_issues_for_complete_paper() -> None:
    paper = make_paper(verification=VerificationLevel.VERIFIED)
    ctx = make_context([paper])

    AutoVerifyHook()(ctx)

    assert paper.metadata_issues == []


def test_auto_verify_updates_meta_statistics() -> None:
    papers = [
        make_paper(doi=None),
        make_paper(authors=[]),
    ]
    ctx = make_context(papers)

    AutoVerifyHook()(ctx)

    assert ctx.meta.metadata_warnings_count == 2
    assert ctx.meta.metadata_errors_count == 1
    assert ctx.meta.papers_with_issues_count == 2
