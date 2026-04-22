"""Tests for bilingual paragraph pairing extraction."""

from __future__ import annotations

from hypo_research.writing.stats import extract_stats


def test_paragraph_pairs_count() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    assert len(stats.paragraph_pairs) == 3


def test_paragraph_pairs_chinese_extraction() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    assert any("FHE 加速器" in pair.chinese for pair in stats.paragraph_pairs)


def test_paragraph_pairs_english_extraction() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    assert any("novel FHE accelerator" in pair.english for pair in stats.paragraph_pairs)


def test_orphan_missing_chinese() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    missing_cn = [orphan for orphan in stats.orphan_paragraphs if orphan.type == "missing_chinese"]
    assert len(missing_cn) >= 1
    assert any("no Chinese comment" in orphan.text for orphan in missing_cn)


def test_orphan_missing_english() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    missing_en = [orphan for orphan in stats.orphan_paragraphs if orphan.type == "missing_english"]
    assert len(missing_en) >= 1
    assert any("只有中文" in orphan.text for orphan in missing_en)


def test_paragraph_pairs_section_attribution() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    assert all(pair.section != "" for pair in stats.paragraph_pairs)


def test_paragraph_pairs_line_numbers() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    for pair in stats.paragraph_pairs:
        assert pair.line_start < pair.line_end
        assert pair.line_start > 0


def test_paragraph_pairs_ignores_latex_commands() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    for pair in stats.paragraph_pairs:
        assert not pair.english.strip().startswith("\\section")
        assert not pair.english.strip().startswith("\\label")
