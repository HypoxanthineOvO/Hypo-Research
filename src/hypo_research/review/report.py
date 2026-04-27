"""Markdown and JSON rendering for simulated review reports."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any


REVISION_PRIORITIES = {"🔴 必须修改", "🟡 建议修改", "⚪ 可以忽略"}
_SPECIFIC_REFERENCE_RE = re.compile(
    r"\b(?:Section|Sec\.?|Figure|Fig\.?|Table|Tab\.?|Equation|Eq\.?|Algorithm|Appendix)\s*[\w.\-()]+",
    re.IGNORECASE,
)
_ELEMENT_RE = re.compile(
    r"\b(?:Section|Sec\.?|Figure|Fig\.?|Table|Tab\.?|Equation|Eq\.?)\s*[\w.\-()]+",
    re.IGNORECASE,
)


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
class MetaReview:
    """AC's meta-review after seeing all individual reviews."""

    ac_name: str
    ac_emoji: str
    consensus_summary: str
    key_disagreements: list[str]
    final_recommendation: str
    recommendation_reasoning: str
    actionable_priorities: list[str]
    confidence: int


@dataclass
class RevisionItem:
    """单个修改项。"""

    priority: str
    title: str
    problem: str
    suggestion: str
    effort_estimate: str
    source_reviewers: list[str]
    dismiss_reason: str | None = None

    def __post_init__(self) -> None:
        if self.priority not in REVISION_PRIORITIES:
            choices = ", ".join(sorted(REVISION_PRIORITIES))
            raise ValueError(f"Invalid revision priority: {self.priority}. Available: {choices}")


@dataclass
class RevisionRoadmap:
    """导师视角的修改路线图。"""

    one_line_summary: str
    must_fix: list[RevisionItem]
    should_fix: list[RevisionItem]
    can_dismiss: list[RevisionItem]
    schedule: list[dict]
    reviewer_notes: list[str]
    concerns_table: dict | None


@dataclass
class ConsistencyFlag:
    """A flag indicating a potential mismatch between review comment and paper content."""

    reviewer_name: str
    issue_title: str
    flag_type: str
    explanation: str
    severity: str


@dataclass
class ConsistencyReport:
    """Post-review consistency check results."""

    flags: list[ConsistencyFlag]
    overall_consistency_score: float
    summary: str


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
    meta_review: MetaReview | None = None
    revision_roadmap: RevisionRoadmap | None = None
    consistency_report: ConsistencyReport | None = None


def aggregate_report(report: ReviewReport) -> ReviewReport:
    """Populate aggregate score, issues, strengths, decision, and consistency."""
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

    if report.meta_review is not None:
        report.overall_decision = report.meta_review.final_recommendation
    elif report.avg_score is None:
        report.overall_decision = "Pending Agent Review"
    elif report.avg_score >= 7.0:
        report.overall_decision = "Accept"
    elif report.avg_score >= 5.5:
        report.overall_decision = "Borderline"
    else:
        report.overall_decision = "Reject"

    if report.meta_review is None and any(review.decision == "Strong Reject" for review in report.reviews):
        if report.overall_decision == "Accept":
            report.overall_decision = "Borderline"
    if report.consistency_report is None:
        report.consistency_report = generate_consistency_report(report.reviews)
    return report


