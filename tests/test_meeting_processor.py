"""Tests for meeting transcript preprocessing."""

from __future__ import annotations

from pathlib import Path

from hypo_research.meeting.glossary import GlossaryManager, GlossaryTerm
from hypo_research.meeting.processor import MeetingInput, MeetingProcessor


def _manager(tmp_path: Path) -> GlossaryManager:
    manager = GlossaryManager(tmp_path / "glossary.toml")
    manager.add_term(
        GlossaryTerm(
            keyword="FHE",
            canonical="全同态加密 (Fully Homomorphic Encryption, FHE)",
            aliases=["fhe", "同台加密"],
            category="crypto",
        )
    )
    manager.save()
    return manager


def test_load_transcript_reads_txt_and_md(tmp_path: Path) -> None:
    processor = MeetingProcessor(_manager(tmp_path))
    txt = tmp_path / "meeting.txt"
    md = tmp_path / "meeting.md"
    txt.write_text("txt content", encoding="utf-8")
    md.write_text("md content", encoding="utf-8")

    assert processor.load_transcript(txt) == "txt content"
    assert processor.load_transcript(md) == "md content"


def test_preprocess_replaces_known_alias(tmp_path: Path) -> None:
    processor = MeetingProcessor(_manager(tmp_path))

    corrected, corrected_terms, unknown_terms = processor.preprocess(
        "今天讨论 fhe 和 ABC。"
    )

    assert "全同态加密 (Fully Homomorphic Encryption, FHE)" in corrected
    assert corrected_terms == ["fhe"]
    assert unknown_terms == ["ABC"]


def test_preprocess_does_not_replace_substrings(tmp_path: Path) -> None:
    processor = MeetingProcessor(_manager(tmp_path))

    corrected, corrected_terms, _ = processor.preprocess("这个 XFHEY 标记不应替换。")

    assert corrected == "这个 XFHEY 标记不应替换。"
    assert corrected_terms == []


def test_preprocess_detects_unknown_quoted_terms(tmp_path: Path) -> None:
    processor = MeetingProcessor(_manager(tmp_path))

    _, _, unknown_terms = processor.preprocess("他们提到“新方法”和 XYZ。")

    assert "新方法" in unknown_terms
    assert "XYZ" in unknown_terms


def test_prepare_prompt_context_contains_required_fields(tmp_path: Path) -> None:
    transcript = tmp_path / "meeting.txt"
    transcript.write_text("今天讨论 fhe。", encoding="utf-8")
    processor = MeetingProcessor(_manager(tmp_path))

    context = processor.prepare_prompt_context(
        MeetingInput(
            transcript_path=transcript,
            meeting_type="advisor_meeting",
            participants=["张老师", "小明"],
            date="2026-04-26",
            topic="课题沟通",
            output_path=tmp_path / "minutes.md",
        )
    )

    assert context["template_used"] == "advisor_meeting"
    assert "Corrected Transcript" not in context
    assert "corrected_transcript" in context
    assert "template_skeleton" in context
    assert "glossary_excerpt" in context
    assert context["metadata"]["participants"] == ["张老师", "小明"]
