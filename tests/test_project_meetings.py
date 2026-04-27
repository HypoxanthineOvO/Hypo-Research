from __future__ import annotations

from pathlib import Path

import pytest

from hypo_research.project.manager import ProjectManager
from hypo_research.project.meetings import add_meeting, extract_meeting_items, get_meeting_context, list_meetings


def test_add_meeting_saves_file_and_updates_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPO_RESEARCH_PROJECTS_DIR", tmp_path.as_posix())
    manager = ProjectManager()
    project = manager.create_project("Cryo Computing", "方向")
    manager.add_paper(project.slug, "Paper", "approx")

    note = add_meeting(project.slug, "导师说：方向OK\nAction: 补充 baseline", tag="advisor", related_paper="approx")

    assert (tmp_path / project.slug / note.source_file).exists()
    assert manager.load_project(project.slug).meetings[0].id == note.id
    assert note.key_decisions
    assert note.action_items


def test_extract_key_decisions_and_action_items() -> None:
    extracted = extract_meeting_items("决定：不要做 X 方向\nTODO: 下周前完成 ablation")

    assert extracted["key_decisions"] == ["不要做 X 方向"]
    assert extracted["action_items"] == ["下周前完成 ablation"]


def test_list_meetings_filters_and_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HYPO_RESEARCH_PROJECTS_DIR", tmp_path.as_posix())
    manager = ProjectManager()
    project = manager.create_project("Cryo Computing", "方向")
    manager.add_paper(project.slug, "Paper", "approx")
    add_meeting(project.slug, "导师说：方向OK", tag="advisor", related_paper="approx")
    add_meeting(project.slug, "组会：补充实验", tag="group")

    assert len(list_meetings(project.slug, tag="advisor")) == 1
    assert len(list_meetings(project.slug, paper_slug="approx")) == 1
    assert get_meeting_context(project.slug)["key_decisions"][0]["source"] == "advisor"
