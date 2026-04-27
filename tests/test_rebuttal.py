from __future__ import annotations

from hypo_research.project.rebuttal import build_response, classify_comment, generate_rebuttal, parse_reviews


REVIEW_TEXT = """
Reviewer 1:
1. The paper lacks a strong baseline experiment.
2. The motivation is unclear and should be clarified.

Reviewer 2:
- Excellent idea and well-written method section.
"""


def test_parse_reviews_splits_comments() -> None:
    comments = parse_reviews(REVIEW_TEXT)

    assert len(comments) == 3
    assert comments[0].reviewer == "Reviewer 1"


def test_classify_comment_and_strategy() -> None:
    assert classify_comment("The paper lacks a baseline experiment.") == "valid_concern"
    assert classify_comment("Excellent work.") == "praise"
    response = build_response(parse_reviews(REVIEW_TEXT)[0])
    assert response.strategy == "supplement"
    assert response.additional_experiment is not None


def test_generate_complete_rebuttal() -> None:
    result = generate_rebuttal(REVIEW_TEXT, paper_draft="# Paper Title")

    assert result.paper_title == "Paper Title"
    assert result.reviews
    assert result.responses
    assert result.additional_experiments
    assert "Dear Area Chair" in result.rebuttal_letter
    assert result.summary_of_changes
