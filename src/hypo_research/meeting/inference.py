"""Heuristic meeting metadata inference from ASR transcripts."""

from __future__ import annotations

import re
from dataclasses import dataclass


TYPE_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "group_meeting": {
        "high": ["进展汇报", "周报", "组会", "下一个同学"],
        "medium": ["我的进展", "上周", "这周计划", "汇报一下"],
    },
    "paper_discussion": {
        "high": ["这篇论文", "论文讨论", "paper reading", "读这篇"],
        "medium": ["作者提出", "实验结果表明", "的方法是", "这篇的贡献"],
    },
    "project_discussion": {
        "high": ["课题讨论", "项目进展", "方案讨论"],
        "medium": ["技术路线", "实验设计", "下一步怎么做", "这个方向"],
    },
    "consultation": {
        "high": ["想请教", "帮我看看", "想问一下"],
        "medium": ["你们是怎么做的", "有没有经验", "能不能分享"],
    },
    "advisor_meeting": {
        "high": ["老师您看", "导师觉得", "想跟老师汇报"],
        "medium": ["老师建议", "您的意见", "这个思路可以吗"],
    },
}


@dataclass
class MeetingInference:
    """Inferred metadata from transcript analysis."""

    meeting_type: str | None
    meeting_type_confidence: str
    meeting_type_reason: str
    participants: list[str]
    topic: str | None
    domain_keywords: list[str]
    language: str
    preview: str


def infer_meeting_metadata(
    transcript: str,
    glossary_terms: list[str] | None = None,
) -> MeetingInference:
    """Analyze transcript text and infer meeting metadata without using an LLM."""
    text = transcript[:2000]
    preview = " ".join(transcript[:500].split())
    meeting_type, confidence, reason = _infer_meeting_type(text)
    return MeetingInference(
        meeting_type=meeting_type,
        meeting_type_confidence=confidence,
        meeting_type_reason=reason,
        participants=_infer_participants(text),
        topic=_infer_topic(text),
        domain_keywords=_infer_domain_keywords(text, glossary_terms or []),
        language=_detect_language(text),
        preview=preview,
    )


def _infer_meeting_type(text: str) -> tuple[str, str, str]:
    lowered = text.casefold()
    matches: dict[str, dict[str, list[str]]] = {}
    for meeting_type, levels in TYPE_KEYWORDS.items():
        high = [keyword for keyword in levels["high"] if keyword.casefold() in lowered]
        medium = [
            keyword for keyword in levels["medium"] if keyword.casefold() in lowered
        ]
        matches[meeting_type] = {"high": high, "medium": medium}

    high_candidates = [
        (meeting_type, values["high"], values["medium"])
        for meeting_type, values in matches.items()
        if values["high"]
    ]
    if high_candidates:
        meeting_type, high, medium = max(
            high_candidates,
            key=lambda item: (len(item[1]), len(item[2])),
        )
        return (
            meeting_type,
            "high",
            f"发现关键词：{'、'.join([*high, *medium])}",
        )

    medium_candidates = [
        (meeting_type, values["medium"])
        for meeting_type, values in matches.items()
        if values["medium"]
    ]
    if medium_candidates:
        meeting_type, medium = max(medium_candidates, key=lambda item: len(item[1]))
        return meeting_type, "medium", f"发现关键词：{'、'.join(medium)}"

    return "group_meeting", "low", "未发现明确会议类型关键词，默认按组会/周报处理"


def _infer_participants(text: str) -> list[str]:
    participants: list[str] = []
    patterns = [
        r"(说话人\s*\d+)\s*[:：]",
        r"(Speaker\s+[A-Z0-9]+)\s*[:：]",
        r"([A-Za-z][A-Za-z ._-]{1,30})\s*[:：]",
        r"([\u4e00-\u9fff]{1,4}(?:老师|教授|师兄|师姐|学长|学姐))\s*[:：]?",
        r"\[([^\[\]\n]{1,20})\]",
        r"\b(师兄|师姐|学长|学姐)\b",
        r"(小[\u4e00-\u9fff]{1,2}?)(?=你|先|后面|补充|汇报|[:：,，。；;\s])",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text):
            candidate = match.strip()
            if _is_valid_participant(candidate):
                participants.append(candidate)
    return list(dict.fromkeys(participants))


def _infer_topic(text: str) -> str | None:
    patterns = [
        r"(?:主题|议题|topic)\s*[:：]\s*([^\n。；;]{2,60})",
        r"(?:今天|本次)(?:主要)?(?:讨论|汇报)\s*([^\n。；;]{2,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _infer_domain_keywords(text: str, glossary_terms: list[str]) -> list[str]:
    keywords: list[str] = []
    lowered = text.casefold()
    for term in glossary_terms:
        cleaned = term.strip()
        if cleaned and cleaned.casefold() in lowered:
            keywords.append(cleaned)
    for acronym in re.findall(r"\b[A-Z]{2,6}\b", text):
        keywords.append(acronym)
    return list(dict.fromkeys(keywords))


def _detect_language(text: str) -> str:
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_count = len(re.findall(r"[A-Za-z]", text))
    if chinese_count and latin_count:
        return "mixed"
    if chinese_count:
        return "zh"
    if latin_count:
        return "en"
    return "zh"


def _is_valid_participant(candidate: str) -> bool:
    if not candidate:
        return False
    if len(candidate) > 30:
        return False
    blocked = {"主题", "议题", "topic"}
    return candidate not in blocked
