from __future__ import annotations

from tests.test_ideation_challenge import make_idea

from hypo_research.ideation.experiment import design_experiment
from hypo_research.ideation.planning import create_plan


def test_create_plan_returns_complete_structure(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.experiment.search_literature", lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    idea = make_idea()
    experiment = design_experiment(idea)

    result = create_plan(idea, experiment, venue="ICLR", deadline="2026-09-01")

    assert result.phases
    assert "压缩" in result.total_estimated_time
    sections = {item["section"] for item in result.paper_outline}
    assert {"Introduction", "Related Work", "Method", "Experiments"}.issubset(sections)
