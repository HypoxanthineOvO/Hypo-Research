from __future__ import annotations

from pathlib import Path

import pytest

from hypo_research.project.dashboard import render_dashboard
from hypo_research.project.manager import ProjectManager
from hypo_research.project.meetings import add_meeting
from hypo_research.project.progress import add_milestone


def setup_dashboard_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("HYPO_RESEARCH_PROJECTS_DIR", tmp_path.as_posix())
    manager = ProjectManager()
    project = manager.create_project("Cryo Computing", "方向")
    manager.add_paper(project.slug, "近似计算框架", "approx", venue="ISCA", deadline="2027-01-15")
    add_milestone(project.slug, "approx", "完成 ablation", "2027-01-01")
    add_meeting(project.slug, "导师说：方向OK\nTODO: 找代码", tag="advisor", related_paper="approx")
    return project.slug


def test_render_dashboard_full_and_brief(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = setup_dashboard_project(tmp_path, monkeypatch)

    full = render_dashboard(slug)
    brief = render_dashboard(slug, brief=True)

    assert "项目：Cryo Computing" in full
    assert "最近会议决策" in full
    assert "Survey" not in brief


def test_render_dashboard_single_paper_and_milestones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slug = setup_dashboard_project(tmp_path, monkeypatch)

    single = render_dashboard(slug, paper_slug="approx")
    milestones = render_dashboard(slug, milestones_only=True)

    assert "近似计算框架" in single
    assert "完成 ablation" in milestones
