"""Deterministic router for common Hypo-Research user requests."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GuideRoute:
    """A suggested Hypo-Research route for a user request."""

    category: str
    scenario: str
    confidence: float
    rationale: str
    suggested_commands: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _RouteRule:
    category: str
    scenario: str
    keywords: tuple[str, ...]
    rationale: str
    commands: tuple[str, ...]
    questions: tuple[str, ...]


_RULES: tuple[_RouteRule, ...] = (
    _RouteRule(
        category="check",
        scenario="paper_check",
        keywords=(
            "快投",
            "投稿",
            "提交",
            "camera-ready",
            "camera ready",
            "paper check",
            "submission",
            "检查",
            "体检",
        ),
        rationale="Request asks for paper readiness or mandatory paper checks.",
        commands=("hypo-research check <paper.tex> --full",),
        questions=(
            "目标 venue 是什么？",
            "输入是 LaTeX 主文件还是项目目录？",
            "需要自动修复，还是只生成报告？",
        ),
    ),
    _RouteRule(
        category="read",
        scenario="paper_reading",
        keywords=("读论文", "读 pdf", "pdf", "paper reading", "read this", "method", "方法"),
        rationale="Request asks to read or understand a paper/PDF.",
        commands=(
            "hypo-research read ingest <paper.pdf> --out <dir>",
            "hypo-research read outline <dir>/artifact.json",
        ),
        questions=(
            "要快速判断是否值得读，还是深读方法、数据、图表和 claim？",
            "是否需要和其他论文对比？",
        ),
    ),
    _RouteRule(
        category="review",
        scenario="simulated_review",
        keywords=("模拟审稿", "审稿", "review", "peer review", "icml", "neurips", "reviewer"),
        rationale="Request asks for simulated peer review or academic quality review.",
        commands=("hypo-research review <paper> --venue <venue> --panel full",),
        questions=(
            "目标 venue 是什么？",
            "需要 gentle、standard 还是 harsh 严厉度？",
        ),
    ),
    _RouteRule(
        category="search",
        scenario="literature_survey",
        keywords=("调研", "文献", "survey", "literature", "search", "陌生方向", "related work"),
        rationale="Request asks for literature search or field survey.",
        commands=("hypo-research search \"<query>\" --source all",),
        questions=(
            "你熟悉这个领域吗？",
            "目标是入门、找最新论文、写 related work，还是找 baseline？",
        ),
    ),
    _RouteRule(
        category="project",
        scenario="research_project",
        keywords=("项目", "project", "milestone", "会议", "meeting", "进度", "管理"),
        rationale="Request asks to manage persistent research project context.",
        commands=("hypo-research project status <project>",),
        questions=(
            "是新建项目、查看状态，还是导入会议/论文材料？",
            "项目 slug 是什么？",
        ),
    ),
    _RouteRule(
        category="idea",
        scenario="research_ideation",
        keywords=("idea", "想法", "实验计划", "experiment", "challenge", "pilot"),
        rationale="Request asks for research ideation, challenge, or planning.",
        commands=("hypo-research pilot \"<direction>\"",),
        questions=(
            "研究方向是什么？",
            "目标 venue 或 deadline 是什么？",
        ),
    ),
)


def route_request(request: str) -> GuideRoute:
    """Route a natural-language request to a Hypo-Research category."""
    normalized = request.lower()
    best_rule: _RouteRule | None = None
    best_hits = 0
    for rule in _RULES:
        hits = sum(1 for keyword in rule.keywords if keyword.lower() in normalized)
        if hits > best_hits:
            best_rule = rule
            best_hits = hits

    if best_rule is None:
        return GuideRoute(
            category="guide",
            scenario="clarify",
            confidence=0.35,
            rationale="No strong route matched; ask for the intended research workflow.",
            suggested_commands=["hypo-research guide \"<your request>\""],
            follow_up_questions=[
                "你是想调研方向、读论文、写论文、审论文，还是管理项目？",
                "输入材料是 query、PDF、LaTeX 项目，还是已有项目？",
            ],
        )

    confidence = min(0.95, 0.55 + best_hits * 0.15)
    return GuideRoute(
        category=best_rule.category,
        scenario=best_rule.scenario,
        confidence=confidence,
        rationale=best_rule.rationale,
        suggested_commands=list(best_rule.commands),
        follow_up_questions=list(best_rule.questions),
    )
