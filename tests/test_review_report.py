"""Tests for simulated review report rendering."""

from __future__ import annotations

import pytest

from hypo_research.review.report import (
    ConsistencyFlag,
    ConsistencyReport,
    MetaReview,
    ReviewReport,
    RevisionItem,
    RevisionRoadmap,
    SingleReview,
    generate_consistency_report,
    generate_report_json,
    generate_report_markdown,
)


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


def make_meta_review(final_recommendation: str = "Reject") -> MetaReview:
    return MetaReview(
        ac_name="贺云翔",
        ac_emoji="🏛️",
        consensus_summary="共识总结",
        key_disagreements=["分歧一"],
        final_recommendation=final_recommendation,
        recommendation_reasoning="AC 理由",
        actionable_priorities=["优先事项一"],
        confidence=4,
    )


def make_roadmap() -> RevisionRoadmap:
    return RevisionRoadmap(
        one_line_summary="路线图总结",
        must_fix=[
            RevisionItem(
                priority="🔴 必须修改",
                title="补实验",
                problem="Section 4 缺实验",
                suggestion="补充 Table 2 对比",
                effort_estimate="3-5 天",
                source_reviewers=["🔬李超凡 [Major #1]"],
            )
        ],
        should_fix=[],
        can_dismiss=[
            RevisionItem(
                priority="⚪ 可以忽略",
                title="开源代码",
                problem="double-blind 阶段要求开源",
                suggestion="rebuttal 中解释匿名限制",
                effort_estimate="0.5 天",
                source_reviewers=["🔧丁麒涵"],
                dismiss_reason="double-blind 阶段不适合公开 deanonymizing 代码。",
            )
        ],
        schedule=[{"phase": "Week 1", "time": "Day 1-5", "tasks": "跑实验"}],
        reviewer_notes=["李超凡会检查实验公平性"],
        concerns_table={"reviewers": ["🏛️贺云翔", "🔬李超凡"], "issues": {"Experiments": ["🔬李超凡"]}},
    )


def test_meta_review_dataclass_serializes() -> None:
    report = ReviewReport("Paper", None, "standard", ["heyunxiang"], [review("a", "Alice", 8, "Accept")], meta_review=make_meta_review())

    payload = generate_report_json(report)

    assert payload["meta_review"]["ac_name"] == "贺云翔"


def test_revision_roadmap_dataclass_serializes() -> None:
    report = ReviewReport(
        "Paper",
        None,
        "standard",
        ["heyunxiang"],
        [review("a", "Alice", 8, "Accept")],
        meta_review=make_meta_review(),
        revision_roadmap=make_roadmap(),
    )

    payload = generate_report_json(report)

    assert payload["revision_roadmap"]["must_fix"][0]["title"] == "补实验"


def test_consistency_report_dataclass_serializes() -> None:
    report = ReviewReport(
        "Paper",
        None,
        "standard",
        ["a"],
        [review("a", "Alice", 6, "Borderline")],
        consistency_report=ConsistencyReport(
            flags=[ConsistencyFlag("Alice", "Major #1", "vague", "未引用具体章节", "warning")],
            overall_consistency_score=0.5,
            summary="有问题",
        ),
    )

    payload = generate_report_json(report)

    assert payload["consistency_report"]["flags"][0]["flag_type"] == "vague"


def test_markdown_contains_meta_review_revision_roadmap_and_consistency() -> None:
    report = ReviewReport(
        "Paper",
        None,
        "standard",
        ["heyunxiang"],
        [review("a", "Alice", 8, "Accept")],
        meta_review=make_meta_review("Borderline"),
        revision_roadmap=make_roadmap(),
    )

    markdown = generate_report_markdown(report)

    assert "## 📋 AC Meta-Review" in markdown
    assert "## 📚 修改路线图" in markdown
    assert "## 🔍 审稿一致性检查" in markdown


def test_no_heyunxiang_meta_and_roadmap_default_to_none() -> None:
    report = ReviewReport("Paper", None, "standard", ["lichaofan"], [review("a", "Alice", 6, "Borderline")])

    assert report.meta_review is None
    assert report.revision_roadmap is None


def test_meta_review_final_recommendation_overrides_average_decision() -> None:
    report = ReviewReport(
        "Paper",
        None,
        "standard",
        ["heyunxiang"],
        [review("a", "Alice", 9, "Accept")],
        meta_review=make_meta_review("Reject"),
    )

    assert generate_report_json(report)["overall_decision"] == "Reject"


def test_consistency_report_always_generated() -> None:
    report = ReviewReport("Paper", None, "standard", ["a"], [review("a", "Alice", 6, "Borderline")])

    payload = generate_report_json(report)

    assert payload["consistency_report"] is not None


def test_vague_flag_for_weakness_without_specific_reference() -> None:
    report = generate_consistency_report([review("a", "Alice", 6, "Borderline")])

    assert any(flag.flag_type == "vague" for flag in report.flags)


def test_contradictory_flag_for_same_element_in_strength_and_weakness() -> None:
    single = review("a", "Alice", 6, "Borderline")
    single.strengths = ["Figure 1 is clear and useful."]
    single.weaknesses = ["[Minor] Figure 1 is confusing and should be redesigned."]

    report = generate_consistency_report([single])

    assert any(flag.flag_type == "contradictory" for flag in report.flags)


def test_consistency_summary_when_no_flags() -> None:
    single = review("a", "Alice", 6, "Borderline")
    single.weaknesses = ["[Major] Section 4 lacks Table 2 comparison with SOTA baselines."]

    report = generate_consistency_report([single])

    assert report.flags == []
    assert "全部审稿意见与论文内容一致" in report.summary


def test_revision_item_priority_validation() -> None:
    with pytest.raises(ValueError):
        RevisionItem("高优先级", "x", "p", "s", "1 天", [])
