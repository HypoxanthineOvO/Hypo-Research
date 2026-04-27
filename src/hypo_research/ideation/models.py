"""Data models for research ideation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from hypo_research.review.literature import LiteratureContext


class IdeaMode(str, Enum):
    QUICK_WIN = "quick_win"
    AMBITIOUS = "ambitious"


class IdeaStrategy(str, Enum):
    DATASET_TRANSFER = "dataset_transfer"
    MODULE_FUSION = "module_fusion"
    SETTING_SHIFT = "setting_shift"
    APPLICATION = "application"
    GAP_ANALYSIS = "gap_analysis"
    METHOD_TRANSFER = "method_transfer"
    PROBLEM_VARIANT = "problem_variant"
    CONTRADICTION = "contradiction"
    PARADIGM_CHALLENGE = "paradigm_challenge"
    COMBINATION = "combination"


class ChallengeSeverity(str, Enum):
    GENTLE = "gentle"
    STANDARD = "standard"
    HARSH = "harsh"


@dataclass
class IdeaScorePenalty:
    """A single scoring penalty or bonus."""

    dimension: str
    delta: float
    reason: str
    evidence: str | None = None


@dataclass
class IdeaScore:
    """Idea scoring result."""

    novelty: float
    significance: float
    feasibility: float
    clarity: float
    adjustments: list[IdeaScorePenalty]
    total_score: float
    tier: str
    summary: str
    suggestions: list[str]


@dataclass
class ResearchIdea:
    """A single generated research idea."""

    title: str
    mode: IdeaMode
    strategy: IdeaStrategy
    research_question: str
    motivation: str
    method_sketch: str
    expected_contribution: list[str]
    feasibility_analysis: str
    risk_factors: list[str]
    related_papers: list[str]
    score: IdeaScore


@dataclass
class IdeaGenerationResult:
    """Complete result from hypo-idea."""

    input_summary: str
    strategies_used: list[IdeaStrategy]
    quick_win_ideas: list[ResearchIdea]
    ambitious_ideas: list[ResearchIdea]
    literature_context: LiteratureContext | None


@dataclass
class ChallengeQuestion:
    """A single challenge question in Socratic questioning."""

    dimension: str
    question: str
    severity: str
    context: str
    similar_work: str | None
    suggested_response: str


@dataclass
class ChallengeResult:
    """Complete result from hypo-challenge."""

    idea_title: str
    severity: ChallengeSeverity
    questions: list[ChallengeQuestion]
    fatal_risks: list[str]
    reinforcement_plan: list[str]
    verdict: str
    score_after_challenge: IdeaScore


@dataclass
class ExperimentBaseline:
    """A baseline method for experiment design."""

    name: str
    paper: str | None
    reason: str


@dataclass
class AblationItem:
    """A single ablation study item."""

    component: str
    experiment: str
    expected_outcome: str
    importance: str


@dataclass
class ExperimentDesign:
    """Complete result from hypo-experiment."""

    idea_title: str
    baselines: list[ExperimentBaseline]
    datasets: list[dict]
    metrics: list[dict]
    ablation_studies: list[AblationItem]
    experiment_matrix: list[dict]
    expected_results: str
    reference_setups: list[str]
    venue_requirements: str | None


@dataclass
class PlanPhase:
    """A phase in the research plan."""

    name: str
    duration: str
    tasks: list[str]
    milestones: list[str]
    risks: list[str]
    deliverables: list[str]


@dataclass
class ResearchPlan:
    """Complete result from hypo-plan."""

    idea_title: str
    target_venue: str | None
    deadline: str | None
    phases: list[PlanPhase]
    paper_outline: list[dict]
    writing_schedule: list[dict]
    risk_mitigation: list[dict]
    total_estimated_time: str


@dataclass
class PilotReport:
    """Complete result from hypo-pilot."""

    ideas: IdeaGenerationResult
    selected_idea: ResearchIdea
    challenge: ChallengeResult
    refined_idea: ResearchIdea
    experiment: ExperimentDesign
    plan: ResearchPlan
    mentor_comments: str