def generate_consistency_report(reviews: list[SingleReview]) -> ConsistencyReport:
    """Run deterministic rule-based consistency checks over review weaknesses."""
    flags: list[ConsistencyFlag] = []
    total_weaknesses = sum(len(review.weaknesses) for review in reviews)
    for review in reviews:
        for index, weakness in enumerate(review.weaknesses, start=1):
            issue_title = _issue_title(weakness, index)
            if not _SPECIFIC_REFERENCE_RE.search(weakness):
                flags.append(
                    ConsistencyFlag(
                        reviewer_name=review.reviewer_name,
                        issue_title=issue_title,
                        flag_type="vague",
                        explanation="该 weakness 未引用具体 Section/Figure/Table/Eq.，可能过于泛泛。",
                        severity="warning",
                    )
                )
        flags.extend(_contradiction_flags(review))

    denominator = max(total_weaknesses, 1)
    score = max(0.0, 1.0 - len([flag for flag in flags if flag.severity == "warning"]) / denominator)
    score = round(score, 2)
    summary = "全部审稿意见与论文内容一致。" if not flags else f"发现 {len(flags)} 个可能的一致性问题。"
    return ConsistencyReport(flags=flags, overall_consistency_score=score, summary=summary)


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
            "---",
            "",
        ]
    )
    if report.meta_review is not None:
        lines.extend(_render_meta_review(report.meta_review))
        lines.extend(["", "---", ""])
    lines.extend([f"## 🔴 Major Issues ({len(report.major_issues)})", ""])
    lines.extend(_numbered_issue_lines(report.major_issues) or ["暂无。"])
    lines.extend(["", f"## 🟡 Minor Issues ({len(report.minor_issues)})", ""])
    lines.extend(_numbered_issue_lines(report.minor_issues) or ["暂无。"])
    lines.extend(["", f"## 🟢 Strengths ({len(report.all_strengths)})", ""])
    lines.extend(_numbered_issue_lines(report.all_strengths) or ["暂无。"])
    lines.extend(["", "---", "", "## 📋 审稿人详细报告", ""])
    for review in report.reviews:
        lines.extend(_render_single_review(review))
        lines.append("")
    if report.revision_roadmap is not None:
        lines.extend(["---", ""])
        lines.extend(_render_revision_roadmap(report.revision_roadmap))
        lines.append("")
    lines.extend(["---", ""])
    lines.extend(_render_consistency_report(report.consistency_report))
    return "\n".join(lines).rstrip() + "\n"


def generate_report_json(report: ReviewReport) -> dict[str, Any]:
    """Render the review report as JSON-compatible data."""
    aggregate_report(report)
    return asdict(report)


def _render_meta_review(meta_review: MetaReview) -> list[str]:
    lines = [
        f"## 📋 AC Meta-Review（{meta_review.ac_name}）",
        "",
        f"**共识**：{meta_review.consensus_summary}",
        "",
        "**关键分歧**：",
    ]
    lines.extend(_numbered_plain(meta_review.key_disagreements))
    lines.extend(
        [
            "",
            f"**最终建议**：{meta_review.final_recommendation}",
            "",
            f"**理由**：{meta_review.recommendation_reasoning}",
            "",
            "**修改优先级**：",
        ]
    )
    lines.extend(_numbered_plain(meta_review.actionable_priorities))
    lines.append("")
    lines.append(f"**AC 信心**：{meta_review.confidence}/5")
    return lines


def _render_revision_roadmap(roadmap: RevisionRoadmap) -> list[str]:
    lines = [
        "## 📚 修改路线图（导师视角）",
        "",
        "> 本节由 AI 以\"导师\"角色生成，站在作者一边帮你规划修改策略。",
        "",
        "### 一句话总结",
        roadmap.one_line_summary,
        "",
        "### 🔴 必须修改（Must Fix）",
    ]
    lines.extend(_render_revision_items(roadmap.must_fix))
    lines.extend(["", "### 🟡 建议修改（Should Fix）"])
    lines.extend(_render_revision_items(roadmap.should_fix))
    lines.extend(["", "### ⚪ 可以忽略（Dismiss）"])
    lines.extend(_render_revision_items(roadmap.can_dismiss))
    lines.extend(["", "### 📅 建议修改时间表"])
    lines.extend(_render_schedule(roadmap.schedule))
    lines.extend(["", "### ⚠️ 审稿人偏好注意事项"])
    lines.extend([f"- {note}" for note in roadmap.reviewer_notes] or ["暂无。"])
    lines.extend(["", "### 📊 问题交叉矩阵（Concerns Table）"])
    lines.extend(_render_concerns_table(roadmap.concerns_table))
    return lines


