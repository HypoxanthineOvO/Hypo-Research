from __future__ import annotations

import json
from pathlib import Path

import pytest

from hypo_research.project.manager import ProjectManager
from hypo_research.project.models import IdeaStatus, PaperStage, ProjectStage


def test_create_project_creates_directory_structure(tmp_path: Path) -> None:
    manager = ProjectManager(tmp_path)

    project = manager.create_project("Cryo Computing", "低温 CMOS 架构加速")

    project_dir = tmp_path / project.slug
    assert (project_dir / "project.json").exists()
    assert (project_dir / "surveys").is_dir()
    assert (project_dir / "literature" / "papers.json").exists()
    assert (project_dir / "papers").is_dir()


def test_load_project_from_filesystem(tmp_path: Path) -> None:
    manager = ProjectManager(tmp_path)
    created = manager.create_project("Cryo Computing", "方向")

    loaded = manager.load_project(created.slug)

    assert loaded.name == "Cryo Computing"
    assert loaded.stage == ProjectStage.EXPLORATION


def test_add_and_update_paper(tmp_path: Path) -> None:
    manager = ProjectManager(tmp_path)
    project = manager.create_project("Cryo Computing", "方向")

    paper = manager.add_paper(project.slug, "近似计算框架", "approx", venue="ISCA", deadline="2027-01-15")
    updated = manager.update_paper(project.slug, paper.slug, stage="experiment")

    assert (tmp_path / project.slug / "papers" / "approx" / "paper.json").exists()
    assert updated.stage == PaperStage.EXPERIMENT
    assert manager.load_project(project.slug).papers[0].target_venue == "ISCA"


def test_import_survey_and_idea(tmp_path: Path) -> None:
    manager = ProjectManager(tmp_path)
    project = manager.create_project("Cryo Computing", "方向")
    manager.add_paper(project.slug, "近似计算框架", "approx")
    survey = tmp_path / "survey.json"
    survey.write_text(json.dumps({"papers": [{"title": "Paper A", "year": 2026}]}), encoding="utf-8")
    idea_file = tmp_path / "idea.json"
    idea_file.write_text(
        json.dumps(
            {
                "quick_win_ideas": [
                    {"title": "Idea A", "strategy": "dataset_transfer", "mode": "quick_win", "score": {"total_score": 0.7, "tier": "不错的工作"}}
                ]
            }
        ),
        encoding="utf-8",
    )

    survey_dest = manager.import_survey(project.slug, survey.as_posix())
    idea = manager.import_idea(project.slug, "approx", idea_file.as_posix())

    assert survey_dest.endswith("survey.json")
    assert json.loads((tmp_path / project.slug / "literature" / "papers.json").read_text(encoding="utf-8"))[0]["title"] == "Paper A"
    assert idea.title == "Idea A"
    assert idea.status == IdeaStatus.CANDIDATE


def test_import_challenge_archive_delete(tmp_path: Path) -> None:
    manager = ProjectManager(tmp_path)
    project = manager.create_project("Cryo Computing", "方向")
    manager.add_paper(project.slug, "近似计算框架", "approx")
    idea_file = tmp_path / "idea.json"
    idea_file.write_text(json.dumps({"title": "Idea", "mode": "quick_win", "strategy": "problem_variant"}), encoding="utf-8")
    idea = manager.import_idea(project.slug, "approx", idea_file.as_posix())
    challenge = tmp_path / "challenge.json"
    challenge.write_text(json.dumps({"verdict": "建议放弃"}), encoding="utf-8")

    manager.import_challenge(project.slug, "approx", idea.id, challenge.as_posix())
    manager.archive_project(project.slug)

    loaded = manager.load_project(project.slug)
    assert loaded.stage == ProjectStage.ARCHIVED
    assert loaded.papers[0].ideas[0].status == IdeaStatus.REJECTED
    with pytest.raises(ValueError):
        manager.delete_project(project.slug)
    manager.delete_project(project.slug, confirm=True)
    assert not (tmp_path / project.slug).exists()
