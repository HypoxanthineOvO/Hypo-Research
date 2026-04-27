"""Research ideation, challenge, experiment design, and planning."""

from hypo_research.ideation.challenge import challenge_idea
from hypo_research.ideation.experiment import design_experiment
from hypo_research.ideation.models import (
    AblationItem,
    ChallengeQuestion,
    ChallengeResult,
    ChallengeSeverity,
    ExperimentBaseline,
    ExperimentDesign,
    IdeaGenerationResult,
    IdeaMode,
    IdeaScore,
    IdeaScorePenalty,
    IdeaStrategy,
    PilotReport,
    PlanPhase,
    ResearchIdea,
    ResearchPlan,
)
from hypo_research.ideation.pilot import run_pilot
from hypo_research.ideation.planning import create_plan
from hypo_research.ideation.scoring import compute_total_score, determine_tier, score_idea
from hypo_research.ideation.strategies import generate_ideas

__all__ = [
    "AblationItem",
    "ChallengeQuestion",
    "ChallengeResult",
    "ChallengeSeverity",
    "ExperimentBaseline",
    "ExperimentDesign",
    "IdeaGenerationResult",
    "IdeaMode",
    "IdeaScore",
    "IdeaScorePenalty",
    "IdeaStrategy",
    "PilotReport",
    "PlanPhase",
    "ResearchIdea",
    "ResearchPlan",
    "challenge_idea",
    "compute_total_score",
    "create_plan",
    "design_experiment",
    "determine_tier",
    "generate_ideas",
    "run_pilot",
    "score_idea",
]
