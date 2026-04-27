"""Build project context for context-aware skill calls."""

from __future__ import annotations

import json
from pathlib import Path

from hypo_research.project.manager import ProjectManager
from hypo_research.project.meetings import get_meeting_context


def build_context(project_slug: str, paper_slug: str | None = None) -> dict:
    """Build project context for existing skills."""
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    project_dir = manager.project_dir(project_slug)
    papers = [paper for paper in project.papers if paper_slug in {None, paper.slug}]
    active_ideas = []
    rejected_ideas = []
    for paper in papers:
        for idea in paper.ideas:
            record = {
                "id": idea.id,
                "paper": paper.slug,
                "title": idea.title,
                "score": idea.score,
                "tier": idea.tier,
                "reason": idea.rejection_reason,
            }
            if idea.status.value == "rejected":
                rejected_ideas.append(record)
            elif idea.status.value in {"candidate", "selected", "challenged", "refined", "active"}:
                active_ideas.append(record)
    return {
        "project_direction": project.direction,
        "project_slug": project.slug,
        "paper_slug": paper_slug,
        "surveys": _survey_summaries(project_dir / "surveys"),
        "literature": _load_literature(project_dir / "literature" / "papers.json"),
        "ideas": {"active": active_ideas, "rejected": rejected_ideas},
        "meetings": get_meeting_context(project_slug),
        "constraints": _constraints_from_project(project, paper_slug),
    }


def inject_context_to_idea(context: dict) -> str:
    """Render project context for hypo-idea."""
    return "\n".join(
        [
            "## 项目上下文（注入到 hypo-idea）",
            f"- 研究方向：{context['project_direction']}",
            f"- 已有 survey：{_compact_list(context['surveys'])}",
            f"- 避免重复的已否决 ideas：{_compact_list(context['ideas']['rejected'])}",
            f"- 导师/组会决策：{_compact_list(context['meetings']['key_decisions'])}",
            f"- 约束：{context.get('constraints') or '无'}",
        ]
    )


def inject_context_to_challenge(context: dict) -> str:
    """Render project context for hypo-challenge."""
    return "\n".join(
        [
            "## 项目上下文（注入到 hypo-challenge）",
            f"- 活跃 ideas：{_compact_list(context['ideas']['active'])}",
            f"- 会议决策：{_compact_list(context['meetings']['key_decisions'])}",
            f"- 文献库规模：{len(context['literature'])} 篇",
        ]
    )


def inject_context_to_experiment(context: dict) -> str:
    """Render project context for hypo-experiment."""
    return "\n".join(
        [
            "## 项目上下文（注入到 hypo-experiment）",
            f"- 项目约束：{context.get('constraints') or '无'}",
            f"- 待办 action items：{_compact_list(context['meetings']['action_items'])}",
            f"- 可用 literature：{_compact_list(context['literature'][:5])}",
        ]
    )


def inject_context_to_plan(context: dict) -> str:
    """Render project context for hypo-plan."""
    return "\n".join(
        [
            "## 项目上下文（注入到 hypo-plan）",
            f"- 研究方向：{context['project_direction']}",
            f"- 会议 action items：{_compact_list(context['meetings']['action_items'])}",
            f"- 约束：{context.get('constraints') or '无'}",
        ]
    )


def _survey_summaries(survey_dir: Path) -> list[dict]:
    summaries = []
    for path in sorted(survey_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        papers = payload.get("papers", payload if isinstance(payload, list) else [])
        titles = [str(item.get("title")) for item in papers[:3] if isinstance(item, dict) and item.get("title")] if isinstance(papers, list) else []
        summaries.append(
            {
                "file": path.name,
                "title": f"{path.name}: {', '.join(titles)}" if titles else path.name,
                "paper_count": len(papers) if isinstance(papers, list) else 0,
            }
        )
    return summaries


def _load_literature(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [
        {"title": item.get("title"), "year": item.get("year"), "venue": item.get("venue")}
        for item in payload
        if isinstance(item, dict)
    ]


def _constraints_from_project(project, paper_slug: str | None) -> str:
    paper = next((item for item in project.papers if item.slug == paper_slug), None)
    parts = []
    if paper and paper.deadline:
        parts.append(f"deadline={paper.deadline}")
    if paper and paper.target_venue:
        parts.append(f"venue={paper.target_venue}")
    return "; ".join(parts)


def _compact_list(items: list, limit: int = 5) -> str:
    if not items:
        return "无"
    rendered = []
    for item in items[:limit]:
        if isinstance(item, dict):
            rendered.append(str(item.get("content") or item.get("title") or item.get("file") or item))
        else:
            rendered.append(str(item))
    suffix = f"；另有 {len(items) - limit} 项" if len(items) > limit else ""
    return "；".join(rendered) + suffix
