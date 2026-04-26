"""Tests for meeting templates."""

from __future__ import annotations

from hypo_research.meeting.templates import get_template, list_templates


def test_get_template_returns_named_template() -> None:
    template = get_template("paper_discussion")
    assert template.name == "paper_discussion"
    assert "论文讨论" in template.skeleton


def test_list_templates_contains_five_types() -> None:
    names = list_templates()
    assert names == [
        "group_meeting",
        "paper_discussion",
        "project_discussion",
        "consultation",
        "advisor_meeting",
    ]


def test_get_template_fallback_to_group_meeting() -> None:
    template = get_template("missing")
    assert template.name == "group_meeting"
