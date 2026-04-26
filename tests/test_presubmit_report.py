"""Tests for presubmit Markdown reports."""

from __future__ import annotations

from hypo_research.presubmit.report import render_presubmit_report
from hypo_research.presubmit.runner import CheckStageResult, PresubmitResult, PresubmitVerdict


def result(verdict: PresubmitVerdict, *, skipped: list[str] | None = None) -> PresubmitResult:
    stages = [
        CheckStageResult(
            stage="check",
            passed=verdict is not PresubmitVerdict.FAIL,
            errors=1 if verdict is PresubmitVerdict.FAIL else 0,
            warnings=1 if verdict is PresubmitVerdict.WARNING else 0,
            details=[],
            duration_seconds=0.1,
        )
    ]
    errors = sum(stage.errors for stage in stages)
    warnings = sum(stage.warnings for stage in stages)
    return PresubmitResult(
        verdict=verdict,
        stages=stages,
        total_errors=errors,
        total_warnings=warnings,
        total_duration_seconds=0.1,
        summary="summary",
        skipped_stages=skipped or [],
    )


def test_pass_report_contains_pass_emoji() -> None:
    report = render_presubmit_report(result(PresubmitVerdict.PASS))
    assert "✅ PASS" in report


def test_fail_report_contains_fail_emoji() -> None:
    report = render_presubmit_report(result(PresubmitVerdict.FAIL))
    assert "❌ FAIL" in report
    assert "强烈建议修复" in report


def test_warning_report_contains_warning_emoji() -> None:
    report = render_presubmit_report(result(PresubmitVerdict.WARNING))
    assert "⚠️ WARNING" in report


def test_summary_table_format() -> None:
    report = render_presubmit_report(result(PresubmitVerdict.PASS))
    assert "| 阶段 | 状态 | Errors | Warnings | 耗时 |" in report
    assert "| **总计** | **✅ PASS**" in report


def test_skipped_stage_displayed() -> None:
    report = render_presubmit_report(result(PresubmitVerdict.PASS, skipped=["lint"]))
    assert "lint) ⏭️ Skipped" in report


def test_exception_stage_displayed_as_error() -> None:
    presubmit = PresubmitResult(
        verdict=PresubmitVerdict.FAIL,
        stages=[
            CheckStageResult(
                stage="check",
                passed=False,
                errors=1,
                warnings=0,
                details=["[error] stage exception RuntimeError: boom"],
                duration_seconds=0,
            )
        ],
        total_errors=1,
        total_warnings=0,
        total_duration_seconds=0,
        summary="failed",
    )
    report = render_presubmit_report(presubmit)
    assert "💥 Error" in report
    assert "RuntimeError" in report


def test_details_sorted_by_severity() -> None:
    presubmit = PresubmitResult(
        verdict=PresubmitVerdict.FAIL,
        stages=[
            CheckStageResult(
                stage="lint",
                passed=False,
                errors=1,
                warnings=1,
                details=["[warning] later", "[error] first"],
                duration_seconds=0,
            )
        ],
        total_errors=1,
        total_warnings=1,
        total_duration_seconds=0,
        summary="failed",
    )
    report = render_presubmit_report(presubmit)
    assert report.index("[error] first") < report.index("[warning] later")
