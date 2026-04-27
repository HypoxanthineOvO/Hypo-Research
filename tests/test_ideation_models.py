from __future__ import annotations

from dataclasses import asdict

from hypo_research.ideation.models import (
    ChallengeSeverity,
    IdeaMode,
    IdeaScore,
    IdeaScorePenalty,
    IdeaStrategy,
    ResearchIdea,
)
from hypo_research.ideation.scoring import compute_total_score, determine_tier


def test_ideation_enums_values() -> None:
    assert IdeaMode.QUICK_WIN.value == "quick_win"
    assert IdeaStrategy.PARADIGM_CHALLENGE.value == "paradigm_challenge"
    assert ChallengeSeverity.HARSH.value == "harsh"


def test_research_idea_dataclass_serializes() -> None:
    idea = ResearchIdea(
        title="Idea",
        mode=IdeaMode.AMBITIOUS,
        strategy=IdeaStrategy.GAP_ANALYSIS,
        research_question="Question",
        motivation="Motivation",
        method_sketch="Method",
        expected_contribution=["C1"],
        feasibility_analysis="Feasible",
        risk_factors=["Risk"],
        related_papers=["Paper"],
        score=IdeaScore(0.8, 0.7, 0.6, 0.9, [IdeaScorePenalty("novelty", 0.1, "reason")], 0.73, "不错的工作", "summary", []),
    )

    payload = asdict(idea)

    assert payload["title"] == "Idea"
    assert payload["score"]["adjustments"][0]["dimension"] == "novelty"


def test_total_score_weights_differ_by_mode() -> None:
    scores = {"novelty": 1.0, "significance": 0.5, "feasibility": 0.0, "clarity": 0.5}

    ambitious = compute_total_score(scores, IdeaMode.AMBITIOUS)
    quick = compute_total_score(scores, IdeaMode.QUICK_WIN)

    assert ambitious > quick


def test_determine_tier_boundaries() -> None:
    assert determine_tier(0.8) == "顶会冲刺"
    assert determine_tier(0.6) == "不错的工作"
    assert determine_tier(0.4) == "快速产出"
    assert determine_tier(0.39) == "需要加强"
