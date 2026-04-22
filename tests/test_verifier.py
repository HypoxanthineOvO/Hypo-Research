"""Tests for cross-source verification."""

from __future__ import annotations

from hypo_research.core.models import PaperResult, VerificationLevel
from hypo_research.core.verifier import Verifier


def make_paper(sources: list[str]) -> PaperResult:
    return PaperResult(
        title="Paper",
        authors=["Alice Smith"],
        year=2024,
        venue="ISSCC",
        abstract="Abstract",
        url="https://example.com",
        source_api=sources[0] if sources else "semantic_scholar",
        sources=sources,
    )


def test_verifier_marks_verified() -> None:
    papers = [make_paper(["semantic_scholar", "openalex"])]

    verified = Verifier().verify(papers)

    assert verified[0].verification is VerificationLevel.VERIFIED


def test_verifier_marks_single_source() -> None:
    papers = [make_paper(["semantic_scholar"])]

    verified = Verifier().verify(papers)

    assert verified[0].verification is VerificationLevel.SINGLE_SOURCE


def test_verifier_marks_unverified() -> None:
    papers = [make_paper([])]

    verified = Verifier().verify(papers)

    assert verified[0].verification is VerificationLevel.UNVERIFIED
