"""CLI commands for ideation workflows."""

from __future__ import annotations

import json
from dataclasses import asdict, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import click

from hypo_research.ideation.challenge import challenge_idea
from hypo_research.ideation.experiment import design_experiment
from hypo_research.ideation.models import (
    ChallengeSeverity,
    IdeaMode,
    IdeaScore,
    IdeaStrategy,
    ResearchIdea,
)
from hypo_research.ideation.pilot import run_pilot
from hypo_research.ideation.planning import create_plan
from hypo_research.ideation.strategies import generate_ideas


OUTPUT_CHOICES = click.Choice(["json", "markdown"])


@click.command("idea")
@click.argument("direction", type=str)
@click.option("--papers", multiple=True, help="输入文献标题，可重复传入。")
@click.option("--survey", type=str, default=None, help="hypo-survey 输出 JSON 文件。")
@click.option("--constraints", type=str, default=None, help="研究资源、时间或方法约束。")
@click.option("--mode", type=click.Choice(["quick_win", "ambitious"]), default=None)
@click.option("--num-ideas", type=int, default=5, show_default=True)
@click.option("--output", "output_format", type=OUTPUT_CHOICES, default="markdown", show_default=True)
@click.option("--output-file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def idea_command(
    direction: str,
    papers: tuple[str, ...],
    survey: str | None,
    constraints: str | None,
    mode: str | None,
    num_ideas: int,
    output_format: str,
    output_file: Path | None,
) -> None:
    """生成 Quick Win 与 Ambitious research ideas。"""
    result = generate_ideas(
        direction,
        list(papers),
        survey,
        constraints,
        IdeaMode(mode) if mode else None,
        num_ideas,
    )
    _emit(result, output_format, output_file, _render_idea_result)


@click.command("challenge")
@click.argument("idea_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--severity", type=click.Choice(["gentle", "standard", "harsh"]), default="harsh", show_default=True)
@click.option("--output", "output_format", type=OUTPUT_CHOICES, default="markdown", show_default=True)
@click.option("--output-file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def challenge_command(
    idea_file: Path,
    severity: str,
    output_format: str,
    output_file: Path | None,
) -> None:
    """对 idea 进行苏格拉底式拷打。"""
    idea = load_idea(idea_file)
    result = challenge_idea(idea, ChallengeSeverity(severity))
    _emit(result, output_format, output_file, _render_challenge_result)


@click.command("experiment")
@click.argument("idea_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--venue", type=str, default=None)
@click.option("--constraints", type=str, default=None)
@click.option("--output", "output_format", type=OUTPUT_CHOICES, default="markdown", show_default=True)
@click.option("--output-file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def experiment_command(
    idea_file: Path,
    venue: str | None,
    constraints: str | None,
    output_format: str,
    output_file: Path | None,
) -> None:
    """为 idea 设计实验方案。"""
    result = design_experiment(load_idea(idea_file), venue=venue, constraints=constraints)
    _emit(result, output_format, output_file, _render_experiment_result)


@click.command("plan")
@click.argument("idea_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--experiment-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--venue", type=str, default=None)
@click.option("--deadline", type=str, default=None)
@click.option("--resources", type=str, default=None)
@click.option("--output", "output_format", type=OUTPUT_CHOICES, default="markdown", show_default=True)
@click.option("--output-file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def plan_command(
    idea_file: Path,
    experiment_file: Path | None,
    venue: str | None,
    deadline: str | None,
    resources: str | None,
    output_format: str,
    output_file: Path | None,
) -> None:
    """生成研究工作路线图。"""
    idea = load_idea(idea_file)
    experiment = design_experiment(idea, venue=venue) if experiment_file is None else _load_experiment(experiment_file)
    result = create_plan(idea, experiment, venue=venue, deadline=deadline, resources=resources)
    _emit(result, output_format, output_file, _render_plan_result)


