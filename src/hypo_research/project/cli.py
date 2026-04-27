"""CLI commands for persistent research projects."""

from __future__ import annotations

import json
from pathlib import Path

import click

from hypo_research.ideation.challenge import challenge_idea
from hypo_research.ideation.cli import load_idea
from hypo_research.ideation.experiment import design_experiment
from hypo_research.ideation.models import ChallengeSeverity
from hypo_research.ideation.pilot import run_pilot
from hypo_research.ideation.planning import create_plan
from hypo_research.ideation.strategies import generate_ideas
from hypo_research.project.context import (
    build_context,
    inject_context_to_challenge,
    inject_context_to_experiment,
    inject_context_to_idea,
    inject_context_to_plan,
)
from hypo_research.project.dashboard import render_dashboard
from hypo_research.project.manager import ProjectManager
from hypo_research.project.meetings import add_meeting, list_meetings
from hypo_research.project.models import PaperStage, to_dict
from hypo_research.project.progress import add_milestone, complete_milestone
from hypo_research.project.rebuttal import generate_rebuttal


@click.group("project")
def project_group() -> None:
    """管理持久化科研项目。"""


@project_group.command("create")
@click.argument("name")
@click.option("--direction", required=True, help="研究方向描述。")
@click.option("--description", default="", help="项目说明。")
def project_create(name: str, direction: str, description: str) -> None:
    """创建科研项目。"""
    project = ProjectManager().create_project(name, direction, description)
    click.echo(f"已创建项目：{project.slug}")


@project_group.command("list")
def project_list() -> None:
    """列出科研项目。"""
    projects = ProjectManager().list_projects()
    if not projects:
        click.echo("暂无项目。")
        return
    for project in projects:
        click.echo(f"- {project.slug} | {project.name} | {project.stage.value} | {project.direction}")


@project_group.command("status")
@click.argument("project_slug")
@click.option("--brief", is_flag=True, default=False)
@click.option("--paper", "paper_slug", default=None)
@click.option("--milestones", "milestones_only", is_flag=True, default=False)
@click.option("--meetings", "meetings_only", is_flag=True, default=False)
def project_status(
    project_slug: str,
    brief: bool,
    paper_slug: str | None,
    milestones_only: bool,
    meetings_only: bool,
) -> None:
    """显示项目仪表盘。"""
    click.echo(render_dashboard(project_slug, brief, paper_slug, milestones_only, meetings_only))


@project_group.command("archive")
@click.argument("project_slug")
def project_archive(project_slug: str) -> None:
    """归档项目。"""
    ProjectManager().archive_project(project_slug)
    click.echo(f"已归档项目：{project_slug}")


@project_group.command("delete")
@click.argument("project_slug")
@click.option("--confirm", is_flag=True, default=False)
def project_delete(project_slug: str, confirm: bool) -> None:
    """删除项目。"""
    ProjectManager().delete_project(project_slug, confirm=confirm)
    click.echo(f"已删除项目：{project_slug}")


@project_group.group("paper")
def paper_group() -> None:
    """管理项目下的论文。"""


@paper_group.command("add")
@click.argument("project_slug")
@click.argument("title")
@click.option("--slug", "paper_slug", required=True)
@click.option("--venue", default=None)
@click.option("--deadline", default=None)
def paper_add(project_slug: str, title: str, paper_slug: str, venue: str | None, deadline: str | None) -> None:
    """新增论文。"""
    paper = ProjectManager().add_paper(project_slug, title, paper_slug, venue, deadline)
    click.echo(f"已新增论文：{paper.slug}")


@paper_group.command("list")
@click.argument("project_slug")
def paper_list(project_slug: str) -> None:
    """列出项目论文。"""
    papers = ProjectManager().list_papers(project_slug)
    if not papers:
        click.echo("暂无论文。")
        return
    for paper in papers:
        click.echo(f"- {paper.slug} | {paper.title} | {paper.stage.value} | {paper.target_venue or '-'}")


