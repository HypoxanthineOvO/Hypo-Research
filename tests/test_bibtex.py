"""Tests for BibTeX generation."""

from __future__ import annotations

from pathlib import Path

from hypo_research.core.models import PaperResult
from hypo_research.output.bibtex import generate_bibtex, paper_to_bibtex_entry


def make_paper(
    *,
    title: str,
    authors: list[str],
    year: int,
    venue: str | None = "Conference on Cryogenic Computing",
    doi: str | None = "10.1234/example",
    arxiv_id: str | None = None,
) -> PaperResult:
    raw_response = {}
    if arxiv_id:
        raw_response["arxiv_primary_category"] = {"term": "cs.AR"}
    return PaperResult(
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        abstract="Abstract",
        doi=doi,
        arxiv_id=arxiv_id,
        url="https://example.com",
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
        raw_response=raw_response,
    )


def test_generate_bibtex_writes_entries(tmp_path: Path) -> None:
    output_path = tmp_path / "references.bib"
    papers = [
        make_paper(title="Paper One", authors=["Alice Smith"], year=2024),
        make_paper(title="Paper Two", authors=["Bob Jones"], year=2023),
    ]

    generate_bibtex(papers, output_path, query="cryogenic computing GPU")

    content = output_path.read_text(encoding="utf-8")
    assert "@inproceedings{" in content
    assert "Paper One" in content
    assert "Paper Two" in content


def test_paper_to_bibtex_entry_generates_citation_key() -> None:
    paper = make_paper(title="Cryogenic CMOS for Quantum Computing", authors=["Alice Smith"], year=2023)

    entry = paper_to_bibtex_entry(paper)

    assert "@inproceedings{smith2023cryogenic," in entry


def test_generate_bibtex_deduplicates_citation_keys(tmp_path: Path) -> None:
    output_path = tmp_path / "references.bib"
    papers = [
        make_paper(title="Cryogenic CMOS", authors=["Alice Smith"], year=2023),
        make_paper(title="Cryogenic CMOS Study", authors=["Alice Smith"], year=2023),
    ]

    generate_bibtex(papers, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "smith2023cryogenic," in content
    assert "smith2023cryogenica," in content


def test_bibtex_entry_type_detection() -> None:
    conference_paper = make_paper(title="Conf Paper", authors=["Alice Smith"], year=2023, venue="Cryogenic Symposium")
    journal_paper = make_paper(title="Journal Paper", authors=["Alice Smith"], year=2023, venue="IEEE Transactions on Computers")
    misc_paper = make_paper(title="Preprint", authors=["Alice Smith"], year=2023, venue=None, doi=None, arxiv_id="2301.12345")

    assert paper_to_bibtex_entry(conference_paper).startswith("@inproceedings")
    assert paper_to_bibtex_entry(journal_paper).startswith("@article")
    assert paper_to_bibtex_entry(misc_paper).startswith("@misc")


def test_bibtex_escapes_special_characters() -> None:
    paper = make_paper(title="Cryogenic & GPU_Design #1", authors=["Alice Smith"], year=2023)

    entry = paper_to_bibtex_entry(paper)

    assert "Cryogenic \\& GPU\\_Design \\#1" in entry


def test_bibtex_includes_arxiv_fields() -> None:
    paper = make_paper(
        title="Preprint",
        authors=["Alice Smith"],
        year=2023,
        venue=None,
        doi=None,
        arxiv_id="2301.12345",
    )

    entry = paper_to_bibtex_entry(paper)

    assert "eprint" in entry
    assert "archiveprefix" in entry
    assert "primaryclass" in entry


def test_generate_bibtex_skips_incomplete_records(tmp_path: Path) -> None:
    output_path = tmp_path / "references.bib"
    papers = [
        make_paper(title="Valid Paper", authors=["Alice Smith"], year=2023),
        PaperResult(
            title="",
            authors=[],
            url="https://example.com",
            source_api="semantic_scholar",
        ),
    ]

    generate_bibtex(papers, output_path)

    content = output_path.read_text(encoding="utf-8")
    assert "Valid Paper" in content
    assert content.count("@") == 1
