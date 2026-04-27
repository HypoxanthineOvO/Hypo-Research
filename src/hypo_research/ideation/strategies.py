"""Idea generation strategies."""

from __future__ import annotations

import json
from pathlib import Path

from hypo_research.ideation.models import IdeaGenerationResult, IdeaMode, IdeaScore, IdeaStrategy, ResearchIdea
from hypo_research.ideation.scoring import score_idea
from hypo_research.review.literature import LiteratureContext, search_literature


QUICK_WIN_STRATEGIES = {
    "dataset_transfer": {
        "name": "换数据集/换领域",
        "description": "把领域 A 的成熟方法拿到领域 B 的数据集上跑",
        "prompt_template": "明确首次将 X 应用于 Y，并说明迁移意义、技术挑战和目标 venue。",
    },
    "module_fusion": {
        "name": "缝模块/搭积木",
        "description": "在现有 backbone 上插入新模块",
        "prompt_template": "说明基准模型、新模块、组合合理性、预期提升和 ablation study。",
    },
    "setting_shift": {
        "name": "换实验设定",
        "description": "同一任务换约束条件",
        "prompt_template": "明确原始 setting、新 setting、技术挑战和实际意义。",
    },
    "application": {
        "name": "应用落地",
        "description": "将算法工作包装为具体应用领域解决方案",
        "prompt_template": "明确应用场景、痛点、现有方法不足和适配方式。",
    },
}

AMBITIOUS_STRATEGIES = {
    "gap_analysis": {
        "name": "缺口分析",
        "description": "从现有文献中找到还没被解决的问题",
        "prompt_template": "提取 limitation、交叉对比、聚类未解决问题并生成 idea。",
    },
    "method_transfer": {
        "name": "跨领域方法迁移",
        "description": "找到深层结构相似性的跨领域迁移",
        "prompt_template": "提取核心原理、目标需求、共同结构并评估迁移可行性。",
    },
    "problem_variant": {
        "name": "问题变体",
        "description": "放宽、加强或替换已有问题假设",
        "prompt_template": "列出假设，逐条变换，并评估新变体的意义和可解性。",
    },
    "contradiction": {
        "name": "矛盾消解",
        "description": "找到领域内矛盾结论并尝试统一解释",
        "prompt_template": "识别矛盾、分析原因、提出统一解释并设计验证实验。",
    },
    "paradigm_challenge": {
        "name": "范式挑战",
        "description": "质疑领域基本假设，提出新的思考方式",
        "prompt_template": "列出常识假设、逐条质疑，并评估推翻后的影响。",
    },
}

CROSS_STRATEGIES = {
    "combination": {
        "name": "组合策略",
        "description": "找到两个独立方向之间的深层联系",
        "prompt_template": "同时给出 Quick Win 组合和 Ambitious 统一框架版本。",
    },
}


def generate_ideas(
    direction: str,
    papers: list[str] | None = None,
    survey_output: str | None = None,
    constraints: str | None = None,
    mode: IdeaMode | None = None,
    num_ideas: int = 5,
) -> IdeaGenerationResult:
    """Generate quick-win and/or ambitious research ideas."""
    paper_titles = _load_papers(papers or [], survey_output)
    literature = _search_supporting_literature(direction, paper_titles)
    strategies = _select_strategies(direction, paper_titles, constraints, mode)

    quick_win_ideas: list[ResearchIdea] = []
    ambitious_ideas: list[ResearchIdea] = []
    if mode in {None, IdeaMode.QUICK_WIN}:
        quick_win_ideas = _generate_for_mode(
            direction,
            IdeaMode.QUICK_WIN,
            strategies,
            literature,
            constraints,
            max(num_ideas, 0),
        )
    if mode in {None, IdeaMode.AMBITIOUS}:
        ambitious_ideas = _generate_for_mode(
            direction,
            IdeaMode.AMBITIOUS,
            strategies,
            literature,
            constraints,
            max(num_ideas, 0),
        )
    return IdeaGenerationResult(
        input_summary=_summarize_input(direction, paper_titles, constraints),
        strategies_used=strategies,
        quick_win_ideas=quick_win_ideas,
        ambitious_ideas=ambitious_ideas,
        literature_context=literature,
    )


def build_strategy_prompt(strategy: IdeaStrategy, direction: str, constraints: str | None = None) -> str:
    """Build the prompt text for one strategy."""
    config = {**QUICK_WIN_STRATEGIES, **AMBITIOUS_STRATEGIES, **CROSS_STRATEGIES}[strategy.value]
    prompt = [
        f"策略：{config['name']}",
        f"说明：{config['description']}",
        f"研究方向：{direction}",
        f"要求：{config['prompt_template']}",
    ]
    if constraints:
        prompt.append(f"约束条件：{constraints}")
    return "\n".join(prompt)


def _select_strategies(
    direction: str,
    papers: list[str],
    constraints: str | None,
    mode: IdeaMode | None,
) -> list[IdeaStrategy]:
    selected: list[IdeaStrategy] = []
    if mode in {None, IdeaMode.QUICK_WIN}:
        selected.extend(
            [
                IdeaStrategy.DATASET_TRANSFER,
                IdeaStrategy.MODULE_FUSION,
                IdeaStrategy.SETTING_SHIFT,
                IdeaStrategy.APPLICATION,
            ]
        )
    if mode in {None, IdeaMode.AMBITIOUS}:
        selected.extend(
            [
                IdeaStrategy.GAP_ANALYSIS if papers else IdeaStrategy.PROBLEM_VARIANT,
                IdeaStrategy.METHOD_TRANSFER,
                IdeaStrategy.CONTRADICTION if papers else IdeaStrategy.PARADIGM_CHALLENGE,
            ]
        )
    if constraints or len(direction.split()) >= 3:
        selected.append(IdeaStrategy.COMBINATION)
    return list(dict.fromkeys(selected))


