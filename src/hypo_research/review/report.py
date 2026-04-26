"""Markdown and JSON rendering for simulated review reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any


@dataclass
class SingleReview:
    """One reviewer's review."""

    reviewer_id: str
    reviewer_name: str
    reviewer_emoji: str
    reviewer_role: str
    severity_label: str
    summary: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    missing_references: list[str] = field(default_factory=list)
    score: int | None = None
    decision: str | None = None
    confidence: int | None = None


@dataclass
class ReviewReport:
    """Aggregated review report."""

    paper_title: str
    venue: str | None
    severity: str
    panel: list[str]
    reviews: list[SingleReview]
    avg_score: float | None = None
    major_issues: list[tuple[str, str]] = field(default_factory=list)
    minor_issues: list[tuple[str, str]] = field(default_factory=list)
    all_strengths: list[tuple[str, str]] = field(default_factory=list)
    overall_decision: str = "Borderline"


def aggregate_report(report: ReviewReport) -> ReviewReport:
    """Populate aggregate score, issues, strengths, and decision in-place."""
    scores = [review.score for review in report.reviews if review.score is not None]
    report.avg_score = round(mean(scores), 1) if scores else None
    report.major_issues = []
    report.minor_issues = []
    report.all_strengths = []
    for review in report.reviews:
        reviewer_label = f"{review.reviewer_emoji} {review.reviewer_name}"
        for weakness in review.weaknesses:
            normalized = weakness.strip()
            if normalized.lower().startswith("[major]") or "major" in normalized[:20].lower():
                report.major_issues.append((reviewer_label, normalized))
            else:
                report.minor_issues.append((reviewer_label, normalized))
        for strength in review.strengths:
            report.all_strengths.append((reviewer_label, strength))

    if report.avg_score is None:
        report.overall_decision = "Pending Agent Review"
    elif report.avg_score >= 7.0:
        report.overall_decision = "Accept"
    elif report.avg_score >= 5.5:
        report.overall_decision = "Borderline"
    else:
        report.overall_decision = "Reject"

    if any(review.decision == "Strong Reject" for review in report.reviews):
        if report.overall_decision == "Accept":
            report.overall_decision = "Borderline"
    return report


def generate_report_markdown(report: ReviewReport) -> str:
    """Render the review report as Markdown."""
    aggregate_report(report)
    venue_text = report.venue or "通用学术标准"
    panel_text = " + ".join(
        f"{review.reviewer_emoji}{review.reviewer_name}" for review in report.reviews
    )
    avg_score = "-" if report.avg_score is None else f"{report.avg_score:.1f}/10"
    lines = [
        f"# 📝 模拟审稿报告: {report.paper_title}",
        "",
        f"**目标 Venue**: {venue_text} | **苛刻程度**: {report.severity}",
        f"**审稿团**: {panel_text}",
        "",
        "---",
        "",
        "## 🎯 总体评价",
        "",
        "| 审稿人 | 评分 | 倾向 | 信心 |",
        "|--------|------|------|------|",
    ]
    for review in report.reviews:
        score = "-" if review.score is None else f"{review.score}/10"
        decision = review.decision or "-"
        confidence = "-" if review.confidence is None else f"{review.confidence}/5"
        lines.append(f"| {review.reviewer_emoji} {review.reviewer_name} | {score} | {decision} | {confidence} |")
    lines.extend(
        [
            f"| **综合** | **{avg_score}** | **{report.overall_decision}** | |",
            "",
            f"## 🔴 Major Issues ({len(report.major_issues)})",
            "",
        ]
    )
    lines.extend(_numbered_issue_lines(report.major_issues) or ["暂无。"])
    lines.extend(["", f"## 🟡 Minor Issues ({len(report.minor_issues)})", ""])
    lines.extend(_numbered_issue_lines(report.minor_issues) or ["暂无。"])
    lines.extend(["", f"## 🟢 Strengths ({len(report.all_strengths)})", ""])
    lines.extend(_numbered_issue_lines(report.all_strengths) or ["暂无。"])
    lines.extend(["", "---", "", "## 📋 审稿人详细报告", ""])
    for review in report.reviews:
        lines.extend(_render_single_review(review))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_report_json(report: ReviewReport) -> dict[str, Any]:
    """Render the review report as JSON-compatible data."""
    aggregate_report(report)
    return asdict(report)


def _numbered_issue_lines(items: list[tuple[str, str]]) -> list[str]:
    return [
        f"{index}. **[{reviewer}]** {issue}"
        for index, (reviewer, issue) in enumerate(items, start=1)
    ]


def _render_single_review(review: SingleReview) -> list[str]:
    score = "-" if review.score is None else f"{review.score}/10"
    confidence = "-" if review.confidence is None else f"{review.confidence}/5"
    lines = [
        f"### {review.reviewer_emoji} {review.reviewer_name}（{review.severity_label}）— {review.reviewer_role}",
        "",
        f"**评分**: {score} | **倾向**: {review.decision or '-'} | **信心**: {confidence}",
        "",
        f"**Summary**: {review.summary}",
        "",
        "**Strengths**:",
    ]
    lines.extend(_numbered_plain(review.strengths))
    lines.extend(["", "**Weaknesses**:"])
    lines.extend(_numbered_plain(review.weaknesses))
    lines.extend(["", "**Questions to Authors**:"])
    lines.extend(_numbered_plain(review.questions))
    lines.extend(["", "**Missing References**:"])
    if review.missing_references:
        lines.extend(f"- {item}" for item in review.missing_references)
    else:
        lines.append("- 无")
    return lines


def _numbered_plain(items: list[str]) -> list[str]:
    if not items:
        return ["暂无。"]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]
