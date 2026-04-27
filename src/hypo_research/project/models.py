"""Data models for persistent research projects."""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import Any, get_args, get_origin, get_type_hints


class ProjectStage(str, Enum):
    """Overall stage of a research direction."""

    EXPLORATION = "exploration"
    ACTIVE = "active"
    WINDING_DOWN = "winding_down"
    ARCHIVED = "archived"


class PaperStage(str, Enum):
    """Stage of a single paper under a research project."""

    SURVEY = "survey"
    IDEATION = "ideation"
    EXPERIMENT = "experiment"
    WRITING = "writing"
    REVIEW = "review"
    REBUTTAL = "rebuttal"
    REVISION = "revision"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ABANDONED = "abandoned"


class IdeaStatus(str, Enum):
    """Lifecycle status of an idea."""

    CANDIDATE = "candidate"
    SELECTED = "selected"
    CHALLENGED = "challenged"
    REFINED = "refined"
    ACTIVE = "active"
    REJECTED = "rejected"
    COMPLETED = "completed"


@dataclass
class Milestone:
    """A milestone in a project or paper."""

    id: str
    description: str
    due_date: str | None = None
    done: bool = False
    done_date: str | None = None
    paper_slug: str | None = None
    notes: str | None = None


@dataclass
class MeetingNote:
    """A meeting note indexed by the project."""

    id: str
    date: str
    tag: str
    title: str
    content: str
    key_decisions: list[str]
    action_items: list[str]
    related_paper: str | None = None
    source_file: str | None = None


@dataclass
class IdeaRecord:
    """A persisted idea record with lifecycle metadata."""

    id: str
    idea_file: str
    title: str
    strategy: str
    mode: str
    status: IdeaStatus
    score: float | None = None
    tier: str | None = None
    challenge_file: str | None = None
    rejection_reason: str | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class PaperConfig:
    """Configuration for one paper under a project."""

    slug: str
    title: str
    stage: PaperStage
    target_venue: str | None = None
    deadline: str | None = None
    ideas: list[IdeaRecord] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)
    collaborators: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ResearchProject:
    """A persistent research project that may contain multiple papers."""

    name: str
    slug: str
    description: str
    direction: str
    stage: ProjectStage
    papers: list[PaperConfig] = field(default_factory=list)
    milestones: list[Milestone] = field(default_factory=list)
    meetings: list[MeetingNote] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class ReviewComment:
    """A single reviewer comment."""

    id: str
    reviewer: str
    category: str
    content: str
    classification: str


@dataclass
class RebuttalResponse:
    """A response to one reviewer comment."""

    comment_id: str
    strategy: str
    response: str
    paper_changes: list[str]
    additional_experiment: str | None


@dataclass
class RebuttalResult:
    """Complete rebuttal result."""

    paper_title: str
    venue: str
    reviews: list[ReviewComment]
    responses: list[RebuttalResponse]
    summary_of_changes: str
    additional_experiments: list[str]
    rebuttal_letter: str
    tone: str


def to_dict(value: Any) -> Any:
    """Convert dataclasses and enums into JSON-friendly values."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: to_dict(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, tuple):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value


def from_dict(model_type: type, payload: dict[str, Any]):
    """Build a dataclass model from a JSON payload."""
    kwargs: dict[str, Any] = {}
    type_hints = get_type_hints(model_type)
    for field_info in fields(model_type):
        if field_info.name not in payload:
            continue
        kwargs[field_info.name] = _coerce_value(type_hints.get(field_info.name, field_info.type), payload[field_info.name])
    return model_type(**kwargs)


def _coerce_value(type_hint: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(type_hint)
    args = get_args(type_hint)
    if origin is list and args:
        return [_coerce_value(args[0], item) for item in value]
    if origin is dict:
        return dict(value)
    if origin is None and isinstance(type_hint, type):
        if issubclass(type_hint, Enum):
            return type_hint(value)
        if is_dataclass(type_hint):
            return from_dict(type_hint, value)
    if origin is not None and type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        if non_none:
            return _coerce_value(non_none[0], value)
    return value
