"""Full ideation pipeline with mentor persona."""

from __future__ import annotations

from dataclasses import replace

from hypo_research.ideation.challenge import challenge_idea
from hypo_research.ideation.experiment import design_experiment
from hypo_research.ideation.models import ChallengeSeverity, PilotReport, ResearchIdea
from hypo_research.ideation.planning import create_plan
from hypo_research.ideation.scoring import score_idea
from hypo_research.ideation.strategies import generate_ideas


MENTOR_PERSONA = {
    "name": "娄萌萌",
    "alias": "hypo-pilot",
    "personality": "严厉但有建设性的科研导师。好的科研不是做得多，是想得清楚。",
}

MENTOR_SUMMARY_PROMPT = """
你是娄萌萌，一位严厉但有建设性的科研导师。请对 idea、拷打结果、实验设计和工作规划给出综合评语。
"""


def run_pilot(
    direction: str,
    papers: list[str] | None = None,
    survey_output: str | None = None,
    constraints: str | None = None,
    venue: str | None = None,
    deadline: str | None = None,
    resources: str | None = None,
    challenge_severity: ChallengeSeverity = ChallengeSeverity.HARSH,
    auto_select: bool = False,
) -> PilotReport:
    """Run idea generation, challenge, refinement, experiment design, and planning."""
    ideas = generate_ideas(direction, papers, survey_output, constraints)
    selected = _select_idea(ideas.quick_win_ideas + ideas.ambitious_ideas, auto_select=auto_select)
    challenge = challenge_idea(selected, challenge_severity)
    refined = _refine_idea(selected, challenge.reinforcement_plan)
    refined.score = score_idea(refined)
    experiment = design_experiment(refined, venue=venue, constraints=constraints)
    plan = create_plan(refined, experiment, venue=venue, deadline=deadline, resources=resources)
    return PilotReport(
        ideas=ideas,
        selected_idea=selected,
        challenge=challenge,
        refined_idea=refined,
        experiment=experiment,
        plan=plan,
        mentor_comments=_mentor_comments(refined, challenge, venue),
    )


def _select_idea(candidates: list[ResearchIdea], auto_select: bool) -> ResearchIdea:
    if not candidates:
        raise ValueError("没有生成候选 idea，无法继续 pilot 流程。")
    if auto_select:
        return max(candidates, key=lambda item: item.score.total_score)
    return candidates[0]


def _refine_idea(idea: ResearchIdea, reinforcement_plan: list[str]) -> ResearchIdea:
    return replace(
        idea,
        title=f"{idea.title}（加固版）",
        motivation=f"{idea.motivation} 拷打后加固重点：{reinforcement_plan[0]}",
        method_sketch=f"{idea.method_sketch} 同时加入强 baseline 对比、失败案例分析和关键假设验证。",
        expected_contribution=[*idea.expected_contribution, "明确 novelty 边界并给出可复现实验协议。"],
    )


def _mentor_comments(idea: ResearchIdea, challenge, venue: str | None) -> str:
    target = f"目标 {venue} 的" if venue else "当前"
    return (
        "娄萌萌评语：你到底想解决什么问题，现在比一开始清楚了。"
        f"{target}版本可以继续推进，但最大风险仍然是 novelty 边界。"
        "先别急着堆实验，先把最相近工作、核心假设和不可替代贡献写成一页纸。"
        f"如果最小实验能支撑“{idea.research_question}”，这个方向值得投入；"
        "如果主效应不明显，要果断缩小问题或换成更诚实的 setting。"
    )
