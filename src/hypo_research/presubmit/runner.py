"""Unified pre-submission check pipeline."""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from hypo_research.writing.check import run_check
from hypo_research.writing.config import load_config
from hypo_research.writing.project import resolve_project
from hypo_research.writing.stats import LintIssue, extract_stats
from hypo_research.writing.verify import VerifyReport, VerifyStatus, verify_bib
from hypo_research.writing.venue import get_venue


class PresubmitVerdict(Enum):
    """Overall presubmit verdict."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class CheckStageResult:
    """Result from one stage of the presubmit pipeline."""

    stage: str
    passed: bool
    errors: int
    warnings: int
    details: list[str]
    duration_seconds: float


@dataclass
class PresubmitResult:
    """Aggregated result from the full presubmit pipeline."""

    verdict: PresubmitVerdict
    stages: list[CheckStageResult]
    total_errors: int
    total_warnings: int
    total_duration_seconds: float
    summary: str
    skipped_stages: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serializable payload."""
        payload = asdict(self)
        payload["verdict"] = self.verdict.value
        return payload


def run_presubmit(
    tex_root: str,
    *,
    venue: str | None = None,
    skip_stages: list[str] | None = None,
    bib_file: str | None = None,
) -> PresubmitResult:
    """Run the full presubmit pipeline."""
    skip_set = {stage.strip().lower() for stage in skip_stages or [] if stage.strip()}
    stages: list[CheckStageResult] = []
    skipped: list[str] = []

    stage_runners: dict[str, Callable[[], CheckStageResult]] = {
        "check": lambda: _run_check_stage(tex_root, venue=venue),
        "lint": lambda: _run_lint_stage(tex_root, venue=venue),
        "verify": lambda: _run_verify_stage(tex_root, venue=venue, bib_file=bib_file),
    }

    start = time.perf_counter()
    for stage_name, runner in stage_runners.items():
        if stage_name in skip_set:
            skipped.append(stage_name)
            continue
        try:
            stages.append(runner())
        except Exception as exc:
            stages.append(
                CheckStageResult(
                    stage=stage_name,
                    passed=False,
                    errors=1,
                    warnings=0,
                    details=[f"[error] stage exception {type(exc).__name__}: {exc}"],
                    duration_seconds=0.0,
                )
            )

    total_errors = sum(stage.errors for stage in stages)
    total_warnings = sum(stage.warnings for stage in stages)
    verdict = _verdict(total_errors, total_warnings)
    duration = time.perf_counter() - start
    return PresubmitResult(
        verdict=verdict,
        stages=stages,
        total_errors=total_errors,
        total_warnings=total_warnings,
        total_duration_seconds=duration,
        summary=_summary(verdict, total_errors, total_warnings),
        skipped_stages=skipped,
    )


def _run_check_stage(tex_root: str, *, venue: str | None) -> CheckStageResult:
    start = time.perf_counter()
    venue_profile = get_venue(venue) if venue else None
    report = run_check(
        tex_root,
        fix=False,
        no_fix=True,
        verify=False,
        save_report=False,
        venue=venue_profile,
    )
    details = [
        f"[{issue['severity']}] {issue['rule']} {issue.get('file') or ''}:{issue['line']} — {issue['message']}"
        for issue in report.issues
    ]
    return CheckStageResult(
        stage="check",
        passed=report.lint.errors == 0,
        errors=report.lint.errors,
        warnings=report.lint.warnings,
        details=details,
        duration_seconds=time.perf_counter() - start,
    )


def _run_lint_stage(tex_root: str, *, venue: str | None) -> CheckStageResult:
    start = time.perf_counter()
    config = load_config(Path(tex_root).expanduser().resolve().parent)
    project = resolve_project(Path(tex_root).expanduser().resolve(), config=config)
    venue_profile = get_venue(venue or config.project.venue)
    stats = extract_stats(project.root_file, project=project, venue=venue_profile)
    issues = stats.filtered_issues(None)
    return CheckStageResult(
        stage="lint",
        passed=not any(issue.severity == "error" for issue in issues),
        errors=sum(1 for issue in issues if issue.severity == "error"),
        warnings=sum(1 for issue in issues if issue.severity == "warning"),
        details=[_lint_issue_detail(issue) for issue in issues],
        duration_seconds=time.perf_counter() - start,
    )


def _run_verify_stage(
    tex_root: str,
    *,
    venue: str | None,
    bib_file: str | None,
) -> CheckStageResult:
    start = time.perf_counter()
    config = load_config(Path(tex_root).expanduser().resolve().parent)
    project = resolve_project(Path(tex_root).expanduser().resolve(), config=config)
    venue_profile = get_venue(venue or config.project.venue)
    report = asyncio.run(
        verify_bib(
            bib_file,
            project=project if bib_file is None else None,
            tex_path=project.root_file,
            venue=venue_profile,
            s2_api_key=config.verify.s2_api_key,
            timeout=config.verify.timeout,
            skip_keys=config.verify.skip_keys,
            max_concurrent=config.verify.max_concurrent,
            max_requests_per_second=config.verify.max_requests_per_second,
            strict_doi=config.verify.strict_doi,
        )
    )
    errors, warnings = _verify_counts(report)
    return CheckStageResult(
        stage="verify",
        passed=errors == 0,
        errors=errors,
        warnings=warnings,
        details=_verify_details(report),
        duration_seconds=time.perf_counter() - start,
    )


def _lint_issue_detail(issue: LintIssue) -> str:
    location = f"{issue.file}:{issue.line}" if issue.file else f"line {issue.line}"
    return f"[{issue.severity.value}] {issue.rule} {location} — {issue.message}"


def _verify_counts(report: VerifyReport) -> tuple[int, int]:
    return report.mismatch + report.error, report.not_found + report.uncertain + report.rate_limited


def _verify_details(report: VerifyReport) -> list[str]:
    details: list[str] = []
    for result in report.results:
        if result.status == VerifyStatus.VERIFIED:
            continue
        severity = "error" if result.status in {VerifyStatus.MISMATCH, VerifyStatus.ERROR} else "warning"
        details.append(f"[{severity}] {result.bib_key}: {result.status.value}")
    return details


def _verdict(errors: int, warnings: int) -> PresubmitVerdict:
    if errors > 0:
        return PresubmitVerdict.FAIL
    if warnings > 0:
        return PresubmitVerdict.WARNING
    return PresubmitVerdict.PASS


def _summary(verdict: PresubmitVerdict, errors: int, warnings: int) -> str:
    if verdict is PresubmitVerdict.FAIL:
        return f"发现 {errors} 个 error 和 {warnings} 个 warning，不建议提交。"
    if verdict is PresubmitVerdict.WARNING:
        return f"发现 {warnings} 个 warning，建议修复后提交。"
    return "全部检查通过，可以提交。"
