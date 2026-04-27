"""Tests for simulated reviewer configuration."""

from __future__ import annotations

from hypo_research.review.parser import PaperStructure
from hypo_research.review.report import SingleReview
from hypo_research.review.reviewers import (
    ACTIONABLE_FEEDBACK_REQUIREMENT,
    DEFAULT_PANEL,
    FULL_PANEL,
    REVIEWERS,
    Severity,
    get_meta_review_prompt,
    get_reviewer_prompt,
)


def paper() -> PaperStructure:
    return PaperStructure(
        title="Paper",
        abstract="We propose a method.",
        sections=[],
        figures=[],
        tables=[],
        equations_count=0,
        references=[],
        claims=["We propose a method."],
        word_count=4,
        page_count=None,
        raw_text="We propose a method.",
        source_type="latex",
        inferred_domain="EDA",
    )


def test_seven_reviewers_are_configured() -> None:
    assert len(REVIEWERS) == 7
    for reviewer in REVIEWERS.values():
        assert reviewer.id
        assert reviewer.name
        assert reviewer.role
        assert reviewer.personality
        assert reviewer.focus_areas


def test_default_and_full_panels() -> None:
    assert DEFAULT_PANEL == ["heyunxiang", "lichaofan", "chenquanyu", "jiangye"]
    assert len(FULL_PANEL) == 7


def test_prompt_contains_role_personality_and_venue() -> None:
    reviewer = REVIEWERS["lichaofan"]
    prompt = get_reviewer_prompt(reviewer, Severity.STANDARD, paper(), venue="dac")

    assert "李超凡" in prompt
    assert "【真实审稿风格参考】" in prompt
    assert "DAC" in prompt
    assert "Summary" in prompt


def test_severity_changes_prompt_text() -> None:
    reviewer = REVIEWERS["heyunxiang"]
    gentle = get_reviewer_prompt(reviewer, Severity.GENTLE, paper())
    standard = get_reviewer_prompt(reviewer, Severity.STANDARD, paper())
    harsh = get_reviewer_prompt(reviewer, Severity.HARSH, paper())

    assert "温和版" in gentle
    assert "标准版" in standard
    assert "地狱版" in harsh
    assert gentle != harsh


def test_reviewer_personality_contains_real_review_style_reference() -> None:
    for reviewer in REVIEWERS.values():
        assert "【真实审稿风格参考】" in reviewer.personality


def test_harsh_prompt_includes_harsh_extra_but_standard_and_gentle_do_not() -> None:
    reviewer = REVIEWERS["heyunxiang"]

    assert "【地狱版👹额外特征】" in get_reviewer_prompt(reviewer, Severity.HARSH, paper())
    assert "【地狱版👹额外特征】" not in get_reviewer_prompt(reviewer, Severity.STANDARD, paper())
    assert "【地狱版👹额外特征】" not in get_reviewer_prompt(reviewer, Severity.GENTLE, paper())


def test_actionable_feedback_requirement_is_in_all_prompts() -> None:
    for reviewer in REVIEWERS.values():
        prompt = get_reviewer_prompt(reviewer, Severity.STANDARD, paper())
        assert ACTIONABLE_FEEDBACK_REQUIREMENT.strip() in prompt


def test_prompt_includes_venue_review_style() -> None:
    prompt = get_reviewer_prompt(REVIEWERS["lichaofan"], Severity.STANDARD, paper(), venue="dac")

    assert "目标 Venue 的审稿文化" in prompt
    assert "runtime 和 scalability" in prompt


def test_meta_review_prompt_includes_all_reviews() -> None:
    reviews = [
        SingleReview("a", "Alice", "🔬", "Expert", "标准版", "Alice summary", score=6, decision="Borderline"),
        SingleReview("b", "Bob", "🤔", "Related", "标准版", "Bob summary", score=7, decision="Accept"),
    ]

    prompt = get_meta_review_prompt(paper(), reviews, Severity.STANDARD, venue="dac")

    assert "Alice summary" in prompt
    assert "Bob summary" in prompt
    assert "AC 决策原则" in prompt
