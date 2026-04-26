"""Tests for simulated review report rendering."""

from __future__ import annotations

from hypo_research.review.report import ReviewReport, SingleReview, generate_report_json, generate_report_markdown


def review(
    reviewer_id: str,
    name: str,
    score: int | None,
    decision: str | None,
) -> SingleReview:
    return SingleReview(
        reviewer_id=reviewer_id,
        reviewer_name=name,
        reviewer_emoji="🔬",
        reviewer_role="Expert",
        severity_label="标准版",
        summary="summary",
        strengths=["strong point"],
        weaknesses=["[Major] major issue", "[Minor] minor issue"],
        questions=["question"],
        missing_references=["missing ref"],
        score=score,
        decision=decision,
        confidence=4 if score is not None else None,
    )


def test_markdown_contains_overall_table_and_details() -> None:
    report = ReviewReport(
        paper_title="Paper",
        venue="dac",
        severity="standard",
        panel=["a"],
        reviews=[review("a", "Alice", 6, "Weak Accept")],
    )

    markdown = generate_report_markdown(report)

    assert "## 🎯 总体评价" in markdown
    assert "## 🔴 Major Issues (1)" in markdown
    assert "## 🟡 Minor Issues (1)" in markdown
    assert "## 🟢 Strengths (1)" in markdown
    assert "### 🔬 Alice" in markdown


def test_overall_decision_accept_borderline_reject() -> None:
    for score, expected in [(8, "Accept"), (6, "Borderline"), (4, "Reject")]:
        report = ReviewReport("Paper", None, "standard", ["a"], [review("a", "Alice", score, "Accept")])
        payload = generate_report_json(report)
        assert payload["overall_decision"] == expected


def test_strong_reject_caps_accept_to_borderline() -> None:
    report = ReviewReport(
        "Paper",
        None,
        "standard",
        ["a", "b"],
        [review("a", "Alice", 9, "Strong Reject"), review("b", "Bob", 9, "Accept")],
    )

    assert generate_report_json(report)["overall_decision"] == "Borderline"


def test_no_score_review_does_not_affect_average() -> None:
    report = ReviewReport(
        "Paper",
        None,
        "standard",
        ["a", "w"],
        [review("a", "Alice", 8, "Accept"), review("w", "Writer", None, None)],
    )

    payload = generate_report_json(report)

    assert payload["avg_score"] == 8
    assert payload["reviews"][1]["score"] is None
