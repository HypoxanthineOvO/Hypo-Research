"""Terminal dashboard rendering for projects."""

from __future__ import annotations

from hypo_research.project.context import build_context
from hypo_research.project.manager import ProjectManager
from hypo_research.project.progress import compute_paper_progress, compute_project_progress


def render_dashboard(
    project_slug: str,
    brief: bool = False,
    paper_slug: str | None = None,
    milestones_only: bool = False,
    meetings_only: bool = False,
) -> str:
    """Render a text dashboard for a project."""
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    context = build_context(project_slug, paper_slug)
    if meetings_only:
        return _render_meetings(project)
    if milestones_only:
        return _render_milestones(project)
    papers = [paper for paper in project.papers if paper_slug in {None, paper.slug}]
    lines = [
        f"项目：{project.name}",
        f"方向：{project.direction}",
        f"阶段：{project.stage.value}",
        f"创建：{project.created_at or '-'}",
        "",
    ]
    if not papers:
        lines.append("暂无论文。")
    for paper in papers:
        progress = compute_paper_progress(paper)
        lines.extend(_render_paper(paper, progress, brief))
    if not brief:
        lines.extend(["", "近期里程碑", *_milestone_lines(project)])
        lines.extend(["", "最近会议决策", *_decision_lines(context)])
        lines.extend(["", "待办 Action Items", *_action_lines(context)])
        summary = compute_project_progress(project)
        lines.extend(["", f"项目整体进度：{summary['percentage']}%"])
    return "\n".join(lines)


def _render_paper(paper, progress: dict, brief: bool) -> list[str]:
    lines = [
        f"论文：{paper.title} ({paper.slug})",
        f"目标：{paper.target_venue or '-'} | 截稿：{paper.deadline or '-'} | 阶段：{paper.stage.value}",
        f"进度：{_bar(progress['percentage'])} {progress['percentage']}%",
    ]
    if progress["days_to_deadline"] is not None:
        lines.append(f"距离截稿：{progress['days_to_deadline']} 天")
    if not brief:
        details = progress["stage_details"]
        lines.extend(
            [
                f"Survey：{details['survey']['status']}",
                f"Idea：{details['ideation']['status']}，active={details['ideation']['active_idea'] or '-'}，rejected={details['ideation']['rejected']}",
                f"Experiment：{details['experiment']['status']}",
                f"Writing：{details['writing']['status']}",
                f"Submission：{details['submission']['status']}",
                "",
            ]
        )
    return lines


def _render_meetings(project) -> str:
    lines = [f"会议纪要：{project.name}"]
    for note in project.meetings:
        lines.append(f"- [{note.date} {note.tag}] {note.title}")
        for decision in note.key_decisions:
            lines.append(f"  决策：{decision}")
        for action in note.action_items:
            lines.append(f"  待办：{action}")
    return "\n".join(lines)


def _render_milestones(project) -> str:
    return "\n".join(["里程碑", *_milestone_lines(project)])


def _milestone_lines(project) -> list[str]:
    milestones = [*project.milestones, *[item for paper in project.papers for item in paper.milestones]]
    milestones.sort(key=lambda item: item.due_date or "9999-12-31")
    if not milestones:
        return ["- 暂无里程碑"]
    return [
        f"- [{'完成' if item.done else '待办'}] {item.description} | due={item.due_date or '-'} | paper={item.paper_slug or 'project'}"
        for item in milestones
    ]


def _decision_lines(context: dict) -> list[str]:
    decisions = context["meetings"]["key_decisions"][-5:]
    return [f"- [{item['date']} {item['source']}] {item['content']}" for item in decisions] or ["- 暂无会议决策"]


def _action_lines(context: dict) -> list[str]:
    actions = context["meetings"]["action_items"][:8]
    return [f"- [ ] {item['content']}" for item in actions] or ["- 暂无待办"]


def _bar(percentage: float) -> str:
    filled = int(round(percentage / 10))
    return "█" * filled + "░" * (10 - filled)
