"""Progress tracking for research projects."""

from __future__ import annotations

from datetime import date, datetime

from hypo_research.project.manager import ProjectManager
from hypo_research.project.models import Milestone, PaperConfig, PaperStage, ResearchProject


STAGE_WEIGHTS = {
    "survey": 10,
    "ideation": 15,
    "experiment": 35,
    "writing": 25,
    "review": 10,
    "rebuttal": 5,
}

PAPER_STAGE_ORDER = [
    PaperStage.SURVEY,
    PaperStage.IDEATION,
    PaperStage.EXPERIMENT,
    PaperStage.WRITING,
    PaperStage.REVIEW,
    PaperStage.REBUTTAL,
]


def compute_paper_progress(paper: PaperConfig) -> dict:
    """Compute progress for a single paper."""
    percentage = _stage_percentage(paper)
    milestones = _milestone_summary(paper.milestones)
    return {
        "stage": paper.stage.value,
        "percentage": percentage,
        "stage_details": {
            "survey": {"status": "done" if percentage >= 10 else "in_progress"},
            "ideation": {
                "status": "done" if paper.ideas else "not_started",
                "active_idea": _active_idea_id(paper),
                "rejected": len([idea for idea in paper.ideas if idea.status.value == "rejected"]),
            },
            "experiment": {"status": "in_progress" if paper.stage == PaperStage.EXPERIMENT else _status_after(paper, PaperStage.EXPERIMENT)},
            "writing": {"status": "in_progress" if paper.stage == PaperStage.WRITING else _status_after(paper, PaperStage.WRITING)},
            "submission": {"status": "done" if paper.stage in {PaperStage.ACCEPTED, PaperStage.REJECTED} else "not_started"},
        },
        "milestones": milestones,
        "days_to_deadline": days_to_date(paper.deadline),
    }


def compute_project_progress(project: ResearchProject) -> dict:
    """Compute aggregate project progress."""
    paper_progress = {paper.slug: compute_paper_progress(paper) for paper in project.papers}
    average = round(sum(item["percentage"] for item in paper_progress.values()) / len(paper_progress), 1) if paper_progress else 0
    project_milestones = _milestone_summary(project.milestones)
    return {
        "project": project.slug,
        "stage": project.stage.value,
        "paper_count": len(project.papers),
        "percentage": average,
        "papers": paper_progress,
        "milestones": project_milestones,
    }


def update_stage(project_slug: str, paper_slug: str, stage: PaperStage, note: str = "") -> None:
    """Manually update a paper stage."""
    manager = ProjectManager()
    paper = manager.update_paper(project_slug, paper_slug, stage=stage.value)
    if note:
        project = manager.load_project(project_slug)
        project.decisions.append({"date": _today(), "content": note, "context": f"stage:{paper.slug}:{stage.value}"})
        manager.save_project(project)


def add_milestone(
    project_slug: str,
    paper_slug: str | None,
    description: str,
    due_date: str | None = None,
) -> Milestone:
    """Add a milestone to a project or paper."""
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    milestone = Milestone(
        id=_next_milestone_id([*project.milestones, *[item for paper in project.papers for item in paper.milestones]]),
        description=description,
        due_date=due_date,
        paper_slug=paper_slug,
    )
    if paper_slug is None:
        project.milestones.append(milestone)
    else:
        paper = next((item for item in project.papers if item.slug == paper_slug), None)
        if paper is None:
            raise KeyError(f"找不到论文：{paper_slug}")
        paper.milestones.append(milestone)
        manager._write_paper(project_slug, paper)
    manager.save_project(project)
    return milestone


def complete_milestone(project_slug: str, milestone_id: str, note: str = "") -> None:
    """Mark a milestone as done."""
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    milestone = _find_milestone(project, milestone_id)
    if milestone is None:
        raise KeyError(f"找不到里程碑：{milestone_id}")
    milestone.done = True
    milestone.done_date = _today()
    milestone.notes = note or milestone.notes
    for paper in project.papers:
        manager._write_paper(project_slug, paper)
    manager.save_project(project)


def days_to_date(value: str | None) -> int | None:
    """Return days from today to an ISO date."""
    if not value:
        return None
    target = date.fromisoformat(value)
    return (target - date.today()).days


def _stage_percentage(paper: PaperConfig) -> int:
    if paper.stage == PaperStage.ACCEPTED:
        return 100
    if paper.stage in {PaperStage.REJECTED, PaperStage.ABANDONED}:
        return min(100, sum(STAGE_WEIGHTS.values()))
    percentage = 0
    for stage in PAPER_STAGE_ORDER:
        if stage == paper.stage:
            percentage += _current_stage_credit(paper, stage)
            break
        percentage += STAGE_WEIGHTS.get(stage.value, 0)
    milestone_bonus = _milestone_completion_bonus(paper.milestones)
    return min(100, round(percentage + milestone_bonus))


def _current_stage_credit(paper: PaperConfig, stage: PaperStage) -> float:
    weight = STAGE_WEIGHTS.get(stage.value, 0)
    if not paper.milestones:
        return weight * 0.35
    related = [item for item in paper.milestones if item.paper_slug in {None, paper.slug}]
    if not related:
        return weight * 0.35
    done = len([item for item in related if item.done])
    return weight * max(0.25, done / len(related))


def _milestone_completion_bonus(milestones: list[Milestone]) -> float:
    if not milestones:
        return 0
    done = len([item for item in milestones if item.done])
    return min(5, 5 * done / len(milestones))


def _milestone_summary(milestones: list[Milestone]) -> dict:
    today = date.today()
    upcoming = []
    overdue = 0
    for milestone in milestones:
        if milestone.done or not milestone.due_date:
            continue
        due = date.fromisoformat(milestone.due_date)
        delta = (due - today).days
        if delta < 0:
            overdue += 1
        elif delta <= 14:
            upcoming.append({"desc": milestone.description, "due": milestone.due_date, "days_left": delta})
    upcoming.sort(key=lambda item: item["days_left"])
    return {
        "total": len(milestones),
        "done": len([item for item in milestones if item.done]),
        "overdue": overdue,
        "upcoming": upcoming,
    }


def _status_after(paper: PaperConfig, stage: PaperStage) -> str:
    try:
        current = PAPER_STAGE_ORDER.index(paper.stage)
        target = PAPER_STAGE_ORDER.index(stage)
    except ValueError:
        return "done" if paper.stage == PaperStage.ACCEPTED else "not_started"
    if current > target:
        return "done"
    return "not_started"


def _active_idea_id(paper: PaperConfig) -> str | None:
    for idea in paper.ideas:
        if idea.status.value in {"selected", "refined", "active", "completed"}:
            return idea.id
    return paper.ideas[0].id if paper.ideas else None


def _next_milestone_id(milestones: list[Milestone]) -> str:
    existing = {item.id for item in milestones}
    index = 1
    while f"ms-{index:03d}" in existing:
        index += 1
    return f"ms-{index:03d}"


def _find_milestone(project: ResearchProject, milestone_id: str) -> Milestone | None:
    for milestone in project.milestones:
        if milestone.id == milestone_id:
            return milestone
    for paper in project.papers:
        for milestone in paper.milestones:
            if milestone.id == milestone_id:
                return milestone
    return None


def _today() -> str:
    return datetime.now().date().isoformat()
