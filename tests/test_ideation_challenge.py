from __future__ import annotations

from hypo_research.ideation.challenge import build_challenge_prompt, challenge_idea
from hypo_research.ideation.models import ChallengeSeverity, IdeaMode, IdeaScore, IdeaStrategy, ResearchIdea
from hypo_research.review.literature import LiteratureContext, LiteratureReference


def make_idea() -> ResearchIdea:
    return ResearchIdea(
        "Idea",
        IdeaMode.AMBITIOUS,
        IdeaStrategy.GAP_ANALYSIS,
        "Question",
        "Motivation",
        "Method",
        ["Contribution"],
        "Feasible",
        ["Risk"],
        [],
        IdeaScore(0.7, 0.7, 0.6, 0.8, [], 0.7, "不错的工作", "", []),
    )


def fake_literature(*args, **kwargs) -> LiteratureContext:
    return LiteratureContext(
        ["idea"],
        [LiteratureReference("Collision Paper", ["Alice"], "ICLR", 2025, "abstract", 12, "p1", False)],
        "now",
        (2023, 2026),
        "Idea",
    )


def test_challenge_has_five_dimensions(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.challenge.search_literature", fake_literature)

    result = challenge_idea(make_idea())

    assert {q.dimension for q in result.questions} == {"novelty", "feasibility", "significance", "methodology", "assumption"}


def test_severity_prompt_changes_persona() -> None:
    gentle = build_challenge_prompt(make_idea(), ChallengeSeverity.GENTLE)
    harsh = build_challenge_prompt(make_idea(), ChallengeSeverity.HARSH)

    assert "娄萌萌" not in gentle
    assert "娄萌萌" in harsh


def test_verdict_is_limited(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.challenge.search_literature", fake_literature)

    result = challenge_idea(make_idea())

    assert result.verdict in {"值得做", "需要重大修改", "建议放弃"}
    assert result.score_after_challenge.total_score >= 0


def test_challenge_calls_search(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_search(*args, **kwargs):
        calls["count"] += 1
        return fake_literature()

    monkeypatch.setattr("hypo_research.ideation.challenge.search_literature", fake_search)

    challenge_idea(make_idea())

    assert calls["count"] == 1
