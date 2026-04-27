from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from hypo_research.cli import main


def test_project_create_list_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HYPO_RESEARCH_PROJECTS_DIR", tmp_path.as_posix())
    runner = CliRunner()

    created = runner.invoke(main, ["project", "create", "Cryo Computing", "--direction", "低温 CMOS"])
    listed = runner.invoke(main, ["project", "list"])

    assert created.exit_code == 0
    assert "cryo-computing" in listed.output


def test_project_paper_milestone_meeting_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HYPO_RESEARCH_PROJECTS_DIR", tmp_path.as_posix())
    runner = CliRunner()
    runner.invoke(main, ["project", "create", "Cryo Computing", "--direction", "低温 CMOS"])
    paper = runner.invoke(main, ["project", "paper", "add", "cryo-computing", "近似计算框架", "--slug", "approx", "--venue", "ISCA"])
    update = runner.invoke(main, ["project", "paper", "update", "cryo-computing", "approx", "--stage", "experiment"])
    milestone = runner.invoke(main, ["project", "milestone", "add", "cryo-computing", "完成 ablation", "--paper", "approx"])
    meeting = runner.invoke(main, ["project", "meeting", "add", "cryo-computing", "--text", "导师说：方向OK\nTODO: 补 baseline", "--tag", "advisor"])

    assert paper.exit_code == 0
    assert update.exit_code == 0
    assert "ms-001" in milestone.output
    assert "关键决策：1 条" in meeting.output


def test_project_import_and_context_idea_cli(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HYPO_RESEARCH_PROJECTS_DIR", tmp_path.as_posix())
    monkeypatch.setattr("hypo_research.ideation.strategies.search_literature", lambda *a, **k: None)
    runner = CliRunner()
    runner.invoke(main, ["project", "create", "Cryo Computing", "--direction", "低温 CMOS"])
    runner.invoke(main, ["project", "paper", "add", "cryo-computing", "近似计算框架", "--slug", "approx"])
    survey = tmp_path / "survey.json"
    survey.write_text(json.dumps({"papers": [{"title": "Paper A"}]}), encoding="utf-8")
    imported = runner.invoke(main, ["project", "import", "survey", "cryo-computing", str(survey)])
    idea = runner.invoke(main, ["project", "idea", "cryo-computing", "--paper", "approx", "--num-ideas", "1"])

    assert imported.exit_code == 0
    assert idea.exit_code == 0
    assert "项目上下文" in idea.output
    assert "Paper A" in idea.output or "paper_count" in idea.output


def test_rebuttal_cli(tmp_path: Path) -> None:
    reviews = tmp_path / "reviews.txt"
    reviews.write_text("Reviewer 1:\n- The paper lacks a baseline experiment.", encoding="utf-8")

    result = CliRunner().invoke(main, ["rebuttal", str(reviews)])

    assert result.exit_code == 0
    assert "Dear Area Chair" in result.output
