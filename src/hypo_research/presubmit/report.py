"""Markdown rendering for presubmit results."""

from __future__ import annotations

from hypo_research.presubmit.runner import CheckStageResult, PresubmitResult, PresubmitVerdict


_VERDICT_EMOJI = {
    PresubmitVerdict.PASS: "✅",
    PresubmitVerdict.WARNING: "⚠️",
    PresubmitVerdict.FAIL: "❌",
}
_STAGE_TITLES = {
    "check": "结构/格式检查",
    "lint": "LaTeX 语法检查",
    "verify": "引用验证",
}
_STAGE_ORDER = {"check": 1, "lint": 2, "verify": 3}


def render_presubmit_report(result: PresubmitResult) -> str:
    """Render a presubmit result as Markdown."""
    emoji = _VERDICT_EMOJI[result.verdict]
    verdict = result.verdict.value.upper()
    lines = [
        "# 📋 提交前检查报告",
        "",
        (
            f"**总体判定：{emoji} {verdict}** "
            f"（{result.total_errors} errors, {result.total_warnings} warnings, "
            f"耗时 {result.total_duration_seconds:.1f}s）"
        ),
        "",
    ]
    if result.verdict is PresubmitVerdict.FAIL:
        lines.extend([f"> ⛔ 发现 {result.total_errors} 个 error 级问题，强烈建议修复后再提交。", ""])
    elif result.verdict is PresubmitVerdict.WARNING:
        lines.extend([f"> 💡 建议修复 {result.total_warnings} 个 warning 后再提交。", ""])
    else:
        lines.extend(["> 💡 所有检查通过，可以提交。", ""])
    lines.append("---")
    lines.append("")

    stage_by_name = {stage.stage: stage for stage in result.stages}
    for stage_name in ["check", "lint", "verify"]:
        if stage_name in result.skipped_stages:
            lines.extend(_render_skipped_stage(stage_name))
        elif stage_name in stage_by_name:
            lines.extend(_render_stage(stage_by_name[stage_name]))

    lines.extend(_render_summary_table(result))
    return "\n".join(lines).rstrip() + "\n"


def _render_stage(stage: CheckStageResult) -> list[str]:
    status = _stage_status(stage)
    lines = [
        f"## 阶段 {_STAGE_ORDER.get(stage.stage, 0)}: {_STAGE_TITLES.get(stage.stage, stage.stage)} ({stage.stage}) {status}",
        f"⏱️ {stage.duration_seconds:.1f}s | {stage.errors} errors | {stage.warnings} warnings",
        "",
    ]
    if stage.details:
        for detail in _sort_details(stage.details):
            icon = "❌" if "[error]" in detail.lower() else "⚠️"
            lines.append(f"- {icon} {detail}")
    else:
        lines.append("全部检查通过。")
    lines.extend(["", "---", ""])
    return lines


def _render_skipped_stage(stage_name: str) -> list[str]:
    return [
        f"## 阶段 {_STAGE_ORDER.get(stage_name, 0)}: {_STAGE_TITLES.get(stage_name, stage_name)} ({stage_name}) ⏭️ Skipped",
        "",
        "该阶段已被跳过。",
        "",
        "---",
        "",
    ]


def _render_summary_table(result: PresubmitResult) -> list[str]:
    lines = [
        "## 📊 汇总",
        "",
        "| 阶段 | 状态 | Errors | Warnings | 耗时 |",
        "|------|------|--------|----------|------|",
    ]
    stage_by_name = {stage.stage: stage for stage in result.stages}
    for stage_name in ["check", "lint", "verify"]:
        if stage_name in result.skipped_stages:
            lines.append(f"| {stage_name} | ⏭️ | 0 | 0 | - |")
            continue
        stage = stage_by_name.get(stage_name)
        if stage is None:
            continue
        lines.append(
            f"| {stage.stage} | {_stage_status(stage)} | {stage.errors} | "
            f"{stage.warnings} | {stage.duration_seconds:.1f}s |"
        )
    emoji = _VERDICT_EMOJI[result.verdict]
    lines.append(
        f"| **总计** | **{emoji} {result.verdict.value.upper()}** | "
        f"**{result.total_errors}** | **{result.total_warnings}** | "
        f"**{result.total_duration_seconds:.1f}s** |"
    )
    lines.extend(["", f"> 💡 {result.summary}", ""])
    return lines


def _stage_status(stage: CheckStageResult) -> str:
    if any(detail.lower().startswith("[error]") and "exception" in detail.lower() for detail in stage.details):
        return "💥 Error"
    if stage.errors > 0:
        return "❌"
    if stage.warnings > 0:
        return "⚠️"
    return "✅"


def _sort_details(details: list[str]) -> list[str]:
    return sorted(details, key=lambda detail: 0 if "[error]" in detail.lower() else 1)
