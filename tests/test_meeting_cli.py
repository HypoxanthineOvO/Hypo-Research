"""CLI tests for meeting and glossary commands."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from hypo_research.cli import main


def test_meeting_list_templates() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["meeting", "--list-templates"])

    assert result.exit_code == 0
    assert "group_meeting" in result.output
    assert "advisor_meeting" in result.output


def test_meeting_basic_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    transcript = tmp_path / "transcript.txt"
    transcript.write_text("今天讨论 CKKS 和 XYZ。", encoding="utf-8")
    output = tmp_path / "minutes.md"
    runner = CliRunner()

    add_result = runner.invoke(
        main,
        [
            "glossary",
            "add",
            "--keyword",
            "CKKS",
            "--canonical",
            "CKKS 方案",
            "--aliases",
            "ckks",
            "--category",
            "crypto",
        ],
    )
    assert add_result.exit_code == 0

    result = runner.invoke(
        main,
        [
            "meeting",
            str(transcript),
            "--type",
            "group_meeting",
            "--participants",
            "张老师,小明",
            "--topic",
            "第 5 周组会",
            "--date",
            "2026-04-26",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "CKKS 方案" in content
    assert "XYZ" in result.output


def test_glossary_add_list_search_remove(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()

    add_result = runner.invoke(
        main,
        [
            "glossary",
            "add",
            "--keyword",
            "bootstrapping",
            "--canonical",
            "Bootstrapping（自举）",
            "--aliases",
            "自举,boot",
            "--category",
            "crypto",
        ],
    )
    assert add_result.exit_code == 0

    list_result = runner.invoke(main, ["glossary", "list", "--category", "crypto"])
    assert list_result.exit_code == 0
    assert "bootstrapping" in list_result.output

    search_result = runner.invoke(main, ["glossary", "search", "boot"])
    assert search_result.exit_code == 0
    assert "Bootstrapping" in search_result.output

    remove_result = runner.invoke(
        main,
        ["glossary", "remove", "--keyword", "bootstrapping"],
    )
    assert remove_result.exit_code == 0

    list_after_remove = runner.invoke(main, ["glossary", "list"])
    assert list_after_remove.exit_code == 0
    assert "No glossary terms found." in list_after_remove.output
