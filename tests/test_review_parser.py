"""Tests for paper review structure parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from hypo_research.review.parser import RAW_TEXT_LIMIT, parse_paper


def write_sample_project(tmp_path: Path) -> Path:
    main = tmp_path / "main.tex"
    section = tmp_path / "method.tex"
    bib = tmp_path / "refs.bib"
    main.write_text(
        r"""
\documentclass{article}
\title{Fast FHE Acceleration for Private Inference}
\begin{document}
\maketitle
\begin{abstract}
We propose a fast accelerator for fully homomorphic encryption inference.
\end{abstract}
\section{Introduction}
Our method targets FHE bootstrapping and we achieve 10x speedup over baselines.
\begin{figure}
\caption{System overview.}
\label{fig:overview}
\end{figure}
\input{method}
\bibliography{refs}
\end{document}
""",
        encoding="utf-8",
    )
    section.write_text(
        r"""
\section{Method}
We present a tiled NTT pipeline.
\begin{table}
\caption{Runtime comparison.}
\label{tab:runtime}
\end{table}
\begin{equation}
y = ax + b
\end{equation}
""",
        encoding="utf-8",
    )
    bib.write_text(
        r"""
@inproceedings{crypto2024,
  title = {CryptoNAS: Private Inference on a Budget},
  author = {Alice Smith},
  year = {2024},
  booktitle = {ICLR},
  doi = {10.0000/example}
}
""",
        encoding="utf-8",
    )
    return main


def test_latex_parse_extracts_title_abstract_sections(tmp_path: Path) -> None:
    paper = parse_paper(write_sample_project(tmp_path).as_posix())

    assert paper.title == "Fast FHE Acceleration for Private Inference"
    assert "fully homomorphic encryption" in paper.abstract
    assert [section.title for section in paper.sections] == ["Introduction", "Method"]


def test_latex_parse_extracts_figures_tables_captions(tmp_path: Path) -> None:
    paper = parse_paper(write_sample_project(tmp_path).as_posix())

    assert paper.figures[0].label == "fig:overview"
    assert paper.figures[0].caption == "System overview."
    assert paper.tables[0].label == "tab:runtime"
    assert paper.tables[0].caption == "Runtime comparison."


def test_latex_parse_extracts_claims_references_and_multifile(tmp_path: Path) -> None:
    paper = parse_paper(write_sample_project(tmp_path).as_posix())

    assert any("we achieve 10x speedup" in claim.lower() for claim in paper.claims)
    assert "CryptoNAS: Private Inference on a Budget" in paper.references
    assert any(section.title == "Method" for section in paper.sections)
    assert paper.equations_count == 1


def test_unsupported_file_format_raises(tmp_path: Path) -> None:
    path = tmp_path / "paper.docx"
    path.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError, match="不支持的文件格式"):
        parse_paper(path.as_posix())


def test_domain_inference_and_raw_text_truncation(tmp_path: Path) -> None:
    path = tmp_path / "long.tex"
    path.write_text(
        "\\documentclass{article}\\title{FHE Bootstrapping}\\begin{document}"
        "\\begin{abstract}fully homomorphic encryption bootstrapping\\end{abstract}"
        + "word " * (RAW_TEXT_LIMIT + 100)
        + "\\end{document}",
        encoding="utf-8",
    )

    paper = parse_paper(path.as_posix())

    assert paper.inferred_domain == "FHE acceleration"
    assert len(paper.raw_text) == RAW_TEXT_LIMIT


def test_pdf_parse_basic_structure(tmp_path: Path) -> None:
    fitz = pytest.importorskip("fitz")
    path = tmp_path / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "A PDF Paper Title\nAbstract\nWe propose a method.\n1 Introduction\nFigure 1: Overview.\nReferences\n[1] Example Paper",
    )
    doc.save(path)
    doc.close()

    paper = parse_paper(path.as_posix())

    assert paper.source_type == "pdf"
    assert paper.page_count == 1
    assert paper.title == "A PDF Paper Title"
    assert paper.figures[0].caption == "Overview."
