"""Tests for review revision roadmap prompts."""

from __future__ import annotations

import pytest

from hypo_research.review.parser import PaperStructure
from hypo_research.review.report import MetaReview, RevisionItem, SingleReview
from hypo_research.review.reviewers import Severity, get_revision_roadmap_prompt


def paper() -> PaperStructure:
    return PaperStructure(
        title="Roadmap Paper",
        abstract="We propose a method.",
        sections=[],
        figures=[],
        tables=[],
        equations_count=0,
        references=[],
        claims=[],
        word_count=4,
        page_count=None,
        raw_text="We propose a method.",
        source_type="latex",
        inferred_domain=None,
    )


def meta_review() -> MetaReview:
    return MetaReview(
        ac_name="贺云翔",
        ac_emoji="🏛️",
        consensus_summary="共识",
        key_disagreements=[],
        final_recommendation="Borderline",
        recommendation_reasoning="理由",
        actionable_priorities=["补充 Section 4 实验"],
        confidence=4,
    )


def reviews() -> list[SingleReview]:
    return [
        SingleReview("lichaofan", "李超凡", "🔬", "Expert-1", "标准版", "需要补实验", weaknesses=["[Major] Section 4 缺少 baseline"])
    ]


def test_revision_roadmap_prompt_contains_mentor_principles() -> None:
    prompt = get_revision_roadmap_prompt(paper(), reviews(), meta_review(), Severity.STANDARD)

    assert "导师视角原则" in prompt
    assert "站在作者一边" in prompt


def test_revision_roadmap_prompt_contains_meta_final_recommendation() -> None:
    prompt = get_revision_roadmap_prompt(paper(), reviews(), meta_review(), Severity.STANDARD)

    assert "最终建议：Borderline" in prompt
    assert "补充 Section 4 实验" in prompt


def test_revision_roadmap_prompt_contains_concerns_table_format() -> None:
    prompt = get_revision_roadmap_prompt(paper(), reviews(), meta_review(), Severity.HARSH)

    assert "问题交叉矩阵" in prompt
    assert "Novelty / Experiments / Writing / Reproducibility" in prompt


def test_revision_item_priority_allows_only_three_values() -> None:
    RevisionItem("🔴 必须修改", "x", "p", "s", "1 天", [])
    RevisionItem("🟡 建议修改", "x", "p", "s", "1 天", [])
    RevisionItem("⚪ 可以忽略", "x", "p", "s", "1 天", [])
    with pytest.raises(ValueError):
        RevisionItem("必须改", "x", "p", "s", "1 天", [])