def _generate_for_mode(
    direction: str,
    mode: IdeaMode,
    strategies: list[IdeaStrategy],
    literature: LiteratureContext | None,
    constraints: str | None,
    num_ideas: int,
) -> list[ResearchIdea]:
    candidates = [
        strategy
        for strategy in strategies
        if _strategy_matches_mode(strategy, mode)
    ]
    ideas: list[ResearchIdea] = []
    for index, strategy in enumerate(candidates[:num_ideas], start=1):
        idea = _make_idea(direction, mode, strategy, index, literature, constraints)
        idea.score = score_idea(idea, _literature_as_dicts(literature))
        ideas.append(idea)
    return ideas


def _strategy_matches_mode(strategy: IdeaStrategy, mode: IdeaMode) -> bool:
    if strategy == IdeaStrategy.COMBINATION:
        return True
    quick = {IdeaStrategy.DATASET_TRANSFER, IdeaStrategy.MODULE_FUSION, IdeaStrategy.SETTING_SHIFT, IdeaStrategy.APPLICATION}
    return strategy in quick if mode == IdeaMode.QUICK_WIN else strategy not in quick


def _make_idea(
    direction: str,
    mode: IdeaMode,
    strategy: IdeaStrategy,
    index: int,
    literature: LiteratureContext | None,
    constraints: str | None,
) -> ResearchIdea:
    title_prefix = "快速可验证" if mode == IdeaMode.QUICK_WIN else "高影响力"
    strategy_name = {**QUICK_WIN_STRATEGIES, **AMBITIOUS_STRATEGIES, **CROSS_STRATEGIES}[strategy.value]["name"]
    related = [ref.title for ref in (literature.references if literature else [])[:3]]
    constraint_text = f"在约束“{constraints}”下，" if constraints else ""
    return ResearchIdea(
        title=f"{title_prefix}：面向{direction}的{strategy_name}方案",
        mode=mode,
        strategy=strategy,
        research_question=f"{constraint_text}如何通过{strategy_name}为“{direction}”提出可验证且有区分度的研究问题？",
        motivation=_motivation(direction, strategy, related),
        method_sketch=_method_sketch(direction, strategy, mode),
        expected_contribution=[
            f"给出“{direction}”下清晰的问题定义和实验协议。",
            f"验证{strategy_name}是否能带来稳定收益或新的解释框架。",
        ],
        feasibility_analysis=(
            "优先复用公开数据集和现有实现，适合 2-4 周内完成 pilot。"
            if mode == IdeaMode.QUICK_WIN
            else "需要先做小规模证据验证，再扩大到完整实验矩阵。"
        ),
        risk_factors=[
            "与已有工作 novelty 边界不够清楚。",
            "实验结果可能只在单一数据集成立。",
        ],
        related_papers=related,
        score=IdeaScore(0, 0, 0, 0, [], 0, "需要加强", "待评分", []),
    )


def _motivation(direction: str, strategy: IdeaStrategy, related: list[str]) -> str:
    evidence = f"已有相关工作包括：{'; '.join(related)}。" if related else "当前未检索到直接支撑文献，需要先补充检索。"
    if strategy == IdeaStrategy.GAP_ANALYSIS:
        return f"{direction} 的现有研究仍有未闭合 limitation，适合从缺口中提炼新问题。{evidence}"
    if strategy == IdeaStrategy.CONTRADICTION:
        return f"{direction} 中可能存在指标、数据集或假设差异导致的结论冲突，统一解释有潜在价值。{evidence}"
    if strategy == IdeaStrategy.PARADIGM_CHALLENGE:
        return f"{direction} 的主流范式可能隐藏未验证假设，质疑这些假设有机会形成高影响力工作。{evidence}"
    return f"{direction} 已有基础积累，适合通过 {strategy.value} 形成可执行的新研究切入点。{evidence}"


def _method_sketch(direction: str, strategy: IdeaStrategy, mode: IdeaMode) -> str:
    if mode == IdeaMode.QUICK_WIN:
        return f"选择一个强 baseline，在“{direction}”上加入 {strategy.value} 变体，配套 ablation 和跨数据集验证。"
    return f"先抽象“{direction}”中的核心假设，再用 {strategy.value} 构造新 formulation，并设计验证该 formulation 的实验。"


def _search_supporting_literature(direction: str, papers: list[str]) -> LiteratureContext | None:
    abstract = " ".join(papers[:5]) if papers else f"Research direction: {direction}"
    try:
        return search_literature(direction, abstract, paper_references=papers, max_results=5, queries=[direction])
    except Exception:
        return None


def _load_papers(papers: list[str], survey_output: str | None) -> list[str]:
    loaded = list(papers)
    if not survey_output:
        return loaded
    path = Path(survey_output)
    if not path.exists():
        return loaded
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return loaded
    for item in payload.get("papers", payload.get("results", [])):
        if isinstance(item, dict) and item.get("title"):
            loaded.append(str(item["title"]))
    return list(dict.fromkeys(loaded))


def _literature_as_dicts(literature: LiteratureContext | None) -> list[dict] | None:
    if literature is None:
        return None
    return [
        {"title": ref.title, "abstract": ref.abstract_snippet, "year": ref.year, "citation_count": ref.citation_count}
        for ref in literature.references
    ]


def _summarize_input(direction: str, papers: list[str], constraints: str | None) -> str:
    parts = [f"研究方向：{direction}"]
    if papers:
        parts.append(f"输入文献 {len(papers)} 篇")
    if constraints:
        parts.append(f"约束：{constraints}")
    return "；".join(parts)