@paper_group.command("update")
@click.argument("project_slug")
@click.argument("paper_slug")
@click.option("--stage", type=click.Choice([item.value for item in PaperStage]), default=None)
@click.option("--venue", default=None)
@click.option("--deadline", default=None)
@click.option("--note", default=None)
def paper_update(
    project_slug: str,
    paper_slug: str,
    stage: str | None,
    venue: str | None,
    deadline: str | None,
    note: str | None,
) -> None:
    """更新论文配置。"""
    paper = ProjectManager().update_paper(
        project_slug,
        paper_slug,
        stage=stage,
        target_venue=venue,
        deadline=deadline,
        notes=note,
    )
    click.echo(f"已更新论文：{paper.slug}，阶段={paper.stage.value}")


@project_group.group("milestone")
def milestone_group() -> None:
    """管理里程碑。"""


@milestone_group.command("add")
@click.argument("project_slug")
@click.argument("description")
@click.option("--paper", "paper_slug", default=None)
@click.option("--due", "due_date", default=None)
def milestone_add(project_slug: str, description: str, paper_slug: str | None, due_date: str | None) -> None:
    """新增里程碑。"""
    milestone = add_milestone(project_slug, paper_slug, description, due_date)
    click.echo(f"已新增里程碑：{milestone.id}")


@milestone_group.command("done")
@click.argument("project_slug")
@click.argument("milestone_id")
@click.option("--note", default="")
def milestone_done(project_slug: str, milestone_id: str, note: str) -> None:
    """完成里程碑。"""
    complete_milestone(project_slug, milestone_id, note)
    click.echo(f"已完成里程碑：{milestone_id}")


@milestone_group.command("list")
@click.argument("project_slug")
@click.option("--paper", "paper_slug", default=None)
@click.option("--overdue", is_flag=True, default=False)
def milestone_list(project_slug: str, paper_slug: str | None, overdue: bool) -> None:
    """列出里程碑。"""
    project = ProjectManager().load_project(project_slug)
    milestones = [*project.milestones, *[item for paper in project.papers for item in paper.milestones]]
    if paper_slug:
        milestones = [item for item in milestones if item.paper_slug == paper_slug]
    if overdue:
        from datetime import date

        today = date.today().isoformat()
        milestones = [item for item in milestones if item.due_date and item.due_date < today and not item.done]
    for milestone in milestones:
        click.echo(f"- {milestone.id} | {milestone.description} | due={milestone.due_date or '-'} | done={milestone.done}")


@project_group.group("meeting")
def meeting_group() -> None:
    """管理会议纪要。"""


@meeting_group.command("add")
@click.argument("project_slug")
@click.option("--file", "file_path", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None)
@click.option("--text", default=None)
@click.option("--tag", default="general")
@click.option("--title", default=None)
@click.option("--date", "meeting_date", default=None)
@click.option("--paper", "paper_slug", default=None)
def meeting_add(
    project_slug: str,
    file_path: Path | None,
    text: str | None,
    tag: str,
    title: str | None,
    meeting_date: str | None,
    paper_slug: str | None,
) -> None:
    """新增会议纪要。"""
    if file_path is None and text is None:
        raise click.ClickException("必须提供 --file 或 --text")
    note = add_meeting(project_slug, file_path.as_posix() if file_path else text or "", tag, title, meeting_date, paper_slug)
    click.echo(f"已新增会议纪要：{note.id}")
    click.echo(f"关键决策：{len(note.key_decisions)} 条；Action items：{len(note.action_items)} 条")


@meeting_group.command("list")
@click.argument("project_slug")
@click.option("--tag", default=None)
@click.option("--paper", "paper_slug", default=None)
def meeting_list(project_slug: str, tag: str | None, paper_slug: str | None) -> None:
    """列出会议纪要。"""
    for note in list_meetings(project_slug, tag, paper_slug):
        click.echo(f"- {note.id} | {note.date} | {note.tag} | {note.title}")


