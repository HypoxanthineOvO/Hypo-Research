from __future__ import annotations

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


def test_project_enums_values() -> None:
    assert ProjectStage.EXPLORATION.value == "exploration"
    assert PaperStage.REBUTTAL.value == "rebuttal"
    assert IdeaStatus.REJECTED.value == "rejected"


def test_research_project_round_trip() -> None:
    project = ResearchProject(
        name="Cryo Computing",
        slug="cryo-computing",
        description="desc",
        direction="低温 CMOS 架构加速",
        stage=ProjectStage.ACTIVE,
        papers=[
            PaperConfig(
                slug="approx",
                title="近似计算框架",
                stage=PaperStage.IDEATION,
                ideas=[
                    IdeaRecord(
                        id="idea-001",
                        idea_file="papers/approx/ideas/idea-001.json",
                        title="Idea",
                        strategy="gap_analysis",
                        mode="ambitious",
                        status=IdeaStatus.CANDIDATE,
                    )
                ],
            )
        ],
    )

    payload = to_dict(project)
    restored = from_dict(ResearchProject, payload)

    assert payload["stage"] == "active"
    assert restored.papers[0].ideas[0].status == IdeaStatus.CANDIDATE
    assert restored.papers[0].stage == PaperStage.IDEATION


def test_paper_config_nested_structure_defaults() -> None:
    paper = PaperConfig(slug="p", title="Paper", stage=PaperStage.SURVEY)

    assert paper.ideas == []
    assert paper.milestones == []
