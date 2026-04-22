"""Writing-side helpers for linting and paper drafting workflows."""

from hypo_research.writing.bib_parser import BibEntryInfo, parse_bib
from hypo_research.writing.stats import (
    ChapterStats,
    OrphanParagraph,
    ParagraphPair,
    TexStats,
    extract_stats,
)
from hypo_research.writing.verify import VerificationResult, VerifyReport, title_similarity, verify_bib

__all__ = [
    "BibEntryInfo",
    "ChapterStats",
    "OrphanParagraph",
    "ParagraphPair",
    "TexStats",
    "VerificationResult",
    "VerifyReport",
    "extract_stats",
    "parse_bib",
    "title_similarity",
    "verify_bib",
]
