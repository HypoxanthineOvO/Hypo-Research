"""Writing pipeline orchestration for lint, fix, verify, and reporting."""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from hypo_research.writing.config import HypoConfig, load_config
from hypo_research.writing.fixer import apply_fixes, generate_fixes
from hypo_research.writing.project import resolve_project
from hypo_research.writing.severity import Severity, coerce_severity
from hypo_research.writing.stats import TexStats, extract_stats
from hypo_research.writing.verify import VerifyReport, verify_bib
from hypo_research.writing.venue import VenueProfile, get_venue


@dataclass
class LintStageResult:
    """Lint 阶段结果。"""

    total_issues: int = 0
    errors: int = 0
    warnings: int = 0
    fixes_applied: int = 0
    fixes_available: int = 0
    rules_triggered: list[str] = field(default_factory=list)


@dataclass
class VerifyStageResult:
    """Verify 阶段结果。"""

    total_entries: int = 0
    verified: int = 0
    mismatch: int = 0
    not_found: int = 0
    uncertain: int = 0
    rate_limited: int = 0
    error: int = 0
    skipped: int = 0


@dataclass
class StatsStageResult:
    """Stats 阶段结果（结构统计摘要）。"""

    total_files: int = 0
    total_sections: int = 0
    total_floats: int = 0
    total_labels: int = 0
    total_refs: int = 0
    total_citations: int = 0
    bib_entries: int = 0


@dataclass
class CheckReport:
    """Pipeline 聚合报告。"""

    project_dir: str = ""
    main_file: str = ""
    timestamp: str = ""
    venue: str = "generic"
    venue_display: str = "Generic LaTeX"
    lint: LintStageResult = field(default_factory=LintStageResult)
    verify: VerifyStageResult | None = None
    stats: StatsStageResult = field(default_factory=StatsStageResult)
    issues: list[dict[str, Any]] = field(default_factory=list)
    report_path: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
        severity_counts = _severity_counts(self)
        payload["summary"] = {
            "errors": severity_counts["error"],
            "warnings": severity_counts["warning"],
            "info": severity_counts["info"],
            "uncertain": severity_counts["uncertain"],
        }
        payload["verify_summary"] = (
            {
                "verified": self.verify.verified,
                "mismatch": self.verify.mismatch,
                "not_found": self.verify.not_found,
                "uncertain": self.verify.uncertain,
                "rate_limited": self.verify.rate_limited,
            }
            if self.verify is not None
            else None
        )
        payload["submission_readiness"] = submission_readiness(self)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), ensure_ascii=False, indent=2)


def run_check(
    tex_path: str | Path,
    *,
    config: HypoConfig | None = None,
    fix: bool = True,
    dry_run: bool = True,
    backup: bool = False,
    lint_only: bool = False,
    no_fix: bool = False,
    verify: bool = True,
    rules: list[str] | None = None,
    save_report: bool = True,
    venue: VenueProfile | None = None,
) -> CheckReport:
    """Run the writing-quality pipeline and aggregate results into a report."""
    input_path = Path(tex_path).expanduser()
    if not input_path.is_absolute():
        input_path = input_path.resolve()

    loaded_config = config or load_config(input_path.parent if input_path.exists() else Path.cwd())
    venue_profile = venue or get_venue(loaded_config.project.venue)
    project = resolve_project(input_path, config=loaded_config)
    initial_stats = extract_stats(
        project.root_file,
        project=project,
        venue=venue_profile,
        strict_doi=loaded_config.verify.strict_doi,
    )
    initial_display_stats = _apply_severity_overrides(initial_stats, loaded_config)
    selected_rules = _selected_lint_rules(loaded_config)
    initial_issues = initial_display_stats.filtered_issues(selected_rules)
    effective_fix_rules = _selected_fix_rules(rules, loaded_config)
    fixes = generate_fixes(initial_stats, project=project, rules=effective_fix_rules)
    fixes_available = len(fixes)
    fixes_applied = 0

    if lint_only:
        verify = False

    if fix and not no_fix:
        fix_report = apply_fixes(
            fixes,
            project=project,
            dry_run=dry_run,
            backup=backup and not dry_run,
        )
        if not dry_run:
            fixes_applied = max(0, len(fix_report.fixes) - len(fix_report.errors))
            project = resolve_project(project.root_file, config=loaded_config)
            final_stats = extract_stats(
                project.root_file,
                project=project,
                venue=venue_profile,
                strict_doi=loaded_config.verify.strict_doi,
            )
        else:
            final_stats = initial_stats
    else:
        final_stats = initial_stats

    final_display_stats = _apply_severity_overrides(final_stats, loaded_config)
    final_issues = final_display_stats.filtered_issues(selected_rules)
    verify_result = (
        _run_verify_stage(project, loaded_config, venue_profile)
        if verify and project.bib_files
        else None
    )
    final_issue_payload = [
        {
            "rule": issue.rule,
            "severity": issue.severity.value,
            "severity_source": issue.severity_source,
            "file": issue.file,
            "line": issue.line,
            "message": issue.message,
            "context": issue.context,
        }
        for issue in final_issues
    ]

    report = CheckReport(
        project_dir=project.project_dir.as_posix(),
        main_file=_relative_to(project.root_file, project.project_dir),
        timestamp=datetime.now().astimezone().isoformat(),
        venue=venue_profile.name,
        venue_display=venue_profile.display_name,
        lint=LintStageResult(
            total_issues=len(final_issues),
            errors=sum(1 for issue in final_issues if issue.severity == "error"),
            warnings=sum(1 for issue in final_issues if issue.severity == "warning"),
            fixes_applied=fixes_applied,
            fixes_available=fixes_available,
            rules_triggered=sorted({issue.rule for issue in initial_issues}),
        ),
        verify=verify_result,
        stats=StatsStageResult(
            total_files=len(final_stats.files),
            total_sections=len(final_stats.sections),
            total_floats=len(final_stats.floats),
            total_labels=len(final_stats.labels),
            total_refs=len(final_stats.refs),
            total_citations=len(final_stats.citations),
            bib_entries=len(final_stats.bib_entries),
        ),
        issues=final_issue_payload,
    )

    if save_report:
        report.report_path = _save_report(report, project.project_dir)
    return report


