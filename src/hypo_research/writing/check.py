"""Writing pipeline orchestration for lint, fix, verify, and reporting."""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from hypo_research.writing.config import HypoConfig, load_config
from hypo_research.writing.fixer import apply_fixes, generate_fixes
from hypo_research.writing.project import resolve_project
from hypo_research.writing.stats import TexStats, extract_stats
from hypo_research.writing.verify import VerifyReport, verify_bib


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
    lint: LintStageResult = field(default_factory=LintStageResult)
    verify: VerifyStageResult | None = None
    stats: StatsStageResult = field(default_factory=StatsStageResult)
    report_path: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
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
) -> CheckReport:
    """Run the writing-quality pipeline and aggregate results into a report."""
    input_path = Path(tex_path).expanduser()
    if not input_path.is_absolute():
        input_path = input_path.resolve()

    loaded_config = config or load_config(input_path.parent if input_path.exists() else Path.cwd())
    project = resolve_project(input_path, config=loaded_config)
    initial_stats = extract_stats(project.root_file, project=project)
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
            final_stats = extract_stats(project.root_file, project=project)
        else:
            final_stats = initial_stats
    else:
        final_stats = initial_stats

    final_display_stats = _apply_severity_overrides(final_stats, loaded_config)
    final_issues = final_display_stats.filtered_issues(selected_rules)
    verify_result = _run_verify_stage(project, loaded_config) if verify and project.bib_files else None

    report = CheckReport(
        project_dir=project.project_dir.as_posix(),
        main_file=_relative_to(project.root_file, project.project_dir),
        timestamp=datetime.now().astimezone().isoformat(),
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
        "",
        (
            f"Lint: {report.lint.errors} errors, {report.lint.warnings} warnings"
            f" | fixes applied: {report.lint.fixes_applied}"
            f" | fixes available: {report.lint.fixes_available}"
        ),
    ]
    if report.lint.rules_triggered:
        lines.append(f"Rules: {', '.join(report.lint.rules_triggered)}")
    if report.verify is None:
        lines.append("Verify: skipped")
    else:
        lines.append(
            "Verify: "
            f"{report.verify.verified}/{report.verify.total_entries} verified"
            f" | mismatch: {report.verify.mismatch}"
            f" | not_found: {report.verify.not_found}"
            f" | uncertain: {report.verify.uncertain}"
            f" | rate_limited: {report.verify.rate_limited}"
        )
    lines.append(
        "Stats: "
        f"{report.stats.total_sections} sections, "
        f"{report.stats.total_floats} floats, "
        f"{report.stats.total_labels} labels, "
        f"{report.stats.total_citations} citations"
    )
    if report.report_path is not None:
        lines.append(f"Report saved to: {report.report_path}")
    return "\n".join(lines)


def check_exit_code(report: CheckReport, *, runtime_error: bool = False) -> int:
    """Return CLI exit code for a completed check report."""
    if runtime_error:
        return 2
    if report.lint.errors > 0:
        return 1
    if report.verify is not None and (report.verify.mismatch > 0 or report.verify.not_found > 0):
        return 1
    return 0


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
            issue.severity = override
    return adjusted


def _run_verify_stage(project, config: HypoConfig) -> VerifyStageResult | None:
    try:
        report = asyncio.run(
            verify_bib(
                project=project,
                tex_path=project.root_file,
                s2_api_key=config.verify.s2_api_key,
                timeout=config.verify.timeout,
                skip_keys=config.verify.skip_keys,
                max_concurrent=config.verify.max_concurrent,
                max_requests_per_second=config.verify.max_requests_per_second,
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
