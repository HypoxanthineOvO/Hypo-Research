"""Experiment design for research ideas."""

from __future__ import annotations

from hypo_research.ideation.models import AblationItem, ExperimentBaseline, ExperimentDesign, ResearchIdea
from hypo_research.review.literature import search_literature


EXPERIMENT_DESIGN_PROMPT = """
你是一个实验设计专家。基于研究 idea 设计 baseline、数据集、指标、ablation 和实验矩阵。
"""


def design_experiment(
    idea: ResearchIdea,
    venue: str | None = None,
    constraints: str | None = None,
) -> ExperimentDesign:
    """Design a complete experiment plan for an idea."""
    references = _reference_setups(idea)
    baselines = _baselines(idea, references)
    datasets = _datasets(idea, constraints)
    metrics = _metrics()
    ablations = [
        AblationItem(
            component="核心模块",
            experiment="移除 proposed component，仅保留 backbone。",
            expected_outcome="如果 idea 成立，主指标应显著下降。",
            importance="essential",
        ),
        AblationItem(
            component="训练或推理策略",
            experiment="替换为标准训练策略或默认推理流程。",
            expected_outcome="验证收益来自设计本身，而不是训练技巧。",
            importance="recommended",
        ),
    ]
    matrix = [
        {"method": baseline.name, "dataset": dataset["name"], "metrics": [metric["name"] for metric in metrics]}
        for baseline in [*baselines, ExperimentBaseline("Proposed", None, "待验证的本文方法")]
        for dataset in datasets
    ]
    venue_requirements = _venue_requirements(venue)
    return ExperimentDesign(
        idea_title=idea.title,
        baselines=baselines,
        datasets=datasets,
        metrics=metrics,
        ablation_studies=ablations,
        experiment_matrix=matrix,
        expected_results="Proposed 应在主指标上稳定超过简单 baseline，并在至少两个数据集上接近或超过强 baseline；ablation 应显示核心模块贡献明确。",
        reference_setups=references,
        venue_requirements=venue_requirements,
    )


def _reference_setups(idea: ResearchIdea) -> list[str]:
    try:
        context = search_literature(idea.title, idea.research_question, max_results=3, queries=[idea.research_question])
        refs = [f"{ref.title} ({ref.year})" for ref in context.references[:3]] if context is not None else []
    except Exception:
        refs = []
    return refs or idea.related_papers[:3] or ["同领域最近 SOTA 论文的实验设置（需人工确认具体版本）"]


def _baselines(idea: ResearchIdea, references: list[str]) -> list[ExperimentBaseline]:
    sota = references[0] if references else None
    return [
        ExperimentBaseline("Simple baseline", None, "证明任务不是 trivial，并提供最低性能参照。"),
        ExperimentBaseline("Classic baseline", idea.related_papers[0] if idea.related_papers else None, "代表领域中稳定、可复现的传统方案。"),
        ExperimentBaseline("Recent SOTA", sota, "必须与最近强方法对比，支撑 novelty 和 significance。"),
    ]


def _datasets(idea: ResearchIdea, constraints: str | None) -> list[dict]:
    source_note = "按约束选择轻量公开数据集" if constraints else "公开 benchmark 或同领域常用数据集"
    return [
        {"name": "Primary Benchmark", "reason": "主任务标准评测，便于与已有工作直接比较。", "source": source_note},
        {"name": "Robustness Benchmark", "reason": "检验跨数据集泛化，避免只在一个数据集 work。", "source": source_note},
    ]


def _metrics() -> list[dict]:
    return [
        {"name": "Primary task metric", "reason": "直接反映任务目标是否被解决。", "higher_is_better": True},
        {"name": "Efficiency / cost", "reason": "衡量方法代价，防止性能提升来自不可接受的资源消耗。", "higher_is_better": False},
    ]


def _venue_requirements(venue: str | None) -> str | None:
    if not venue:
        return None
    return f"目标 venue 为 {venue}：实验需包含最新 SOTA、充分 ablation、统计显著性或多 seed 结果，并解释失败案例。"
