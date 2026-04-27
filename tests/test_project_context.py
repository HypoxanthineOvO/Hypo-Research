from __future__ import annotations

import json
from pathlib import Path

import pytest

from hypo_research.project.context import (
    build_context,
    inject_context_to_challenge,
    inject_context_to_experiment,
    inject_context_to_idea,
    inject_context_to_plan,
)
from hypo_research.project.manager import ProjectManager
from hypo_research.project.meetings import add_meeting
from hypo_research.project.models import IdeaStatus


def setup_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("HYPO_RESEARCH_PROJECTS_DIR", tmp_path.as_posix())
    manager = ProjectManager()
    project = manager.create_project("Cryo Computing", "低温 CMOS 架构加速")
    manager.add_paper(project.slug, "近似计算框架", "approx", venue="ISCA", deadline="2027-01-15")
    survey = tmp_path / "survey.json"
    survey.write_text(json.dumps({"papers": [{"title": "FHE Paper", "year": 2026}]}), encoding="utf-8")
    manager.import_survey(project.slug, survey.as_posix())
    idea_file = tmp_path / "idea.json"
    idea_file.write_text(json.dumps({"title": "Bad Idea", "mode": "quick_win", "strategy": "application"}), encoding="utf-8")
    record = manager.import_idea(project.slug, "approx", idea_file.as_posix())
    project = manager.load_project(project.slug)
    project.papers[0].ideas[0].status = IdeaStatus.REJECTED
    project.papers[0].ideas[0].rejection_reason = "导师说不要做 X 方向"
    manager.save_project(project)
    add_meeting(project.slug, "导师说：方向OK，注意精度损失\nTODO: 下周前完成 ablation", tag="advisor", related_paper="approx")
    return project.slug


def test_build_context_contains_required_information(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = setup_project(tmp_path, monkeypatch)

    context = build_context(slug, "approx")

    assert context["project_direction"] == "低温 CMOS 架构加速"
    assert context["surveys"][0]["paper_count"] == 1
    assert context["literature"][0]["title"] == "FHE Paper"
    assert context["ideas"]["rejected"][0]["title"] == "Bad Idea"
    assert context["meetings"]["key_decisions"]


def test_context_injection_prompts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = setup_project(tmp_path, monkeypatch)
    context = build_context(slug, "approx")

    assert "已否决 ideas" in inject_context_to_idea(context)
    assert "活跃 ideas" in inject_context_to_challenge(context)
    assert "待办 action items" in inject_context_to_experiment(context)
    assert "会议 action items" in inject_context_to_plan(context)
