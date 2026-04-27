from __future__ import annotations

from hypo_research.ideation.pilot import run_pilot
from hypo_research.review.literature import LiteratureContext


def test_run_pilot_returns_complete_report(monkeypatch) -> None:
    monkeypatch.setattr(
        "hypo_research.ideation.strategies.search_literature",
        lambda *a, **k: LiteratureContext(["x"], [], "now", (2023, 2026), "x"),
    )
    monkeypatch.setattr(
        "hypo_research.ideation.challenge.search_literature",
        lambda *a, **k: LiteratureContext(["x"], [], "now", (2023, 2026), "x"),
    )
    monkeypatch.setattr(
        "hypo_research.ideation.experiment.search_literature",
        lambda *a, **k: LiteratureContext(["x"], [], "now", (2023, 2026), "x"),
    )

    result = run_pilot("scientific retrieval", auto_select=True)

    assert result.selected_idea.score.total_score == max(
        [idea.score.total_score for idea in result.ideas.quick_win_ideas + result.ideas.ambitious_ideas]
    )
    assert result.mentor_comments
    assert result.experiment.baselines
