"""Scoring framework for research ideas."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from hypo_research.ideation.models import IdeaMode, IdeaScore, IdeaScorePenalty, ResearchIdea


SCORING_PROMPT = """
你是一个科研项目评审专家。请对以下研究 idea 进行评分。

评分维度包括 Novelty、Significance、Feasibility、Clarity，每项 0.0-1.0。
请结合文献上下文列出加扣分项、综合 tier 和改进建议。
"""

LITERATURE_ADJUSTMENT_RULES = [
    {"condition": "高度相似工作", "adjustment": "novelty -0.3"},
    {"condition": "类似工作存在但方法不同", "adjustment": "novelty -0.1"},
    {"condition": "SOTA 接近上限", "adjustment": "significance -0.2"},
    {"condition": "大量计算资源", "adjustment": "feasibility -0.2"},
    {"condition": "未发现直接竞争工作", "adjustment": "novelty +0.1"},
    {"condition": "挑战主流假设", "adjustment": "novelty +0.3"},
]


def compute_total_score(scores: dict[str, float], mode: IdeaMode) -> float:
    """Compute weighted total score for an idea."""
    if mode == IdeaMode.AMBITIOUS:
        weights = {"novelty": 0.35, "significance": 0.30, "feasibility": 0.20, "clarity": 0.15}
    else:
        weights = {"novelty": 0.15, "significance": 0.20, "feasibility": 0.40, "clarity": 0.25}
    return round(sum(_clamp(scores[k]) * w for k, w in weights.items()), 3)


def determine_tier(total_score: float) -> str:
    """Map total score to a Chinese research tier."""
    if total_score >= 0.8:
        return "顶会冲刺"
    if total_score >= 0.6:
        return "不错的工作"
    if total_score >= 0.4:
        return "快速产出"
    return "需要加强"


def score_idea(
    idea: ResearchIdea,
    literature_results: list[dict] | None = None,
) -> IdeaScore:
    """Score an idea with deterministic heuristics and literature adjustments."""
    scores = _base_scores(idea)
    adjustments: list[IdeaScorePenalty] = []

    similar = _most_similar_paper(idea, literature_results or [])
    if similar is not None:
        title, similarity = similar
        if similarity > 0.8:
            adjustments.append(
                IdeaScorePenalty("novelty", -0.3, f"发现高度相似工作：{title}", title)
            )
        elif similarity > 0.55:
            adjustments.append(
                IdeaScorePenalty("novelty", -0.1, f"问题已有类似工作，但方法仍可区分：{title}", title)
            )
    elif literature_results is not None:
        adjustments.append(IdeaScorePenalty("novelty", 0.1, "检索未发现直接竞争工作", None))

    lower_text = " ".join(
        [idea.title, idea.research_question, idea.motivation, idea.method_sketch]
    ).lower()
    if idea.strategy.value in {"paradigm_challenge", "contradiction"} or "assumption" in lower_text:
        adjustments.append(IdeaScorePenalty("novelty", 0.2, "该 idea 触及主流假设或矛盾消解", None))
    if "large-scale" in lower_text or "大模型" in lower_text or "大量" in lower_text:
        adjustments.append(IdeaScorePenalty("feasibility", -0.15, "可能需要较高计算或数据资源", None))

    for adjustment in adjustments:
        if adjustment.dimension in scores:
            scores[adjustment.dimension] = _clamp(scores[adjustment.dimension] + adjustment.delta)

    total = compute_total_score(scores, idea.mode)
    tier = determine_tier(total)
    suggestions = _suggestions(scores, idea, adjustments)
    return IdeaScore(
        novelty=scores["novelty"],
        significance=scores["significance"],
        feasibility=scores["feasibility"],
        clarity=scores["clarity"],
        adjustments=adjustments,
        total_score=total,
        tier=tier,
        summary=f"综合评分 {total:.2f}，定位为“{tier}”。",
        suggestions=suggestions,
    )


def _base_scores(idea: ResearchIdea) -> dict[str, float]:
    if idea.mode == IdeaMode.AMBITIOUS:
        novelty = 0.72
        significance = 0.72
        feasibility = 0.58
    else:
        novelty = 0.46
        significance = 0.55
        feasibility = 0.78
    clarity = 0.72
    if len(idea.expected_contribution) >= 2:
        clarity += 0.06
    if len(idea.risk_factors) >= 2:
        feasibility -= 0.05
    if idea.related_papers:
        significance += 0.04
    return {
        "novelty": _clamp(novelty),
        "significance": _clamp(significance),
        "feasibility": _clamp(feasibility),
        "clarity": _clamp(clarity),
    }


def _most_similar_paper(idea: ResearchIdea, literature_results: list[dict]) -> tuple[str, float] | None:
    best: tuple[str, float] | None = None
    idea_text = f"{idea.title} {idea.research_question}".lower()
    for paper in literature_results:
        title = str(_field(paper, "title") or "")
        if not title:
            continue
        abstract = str(_field(paper, "abstract") or "")
        similarity = max(
            SequenceMatcher(None, idea.title.lower(), title.lower()).ratio(),
            SequenceMatcher(None, idea_text, f"{title} {abstract}".lower()).ratio(),
        )
        if best is None or similarity > best[1]:
            best = (title, similarity)
    return best


def _field(item: dict | Any, name: str) -> Any:
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _suggestions(
    scores: dict[str, float],
    idea: ResearchIdea,
    adjustments: list[IdeaScorePenalty],
) -> list[str]:
    suggestions: list[str] = []
    if scores["novelty"] < 0.6:
        suggestions.append("进一步明确与最近相似工作的区别，避免只停留在换数据集或加模块。")
    if scores["feasibility"] < 0.6:
        suggestions.append("先做最小可行实验，并准备资源不足时的简化方案。")
    if scores["clarity"] < 0.7:
        suggestions.append("把 research question、核心假设和贡献边界写得更具体。")
    if not idea.related_papers:
        suggestions.append("补充 3-5 篇直接相关论文作为 novelty 和 baseline 依据。")
    if any(item.delta < 0 for item in adjustments):
        suggestions.append("针对扣分项补做对比实验或重构问题表述。")
    return suggestions or ["当前方向可以推进，下一步应优先补强实验设计和竞争工作分析。"]


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)