@meeting_group.command("import")
@click.argument("project_slug")
@click.option("--from", "source", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--tag", default="general")
@click.option("--paper", "paper_slug", default=None)
def meeting_import(project_slug: str, source: Path, tag: str, paper_slug: str | None) -> None:
    """导入 hypo-meeting 或 Markdown 输出。"""
    note = add_meeting(project_slug, source.as_posix(), tag=tag, related_paper=paper_slug)
    click.echo(f"已导入会议纪要：{note.id}")


@project_group.group("import")
def import_group() -> None:
    """导入已有输出。"""


@import_group.command("survey")
@click.argument("project_slug")
@click.argument("survey_file", type=click.Path(exists=True, dir_okay=False))
def import_survey(project_slug: str, survey_file: str) -> None:
    dest = ProjectManager().import_survey(project_slug, survey_file)
    click.echo(f"已导入 survey：{dest}")


@import_group.command("idea")
@click.argument("project_slug")
@click.argument("idea_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--paper", "paper_slug", required=True)
def import_idea(project_slug: str, idea_file: str, paper_slug: str) -> None:
    record = ProjectManager().import_idea(project_slug, paper_slug, idea_file)
    click.echo(f"已导入 idea：{record.id}")


@import_group.command("challenge")
@click.argument("project_slug")
@click.argument("challenge_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--paper", "paper_slug", required=True)
@click.option("--idea", "idea_id", required=True)
def import_challenge(project_slug: str, challenge_file: str, paper_slug: str, idea_id: str) -> None:
    ProjectManager().import_challenge(project_slug, paper_slug, _normalize_idea_id(idea_id), challenge_file)
    click.echo(f"已导入 challenge：{idea_id}")


@project_group.command("idea")
@click.argument("project_slug")
@click.option("--paper", "paper_slug", default=None)
@click.option("--num-ideas", default=3)
@click.option("--mode", type=click.Choice(["quick_win", "ambitious"]), default=None)
def project_idea(project_slug: str, paper_slug: str | None, num_ideas: int, mode: str | None) -> None:
    """带项目上下文生成 idea。"""
    from hypo_research.ideation.models import IdeaMode

    context = build_context(project_slug, paper_slug)
    prompt_context = inject_context_to_idea(context)
    result = generate_ideas(
        context["project_direction"],
        constraints=prompt_context,
        mode=IdeaMode(mode) if mode else None,
        num_ideas=num_ideas,
    )
    click.echo(prompt_context)
    click.echo(json.dumps(to_dict(result), ensure_ascii=False, indent=2))


@project_group.command("challenge")
@click.argument("project_slug")
@click.option("--paper", "paper_slug", required=True)
@click.option("--idea", "idea_id", required=True)
@click.option("--severity", type=click.Choice(["gentle", "standard", "harsh"]), default="harsh")
def project_challenge(project_slug: str, paper_slug: str, idea_id: str, severity: str) -> None:
    """带项目上下文拷打 idea。"""
    idea_path = _idea_path(project_slug, paper_slug, idea_id)
    context = build_context(project_slug, paper_slug)
    result = challenge_idea(load_idea(idea_path), ChallengeSeverity(severity))
    click.echo(inject_context_to_challenge(context))
    click.echo(json.dumps(to_dict(result), ensure_ascii=False, indent=2))


@project_group.command("experiment")
@click.argument("project_slug")
@click.option("--paper", "paper_slug", required=True)
@click.option("--idea", "idea_id", required=True)
def project_experiment(project_slug: str, paper_slug: str, idea_id: str) -> None:
    """带项目上下文设计实验。"""
    idea = load_idea(_idea_path(project_slug, paper_slug, idea_id))
    context = build_context(project_slug, paper_slug)
    result = design_experiment(idea, constraints=inject_context_to_experiment(context))
    click.echo(inject_context_to_experiment(context))
    click.echo(json.dumps(to_dict(result), ensure_ascii=False, indent=2))


@project_group.command("plan")
@click.argument("project_slug")
@click.option("--paper", "paper_slug", required=True)
@click.option("--idea", "idea_id", required=True)
def project_plan(project_slug: str, paper_slug: str, idea_id: str) -> None:
    """带项目上下文生成工作计划。"""
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    paper = next(item for item in project.papers if item.slug == paper_slug)
    idea = load_idea(_idea_path(project_slug, paper_slug, idea_id))
    context = build_context(project_slug, paper_slug)
    experiment = design_experiment(idea, venue=paper.target_venue, constraints=inject_context_to_experiment(context))
    result = create_plan(idea, experiment, venue=paper.target_venue, deadline=paper.deadline, resources=inject_context_to_plan(context))
    click.echo(inject_context_to_plan(context))
    click.echo(json.dumps(to_dict(result), ensure_ascii=False, indent=2))


@project_group.command("pilot")
@click.argument("project_slug")
@click.option("--paper", "paper_slug", default=None)
@click.option("--auto-select", is_flag=True, default=True)
def project_pilot(project_slug: str, paper_slug: str | None, auto_select: bool) -> None:
    """带项目上下文运行 hypo-pilot。"""
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    paper = next((item for item in project.papers if item.slug == paper_slug), None)
    context = build_context(project_slug, paper_slug)
    report = run_pilot(
        project.direction,
        constraints=inject_context_to_idea(context),
        venue=paper.target_venue if paper else None,
        deadline=paper.deadline if paper else None,
        auto_select=auto_select,
    )
    click.echo(json.dumps(to_dict(report), ensure_ascii=False, indent=2))


@project_group.command("rebuttal")
@click.argument("project_slug")
@click.option("--paper", "paper_slug", required=True)
@click.option("--reviews", "reviews_file", required=True, type=click.Path(exists=True, dir_okay=False))
def project_rebuttal(project_slug: str, paper_slug: str, reviews_file: str) -> None:
    """带项目上下文生成 rebuttal。"""
    context = build_context(project_slug, paper_slug)
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    paper = next(item for item in project.papers if item.slug == paper_slug)
    result = generate_rebuttal(reviews_file, project_context={**context, "paper_title": paper.title, "venue": paper.target_venue})
    dest = manager.project_dir(project_slug) / "papers" / paper_slug / "rebuttals" / "rebuttal.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(to_dict(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    click.echo(result.rebuttal_letter)


@click.command("rebuttal")
@click.argument("reviews_file", type=click.Path(exists=True, dir_okay=False))
@click.option("--paper-draft", default=None)
@click.option("--experiment-results", default=None)
@click.option("--project", "project_slug", default=None)
@click.option("--paper", "paper_slug", default=None)
@click.option("--output", "output_format", type=click.Choice(["json", "markdown"]), default="markdown")
def rebuttal_command(
    reviews_file: str,
    paper_draft: str | None,
    experiment_results: str | None,
    project_slug: str | None,
    paper_slug: str | None,
    output_format: str,
) -> None:
    """生成 rebuttal。"""
    context = build_context(project_slug, paper_slug) if project_slug else None
    result = generate_rebuttal(reviews_file, paper_draft, experiment_results, context)
    if output_format == "json":
        click.echo(json.dumps(to_dict(result), ensure_ascii=False, indent=2))
    else:
        click.echo(result.rebuttal_letter)


PROJECT_COMMANDS = [project_group, rebuttal_command]


def _normalize_idea_id(value: str) -> str:
    return value if value.startswith("idea-") else f"idea-{int(value):03d}" if value.isdigit() else value


def _idea_path(project_slug: str, paper_slug: str, idea_id: str) -> Path:
    normalized = _normalize_idea_id(idea_id)
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    paper = next(item for item in project.papers if item.slug == paper_slug)
    record = next(item for item in paper.ideas if item.id == normalized)
    return manager.project_dir(project_slug) / record.idea_file
