from __future__ import annotations

from tests.test_ideation_challenge import make_idea

from hypo_research.ideation.experiment import design_experiment


def test_design_experiment_returns_complete_structure(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.experiment.search_literature", lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))

    result = design_experiment(make_idea(), venue="ACL")

    assert result.idea_title
    assert len(result.baselines) >= 1
    assert len(result.datasets) >= 2
    assert result.ablation_studies
    assert result.venue_requirements and "ACL" in result.venue_requirements
