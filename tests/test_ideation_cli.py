from __future__ import annotations

import json

from click.testing import CliRunner

from hypo_research.cli import main


def test_idea_command_mode_and_output(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.strategies.search_literature", lambda *a, **k: None)
    runner = CliRunner()

    result = runner.invoke(main, ["idea", "graph learning", "--mode", "quick_win", "--num-ideas", "1", "--output", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["quick_win_ideas"]
    assert payload["ambitious_ideas"] == []


def test_challenge_command_severity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.challenge.search_literature", lambda *a, **k: None)
    idea_file = tmp_path / "idea.json"
    idea_file.write_text(
        json.dumps(
            {
                "title": "Idea",
                "mode": "quick_win",
                "strategy": "problem_variant",
                "research_question": "Question",
                "score": {"total_score": 0.5},
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["challenge", str(idea_file), "--severity", "gentle"])

    assert result.exit_code == 0
    assert "Idea 拷打结果" in result.output


def test_experiment_plan_pilot_commands_parse(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.experiment.search_literature", lambda *a, **k: None)
    monkeypatch.setattr("hypo_research.ideation.strategies.search_literature", lambda *a, **k: None)
    monkeypatch.setattr("hypo_research.ideation.challenge.search_literature", lambda *a, **k: None)
    idea_file = tmp_path / "idea.txt"
    idea_file.write_text("A new idea\nDetails", encoding="utf-8")
    runner = CliRunner()

    assert runner.invoke(main, ["experiment", str(idea_file), "--venue", "ICLR"]).exit_code == 0
    assert runner.invoke(main, ["plan", str(idea_file), "--deadline", "2026-09-01"]).exit_code == 0
    pilot = runner.invoke(main, ["pilot", "graph learning", "--auto-select", "--output", "markdown"])
    assert pilot.exit_code == 0
    assert "娄萌萌" in pilot.output
