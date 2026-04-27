"""Persistent research project management."""

from hypo_research.project.manager import ProjectManager, slugify
from hypo_research.project.models import (
    IdeaRecord,
    IdeaStatus,
    MeetingNote,
    Milestone,
    PaperConfig,
    PaperStage,
    ProjectStage,
    RebuttalResponse,
    RebuttalResult,
    ResearchProject,
    ReviewComment,
)

__all__ = [
    "IdeaRecord",
    "IdeaStatus",
    "MeetingNote",
    "Milestone",
    "PaperConfig",
    "PaperStage",
    "ProjectManager",
    "ProjectStage",
    "RebuttalResponse",
    "RebuttalResult",
    "ResearchProject",
    "ReviewComment",
    "slugify",
]
