"""Tests for lint --stats output extensions used by polish/translate skills."""

from __future__ import annotations

import json
import subprocess


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "hypo-research", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_lint_stats_includes_chapter_stats() -> None:
    result = run_cli(["lint", "--stats", "tests/fixtures/polish_sample.tex"])
    data = json.loads(result.stdout)
    assert "chapter_stats" in data
    assert len(data["chapter_stats"]) > 0


def test_lint_stats_includes_paragraph_pairs() -> None:
    result = run_cli(["lint", "--stats", "tests/fixtures/translate_sample.tex"])
    data = json.loads(result.stdout)
    assert "paragraph_pairs" in data
    assert "orphan_paragraphs" in data


def test_lint_stats_chapter_stats_schema() -> None:
    result = run_cli(["lint", "--stats", "tests/fixtures/polish_sample.tex"])
    data = json.loads(result.stdout)
    for chapter in data["chapter_stats"]:
        assert "section_title" in chapter
        assert "word_count" in chapter
        assert "sentence_count" in chapter
        assert "avg_sentence_length" in chapter
        assert "paragraph_starts" in chapter
        assert "long_sentences" in chapter


def test_lint_stats_paragraph_pairs_schema() -> None:
    result = run_cli(["lint", "--stats", "tests/fixtures/translate_sample.tex"])
    data = json.loads(result.stdout)
    for pair in data["paragraph_pairs"]:
        assert "chinese" in pair
        assert "english" in pair
        assert "section" in pair
        assert "line_start" in pair
        assert "line_end" in pair
