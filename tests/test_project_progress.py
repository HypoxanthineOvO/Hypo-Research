from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from hypo_research.project.manager import ProjectManager
from hypo_research.project.models import Milestone, PaperConfig, PaperStage
from hypo_research.project.progress import add_milestone, complete_milestone, compute_paper_progress, days_to_date


def test_compute_paper_progress_percentage() -> None:
    paper = PaperConfig(
        slug="approx",
        title="Paper",
        stage=PaperStage.EXPERIMENT,
        milestones=[Milestone("ms-001", "完成 pilot", done=True)],
    )

    progress = compute_paper_progress(paper)

    assert progress["stage"] == "experiment"
    assert progress["percentage"] >= 25


def test_milestone_crud_and_overdue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPO_RESEARCH_PROJECTS_DIR", tmp_path.as_posix())
    manager = ProjectManager()
    project = manager.create_project("Cryo Computing", "方向")
    manager.add_paper(project.slug, "Paper", "approx")

    overdue_date = (date.today() - timedelta(days=1)).isoformat()
    milestone = add_milestone(project.slug, "approx", "完成 ablation", overdue_date)
    loaded = manager.load_project(project.slug)

    assert loaded.papers[0].milestones[0].id == milestone.id
    assert compute_paper_progress(loaded.papers[0])["milestones"]["overdue"] == 1
    complete_milestone(project.slug, milestone.id, "done")
    assert manager.load_project(project.slug).papers[0].milestones[0].done is True


def test_days_to_deadline() -> None:
    future = (date.today() + timedelta(days=7)).isoformat()

    assert days_to_date(future) == 7
