"""Tests for the lightweight BibTeX parser."""

from __future__ import annotations

from hypo_research.writing.bib_parser import parse_bib


def test_parse_bib_entry_count() -> None:
    entries = parse_bib("tests/fixtures/lint_buggy.bib")
    assert len(entries) == 4


def test_parse_bib_fields() -> None:
    entries = parse_bib("tests/fixtures/lint_buggy.bib")
    cinnamon = next(entry for entry in entries if entry.key == "cinnamon2025")
    assert cinnamon.entry_type == "inproceedings"
    assert "doi" in cinnamon.fields
    assert cinnamon.fields["year"] == "2025"


def test_parse_bib_missing_doi() -> None:
    entries = parse_bib("tests/fixtures/lint_buggy.bib")
    craterlake = next(entry for entry in entries if entry.key == "craterlake2022")
    assert "doi" in craterlake.missing_fields


def test_parse_bib_all_fields_present() -> None:
    entries = parse_bib("tests/fixtures/lint_buggy.bib")
    cinnamon = next(entry for entry in entries if entry.key == "cinnamon2025")
    assert len(cinnamon.missing_fields) == 0


def test_parse_bib_entry_types() -> None:
    entries = parse_bib("tests/fixtures/lint_buggy.bib")
    types = {entry.key: entry.entry_type for entry in entries}
    assert types["cinnamon2025"] == "inproceedings"
    assert types["fakepaper2024"] == "article"
