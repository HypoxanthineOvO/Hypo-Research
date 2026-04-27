from __future__ import annotations

from hypo_research.ideation.models import IdeaMode, IdeaScore, IdeaStrategy, ResearchIdea
from hypo_research.ideation.scoring import compute_total_score, determine_tier, score_idea


def make_idea(mode: IdeaMode = IdeaMode.AMBITIOUS) -> ResearchIdea:
    return ResearchIdea(
        title="Adaptive Retrieval for Scientific Literature Review",
        mode=mode,
        strategy=IdeaStrategy.GAP_ANALYSIS,
        research_question="How can retrieval adapt to scientific review gaps?",
        motivation="Important gap.",
        method_sketch="A retrieval planner.",
        expected_contribution=["New formulation", "Benchmark"],
        feasibility_analysis="Feasible",
        risk_factors=["Similarity"],
        related_papers=["Paper"],
        score=IdeaScore(0, 0, 0, 0, [], 0, "需要加强", "", []),
    )


def test_score_idea_returns_complete_score() -> None:
    score = score_idea(make_idea(), [])

    assert 0 <= score.total_score <= 1
    assert score.tier in {"顶会冲刺", "不错的工作", "快速产出", "需要加强"}
    assert score.summary


def test_similar_work_penalizes_novelty() -> None:
    score = score_idea(make_idea(), [{"title": "Adaptive Retrieval for Scientific Literature Review", "abstract": ""}])

    assert any(item.dimension == "novelty" and item.delta < 0 for item in score.adjustments)


def test_ambitious_weights_novelty_more_than_quick_win() -> None:
    scores = {"novelty": 0.9, "significance": 0.5, "feasibility": 0.2, "clarity": 0.5}

    assert compute_total_score(scores, IdeaMode.AMBITIOUS) > compute_total_score(scores, IdeaMode.QUICK_WIN)


def test_tier_logic() -> None:
    assert determine_tier(0.81) == "顶会冲刺"
