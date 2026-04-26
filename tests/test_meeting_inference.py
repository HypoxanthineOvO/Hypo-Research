"""Tests for heuristic meeting metadata inference."""

from __future__ import annotations

from hypo_research.meeting.inference import infer_meeting_metadata


def test_infer_group_meeting_high_confidence() -> None:
    inference = infer_meeting_metadata("今天组会开始，大家做进展汇报，下一个同学准备。")

    assert inference.meeting_type == "group_meeting"
    assert inference.meeting_type_confidence == "high"
    assert "进展汇报" in inference.meeting_type_reason


def test_infer_paper_discussion() -> None:
    inference = infer_meeting_metadata("今天做论文讨论，这篇论文的实验结果表明方法有效。")

    assert inference.meeting_type == "paper_discussion"
    assert inference.meeting_type_confidence == "high"


def test_infer_advisor_meeting() -> None:
    inference = infer_meeting_metadata("老师您看，这个思路可以吗？我想跟老师汇报一下。")

    assert inference.meeting_type == "advisor_meeting"
    assert inference.meeting_type_confidence == "high"


def test_infer_consultation() -> None:
    inference = infer_meeting_metadata("我想请教一下，你们是怎么做的，有没有经验？")

    assert inference.meeting_type == "consultation"
    assert inference.meeting_type_confidence == "high"


def test_infer_project_discussion() -> None:
    inference = infer_meeting_metadata("今天是方案讨论，重点看技术路线和实验设计。")

    assert inference.meeting_type == "project_discussion"
    assert inference.meeting_type_confidence == "high"


def test_infer_fallback_low_confidence() -> None:
    inference = infer_meeting_metadata("今天中午吃什么，天气不错。")

    assert inference.meeting_type == "group_meeting"
    assert inference.meeting_type_confidence == "low"


def test_infer_multiple_types_uses_most_high_matches() -> None:
    inference = infer_meeting_metadata(
        "这篇论文值得读，不过今天组会先做进展汇报，下一个同学继续。"
    )

    assert inference.meeting_type == "group_meeting"
    assert inference.meeting_type_confidence == "high"


def test_infer_participants_from_asr_speaker_marks() -> None:
    inference = infer_meeting_metadata("说话人1：大家好。\nSpeaker A: I agree.")

    assert "说话人1" in inference.participants
    assert "Speaker A" in inference.participants


def test_infer_participants_from_honorifics_and_names() -> None:
    inference = infer_meeting_metadata("张老师：小明你先汇报。小红后面补充。")

    assert "张老师" in inference.participants
    assert "小明" in inference.participants
    assert "小红" in inference.participants


def test_infer_participants_deduplicates() -> None:
    inference = infer_meeting_metadata("张老师：开始。张老师说小明先来。小明：好的。")

    assert inference.participants.count("张老师") == 1
    assert inference.participants.count("小明") == 1


def test_infer_domain_keywords_from_acronyms() -> None:
    inference = infer_meeting_metadata("今天讨论 FHE、NTT 和 GPU 的实现。")

    assert "FHE" in inference.domain_keywords
    assert "NTT" in inference.domain_keywords
    assert "GPU" in inference.domain_keywords


def test_infer_domain_keywords_from_glossary_terms() -> None:
    inference = infer_meeting_metadata(
        "今天讨论同台加密的 bootstrapping。",
        glossary_terms=["同台加密", "bootstrapping"],
    )

    assert "同台加密" in inference.domain_keywords
    assert "bootstrapping" in inference.domain_keywords


def test_infer_only_analyzes_first_2000_characters() -> None:
    transcript = "闲聊。" * 800 + "进展汇报 组会"

    inference = infer_meeting_metadata(transcript)

    assert inference.meeting_type == "group_meeting"
    assert inference.meeting_type_confidence == "low"


def test_infer_empty_text() -> None:
    inference = infer_meeting_metadata("")

    assert inference.meeting_type == "group_meeting"
    assert inference.meeting_type_confidence == "low"
    assert inference.preview == ""
    assert inference.participants == []


def test_detect_language_zh() -> None:
    inference = infer_meeting_metadata("今天讨论实验结果。")

    assert inference.language == "zh"


def test_detect_language_en() -> None:
    inference = infer_meeting_metadata("Today we discuss experiment results.")

    assert inference.language == "en"


def test_detect_language_mixed() -> None:
    inference = infer_meeting_metadata("今天讨论 FHE experiment results.")

    assert inference.language == "mixed"
