from __future__ import annotations

from hypo_research.ideation.models import IdeaMode, IdeaStrategy
from hypo_research.ideation.strategies import build_strategy_prompt, generate_ideas
from hypo_research.review.literature import LiteratureContext, LiteratureReference


def fake_literature(*args, **kwargs) -> LiteratureContext:
    return LiteratureContext(
        query_terms=["retrieval"],
        references=[
            LiteratureReference("A Retrieval Paper", ["Alice"], "ACL", 2025, "abstract", 10, "p1", False),
            LiteratureReference("A Planning Paper", ["Bob"], "NeurIPS", 2024, "abstract", 8, "p2", False),
        ],
        search_timestamp="2026-04-27T00:00:00",
        year_range=(2023, 2026),
        paper_title="retrieval",
    )


def test_generate_ideas_outputs_both_modes(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.strategies.search_literature", fake_literature)

    result = generate_ideas("scientific literature retrieval", num_ideas=2)

    assert len(result.quick_win_ideas) == 2
    assert len(result.ambitious_ideas) == 2


def test_generate_ideas_specific_mode(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.ideation.strategies.search_literature", fake_literature)

    result = generate_ideas("scientific literature retrieval", mode=IdeaMode.QUICK_WIN, num_ideas=2)

    assert result.quick_win_ideas
    assert result.ambitious_ideas == []


def test_each_strategy_prompt_contains_direction() -> None:
    for strategy in IdeaStrategy:
        prompt = build_strategy_prompt(strategy, "graph learning")
        assert "graph learning" in prompt
        assert "策略" in prompt


def test_no_papers_calls_search(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_search(*args, **kwargs):
        calls["count"] += 1
        return fake_literature()

    monkeypatch.setattr("hypo_research.ideation.strategies.search_literature", fake_search)

    generate_ideas("new direction", num_ideas=1)

    assert calls["count"] == 1
