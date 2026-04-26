"""Tests for simulated reviewer configuration."""

from __future__ import annotations

from hypo_research.review.parser import PaperStructure
from hypo_research.review.reviewers import DEFAULT_PANEL, FULL_PANEL, REVIEWERS, Severity, get_reviewer_prompt


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
    prompt = get_reviewer_prompt(reviewer, Severity.STANDARD, paper(), venue="DAC")

    assert "李超凡" in prompt
    assert reviewer.personality in prompt
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