@click.command("pilot")
@click.argument("direction", type=str)
@click.option("--papers", multiple=True)
@click.option("--survey", type=str, default=None)
@click.option("--constraints", type=str, default=None)
@click.option("--venue", type=str, default=None)
@click.option("--deadline", type=str, default=None)
@click.option("--resources", type=str, default=None)
@click.option("--severity", type=click.Choice(["gentle", "standard", "harsh"]), default="harsh", show_default=True)
@click.option("--auto-select", is_flag=True, default=False)
@click.option("--output", "output_format", type=OUTPUT_CHOICES, default="markdown", show_default=True)
@click.option("--output-file", type=click.Path(dir_okay=False, path_type=Path), default=None)
def pilot_command(
    direction: str,
    papers: tuple[str, ...],
    survey: str | None,
    constraints: str | None,
    venue: str | None,
    deadline: str | None,
    resources: str | None,
    severity: str,
    auto_select: bool,
    output_format: str,
    output_file: Path | None,
) -> None:
    """运行娄萌萌全流程研究领航。"""
    result = run_pilot(
        direction,
        list(papers),
        survey,
        constraints,
        venue,
        deadline,
        resources,
        ChallengeSeverity(severity),
        auto_select,
    )
    _emit(result, output_format, output_file, _render_pilot_result)


def load_idea(path: Path) -> ResearchIdea:
    """Load an idea from JSON or plain text."""
    content = path.read_text(encoding="utf-8").strip()
    if content.startswith("{"):
        payload = json.loads(content)
        if "selected_idea" in payload:
            payload = payload["selected_idea"]
        elif "quick_win_ideas" in payload and payload["quick_win_ideas"]:
            payload = payload["quick_win_ideas"][0]
        return _idea_from_dict(payload)
    return _idea_from_text(content)


def _idea_from_dict(payload: dict[str, Any]) -> ResearchIdea:
    score_payload = payload.get("score") or {}
    score = IdeaScore(
        novelty=float(score_payload.get("novelty", 0.5)),
        significance=float(score_payload.get("significance", 0.5)),
        feasibility=float(score_payload.get("feasibility", 0.5)),
        clarity=float(score_payload.get("clarity", 0.5)),
        adjustments=[],
        total_score=float(score_payload.get("total_score", 0.5)),
        tier=str(score_payload.get("tier", "快速产出")),
        summary=str(score_payload.get("summary", "从文件载入的 idea。")),
        suggestions=list(score_payload.get("suggestions", [])),
    )
    return ResearchIdea(
        title=str(payload.get("title", "未命名 Idea")),
        mode=IdeaMode(payload.get("mode", "quick_win")),
        strategy=IdeaStrategy(payload.get("strategy", "problem_variant")),
        research_question=str(payload.get("research_question", payload.get("question", ""))),
        motivation=str(payload.get("motivation", "")),
        method_sketch=str(payload.get("method_sketch", payload.get("method", ""))),
        expected_contribution=list(payload.get("expected_contribution", [])),
        feasibility_analysis=str(payload.get("feasibility_analysis", "")),
        risk_factors=list(payload.get("risk_factors", [])),
        related_papers=list(payload.get("related_papers", [])),
        score=score,
    )


def _idea_from_text(content: str) -> ResearchIdea:
    return ResearchIdea(
        title=content.splitlines()[0][:80] if content else "未命名 Idea",
        mode=IdeaMode.QUICK_WIN,
        strategy=IdeaStrategy.PROBLEM_VARIANT,
        research_question=content,
        motivation="从纯文本 idea 文件载入，需进一步补全文献动机。",
        method_sketch="根据文本描述补全方法并设计最小可行实验。",
        expected_contribution=["提出一个可验证的研究问题。"],
        feasibility_analysis="需要进一步确认数据、baseline 和资源。",
        risk_factors=["输入信息较少，novelty 和可行性仍需验证。"],
        related_papers=[],
        score=IdeaScore(0.5, 0.5, 0.5, 0.5, [], 0.5, "快速产出", "从文本载入，待重新评分。", []),
    )