def render_check_report(report: CheckReport) -> str:
    """Render a concise human-readable check summary."""
    lines = [
        "=== Hypo-Research Check Report ===",
        "",
        f"Project: {report.project_dir} ({report.main_file})",
    ]
    if report.venue != "generic":
        lines.extend(["", f"Venue: {report.venue_display}"])
    lines.extend(
        [
            "",
            (
                f"Lint: {report.lint.errors} errors, {report.lint.warnings} warnings"
                f" | fixes applied: {report.lint.fixes_applied}"
                f" | fixes available: {report.lint.fixes_available}"
            ),
        ]
    )
    if report.issues:
        for issue in report.issues:
            severity = issue["severity"]
            severity_source = issue.get("severity_source") or ""
            severity_label = f"{severity} ({severity_source})" if severity_source else severity
            location = (
                f"{issue['file']}:{issue['line']}"
                if issue["file"]
                else f"line {issue['line']}"
            )
            lines.append(f"[{issue['rule']}] {severity_label} {location} — {issue['message']}")
    if report.lint.rules_triggered:
        lines.append(f"Rules: {', '.join(report.lint.rules_triggered)}")
    if report.verify is None:
        lines.append("Verify: skipped")
    else:
        lines.extend(
            [
                "Verify:",
                f"  verified: {report.verify.verified}",
                f"  mismatch: {report.verify.mismatch}",
                f"  not_found: {report.verify.not_found}",
                f"  uncertain: {report.verify.uncertain}",
                f"  rate_limited: {report.verify.rate_limited}",
            ]
        )
    lines.append(
        "Stats: "
        f"{report.stats.total_sections} sections, "
        f"{report.stats.total_floats} floats, "
        f"{report.stats.total_labels} labels, "
        f"{report.stats.total_citations} citations"
    )
    lines.extend(
        [
            "",
            "Bottom Line:",
            f"  Errors: {_severity_counts(report)['error']}",
            f"  Warnings: {_severity_counts(report)['warning']}",
            f"  Info: {_severity_counts(report)['info']}",
            f"  Uncertain: {_severity_counts(report)['uncertain']}",
            (
                f"  Verify: {report.verify.verified}/{report.verify.total_entries} verified, "
                f"{report.verify.rate_limited} rate-limited"
                if report.verify is not None
                else "  Verify: skipped"
            ),
            f"  Submission readiness: {submission_readiness_label(report)}",
        ]
    )
    if report.report_path is not None:
        lines.append(f"Report saved to: {report.report_path}")
    return "\n".join(lines)


