"""Cross-source verification helpers."""

from __future__ import annotations

from hypo_research.core.models import PaperResult, VerificationLevel


class Verifier:
    """Cross-source verification for paper results."""

    def verify(
        self,
        papers: list[PaperResult],
    ) -> list[PaperResult]:
        """Set verification status based on source count."""
        for paper in papers:
            source_count = len(paper.sources)
            if source_count >= 2:
                paper.verification = VerificationLevel.VERIFIED
            elif source_count == 1:
                paper.verification = VerificationLevel.SINGLE_SOURCE
            else:
                paper.verification = VerificationLevel.UNVERIFIED
        return papers
