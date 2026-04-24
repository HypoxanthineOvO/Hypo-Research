"""Writing-side helpers for linting and paper drafting workflows."""

from hypo_research.writing.bib_parser import BibEntryInfo, parse_bib, parse_bib_files
from hypo_research.writing.project import (
    CircularInputError,
    MultipleMainFilesError,
    TexFile,
    TexProject,
    resolve_project,
    virtual_to_real,
)
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
    "CircularInputError",
    "MultipleMainFilesError",
    "OrphanParagraph",
    "ParagraphPair",
    "TexFile",
    "TexStats",
    "TexProject",
    "VerificationResult",
    "VerifyReport",
    "extract_stats",
    "parse_bib",
    "parse_bib_files",
    "resolve_project",
    "title_similarity",
    "verify_bib",
    "virtual_to_real",
]
