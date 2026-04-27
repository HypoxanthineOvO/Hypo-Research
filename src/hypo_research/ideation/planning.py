"""Research planning from idea and experiment design."""

from __future__ import annotations

from hypo_research.ideation.models import ExperimentDesign, PlanPhase, ResearchIdea, ResearchPlan


PLAN_PROMPT = """
你是一个科研项目管理专家。请基于 idea 和实验方案制定阶段、论文大纲、写作计划和风险缓解。
"""


def create_plan(
    idea: ResearchIdea,
    experiment: ExperimentDesign,
    venue: str | None = None,
    deadline: str | None = None,
    resources: str | None = None,
) -> ResearchPlan:
    """Create a staged research plan."""
    compressed = bool(deadline)
    phases = [
        PlanPhase(
            "文献补充与问题收敛",
            "Week 1" if compressed else "Week 1-2",
            [
                "补齐最近 3 年直接竞争工作。",
                "重写 research question、claim 和 novelty 表格。",
            ],
            ["确认最相近工作和不可替代差异"],
            ["发现高度相似工作导致选题重构"],
            ["相关工作矩阵", "最终 idea 定义"],
        ),
        PlanPhase(
            "方法实现与最小实验",
            "Week 2" if compressed else "Week 3-4",
            ["实现 baseline 与 proposed prototype。", "在 Primary Benchmark 上跑通最小实验。"],
            ["主效应初步成立或明确失败原因"],
            ["代码复现成本超出预期"],
            ["可运行代码", "pilot 结果表"],
        ),
        PlanPhase(
            "完整实验与消融",
            "Week 3-4" if compressed else "Week 5-7",
            ["完成所有 baseline 对比。", "运行 ablation、效率和泛化实验。"],
            ["实验矩阵覆盖主 claim"],
            ["结果只在单一数据集成立"],
            ["完整结果表", "失败案例分析"],
        ),
        PlanPhase(
            "论文写作与提交检查",
            "Week 5" if compressed else "Week 8-10",
            ["按 Method、Experiment、Introduction、Related Work 顺序写作。", "运行 hypo-presubmit 做提交前检查。"],
            ["形成可投稿初稿"],
            ["实验解释不足导致故事线不稳"],
            ["论文初稿", "presubmit 报告"],
        ),
    ]
    outline = _paper_outline(experiment)
    return ResearchPlan(
        idea_title=idea.title,
        target_venue=venue,
        deadline=deadline,
        phases=phases,
        paper_outline=outline,
        writing_schedule=_writing_schedule(compressed),
        risk_mitigation=_risk_mitigation(resources),
        total_estimated_time="约 5 周（压缩排期）" if compressed else "约 10 周（常规排期）",
    )


def _paper_outline(experiment: ExperimentDesign) -> list[dict]:
    return [
        {"section": "Introduction", "content_plan": "问题动机、核心缺口、贡献列表。", "depends_on": "最终 claim 和主实验趋势"},
        {"section": "Related Work", "content_plan": "按最相近工作、baseline、setting 分类。", "depends_on": "文献补充"},
        {"section": "Method", "content_plan": "问题定义、方法组件、复杂度或实现细节。", "depends_on": "方法冻结"},
        {"section": "Experiments", "content_plan": f"覆盖 {len(experiment.experiment_matrix)} 个实验配置。", "depends_on": "完整实验结果"},
        {"section": "Conclusion", "content_plan": "总结贡献、限制和未来工作。", "depends_on": "失败案例和限制分析"},
    ]


def _writing_schedule(compressed: bool) -> list[dict]:
    if compressed:
        return [
            {"section": "Method", "start": "Week 2", "end": "Week 3", "notes": "边实现边写。"},
            {"section": "Experiments", "start": "Week 3", "end": "Week 5", "notes": "结果出来后滚动更新。"},
            {"section": "Introduction/Related Work", "start": "Week 4", "end": "Week 5", "notes": "最后收束故事线。"},
        ]
    return [
        {"section": "Method", "start": "Week 3", "end": "Week 5", "notes": "方法稳定后先写。"},
        {"section": "Experiments", "start": "Week 6", "end": "Week 8", "notes": "跟随实验结果更新。"},
        {"section": "Introduction/Related Work", "start": "Week 8", "end": "Week 10", "notes": "根据最终结果强化叙事。"},
    ]


def _risk_mitigation(resources: str | None) -> list[dict]:
    plan_b = "降低模型规模、减少 seed、优先保留主实验和 essential ablation。"
    if resources:
        plan_b = f"按可用资源“{resources}”裁剪实验矩阵，优先保证主 claim。"
    return [
        {"risk": "novelty 不足", "plan_b": "转向更明确的 setting shift 或补充理论/机制解释。"},
        {"risk": "资源不足", "plan_b": plan_b},
        {"risk": "实验结果不稳定", "plan_b": "增加错误分析，改写为条件性结论或负结果洞察。"},
    ]
