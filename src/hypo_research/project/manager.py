"""Filesystem-backed project manager."""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from hypo_research.project.models import (
    IdeaRecord,
    IdeaStatus,
    PaperConfig,
    PaperStage,
    ProjectStage,
    ResearchProject,
    from_dict,
    to_dict,
)


PROJECT_SUBDIRS = ["surveys", "literature", "meetings", "notes", "papers"]
PAPER_SUBDIRS = ["ideas", "challenges", "experiments", "plans", "drafts", "reviews", "rebuttals"]


class ProjectManager:
    """Manage projects under ~/.hypo-research/projects/."""

    BASE_DIR = Path.home() / ".hypo-research" / "projects"

    def __init__(self, base_dir: str | Path | None = None) -> None:
        env_dir = os.environ.get("HYPO_RESEARCH_PROJECTS_DIR")
        self.base_dir = Path(base_dir or env_dir) if (base_dir is not None or env_dir) else self.BASE_DIR

    def create_project(self, name: str, direction: str, description: str = "") -> ResearchProject:
        """Create a new project and initialize its directory structure."""
        slug = slugify(name)
        project_dir = self._project_dir(slug)
        if project_dir.exists():
            raise FileExistsError(f"项目已存在：{slug}")
        now = _now()
        project = ResearchProject(
            name=name,
            slug=slug,
            description=description,
            direction=direction,
            stage=ProjectStage.EXPLORATION,
            created_at=now,
            updated_at=now,
        )
        self._init_project_dirs(project_dir)
        self._write_project(project)
        (project_dir / "literature" / "papers.json").write_text("[]\n", encoding="utf-8")
        (project_dir / "progress.json").write_text("{}\n", encoding="utf-8")
        (project_dir / "decisions.log").write_text("", encoding="utf-8")
        return project

    def load_project(self, slug: str) -> ResearchProject:
        """Load an existing project from project.json."""
        project_file = self._project_dir(slug) / "project.json"
        if not project_file.exists():
            raise FileNotFoundError(f"找不到项目：{slug}")
        payload = json.loads(project_file.read_text(encoding="utf-8"))
        return from_dict(ResearchProject, payload)

    def list_projects(self) -> list[ResearchProject]:
        """List all projects."""
        if not self.base_dir.exists():
            return []
        projects: list[ResearchProject] = []
        for project_file in sorted(self.base_dir.glob("*/project.json")):
            projects.append(from_dict(ResearchProject, json.loads(project_file.read_text(encoding="utf-8"))))
        return projects

    def archive_project(self, slug: str) -> None:
        """Archive a project."""
        project = self.load_project(slug)
        project.stage = ProjectStage.ARCHIVED
        project.updated_at = _now()
        self._write_project(project)

    def delete_project(self, slug: str, confirm: bool = False) -> None:
        """Delete a project. Confirmation is required."""
        if not confirm:
            raise ValueError("删除项目需要 confirm=True")
        shutil.rmtree(self._project_dir(slug))

    def add_paper(
        self,
        project_slug: str,
        title: str,
        slug: str,
        venue: str | None = None,
        deadline: str | None = None,
    ) -> PaperConfig:
        """Add a paper under a project."""
        project = self.load_project(project_slug)
        paper_slug = slugify(slug)
        if self._find_paper(project, paper_slug) is not None:
            raise FileExistsError(f"论文已存在：{paper_slug}")
        now = _now()
        paper = PaperConfig(
            slug=paper_slug,
            title=title,
            stage=PaperStage.SURVEY,
            target_venue=venue,
            deadline=deadline,
            created_at=now,
            updated_at=now,
        )
        paper_dir = self._paper_dir(project_slug, paper_slug)
        for subdir in PAPER_SUBDIRS:
            (paper_dir / subdir).mkdir(parents=True, exist_ok=True)
        self._write_paper(project_slug, paper)
        project.papers.append(paper)
        project.stage = ProjectStage.ACTIVE
        project.updated_at = now
        self._write_project(project)
        return paper

    def update_paper(self, project_slug: str, paper_slug: str, **kwargs: Any) -> PaperConfig:
        """Update paper configuration."""
        project = self.load_project(project_slug)
        paper = self._require_paper(project, paper_slug)
        allowed = {"title", "stage", "target_venue", "deadline", "collaborators", "notes"}
        for key, value in kwargs.items():
            if key not in allowed or value is None:
                continue
            if key == "stage":
                value = PaperStage(value)
            setattr(paper, key, value)
        paper.updated_at = _now()
        project.updated_at = paper.updated_at
        self._replace_paper(project, paper)
        self._write_paper(project_slug, paper)
        self._write_project(project)
        return paper

    def list_papers(self, project_slug: str) -> list[PaperConfig]:
        """List papers under a project."""
        return self.load_project(project_slug).papers

    def import_survey(self, project_slug: str, survey_file: str) -> str:
        """Import a hypo-survey output into the project."""
        project = self.load_project(project_slug)
        src = Path(survey_file)
        if not src.exists():
            raise FileNotFoundError(survey_file)
        dest = self._unique_dest(self._project_dir(project_slug) / "surveys", src.name)
        shutil.copy2(src, dest)
        self._merge_literature(project_slug, src)
        project.updated_at = _now()
        self._write_project(project)
        return dest.as_posix()

    def import_idea(self, project_slug: str, paper_slug: str, idea_file: str) -> IdeaRecord:
        """Import an idea result into a paper."""
        project = self.load_project(project_slug)
        paper = self._require_paper(project, paper_slug)
        src = Path(idea_file)
        if not src.exists():
            raise FileNotFoundError(idea_file)
        idea_id = self._next_id(paper.ideas, "idea")
        dest = self._paper_dir(project_slug, paper.slug) / "ideas" / f"{idea_id}{src.suffix or '.json'}"
        shutil.copy2(src, dest)
        meta = _extract_idea_meta(src)
        now = _now()
        record = IdeaRecord(
            id=idea_id,
            idea_file=dest.relative_to(self._project_dir(project_slug)).as_posix(),
            title=meta["title"],
            strategy=meta["strategy"],
            mode=meta["mode"],
            status=IdeaStatus.CANDIDATE,
            score=meta["score"],
            tier=meta["tier"],
            created_at=now,
            updated_at=now,
        )
        paper.ideas.append(record)
        paper.stage = PaperStage.IDEATION
        paper.updated_at = now
        project.updated_at = now
        self._replace_paper(project, paper)
        self._write_paper(project_slug, paper)
        self._write_project(project)
        return record

    def import_challenge(self, project_slug: str, paper_slug: str, idea_id: str, challenge_file: str) -> None:
        """Import a challenge result and update idea lifecycle."""
        project = self.load_project(project_slug)
        paper = self._require_paper(project, paper_slug)
        idea = self._require_idea(paper, idea_id)
        src = Path(challenge_file)
        if not src.exists():
            raise FileNotFoundError(challenge_file)
        dest = self._paper_dir(project_slug, paper.slug) / "challenges" / f"{idea_id}{src.suffix or '.json'}"
        shutil.copy2(src, dest)
        verdict = _extract_challenge_verdict(src)
        idea.challenge_file = dest.relative_to(self._project_dir(project_slug)).as_posix()
        idea.status = IdeaStatus.REJECTED if verdict == "建议放弃" else IdeaStatus.CHALLENGED
        idea.rejection_reason = verdict if idea.status == IdeaStatus.REJECTED else None
        idea.updated_at = _now()
        paper.updated_at = idea.updated_at
        project.updated_at = idea.updated_at
        self._replace_paper(project, paper)
        self._write_paper(project_slug, paper)
        self._write_project(project)

    def import_experiment(self, project_slug: str, paper_slug: str, experiment_file: str) -> None:
        """Import an experiment design."""
        self._import_paper_artifact(project_slug, paper_slug, experiment_file, "experiments", PaperStage.EXPERIMENT)

    def import_plan(self, project_slug: str, paper_slug: str, plan_file: str) -> None:
        """Import a research plan."""
        self._import_paper_artifact(project_slug, paper_slug, plan_file, "plans", None)

    def save_project(self, project: ResearchProject) -> None:
        """Persist a project."""
        project.updated_at = _now()
        self._write_project(project)

    def project_dir(self, slug: str) -> Path:
        """Return the project directory."""
        return self._project_dir(slug)

    def _import_paper_artifact(
        self,
        project_slug: str,
        paper_slug: str,
        source_file: str,
        subdir: str,
        stage: PaperStage | None,
    ) -> None:
        project = self.load_project(project_slug)
        paper = self._require_paper(project, paper_slug)
        src = Path(source_file)
        if not src.exists():
            raise FileNotFoundError(source_file)
        dest = self._unique_dest(self._paper_dir(project_slug, paper.slug) / subdir, src.name)
        shutil.copy2(src, dest)
        if stage is not None:
            paper.stage = stage
        paper.updated_at = _now()
        project.updated_at = paper.updated_at
        self._replace_paper(project, paper)
        self._write_paper(project_slug, paper)
        self._write_project(project)

    def _project_dir(self, slug: str) -> Path:
        return self.base_dir / slugify(slug)

    def _paper_dir(self, project_slug: str, paper_slug: str) -> Path:
        return self._project_dir(project_slug) / "papers" / slugify(paper_slug)

    def _init_project_dirs(self, project_dir: Path) -> None:
        for subdir in PROJECT_SUBDIRS:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _write_project(self, project: ResearchProject) -> None:
        project_dir = self._project_dir(project.slug)
        self._init_project_dirs(project_dir)
        (project_dir / "project.json").write_text(
            json.dumps(to_dict(project), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _write_paper(self, project_slug: str, paper: PaperConfig) -> None:
        paper_dir = self._paper_dir(project_slug, paper.slug)
        paper_dir.mkdir(parents=True, exist_ok=True)
        (paper_dir / "paper.json").write_text(
            json.dumps(to_dict(paper), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _find_paper(self, project: ResearchProject, paper_slug: str) -> PaperConfig | None:
        return next((paper for paper in project.papers if paper.slug == slugify(paper_slug)), None)

    def _require_paper(self, project: ResearchProject, paper_slug: str) -> PaperConfig:
        paper = self._find_paper(project, paper_slug)
        if paper is None:
            raise KeyError(f"找不到论文：{paper_slug}")
        return paper

    def _require_idea(self, paper: PaperConfig, idea_id: str) -> IdeaRecord:
        idea = next((item for item in paper.ideas if item.id == idea_id), None)
        if idea is None:
            raise KeyError(f"找不到 idea：{idea_id}")
        return idea

    def _replace_paper(self, project: ResearchProject, paper: PaperConfig) -> None:
        project.papers = [paper if item.slug == paper.slug else item for item in project.papers]

    def _next_id(self, records: list[Any], prefix: str) -> str:
        existing = {getattr(item, "id", "") for item in records}
        index = 1
        while f"{prefix}-{index:03d}" in existing:
            index += 1
        return f"{prefix}-{index:03d}"

    def _unique_dest(self, directory: Path, filename: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem
        suffix = Path(filename).suffix
        candidate = directory / filename
        index = 1
        while candidate.exists():
            candidate = directory / f"{stem}-{index}{suffix}"
            index += 1
        return candidate

    def _merge_literature(self, project_slug: str, survey_file: Path) -> None:
        papers_path = self._project_dir(project_slug) / "literature" / "papers.json"
        try:
            existing = json.loads(papers_path.read_text(encoding="utf-8")) if papers_path.exists() else []
            payload = json.loads(survey_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        candidates = payload.get("papers") if isinstance(payload, dict) else payload
        if not isinstance(candidates, list):
            return
        seen = {item.get("title") for item in existing if isinstance(item, dict)}
        for item in candidates:
            if isinstance(item, dict) and item.get("title") not in seen:
                existing.append(item)
                seen.add(item.get("title"))
        papers_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(value: str) -> str:
    """Create a filesystem-safe slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.strip().lower())
    return cleaned.strip("-") or "project"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _extract_idea_meta(path: Path) -> dict[str, Any]:
    default = {"title": path.stem, "strategy": "unknown", "mode": "unknown", "score": None, "tier": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        return {**default, "title": first_line[:120] if first_line else path.stem}
    if "selected_idea" in payload:
        payload = payload["selected_idea"]
    elif payload.get("quick_win_ideas"):
        payload = payload["quick_win_ideas"][0]
    elif payload.get("ambitious_ideas"):
        payload = payload["ambitious_ideas"][0]
    score = payload.get("score") if isinstance(payload, dict) else {}
    return {
        "title": payload.get("title", path.stem),
        "strategy": payload.get("strategy", "unknown"),
        "mode": payload.get("mode", "unknown"),
        "score": score.get("total_score") if isinstance(score, dict) else None,
        "tier": score.get("tier") if isinstance(score, dict) else None,
    }


def _extract_challenge_verdict(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload.get("verdict") if isinstance(payload, dict) else None