def _load_experiment(path: Path):
    from hypo_research.ideation.models import AblationItem, ExperimentBaseline, ExperimentDesign

    payload = json.loads(path.read_text(encoding="utf-8"))
    return ExperimentDesign(
        idea_title=str(payload.get("idea_title", "未命名 Idea")),
        baselines=[ExperimentBaseline(**item) for item in payload.get("baselines", [])],
        datasets=list(payload.get("datasets", [])),
        metrics=list(payload.get("metrics", [])),
        ablation_studies=[AblationItem(**item) for item in payload.get("ablation_studies", [])],
        experiment_matrix=list(payload.get("experiment_matrix", [])),
        expected_results=str(payload.get("expected_results", "")),
        reference_setups=list(payload.get("reference_setups", [])),
        venue_requirements=payload.get("venue_requirements"),
    )


def _emit(result: Any, output_format: str, output_file: Path | None, renderer) -> None:
    rendered = json.dumps(_to_plain(result), ensure_ascii=False, indent=2) if output_format == "json" else renderer(result)
    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(rendered, encoding="utf-8")
    else:
        click.echo(rendered)


def _to_plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _to_plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}
    return value


def _render_idea_result(result) -> str:
    lines = [f"# Idea 生成结果", "", result.input_summary, ""]
    for title, ideas in [("Quick Win", result.quick_win_ideas), ("Ambitious", result.ambitious_ideas)]:
        lines.extend([f"## {title}", ""])
        for item in ideas:
            lines.extend(_render_idea(item))
    return "\n".join(lines)


def _render_idea(idea: ResearchIdea) -> list[str]:
    return [
        f"### {idea.title}",
        f"- 策略：{idea.strategy.value}",
        f"- 研究问题：{idea.research_question}",
        f"- 方法概述：{idea.method_sketch}",
        f"- 评分：{idea.score.total_score:.2f}（{idea.score.tier}）",
        "",
    ]


def _render_challenge_result(result) -> str:
    lines = [f"# Idea 拷打结果：{result.idea_title}", "", f"结论：{result.verdict}", ""]
    for question in result.questions:
        lines.append(f"- [{question.dimension}] {question.question}")
    lines.extend(["", "## 致命风险", *[f"- {risk}" for risk in result.fatal_risks]])
    lines.extend(["", "## 加固策略", *[f"- {item}" for item in result.reinforcement_plan]])
    return "\n".join(lines)


def _render_experiment_result(result) -> str:
    lines = [f"# 实验设计：{result.idea_title}", "", "## Baseline"]
    lines.extend([f"- {item.name}：{item.reason}" for item in result.baselines])
    lines.extend(["", "## 数据集", *[f"- {item['name']}：{item['reason']}" for item in result.datasets]])
    lines.extend(["", "## Ablation", *[f"- {item.component}：{item.experiment}" for item in result.ablation_studies]])
    lines.extend(["", "## 预期结果", result.expected_results])
    if result.venue_requirements:
        lines.extend(["", "## Venue 要求", result.venue_requirements])
    return "\n".join(lines)


def _render_plan_result(result) -> str:
    lines = [f"# 工作规划：{result.idea_title}", "", f"总时间估算：{result.total_estimated_time}", ""]
    for phase in result.phases:
        lines.extend([f"## {phase.name}（{phase.duration}）", *[f"- {task}" for task in phase.tasks], ""])
    lines.append("## 论文大纲")
    lines.extend([f"- {item['section']}：{item['content_plan']}" for item in result.paper_outline])
    return "\n".join(lines)


def _render_pilot_result(result) -> str:
    return "\n".join(
        [
            "# hypo-pilot（娄萌萌）报告",
            "",
            f"选中 Idea：{result.selected_idea.title}",
            f"拷打结论：{result.challenge.verdict}",
            "",
            "## 实验设计摘要",
            _render_experiment_result(result.experiment),
            "",
            "## 工作规划摘要",
            _render_plan_result(result.plan),
            "",
            "## 娄萌萌评语",
            result.mentor_comments,
        ]
    )


IDEATION_COMMANDS = [
    idea_command,
    challenge_command,
    experiment_command,
    plan_command,
    pilot_command,
]
