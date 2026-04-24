"""Writing-side helpers for linting and paper drafting workflows."""

from hypo_research.writing.bib_parser import BibEntryInfo, parse_bib, parse_bib_files
from hypo_research.writing.check import (
    CheckReport,
    LintStageResult,
    StatsStageResult,
    VerifyStageResult,
    check_exit_code,
    render_check_report,
    run_check,
)
from hypo_research.writing.config import (
    CONFIG_FILENAME,
    HypoConfig,
    generate_default_config,
    load_config,
    load_config_from_file,
    merge_cli_args,
)
from hypo_research.writing.fixer import Fix, FixAction, FixReport, apply_fixes, generate_fixes
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
    "CheckReport",
    "CircularInputError",
    "CONFIG_FILENAME",
    "Fix",
    "FixAction",
    "FixReport",
    "HypoConfig",
    "LintStageResult",
    "MultipleMainFilesError",
    "OrphanParagraph",
    "ParagraphPair",
    "StatsStageResult",
    "TexFile",
    "TexStats",
    "TexProject",
    "VerificationResult",
    "VerifyReport",
    "VerifyStageResult",
    "apply_fixes",
    "check_exit_code",
    "extract_stats",
    "generate_fixes",
    "generate_default_config",
    "load_config",
    "load_config_from_file",
    "merge_cli_args",
    "parse_bib",
    "parse_bib_files",
    "render_check_report",
    "resolve_project",
    "run_check",
    "title_similarity",
    "verify_bib",
    "virtual_to_real",
]