def _render_consistency_report(report: ConsistencyReport | None) -> list[str]:
    if report is None:
        report = ConsistencyReport([], 1.0, "全部审稿意见与论文内容一致。")
    lines = [
        "## 🔍 审稿一致性检查",
        "",
        "> 以下标记表示审稿意见可能与论文内容不一致，供作者参考。",
        "",
        f"整体一致性得分：{report.overall_consistency_score:.2f} / 1.0",
        "",
        report.summary,
        "",
    ]
    if not report.flags:
        lines.append("全部审稿意见与论文内容一致。")
        return lines
    lines.extend(
        [
            "| 审稿人 | 意见 | 标记 | 说明 |",
            "| --- | --- | --- | --- |",
        ]
    )
    icon_map = {
        "vague": "⚠️ vague",
        "unsupported": "⚠️ unsupported",
        "already_addressed": "ℹ️ already_addressed",
        "contradictory": "⚠️ contradictory",
    }
    for flag in report.flags:
        lines.append(
            f"| {flag.reviewer_name} | {flag.issue_title} | {icon_map.get(flag.flag_type, flag.flag_type)} | {flag.explanation} |"
        )
    return lines


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


def _render_revision_items(items: list[RevisionItem]) -> list[str]:
    if not items:
        return ["暂无。"]
    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. **{item.title}**",
                f"   - 📍 问题：{item.problem}",
                f"   - 🔧 建议：{item.suggestion}",
                f"   - ⏱ 预估：{item.effort_estimate}",
                f"   - 👤 来源：{', '.join(item.source_reviewers) or '未知'}",
            ]
        )
        if item.dismiss_reason:
            lines.append(f"   - 🧭 忽略理由：{item.dismiss_reason}")
    return lines


def _render_schedule(schedule: list[dict]) -> list[str]:
    if not schedule:
        return ["暂无。"]
    lines = ["| 阶段 | 时间 | 任务 |", "| --- | --- | --- |"]
    for item in schedule:
        lines.append(f"| {item.get('phase', '-')} | {item.get('time', '-')} | {item.get('tasks', '-')} |")
    return lines


def _render_concerns_table(concerns_table: dict | None) -> list[str]:
    if not concerns_table:
        return ["暂无。"]
    reviewers = list(concerns_table.get("reviewers", []))
    issues = concerns_table.get("issues", {})
    if not reviewers or not isinstance(issues, dict):
        return ["暂无。"]
    lines = [
        "| 问题类别 | " + " | ".join(reviewers) + " |",
        "| --- | " + " | ".join("---" for _ in reviewers) + " |",
    ]
    for issue, issue_reviewers in issues.items():
        issue_reviewer_set = set(issue_reviewers)
        cells = ["✅" if reviewer in issue_reviewer_set else "" for reviewer in reviewers]
        lines.append(f"| {issue} | " + " | ".join(cells) + " |")
    return lines


def _numbered_plain(items: list[str]) -> list[str]:
    if not items:
        return ["暂无。"]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]


def _issue_title(weakness: str, index: int) -> str:
    severity = "Major" if "major" in weakness[:20].lower() else "Minor"
    return f"{severity} #{index}"


def _contradiction_flags(review: SingleReview) -> list[ConsistencyFlag]:
    strength_elements = _elements_by_text(review.strengths)
    weakness_elements = _elements_by_text(review.weaknesses)
    shared = sorted(set(strength_elements) & set(weakness_elements))
    return [
        ConsistencyFlag(
            reviewer_name=review.reviewer_name,
            issue_title=element,
            flag_type="contradictory",
            explanation=f"同一审稿人在 strengths 和 weaknesses 中都提到 {element}，需要检查评价是否自相矛盾。",
            severity="warning",
        )
        for element in shared
    ]


def _elements_by_text(items: list[str]) -> set[str]:
    elements: set[str] = set()
    for item in items:
        for match in _ELEMENT_RE.finditer(item):
            elements.add(match.group(0).lower().replace("sec.", "section").replace("fig.", "figure"))
    return elements