def check_exit_code(report: CheckReport, *, runtime_error: bool = False) -> int:
    """Return CLI exit code for a completed check report."""
    if runtime_error:
        return 2
    if report.lint.errors > 0 or report.lint.warnings > 0:
        return 1
    if report.verify is not None and (report.verify.mismatch > 0 or report.verify.not_found > 0):
        return 1
    return 0


def submission_readiness(report: CheckReport) -> str:
    """Return machine-readable submission readiness state."""
    counts = _severity_counts(report)
    if counts["error"] > 0:
        return "fail"
    if counts["warning"] > 0:
        return "review"
    return "pass"


def submission_readiness_label(report: CheckReport) -> str:
    """Return a human-readable readiness summary."""
    state = submission_readiness(report)
    if state == "fail":
        return f"❌ Blocking issues found for {report.venue_display}"
    if state == "review":
        return f"⚠️ Review recommended before submission to {report.venue_display}"
    return f"✅ No blocking issues for {report.venue_display}"


def _selected_lint_rules(config: HypoConfig) -> set[str] | None:
    if config.lint.enabled_rules:
        return set(config.lint.enabled_rules) - set(config.lint.disabled_rules)
    if config.lint.disabled_rules:
        all_rules = {f"L{index:02d}" for index in range(1, 20)}
        return all_rules - set(config.lint.disabled_rules)
    return None


def _selected_fix_rules(rules: list[str] | None, config: HypoConfig) -> list[str] | None:
    if rules is not None:
        return [rule.upper() for rule in rules]
    if config.lint.fix_rules:
        return [rule for rule in config.lint.fix_rules if rule not in set(config.lint.disabled_rules)]
    if config.lint.disabled_rules:
        return [
            rule
            for rule in ["L01", "L02", "L03", "L04", "L05", "L06", "L11", "L13"]
            if rule not in set(config.lint.disabled_rules)
        ]
    return None


def _apply_severity_overrides(stats: TexStats, config: HypoConfig) -> TexStats:
    if not config.lint.severity_overrides:
        return stats
    adjusted = copy.deepcopy(stats)
    for issue in adjusted.issues:
        override = config.lint.severity_overrides.get(issue.rule)
        if override is not None:
            issue.severity = coerce_severity(override)
            issue.severity_source = "config"
    return adjusted


def _run_verify_stage(
    project,
    config: HypoConfig,
    venue: VenueProfile,
) -> VerifyStageResult | None:
    try:
        report = asyncio.run(
            verify_bib(
                project=project,
                tex_path=project.root_file,
                venue=venue,
                s2_api_key=config.verify.s2_api_key,
                timeout=config.verify.timeout,
                skip_keys=config.verify.skip_keys,
                max_concurrent=config.verify.max_concurrent,
                max_requests_per_second=config.verify.max_requests_per_second,
                strict_doi=config.verify.strict_doi,
            )
        )
    except Exception:
        return VerifyStageResult(error=1)

    return _verify_stage_from_report(report)


def _verify_stage_from_report(report: VerifyReport) -> VerifyStageResult:
    return VerifyStageResult(
        total_entries=report.total,
        verified=report.verified,
        mismatch=report.mismatch,
        not_found=report.not_found,
        uncertain=report.uncertain,
        rate_limited=report.rate_limited,
        error=report.error,
        skipped=len(report.skipped),
    )


def _save_report(report: CheckReport, project_dir: Path) -> str:
    report_dir = project_dir / ".hypo-research-report"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"check-{datetime.now().astimezone().date().isoformat()}.json"
    report.report_path = report_path.as_posix()
    report_path.write_text(report.to_json(), encoding="utf-8")
    return report.report_path


def _relative_to(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _severity_counts(report: CheckReport) -> dict[str, int]:
    """Aggregate lint and verify severities for reporting."""
    counts = {
        "error": sum(1 for issue in report.issues if issue.get("severity") == Severity.ERROR.value),
        "warning": sum(1 for issue in report.issues if issue.get("severity") == Severity.WARNING.value),
        "info": sum(1 for issue in report.issues if issue.get("severity") == Severity.INFO.value),
        "uncertain": sum(1 for issue in report.issues if issue.get("severity") == Severity.UNCERTAIN.value),
    }
    if report.verify is not None:
        counts["error"] += report.verify.mismatch
        counts["warning"] += report.verify.not_found
        counts["uncertain"] += report.verify.uncertain + report.verify.rate_limited + report.verify.error
    return counts
