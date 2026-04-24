"""Tests for multi-file LaTeX stats extraction."""

from __future__ import annotations

from hypo_research.writing.stats import extract_stats


def test_cross_file_label_not_orphan() -> None:
    stats = extract_stats("tests/fixtures/multifile/main.tex")
    assert "fig:overview" not in stats.orphan_labels
    assert "fig:overview" not in stats.orphan_refs


def test_cross_file_ref_violation() -> None:
    stats = extract_stats("tests/fixtures/multifile/main.tex")
    ref_violations = [ref for ref in stats.refs if ref.type == "ref"]
    assert len(ref_violations) >= 1
    assert any("eval" in ref.file for ref in ref_violations)


def test_stats_file_field_populated() -> None:
    stats = extract_stats("tests/fixtures/multifile/main.tex")
    for label in stats.labels:
        assert label.file != ""
    for ref in stats.refs:
        assert ref.file != ""
    for section in stats.sections:
        assert section.file != ""


def test_stats_file_field_empty_for_single_file() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    for label in stats.labels:
        assert label.file == ""


def test_multifile_chapter_stats() -> None:
    stats = extract_stats("tests/fixtures/multifile/main.tex")
    for chapter in stats.chapter_stats:
        assert chapter.file != ""
    intro = next(chapter for chapter in stats.chapter_stats if "Introduction" in chapter.section_title)
    assert "intro" in intro.file


def test_multifile_paragraph_pairs() -> None:
    stats = extract_stats("tests/fixtures/multifile/main.tex")
    for pair in stats.paragraph_pairs:
        assert pair.file != ""


def test_multifile_multi_bib() -> None:
    stats = extract_stats("tests/fixtures/multifile/main.tex")
    bib_keys = [entry.key for entry in stats.bib_entries]
    assert "craterlake2022" in bib_keys
    assert "f1_2021" in bib_keys
