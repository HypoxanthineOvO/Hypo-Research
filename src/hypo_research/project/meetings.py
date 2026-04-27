"""Meeting note management for projects."""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

from hypo_research.project.manager import ProjectManager, slugify
from hypo_research.project.models import MeetingNote


def add_meeting(
    project_slug: str,
    content: str,
    tag: str = "general",
    title: str | None = None,
    date: str | None = None,
    related_paper: str | None = None,
) -> MeetingNote:
    """Add a meeting note and index extracted decisions/actions."""
    manager = ProjectManager()
    project = manager.load_project(project_slug)
    meeting_date = date or datetime.now().date().isoformat()
    source_path = Path(content)
    if source_path.exists():
        raw_content = source_path.read_text(encoding="utf-8")
        source_file = source_path.as_posix()
    else:
        raw_content = content
        source_file = None
    meeting_id = _next_meeting_id(project.meetings)
    note_title = title or _infer_title(raw_content, tag, meeting_date)
    extracted = extract_meeting_items(raw_content)
    filename = f"{meeting_date}-{slugify(tag)}-{meeting_id}.md"
    dest = manager.project_dir(project_slug) / "meetings" / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source_file:
        shutil.copy2(source_path, dest)
    else:
        dest.write_text(raw_content, encoding="utf-8")
    note = MeetingNote(
        id=meeting_id,
        date=meeting_date,
        tag=tag,
        title=note_title,
        content=raw_content,
        key_decisions=extracted["key_decisions"],
        action_items=extracted["action_items"],
        related_paper=related_paper,
        source_file=dest.relative_to(manager.project_dir(project_slug)).as_posix(),
    )
    project.meetings.append(note)
    for decision in note.key_decisions:
        project.decisions.append({"date": meeting_date, "content": decision, "context": f"meeting:{meeting_id}"})
    manager.save_project(project)
    return note


def list_meetings(
    project_slug: str,
    tag: str | None = None,
    paper_slug: str | None = None,
) -> list[MeetingNote]:
    """List meeting notes with optional filters."""
    meetings = ProjectManager().load_project(project_slug).meetings
    if tag is not None:
        meetings = [item for item in meetings if item.tag == tag]
    if paper_slug is not None:
        meetings = [item for item in meetings if item.related_paper == paper_slug]
    return meetings


def get_meeting_context(project_slug: str) -> dict:
    """Collect key decisions and action items from meeting notes."""
    project = ProjectManager().load_project(project_slug)
    key_decisions = [
        {"date": note.date, "source": note.tag, "content": decision}
        for note in project.meetings
        for decision in note.key_decisions
    ]
    action_items = [
        {"content": action, "done": False, "due": _extract_due(action)}
        for note in project.meetings
        for action in note.action_items
    ]
    open_questions = _extract_open_questions(project.meetings)
    return {"key_decisions": key_decisions, "action_items": action_items, "open_questions": open_questions}


def extract_meeting_items(content: str) -> dict:
    """Extract decisions and action items with deterministic rules."""
    decisions: list[str] = []
    actions: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip(" -\t")
        if not line:
            continue
        lower = line.lower()
        if any(keyword in line for keyword in ["决定", "导师说", "结论", "不要做", "方向OK", "需要改"]) or "decision" in lower:
            decisions.append(_strip_marker(line))
        if any(keyword in line for keyword in ["TODO", "Action", "action", "下周", "完成", "补充", "跑实验"]):
            actions.append(_strip_marker(line))
    return {
        "key_decisions": list(dict.fromkeys(decisions)),
        "action_items": list(dict.fromkeys(actions)),
    }


def _next_meeting_id(meetings: list[MeetingNote]) -> str:
    existing = {item.id for item in meetings}
    index = 1
    while f"mtg-{index:03d}" in existing:
        index += 1
    return f"mtg-{index:03d}"


def _infer_title(content: str, tag: str, meeting_date: str) -> str:
    first = next((line.strip("# ") for line in content.splitlines() if line.strip()), "")
    return first[:80] if first else f"{meeting_date} {tag} 会议"


def _strip_marker(line: str) -> str:
    return re.sub(r"^(TODO|Action|Decision|决定|结论)[:：]\s*", "", line, flags=re.IGNORECASE)


def _extract_due(action: str) -> str | None:
    match = re.search(r"\d{4}-\d{2}-\d{2}", action)
    return match.group(0) if match else None


def _extract_open_questions(meetings: list[MeetingNote]) -> list[str]:
    questions: list[str] = []
    for note in meetings:
        for line in note.content.splitlines():
            cleaned = line.strip(" -\t")
            if cleaned.endswith("?") or cleaned.endswith("？"):
                questions.append(cleaned)
    return questions
