"""Tests for chapter-level writing statistics extraction."""

from __future__ import annotations

from hypo_research.writing.stats import extract_stats


def test_chapter_stats_section_count() -> None:
    stats = extract_stats("tests/fixtures/polish_sample.tex")
    assert len(stats.chapter_stats) == 3


def test_chapter_stats_word_count() -> None:
    stats = extract_stats("tests/fixtures/polish_sample.tex")
    for chapter in stats.chapter_stats:
        assert chapter.word_count > 0


def test_chapter_stats_long_sentences() -> None:
    stats = extract_stats("tests/fixtures/polish_sample.tex")
    intro = next(chapter for chapter in stats.chapter_stats if "Introduction" in chapter.section_title)
    assert len(intro.long_sentences) >= 1
    assert intro.long_sentences[0]["word_count"] > 40


def test_chapter_stats_paragraph_starts_repetition() -> None:
    stats = extract_stats("tests/fixtures/polish_sample.tex")
    intro = next(chapter for chapter in stats.chapter_stats if "Introduction" in chapter.section_title)
    we_count = sum(1 for word in intro.paragraph_starts if word.lower() == "we")
    assert we_count >= 3


def test_chapter_stats_avg_sentence_length() -> None:
    stats = extract_stats("tests/fixtures/polish_sample.tex")
    for chapter in stats.chapter_stats:
        if chapter.sentence_count > 0:
            assert 5 <= chapter.avg_sentence_length <= 50


def test_chapter_stats_excludes_comments() -> None:
    stats = extract_stats("tests/fixtures/translate_sample.tex")
    intro = next(chapter for chapter in stats.chapter_stats if "Introduction" in chapter.section_title)
    assert intro.word_count > 0


def test_chapter_stats_section_levels() -> None:
    stats = extract_stats("tests/fixtures/polish_sample.tex")
    assert all(chapter.level == 1 for chapter in stats.chapter_stats)
