"""Tests for paper target resolution."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from hypo_research.paper_target import PaperTargetError, resolve_paper_target


def test_resolve_latex_directory() -> None:
    with resolve_paper_target("tests/fixtures/multifile", prefer=("latex",)) as target:
        assert target.name == "main.tex"


def test_resolve_pdf_directory(tmp_path: Path) -> None:
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    shutil.copy("data/reviews/FRR/FRRPaper.pdf", paper_dir / "paper.pdf")

    with resolve_paper_target(paper_dir, prefer=("pdf",)) as target:
        assert target.name == "paper.pdf"


def test_resolve_zip_archive_with_pdf(tmp_path: Path) -> None:
    archive = tmp_path / "paper.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.write("data/reviews/FRR/FRRPaper.pdf", "paper/FRRPaper.pdf")

    with resolve_paper_target(archive, prefer=("pdf",)) as target:
        assert target.name == "FRRPaper.pdf"
        assert target.exists()


def test_multiple_pdf_directory_requires_exact_file(tmp_path: Path) -> None:
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    shutil.copy("data/reviews/FRR/FRRPaper.pdf", paper_dir / "a.pdf")
    shutil.copy("data/reviews/FRR/FRRPaper.pdf", paper_dir / "b.pdf")

    with pytest.raises(PaperTargetError, match="Multiple pdf paper targets"):
        with resolve_paper_target(paper_dir, prefer=("pdf",)):
            pass


def test_zip_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../escape.tex", "\\documentclass{article}")

    with pytest.raises(PaperTargetError, match="escapes extraction"):
        with resolve_paper_target(archive, prefer=("latex",)):
            pass
