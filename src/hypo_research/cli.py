"""CLI entrypoints for Hypo-Research."""

from __future__ import annotations

import asyncio
import ast
import copy
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import click
from click.core import ParameterSource
from rich.console import Console
from rich.table import Table

from hypo_research.cite import CitationTraverser
from hypo_research.core.models import (
    ExpansionTrace,
    PaperResult,
    QueryVariant,
    SearchParams,
    SearchResult,
    SurveyMeta,
)
from hypo_research.core.sources import (
    ArxivSource,
    BaseSource,
    OpenAlexSource,
    SemanticScholarSource,
    SourceError,
)
from hypo_research.core.verifier import Verifier
from hypo_research.hooks import AutoBibHook, AutoReportHook, AutoVerifyHook, HookContext, HookEvent, HookManager
from hypo_research.meeting import (
    GlossaryManager,
    GlossaryTerm,
    MeetingInput,
    MeetingProcessor,
    get_template,
    list_templates,
)
from hypo_research.output.json_output import write_search_output
from hypo_research.output.markdown_report import generate_report
from hypo_research.presubmit import (
    PresubmitVerdict,
    render_presubmit_report,
    run_presubmit,
)
from hypo_research.review.literature import LiteratureContext, search_literature
from hypo_research.review.parser import PaperStructure, parse_paper
from hypo_research.review.report import (
    MetaReview,
    ReviewReport,
    RevisionItem,
    RevisionRoadmap,
    SingleReview,
    generate_report_json as generate_review_report_json,
    generate_report_markdown as generate_review_report_markdown,
)
from hypo_research.review.reviewers import (
    DEFAULT_PANEL,
    FULL_PANEL,
    REVIEWERS,
    SEVERITY_MODIFIERS,
    ReviewerConfig,
    Severity as ReviewSeverity,
    get_meta_review_prompt,
    get_revision_roadmap_prompt,
    get_reviewer_prompt,
)
from hypo_research.review.venues import VENUES as REVIEW_VENUES
from hypo_research.survey.targeted import TargetedSearch, slugify_query
from hypo_research.writing.bib_parser import parse_bib, parse_bib_files
from hypo_research.writing.check import check_exit_code, render_check_report, run_check
from hypo_research.writing.config import (
    CONFIG_FILENAME,
    HypoConfig,
    detect_project_config_values,
    generate_default_config,
    load_config,
)
from hypo_research.writing.fixer import FixReport, apply_fixes, generate_fixes
from hypo_research.writing.project import MultipleMainFilesError, TexProject, resolve_project
from hypo_research.writing.severity import Severity, coerce_severity
from hypo_research.writing.stats import TexStats, extract_stats
from hypo_research.writing.venue import VenueProfile, get_venue, list_venues
from hypo_research.writing.verify import VerifyReport, verify_bib


def _truncate(value: str | None, limit: int) -> str:
    if not value:
        return "-"
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _normalize_queries(queries: list[str]) -> list[str]:
    """Remove empty query strings while preserving order."""
    normalized: list[str] = []
    for query in queries:
        cleaned = query.strip()
        if cleaned:
            normalized.append(cleaned)
    return normalized


def _cli_value_provided(ctx: click.Context, name: str) -> bool:
    source = ctx.get_parameter_source(name)
    return source in {
        ParameterSource.COMMANDLINE,
        ParameterSource.ENVIRONMENT,
        ParameterSource.PROMPT,
    }


def _load_command_config(
    *,
    start_dir: str | Path | None = None,
) -> HypoConfig:
    config = load_config(start_dir)
    if config.config_path is not None:
        click.echo(f"Loaded config from {config.config_path}", err=True)
    return config


def _resolve_venue_profile(
    *,
    cli_venue: str | None,
    config: HypoConfig,
) -> VenueProfile:
    venue_name = cli_venue or config.project.venue or "generic"
    if venue_name not in list_venues():
        choices = ", ".join(list_venues())
        raise click.ClickException(f"Unknown venue '{venue_name}'. Available: {choices}")
    return get_venue(venue_name)


class OptionEatAll(click.Option):
    """A Click option that consumes values until the next option token."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.pop("nargs", None)
        super().__init__(*args, **kwargs)
        self.nargs = 1
        self._previous_parser_process = None
        self._parser = None

    def add_to_parser(self, parser: click.parser.OptionParser, ctx: click.Context) -> None:
        def parser_process(value: str, state: click.parser.ParsingState) -> None:
            collected = [value]
            assert self._parser is not None
            prefixes = tuple(self._parser.prefixes)
            while state.rargs and not state.rargs[0].startswith(prefixes):
                collected.append(state.rargs.pop(0))
            assert self._previous_parser_process is not None
            self._previous_parser_process(tuple(collected), state)

        retval = super().add_to_parser(parser, ctx)
        for option_name in self.opts:
            our_parser = parser._long_opt.get(option_name) or parser._short_opt.get(option_name)
            if our_parser is not None:
                self._parser = our_parser
                self._previous_parser_process = our_parser.process
                our_parser.process = parser_process
                break
        return retval


def _normalize_seeds(raw_values: tuple[str, ...] | str) -> list[str]:
    """Normalize --seeds values, supporting either split or comma-separated input."""
    seeds: list[str] = []
    values = (raw_values,) if isinstance(raw_values, str) else raw_values
    for raw_value in values:
        if raw_value.startswith(("(", "[")) and raw_value.endswith((")", "]")):
            try:
                parsed = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError):
                parsed = None
            if isinstance(parsed, (list, tuple)):
                seeds.extend(_normalize_seeds(tuple(str(item) for item in parsed)))
                continue
        for candidate in raw_value.split(","):
            cleaned = candidate.strip()
            if cleaned:
                seeds.append(cleaned)
    return seeds


def _parse_rules_option(raw_value: str | None) -> set[str] | None:
    """Parse a comma-separated lint rule filter."""
    if raw_value is None:
        return None
    rules = {
        candidate.strip().upper()
        for candidate in raw_value.split(",")
        if candidate.strip()
    }
    return rules or None


def _parse_csv_option(raw_value: str | None) -> list[str]:
    """Parse a comma-separated option value."""
    if raw_value is None:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _resolve_lint_rules(
    *,
    cli_rules: set[str] | None,
    config: HypoConfig,
) -> set[str] | None:
    if cli_rules is not None:
        return cli_rules
    if config.lint.enabled_rules:
        return set(config.lint.enabled_rules) - set(config.lint.disabled_rules)
    if config.lint.disabled_rules:
        all_rules = {f"L{index:02d}" for index in range(1, 20)}
        return all_rules - set(config.lint.disabled_rules)
    return None


def _resolve_fix_rules(
    *,
    cli_rules: set[str] | None,
    config: HypoConfig,
) -> list[str] | None:
    if cli_rules is not None:
        return sorted(cli_rules)
    if config.lint.fix_rules:
        return list(config.lint.fix_rules)
    return None


def _format_lint_issue(issue: object, *, show_file: bool) -> str:
    """Render a human-readable lint issue line."""
    rule = getattr(issue, "rule")
    file = getattr(issue, "file")
    line = getattr(issue, "line")
    message = getattr(issue, "message")
    severity = getattr(issue, "severity")
    severity_source = getattr(issue, "severity_source", "")
    severity_text = str(severity)
    if severity_source:
        severity_text = f"{severity_text} ({severity_source})"
    if show_file and file:
        return f"[{rule}] {severity_text} {file}:{line} — {message}"
    return f"[{rule}] {severity_text} line {line} — {message}"


def _format_fix(fix: object, *, show_file: bool, applied: bool) -> str:
    rule = getattr(fix, "rule")
    file = getattr(fix, "file")
    line = getattr(fix, "line")
    original = getattr(fix, "original")
    replacement = getattr(fix, "replacement")
    location = f"{file}:{line}" if show_file and file else f"line {line}"
    status = " ✓" if applied else ""
    return f"[{rule}] {location} — {original} → {replacement}{status}"


def _render_fix_report(report: FixReport, *, show_file: bool) -> list[str]:
    title = "=== Auto-Fix Report (dry-run) ===" if report.dry_run else "=== Auto-Fix Report ==="
    lines = [title, ""]
    if report.fixes:
        for fix in report.fixes:
            lines.append(_format_fix(fix, show_file=show_file, applied=not report.dry_run))
    else:
        lines.append("No fixes available.")

    lines.append("")
    if report.dry_run:
        lines.append(f"{len(report.fixes)} fixes available. Run with --no-dry-run to apply.")
    else:
        lines.append(f"{len(report.fixes)} fixes applied to {len(report.files_modified)} files.")
        if report.backup_paths:
            lines.append(f"Backup: {', '.join(report.backup_paths)}")
    if report.errors:
        lines.append(f"Errors: {len(report.errors)}")
        lines.extend(report.errors)
    return lines


def _apply_severity_overrides(
    stats: TexStats,
    config: HypoConfig,
) -> TexStats:
    if not config.lint.severity_overrides:
        return stats
    adjusted = copy.deepcopy(stats)
    for issue in adjusted.issues:
        override = config.lint.severity_overrides.get(issue.rule)
        if override is not None:
            issue.severity = coerce_severity(override)
            issue.severity_source = "config"
    return adjusted


def _lint_exit_code(stats: TexStats, rules: set[str] | None) -> int:
    """Return lint exit code based on filtered error severity."""
    return 1 if any(issue.severity == "error" for issue in stats.filtered_issues(rules)) else 0


def _parse_keys_option(raw_value: str | None) -> list[str] | None:
    """Parse a comma-separated cite-key filter."""
    if raw_value is None:
        return None
    keys = [candidate.strip() for candidate in raw_value.split(",") if candidate.strip()]
    return keys or None


def _verify_exit_code(report: VerifyReport) -> int:
    """Return verify exit code based on high-severity verification outcomes."""
    return 1 if report.mismatch > 0 or report.not_found > 0 or report.error > 0 else 0


def _estimate_verify_total(
    bib_path: Path | None,
    bib_paths: list[Path] | None,
    tex_path: Path | None,
    project: TexProject | None,
    keys: list[str] | None,
    skip_keys: list[str] | None = None,
) -> int:
    """Estimate how many entries will be verified for progress reporting."""
    if bib_paths:
        entries = parse_bib_files(bib_paths)
    elif bib_path is not None:
        entries = parse_bib(bib_path.as_posix())
    elif project is not None:
        entries = parse_bib_files(project.bib_files) if len(project.bib_files) > 1 else (
            parse_bib(project.bib_files[0].as_posix()) if project.bib_files else []
        )
    else:
        entries = []
    selected_keys = {key for key in keys or []} if keys else None
    if tex_path is not None or project is not None:
        stats = extract_stats(tex_path or project.root_file, project=project)
        cited_keys = {citation.key for citation in stats.citations}
        selected_keys = cited_keys if selected_keys is None else selected_keys & cited_keys

    filtered = entries
    if selected_keys is not None:
        filtered = [entry for entry in filtered if entry.key in selected_keys]
    if skip_keys:
        skip_key_set = {key for key in skip_keys}
        filtered = [entry for entry in filtered if entry.key not in skip_key_set]
    return len(filtered)


def _resolve_existing_path(path: Path, *, project_dir: Path | None = None) -> Path:
    candidates = [path]
    if project_dir is not None and not path.is_absolute():
        candidates.insert(0, project_dir / path)
    for candidate in candidates:
        expanded = candidate.expanduser()
        if expanded.exists():
            return expanded.resolve()
    return candidates[0].expanduser().resolve()


def _resolve_optional_file(
    path: Path | None,
    *,
    project_dir: Path | None = None,
    must_exist: bool = True,
) -> Path | None:
    if path is None:
        return None
    resolved = _resolve_existing_path(path, project_dir=project_dir)
    if must_exist and not resolved.exists():
        raise click.ClickException(f"Path does not exist: {path}")
    return resolved


def _resolve_project_arg(
    path: Path,
    *,
    project_dir: Path | None = None,
    config: HypoConfig | None = None,
) -> TexProject:
    resolved_input = _resolve_optional_file(path, project_dir=project_dir)
    assert resolved_input is not None
    try:
        return resolve_project(resolved_input, config=config)
    except (FileNotFoundError, MultipleMainFilesError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_project_root_only(project_dir: Path, *, config: HypoConfig | None = None) -> TexProject:
    try:
        return resolve_project(project_dir, config=config)
    except (FileNotFoundError, MultipleMainFilesError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def _load_queries_payload(
    queries_file: Path,
) -> tuple[list[str], ExpansionTrace | None]:
    """Load query list and optional expansion trace from a JSON file."""
    try:
        payload = json.loads(queries_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid JSON in queries file: {exc}") from exc

    if not isinstance(payload, dict):
        raise click.ClickException("queries file must contain a JSON object")

    queries = payload.get("queries")
    if not isinstance(queries, list) or not all(isinstance(item, str) for item in queries):
        raise click.ClickException("queries file must contain a 'queries' string list")

    expansion_trace_payload = payload.get("expansion_trace")
    expansion_trace = None
    if expansion_trace_payload is not None:
        try:
            expansion_trace = ExpansionTrace.model_validate(expansion_trace_payload)
        except Exception as exc:
            raise click.ClickException(f"Invalid expansion_trace payload: {exc}") from exc

    return _normalize_queries(queries), expansion_trace


def _apply_relevance_threshold(
    result: SearchResult,
    threshold: int,
) -> tuple[int, int]:
    """Filter papers in-place using pre-filled relevance scores."""
    before_count = len(result.papers)
    filtered = [
        paper
        for paper in result.papers
        if paper.relevance_score is None or paper.relevance_score >= threshold
    ]
    result.papers = filtered
    if result.meta.pre_filter_count is None:
        result.meta.pre_filter_count = before_count
    result.meta.post_filter_count = len(filtered)
    result.meta.relevance_threshold = threshold
    result.meta.total_results = len(filtered)
    return before_count, len(filtered)


def _resolve_source_names(selected_sources: tuple[str, ...]) -> list[str]:
    if not selected_sources or "all" in selected_sources:
        return ["semantic_scholar", "openalex", "arxiv"]

    mapping = {
        "s2": "semantic_scholar",
        "openalex": "openalex",
        "arxiv": "arxiv",
    }
    resolved = [mapping[source.lower()] for source in selected_sources]
    return list(dict.fromkeys(resolved))


def _build_sources(
    selected_sources: tuple[str, ...],
    s2_api_key: str | None,
    openalex_email: str | None,
) -> list[BaseSource]:
    names = _resolve_source_names(selected_sources)
    sources: list[BaseSource] = []
    for name in names:
        if name == "semantic_scholar":
            sources.append(SemanticScholarSource(api_key=s2_api_key))
        elif name == "openalex":
            sources.append(OpenAlexSource(email=openalex_email))
        elif name == "arxiv":
            sources.append(ArxivSource())
    return sources


def _build_hook_manager(
    no_hooks: bool,
    no_bib: bool,
    no_report: bool,
    no_auto_verify: bool,
) -> HookManager:
    """Build a hook manager based on CLI flags."""
    manager = HookManager()
    if no_hooks:
        return manager
    if not no_auto_verify:
        manager.register(HookEvent.POST_VERIFY, AutoVerifyHook())
    if not no_bib:
        manager.register(HookEvent.POST_OUTPUT, AutoBibHook())
    if not no_report:
        manager.register(HookEvent.POST_OUTPUT, AutoReportHook())
    return manager


async def _run_single_search(
    params: SearchParams,
    output_dir: str | None,
    sources: list[BaseSource],
    hook_manager: HookManager | None,
) -> SearchResult:
    searcher = TargetedSearch(sources=sources, hook_manager=hook_manager)
    try:
        return await searcher.search(params=params, output_dir=output_dir)
    finally:
        await searcher.close()


async def _run_multi_query_search(
    queries: list[str],
    base_params: SearchParams,
    output_dir: str | None,
    sources: list[BaseSource],
    expansion_trace: ExpansionTrace | None,
    hook_manager: HookManager | None,
) -> SearchResult:
    searcher = TargetedSearch(sources=sources, hook_manager=hook_manager)
    try:
        return await searcher.multi_query_search(
            queries=queries,
            base_params=base_params,
            expansion_trace=expansion_trace,
            output_dir=output_dir,
        )
    finally:
        await searcher.close()


async def _run_citation_traversal(
    seeds: list[str],
    depth: int,
    direction: str,
    min_citations: int,
    year_range: tuple[int, int] | None,
    max_papers: int,
    s2_api_key: str | None,
    openalex_email: str | None,
):
    traverser = CitationTraverser(
        s2_source=SemanticScholarSource(api_key=s2_api_key),
        openalex_source=OpenAlexSource(email=openalex_email),
    )
    try:
        return await traverser.traverse(
            seeds=seeds,
            depth=depth,
            direction=direction,
            min_citations=min_citations,
            year_range=year_range,
            max_papers=max_papers,
        )
    finally:
        await traverser.close()


def _resolve_citation_output_dir(seeds: list[str], output_dir: str | None) -> Path:
    """Resolve output directory for citation graph runs."""
    if output_dir is not None:
        return Path(output_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    return Path("data") / "citations" / f"{timestamp}_{slugify_query(seeds[0])}"


def _write_graph_output(output_dir: Path, seed_papers: list, graph_edges: list) -> None:
    """Persist traversal graph metadata alongside standard outputs."""
    payload = {
        "seeds": [
            paper.model_dump(mode="json", exclude={"raw_response"})
            for paper in seed_papers
        ],
        "edges": [asdict(edge) for edge in graph_edges],
    }
    (output_dir / "graph.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


@click.group()
def main() -> None:
    """Hypo-Research: Academic research assistant."""


@main.command()
@click.option(
    "--dir",
    "target_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    help="Directory to initialize with a .hypo-research.toml file.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite an existing config file.",
)
def init(target_dir: Path, force: bool) -> None:
    """Create a default project config file in the target directory."""
    resolved_dir = target_dir.expanduser().resolve()
    resolved_dir.mkdir(parents=True, exist_ok=True)
    config_path = resolved_dir / CONFIG_FILENAME
    if config_path.exists() and not force:
        raise click.ClickException(f"{CONFIG_FILENAME} already exists at {config_path}")

    content = generate_default_config(project_dir=resolved_dir)
    config_path.write_text(content, encoding="utf-8")

    detected_main, detected_bibs = detect_project_config_values(resolved_dir)
    click.echo(f"Created {config_path}")
    if detected_main:
        click.echo(f"Detected main_file: {detected_main}")
    if detected_bibs:
        click.echo(f"Detected bib_files: {', '.join(detected_bibs)}")


@main.command()
@click.pass_context
@click.argument(
    "transcript",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--type",
    "meeting_type",
    default="group_meeting",
    show_default=True,
    help="Meeting template name.",
)
@click.option(
    "--participants",
    default=None,
    help="Comma-separated participant names.",
)
@click.option("--topic", default="", help="Meeting topic.")
@click.option("--date", "meeting_date", default="", help="Meeting date, e.g. 2026-04-26.")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output path. Defaults to <transcript_stem>_minutes.md.",
)
@click.option(
    "--list-templates",
    "list_templates_flag",
    is_flag=True,
    default=False,
    help="List built-in meeting templates.",
)
@click.option(
    "--infer",
    "infer_only",
    is_flag=True,
    default=False,
    help="Only infer meeting metadata and print JSON.",
)
def meeting(
    ctx: click.Context,
    transcript: Path | None,
    meeting_type: str,
    participants: str | None,
    topic: str,
    meeting_date: str,
    output: Path | None,
    list_templates_flag: bool,
    infer_only: bool,
) -> None:
    """Prepare meeting transcript context for Agent-written minutes."""
    if list_templates_flag:
        for template_name in list_templates():
            template = get_template(template_name)
            click.echo(
                f"{template.name}\t{template.display_name}\t{template.description}"
            )
        return

    if transcript is None:
        raise click.UsageError(
            "TRANSCRIPT is required unless --list-templates is used"
        )

    processor = MeetingProcessor(GlossaryManager())
    try:
        transcript_text = processor.load_transcript(transcript)
        inference = processor.infer(transcript_text)
        if infer_only:
            click.echo(json.dumps(asdict(inference), ensure_ascii=False, indent=2))
            return

        type_was_provided = _cli_value_provided(ctx, "meeting_type")
        effective_meeting_type = (
            meeting_type
            if type_was_provided
            else inference.meeting_type or meeting_type
        )
        result = processor.write_prompt_context(
            MeetingInput(
                transcript_path=transcript,
                meeting_type=effective_meeting_type,
                participants=_parse_csv_option(participants),
                date=meeting_date,
                topic=topic,
                output_path=output,
            )
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    inferred_suffix = " (inferred)" if not type_was_provided else ""
    click.echo(
        "Inference: "
        f"{result.inference.meeting_type} "
        f"({result.inference.meeting_type_confidence} confidence)"
        f"{inferred_suffix}"
    )
    click.echo(f"Output: {result.minutes_path}")
    click.echo(f"Template: {result.template_used}")
    click.echo(f"Terms corrected: {', '.join(result.terms_corrected) or 'None'}")
    if result.unknown_terms:
        click.echo(f"Unknown terms: {', '.join(result.unknown_terms)}")


@main.group()
def glossary() -> None:
    """Manage the global meeting glossary."""


@glossary.command("list")
@click.option("--category", default=None, help="Filter terms by category.")
def glossary_list(category: str | None) -> None:
    """List glossary terms."""
    manager = GlossaryManager()
    terms = manager.load()
    filtered = [
        term
        for term in terms.values()
        if category is None or term.category == category
    ]
    if not filtered:
        click.echo("No glossary terms found.")
        return

    for term in sorted(filtered, key=lambda item: item.keyword.lower()):
        aliases = ", ".join(term.aliases) if term.aliases else "-"
        category_text = f" [{term.category}]" if term.category else ""
        click.echo(
            f"{term.keyword}{category_text}: {term.canonical} (aliases: {aliases})"
        )


@glossary.command("add")
@click.option("--keyword", required=True, help="Primary keyword.")
@click.option("--canonical", required=True, help="Canonical spelling.")
@click.option("--aliases", default="", help="Comma-separated aliases.")
@click.option("--category", default="", help="Optional category.")
def glossary_add(
    keyword: str,
    canonical: str,
    aliases: str,
    category: str,
) -> None:
    """Add or update a glossary term."""
    manager = GlossaryManager()
    manager.load()
    manager.add_term(
        GlossaryTerm(
            keyword=keyword,
            canonical=canonical,
            aliases=_parse_csv_option(aliases),
            category=category,
        )
    )
    manager.save()
    click.echo(f"Added glossary term: {keyword}")


@glossary.command("remove")
@click.option("--keyword", required=True, help="Keyword or alias to remove.")
def glossary_remove(keyword: str) -> None:
    """Remove a glossary term."""
    manager = GlossaryManager()
    manager.load()
    removed = manager.remove_term(keyword)
    if not removed:
        raise click.ClickException(f"Glossary term not found: {keyword}")
    manager.save()
    click.echo(f"Removed glossary term: {keyword}")


@glossary.command("search")
@click.argument("keyword")
def glossary_search(keyword: str) -> None:
    """Search a glossary term by keyword or alias."""
    manager = GlossaryManager()
    term = manager.lookup(keyword)
    if term is None:
        raise click.ClickException(f"Glossary term not found: {keyword}")
    aliases = ", ".join(term.aliases) if term.aliases else "-"
    category = f" [{term.category}]" if term.category else ""
    click.echo(f"{term.keyword}{category}: {term.canonical} (aliases: {aliases})")


@main.command()
@click.argument("tex_root", type=click.Path(exists=True, path_type=Path))
@click.option("--venue", default=None, help="Venue profile, e.g. ieee_journal.")
@click.option(
    "--skip",
    "skip_stages",
    multiple=True,
    type=click.Choice(["check", "lint", "verify"]),
    help="Stage to skip. Can be used multiple times.",
)
@click.option("--bib", "bib_file", default=None, type=click.Path(path_type=Path), help="BibTeX file for verify stage.")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Write Markdown report to file.")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Print JSON payload.")
def presubmit(
    tex_root: Path,
    venue: str | None,
    skip_stages: tuple[str, ...],
    bib_file: Path | None,
    output: Path | None,
    json_mode: bool,
) -> None:
    """Run the full pre-submission check pipeline."""
    result = run_presubmit(
        tex_root.as_posix(),
        venue=venue,
        skip_stages=list(skip_stages),
        bib_file=bib_file.as_posix() if bib_file is not None else None,
    )
    rendered = (
        json.dumps(result.to_payload(), indent=2, ensure_ascii=False)
        if json_mode
        else render_presubmit_report(result)
    )
    if output is not None:
        output.write_text(rendered, encoding="utf-8")
    else:
        click.echo(rendered, nl=not rendered.endswith("\n"))
    raise click.exceptions.Exit(_presubmit_exit_code(result.verdict))


def _presubmit_exit_code(verdict: PresubmitVerdict) -> int:
    if verdict is PresubmitVerdict.FAIL:
        return 1
    if verdict is PresubmitVerdict.WARNING:
        return 2
    return 0


def _normalize_reviewer_ids(raw_values: tuple[str, ...] | str | None) -> list[str]:
    """Normalize reviewer ids from comma-separated or space-separated CLI input."""
    if raw_values is None:
        return []
    values = (raw_values,) if isinstance(raw_values, str) else raw_values
    reviewer_ids: list[str] = []
    for raw_value in values:
        if isinstance(raw_value, (tuple, list)):
            reviewer_ids.extend(_normalize_reviewer_ids(tuple(str(item) for item in raw_value)))
            continue
        text_value = str(raw_value).strip()
        if text_value.startswith(("(", "[")) and text_value.endswith((")", "]")):
            try:
                parsed = ast.literal_eval(text_value)
            except (SyntaxError, ValueError):
                parsed = None
            if isinstance(parsed, (tuple, list)):
                reviewer_ids.extend(_normalize_reviewer_ids(tuple(str(item) for item in parsed)))
                continue
        for candidate in text_value.replace(",", " ").split():
            cleaned = candidate.strip().lower()
            if cleaned:
                reviewer_ids.append(cleaned)
    return list(dict.fromkeys(reviewer_ids))


def _resolve_review_panel(panel: str, reviewers: tuple[str, ...] | str | None) -> list[str]:
    selected = _normalize_reviewer_ids(reviewers)
    if selected:
        unknown = [reviewer_id for reviewer_id in selected if reviewer_id not in REVIEWERS]
        if unknown:
            choices = ", ".join(REVIEWERS)
            raise click.ClickException(f"Unknown reviewer id: {', '.join(unknown)}. Available: {choices}")
        return selected
    if panel == "full":
        return list(FULL_PANEL)
    return list(DEFAULT_PANEL)


def _build_review_scaffold(
    paper: PaperStructure,
    reviewer_ids: list[str],
    severity: ReviewSeverity,
    venue: str | None,
    literature: LiteratureContext | None = None,
) -> ReviewReport:
    """Build a structured report shell; Agent personas fill semantic judgments."""
    severity_label = SEVERITY_MODIFIERS[severity]["label"]
    reviews: list[SingleReview] = []
    structural_weaknesses = _structural_review_weaknesses(paper)
    structural_strengths = _structural_review_strengths(paper)
    for reviewer_id in reviewer_ids:
        reviewer = REVIEWERS[reviewer_id]
        reviews.append(
            SingleReview(
                reviewer_id=reviewer.id,
                reviewer_name=reviewer.name,
                reviewer_emoji=reviewer.emoji,
                reviewer_role=reviewer.role,
                severity_label=severity_label,
                summary="CLI 已完成论文解析和审稿 prompt 生成；该条审稿意见需要 Agent 按角色独立填写。",
                strengths=structural_strengths,
                weaknesses=structural_weaknesses,
                questions=["请 Agent 基于该角色 prompt 阅读全文后补充作者问题。"],
                missing_references=[],
                score=None,
                decision=None,
                confidence=None,
            )
        )
    meta_review = _build_meta_review_scaffold(reviewer_ids) if "heyunxiang" in reviewer_ids else None
    revision_roadmap = (
        _build_revision_roadmap_scaffold(meta_review, reviews)
        if meta_review is not None
        else None
    )
    return ReviewReport(
        paper_title=paper.title,
        venue=venue,
        severity=severity.value,
        panel=reviewer_ids,
        reviews=reviews,
        meta_review=meta_review,
        revision_roadmap=revision_roadmap,
        literature=literature,
    )


def _build_meta_review_scaffold(reviewer_ids: list[str]) -> MetaReview:
    reviewers = [
        f"{REVIEWERS[reviewer_id].emoji}{REVIEWERS[reviewer_id].name}"
        for reviewer_id in reviewer_ids
    ]
    return MetaReview(
        ac_name="贺云翔",
        ac_emoji="🏛️",
        consensus_summary="CLI 已生成 AC Meta-Review 结构；请在所有独立审稿完成后由贺云翔综合填写。",
        key_disagreements=["待 Agent 汇总审稿人之间的关键分歧。"],
        final_recommendation="Borderline",
        recommendation_reasoning=f"当前仅有结构化脚手架，已纳入审稿团：{', '.join(reviewers)}。最终建议需基于完整审稿意见更新。",
        actionable_priorities=["待 Agent 根据 Major Issues 和共识问题排序。"],
        confidence=3,
    )


def _build_revision_roadmap_scaffold(
    meta_review: MetaReview,
    reviews: list[SingleReview],
) -> RevisionRoadmap:
    reviewer_names = [f"{review.reviewer_emoji}{review.reviewer_name}" for review in reviews]
    return RevisionRoadmap(
        one_line_summary="CLI 已生成修改路线图结构；请在 Meta-Review 完成后由导师视角补充具体修改计划。",
        must_fix=[
            RevisionItem(
                priority="🔴 必须修改",
                title="处理 AC Meta-Review 中确认的致命问题",
                problem="Meta-Review 尚未由 Agent 填写，当前无法判断具体致命问题。",
                suggestion="完成逐角色审稿后，将所有 Major Issues 合并去重，并优先处理多个审稿人共同指出的问题。",
                effort_estimate="待评估",
                source_reviewers=[f"{meta_review.ac_emoji}{meta_review.ac_name} [Meta-Review]"],
            )
        ],
        should_fix=[],
        can_dismiss=[],
        schedule=[
            {"phase": "Week 1", "time": "Day 1-5", "tasks": "补齐 Must Fix 实验或理论论证"},
            {"phase": "Week 2", "time": "Day 6-10", "tasks": "处理 Should Fix、写作和格式问题"},
        ],
        reviewer_notes=[
            "贺云翔关注 novelty 和本质贡献，rebuttal 必须正面回应。",
            "李超凡关注实验公平性和 claim 是否过度，所有新增数据需要可复核。",
        ],
        concerns_table={
            "reviewers": reviewer_names,
            "issues": {"Novelty": [], "Experiments": [], "Writing": [], "Reproducibility": []},
        },
    )


def _structural_review_strengths(paper: PaperStructure) -> list[str]:
    strengths: list[str] = []
    if paper.abstract:
        strengths.append("解析到完整 abstract，可作为审稿 summary 的基础。")
    if paper.sections:
        strengths.append(f"解析到 {len(paper.sections)} 个章节，论文结构可供逐节审查。")
    if paper.figures or paper.tables:
        strengths.append(f"解析到 {len(paper.figures)} 个 figure 和 {len(paper.tables)} 个 table，可检查图表叙事。")
    return strengths or ["解析器已提取全文 raw_text，可供 Agent 直接审稿。"]


def _structural_review_weaknesses(paper: PaperStructure) -> list[str]:
    weaknesses: list[str] = []
    if not paper.abstract:
        weaknesses.append("[Major] 未识别到 abstract，可能影响审稿人快速判断贡献。")
    if not paper.sections:
        weaknesses.append("[Major] 未识别到章节结构，请确认输入文件是否为完整论文。")
    if not paper.references:
        weaknesses.append("[Major] 未识别到 references，Related Work 和引用完整性需要人工确认。")
    if not paper.claims:
        weaknesses.append("[Minor] 未识别到显式 claim 句子，可能需要人工检查 contribution 表述是否清晰。")
    return weaknesses or ["[Minor] CLI 未发现明显结构缺失；语义问题需由 Agent 审稿判断。"]


def _paper_structure_payload(paper: PaperStructure) -> dict:
    return asdict(paper)


def _render_review_prompt_packet(
    paper: PaperStructure,
    reviewer_ids: list[str],
    severity: ReviewSeverity,
    venue: str | None,
    expert2_domain: str | None,
    literature: LiteratureContext | None = None,
) -> str:
    prompts = []
    meta_prompt = None
    roadmap_prompt = None
    scaffold_reviews: list[SingleReview] = []
    for reviewer_id in reviewer_ids:
        reviewer = REVIEWERS[reviewer_id]
        scaffold_reviews.append(
            SingleReview(
                reviewer_id=reviewer.id,
                reviewer_name=reviewer.name,
                reviewer_emoji=reviewer.emoji,
                reviewer_role=reviewer.role,
                severity_label=SEVERITY_MODIFIERS[severity]["label"],
                summary="待填写",
                weaknesses=[],
            )
        )
        prompts.append(
            f"## {reviewer.emoji} {reviewer.name} — {reviewer.role}\n\n"
            f"{get_reviewer_prompt(reviewer, severity, paper, venue=venue, expert2_domain=expert2_domain, literature=literature)}"
        )
    if "heyunxiang" in reviewer_ids:
        meta_prompt = get_meta_review_prompt(paper, scaffold_reviews, severity, venue=venue, literature=literature)
        meta_review = _build_meta_review_scaffold(reviewer_ids)
        roadmap_prompt = get_revision_roadmap_prompt(paper, scaffold_reviews, meta_review, severity, literature=literature)
    if meta_prompt:
        prompts.append(f"## 🏛️ 贺云翔 — AC Meta-Review\n\n{meta_prompt}")
    if roadmap_prompt:
        prompts.append(f"## 📚 导师视角 — Revision Roadmap\n\n{roadmap_prompt}")
    return "\n\n---\n\n".join(prompts)


@main.command()
@click.argument("paper_path", required=False, type=click.Path(path_type=Path))
@click.option("--venue", default=None, help="Review venue id, e.g. dac, neurips, tcas1.")
@click.option(
    "--panel",
    type=click.Choice(["default", "full"]),
    default="default",
    show_default=True,
    help="Reviewer panel preset.",
)
@click.option(
    "--reviewers",
    cls=OptionEatAll,
    default=None,
    help="Reviewer ids. Accepts comma-separated or space-separated values after one --reviewers flag.",
)
@click.option(
    "--severity",
    type=click.Choice([item.value for item in ReviewSeverity]),
    default=ReviewSeverity.STANDARD.value,
    show_default=True,
    help="Review strictness.",
)
@click.option("--expert2-domain", default=None, help="Adjacent domain context for Expert-2.")
@click.option("--domain", default=None, help="Override inferred paper domain.")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=None, help="Write Markdown report to file.")
@click.option("--json", "json_mode", is_flag=True, default=False, help="Print JSON ReviewReport payload.")
@click.option("--parse-only", is_flag=True, default=False, help="Only parse the paper and print PaperStructure JSON.")
@click.option("--list-reviewers", is_flag=True, default=False, help="List available reviewer personas.")
@click.option("--list-venues", is_flag=True, default=False, help="List available review venues.")
@click.option("--prompts", is_flag=True, default=False, help="Print reviewer prompts instead of the report scaffold.")
@click.option("--no-literature", is_flag=True, default=False, help="跳过自动文献检索（离线/快速模式）")
@click.option("--literature-years", type=int, default=3, show_default=True, help="文献检索的年份范围")
@click.option("--literature-count", type=int, default=8, show_default=True, help="检索的最大文献数量")
def review(
    paper_path: Path | None,
    venue: str | None,
    panel: str,
    reviewers: tuple[str, ...] | str | None,
    severity: str,
    expert2_domain: str | None,
    domain: str | None,
    output: Path | None,
    json_mode: bool,
    parse_only: bool,
    list_reviewers: bool,
    list_venues: bool,
    prompts: bool,
    no_literature: bool,
    literature_years: int,
    literature_count: int,
) -> None:
    """Parse a paper and prepare a multi-reviewer simulated review scaffold."""
    if list_reviewers:
        for reviewer in REVIEWERS.values():
            default_marker = "default" if reviewer.default else "optional"
            scoring = "scoring" if reviewer.scoring else "no-score"
            click.echo(f"{reviewer.id}\t{reviewer.emoji} {reviewer.name}\t{reviewer.role}\t{default_marker}\t{scoring}")
        return

    if list_venues:
        for venue_profile in REVIEW_VENUES.values():
            click.echo(
                f"{venue_profile.id}\t{venue_profile.name}\t{venue_profile.category}\t"
                f"{venue_profile.typical_accept_rate or '-'}\t{venue_profile.page_limit or '-'}"
            )
        return

    if paper_path is None:
        raise click.UsageError("PAPER_PATH is required unless --list-reviewers or --list-venues is used")
    if venue is not None and venue.lower() not in REVIEW_VENUES:
        choices = ", ".join(sorted(REVIEW_VENUES))
        raise click.ClickException(f"Unknown review venue '{venue}'. Available: {choices}")

    try:
        paper = parse_paper(paper_path.as_posix())
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    if domain:
        paper.inferred_domain = domain

    if parse_only:
        click.echo(json.dumps(_paper_structure_payload(paper), indent=2, ensure_ascii=False))
        return

    reviewer_ids = _resolve_review_panel(panel, reviewers)
    review_severity = ReviewSeverity(severity)
    literature = None
    if not no_literature:
        literature = _search_review_literature(
            paper=paper,
            literature_years=literature_years,
            literature_count=literature_count,
        )
    venue_text = None
    venue_profile = None
    if venue is not None:
        venue_profile = REVIEW_VENUES[venue.lower()]
        venue_text = f"{venue_profile.name}: {venue_profile.review_criteria}"

    if prompts:
        rendered = _render_review_prompt_packet(
            paper,
            reviewer_ids,
            review_severity,
            venue_profile or venue_text,
            expert2_domain,
            literature,
        )
    else:
        report = _build_review_scaffold(paper, reviewer_ids, review_severity, venue, literature)
        rendered = (
            json.dumps(generate_review_report_json(report), indent=2, ensure_ascii=False)
            if json_mode
            else generate_review_report_markdown(report)
        )

    if output is not None:
        output.write_text(rendered, encoding="utf-8")
    else:
        click.echo(rendered, nl=not rendered.endswith("\n"))


def _search_review_literature(
    *,
    paper: PaperStructure,
    literature_years: int,
    literature_count: int,
) -> LiteratureContext | None:
    click.echo("📚 正在检索相关文献...", err=True)
    try:
        literature = search_literature(
            paper_title=paper.title,
            paper_abstract=paper.abstract,
            paper_references=paper.references,
            year_range=literature_years,
            max_results=literature_count,
        )
    except Exception as exc:
        click.echo(f"⚠️ 文献检索失败（{exc}），将继续审稿但不含文献对比", err=True)
        return None
    if literature.references:
        cited = sum(1 for reference in literature.references if reference.is_cited_by_paper)
        uncited = len(literature.references) - cited
        click.echo(f"📚 找到 {len(literature.references)} 篇相关文献（{cited} 篇已被引用，{uncited} 篇未被引用）", err=True)
    else:
        click.echo("📚 未找到相关文献，将跳过文献对比", err=True)
    return literature


@main.command()
@click.pass_context
@click.argument("query", required=False)
@click.option("--year-start", type=int, default=None, help="Start year (inclusive)")
@click.option("--year-end", type=int, default=None, help="End year (inclusive)")
@click.option("--max-results", type=int, default=100, help="Maximum number of results")
@click.option("--fields", multiple=True, help="Fields of study filter")
@click.option(
    "--sort",
    type=click.Choice(["all", "overall", "citations", "relevance", "time"]),
    default="all",
    show_default=True,
    help="Markdown ranking view to render.",
)
@click.option("--output-dir", type=str, default=None, help="Override output directory")
@click.option(
    "--extra-query",
    "-eq",
    multiple=True,
    help="Additional query variants (can specify multiple times). Used together with the main QUERY argument.",
)
@click.option(
    "--queries-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="JSON file containing a list of query strings. If provided, QUERY argument and --extra-query are ignored.",
)
@click.option(
    "--relevance-threshold",
    type=click.IntRange(0, 5),
    default=None,
    help="If set, only output papers with relevance_score >= threshold. Relevance scores must be pre-filled in results (e.g. by Agent).",
)
@click.option(
    "--source",
    "-s",
    multiple=True,
    type=click.Choice(["s2", "openalex", "arxiv", "all"], case_sensitive=False),
    default=(),
    help="Data sources to search. Can specify multiple. Default: all.",
)
@click.option(
    "--openalex-email",
    envvar="OPENALEX_EMAIL",
    default=None,
    help="Email for OpenAlex polite pool (higher rate limit).",
)
@click.option(
    "--s2-api-key",
    envvar=["SEMANTIC_SCHOLAR_API_KEY", "S2_API_KEY"],
    default=None,
    help="Semantic Scholar API key",
)
@click.option(
    "--no-hooks",
    is_flag=True,
    default=False,
    help="Disable all hooks (no BibTeX, no report, no auto-verify).",
)
@click.option(
    "--no-bib",
    is_flag=True,
    default=False,
    help="Disable automatic BibTeX generation.",
)
@click.option(
    "--no-report",
    is_flag=True,
    default=False,
    help="Disable automatic Markdown report generation.",
)
@click.option(
    "--no-auto-verify",
    is_flag=True,
    default=False,
    help="Disable automatic metadata quality check.",
)
def search(
    ctx: click.Context,
    query: str | None,
    year_start: int | None,
    year_end: int | None,
    max_results: int,
    fields: tuple[str, ...],
    sort: str,
    output_dir: str | None,
    extra_query: tuple[str, ...],
    queries_file: Path | None,
    relevance_threshold: int | None,
    source: tuple[str, ...],
    openalex_email: str | None,
    s2_api_key: str | None,
    no_hooks: bool,
    no_bib: bool,
    no_report: bool,
    no_auto_verify: bool,
) -> None:
    """Run a targeted literature search."""
    config = _load_command_config()
    if (year_start is None) != (year_end is None):
        raise click.BadParameter(
            "--year-start and --year-end must be provided together"
        )

    expansion_trace: ExpansionTrace | None = None
    if queries_file is not None:
        queries, expansion_trace = _load_queries_payload(queries_file)
    else:
        if not query and config.survey.default_topic:
            query = config.survey.default_topic
        if not query:
            raise click.UsageError(
                "QUERY is required unless --queries-file is provided"
            )
        queries = _normalize_queries([query, *extra_query])
        if len(queries) > 1:
            expansion_trace = ExpansionTrace(
                original_query=queries[0],
                variants=[
                    QueryVariant(
                        query=variant_query,
                        strategy="manual",
                        rationale="Provided via --extra-query",
                    )
                    for variant_query in queries[1:]
                ],
                all_queries=queries,
            )

    if not queries:
        raise click.ClickException("At least one non-empty query is required")

    effective_max_results = max_results if _cli_value_provided(ctx, "max_results") else config.survey.max_results
    effective_sources = source if _cli_value_provided(ctx, "source") else tuple(config.survey.sources)
    sources = _build_sources(effective_sources, s2_api_key, openalex_email)
    hook_manager = _build_hook_manager(
        no_hooks=no_hooks,
        no_bib=no_bib,
        no_report=no_report,
        no_auto_verify=no_auto_verify,
    )
    source_names = [source.name for source in sources]

    base_query = expansion_trace.original_query if expansion_trace else queries[0]
    params = SearchParams(
        query=base_query,
        year_range=(year_start, year_end) if year_start is not None else None,
        fields_of_study=list(fields) or None,
        max_results=effective_max_results,
        sort_by="relevance",
    )

    console = Console()
    console.print(f"Sources: {', '.join(source_names)}")

    try:
        if len(queries) == 1:
            single_params = params.model_copy(update={"query": queries[0]})
            result = asyncio.run(
                _run_single_search(single_params, output_dir, sources, hook_manager)
            )
        else:
            result = asyncio.run(
                _run_multi_query_search(
                    queries=queries,
                    base_params=params,
                    output_dir=output_dir,
                    sources=sources,
                    expansion_trace=expansion_trace,
                    hook_manager=hook_manager,
                )
            )
    except SourceError as exc:
        raise click.ClickException(str(exc)) from exc

    should_persist = False
    if len(queries) == 1 and expansion_trace is not None:
        result.meta.expansion = expansion_trace
        should_persist = True

    if relevance_threshold is not None:
        before_count, after_count = _apply_relevance_threshold(result, relevance_threshold)
        console.print(
            f"Relevance filter: {before_count} -> {after_count} (threshold={relevance_threshold})"
        )
        should_persist = True

    if should_persist:
        write_search_output(Path(result.output_dir), result.meta, result.papers)
        hook_manager.trigger(
            HookEvent.POST_OUTPUT,
            HookContext(
                papers=result.papers,
                meta=result.meta,
                output_dir=Path(result.output_dir),
                event=HookEvent.POST_OUTPUT,
                console=None,
            ),
        )

    _rewrite_markdown_report(
        papers=result.papers,
        meta=result.meta,
        output_dir=Path(result.output_dir),
        ranking_view=sort,
        no_hooks=no_hooks,
        no_report=no_report,
        console=console,
    )

    table = Table(title="Search Results")
    table.add_column("#", justify="right")
    table.add_column("Title")
    table.add_column("Authors")
    table.add_column("Year", justify="right")
    table.add_column("Venue")
    table.add_column("Citations", justify="right")

    for index, paper in enumerate(result.papers, start=1):
        authors = ", ".join(paper.authors)
        table.add_row(
            str(index),
            _truncate(paper.title, 60),
            _truncate(authors, 30),
            str(paper.year or "-"),
            _truncate(paper.venue, 20),
            str(paper.citation_count or 0),
        )

    console.print(table)
    console.print(f"[bold]Output directory:[/bold] {result.output_dir}")


def _rewrite_markdown_report(
    *,
    papers: list[PaperResult],
    meta: SurveyMeta,
    output_dir: Path,
    ranking_view: str,
    no_hooks: bool,
    no_report: bool,
    console: Console,
) -> None:
    """Rewrite results.md with the requested ranking view."""
    if no_hooks or no_report:
        return
    if not isinstance(meta, SurveyMeta):
        return
    if ranking_view == "overall" and not any(
        getattr(paper, "overall_score", None) is not None for paper in papers
    ):
        console.print("Overall ranking has no Agent scores; falling back to citations.")
    if ranking_view == "relevance" and not any(
        getattr(paper, "relevance_score", None) is not None for paper in papers
    ):
        console.print("Relevance ranking requires Agent scores; no relevance view generated.")
    generate_report(
        papers,
        meta,
        output_dir / "results.md",
        ranking_view=ranking_view,  # type: ignore[arg-type]
    )


@main.command()
@click.option(
    "--seeds",
    cls=OptionEatAll,
    required=True,
    help="Seed papers for citation traversal. Accepts multiple values after one --seeds flag.",
)
@click.option(
    "--depth",
    type=click.IntRange(1, 2),
    default=1,
    show_default=True,
    help="Citation traversal depth.",
)
@click.option(
    "--direction",
    type=click.Choice(["citations", "references", "both"]),
    default="both",
    show_default=True,
    help="Which citation relationships to traverse.",
)
@click.option(
    "--min-citations",
    type=int,
    default=0,
    show_default=True,
    help="Only expand depth-2 frontier papers with at least this many citations.",
)
@click.option("--year-start", type=int, default=None, help="Start year (inclusive)")
@click.option("--year-end", type=int, default=None, help="End year (inclusive)")
@click.option("--max-papers", type=int, default=2000, help="Safety cap on final deduped papers")
@click.option("--output-dir", type=str, default=None, help="Override output directory")
@click.option(
    "--openalex-email",
    envvar="OPENALEX_EMAIL",
    default=None,
    help="Email for OpenAlex polite pool requests.",
)
@click.option(
    "--s2-api-key",
    envvar=["SEMANTIC_SCHOLAR_API_KEY", "S2_API_KEY"],
    default=None,
    help="Semantic Scholar API key.",
)
@click.option(
    "--no-hooks",
    is_flag=True,
    default=False,
    help="Disable all hooks (no BibTeX, no report, no auto-verify).",
)
@click.option(
    "--no-bib",
    is_flag=True,
    default=False,
    help="Disable automatic BibTeX generation.",
)
@click.option(
    "--no-report",
    is_flag=True,
    default=False,
    help="Disable automatic Markdown report generation.",
)
@click.option(
    "--no-auto-verify",
    is_flag=True,
    default=False,
    help="Disable automatic metadata quality check.",
)
def cite(
    seeds: tuple[str, ...] | str,
    depth: int,
    direction: str,
    min_citations: int,
    year_start: int | None,
    year_end: int | None,
    max_papers: int,
    output_dir: str | None,
    openalex_email: str | None,
    s2_api_key: str | None,
    no_hooks: bool,
    no_bib: bool,
    no_report: bool,
    no_auto_verify: bool,
) -> None:
    """Expand a candidate pool by traversing citations and references."""
    if (year_start is None) != (year_end is None):
        raise click.BadParameter(
            "--year-start and --year-end must be provided together"
        )

    normalized_seeds = _normalize_seeds(seeds)
    if not normalized_seeds:
        raise click.ClickException("At least one seed paper is required")

    output_path = _resolve_citation_output_dir(normalized_seeds, output_dir)
    hook_manager = _build_hook_manager(
        no_hooks=no_hooks,
        no_bib=no_bib,
        no_report=no_report,
        no_auto_verify=no_auto_verify,
    )
    console = Console()
    console.print("Sources: semantic_scholar, openalex")

    try:
        traversal = asyncio.run(
            _run_citation_traversal(
                seeds=normalized_seeds,
                depth=depth,
                direction=direction,
                min_citations=min_citations,
                year_range=(year_start, year_end) if year_start is not None else None,
                max_papers=max_papers,
                s2_api_key=s2_api_key,
                openalex_email=openalex_email,
            )
        )
    except SourceError as exc:
        raise click.ClickException(str(exc)) from exc

    verifier = Verifier()
    papers = verifier.verify(traversal.expanded_papers)
    verified_count = sum(1 for paper in papers if paper.verification.value == "verified")
    single_source_count = sum(
        1 for paper in papers if paper.verification.value == "single_source"
    )

    meta = SurveyMeta(
        query=f"citation graph traversal from {len(normalized_seeds)} seed(s)",
        params=SearchParams(
            query="citation graph traversal",
            year_range=(year_start, year_end) if year_start is not None else None,
            max_results=max_papers,
            sort_by="citation_count",
        ),
        mode="citation_graph",
        total_results=len(papers),
        sources_used=["semantic_scholar", "openalex"],
        output_dir=str(output_path),
        per_source_counts=traversal.source_stats,
        verified_count=verified_count,
        single_source_count=single_source_count,
        pre_filter_count=len(papers),
        seed_identifiers=normalized_seeds,
        seed_resolved_count=len(traversal.seed_papers),
        failed_seeds=traversal.failed_seeds,
        total_raw_results=traversal.total_raw,
        depth=depth,
        direction=direction,
        depth_stats={str(level): count for level, count in traversal.depth_stats.items()},
        source_contributions=traversal.source_stats,
        relationship_contributions=traversal.relationship_stats,
    )

    hook_manager.trigger(
        HookEvent.POST_VERIFY,
        HookContext(
            papers=papers,
            meta=meta,
            output_dir=output_path,
            event=HookEvent.POST_VERIFY,
            console=None,
        ),
    )
    write_search_output(output_path, meta, papers)
    _write_graph_output(output_path, traversal.seed_papers, traversal.graph_edges)
    hook_manager.trigger(
        HookEvent.POST_OUTPUT,
        HookContext(
            papers=papers,
            meta=meta,
            output_dir=output_path,
            event=HookEvent.POST_OUTPUT,
            console=None,
        ),
    )

    display_papers = sorted(
        papers,
        key=lambda paper: (
            paper.citation_count or 0,
            paper.year or 0,
        ),
        reverse=True,
    )[:20]
    table = Table(title="Citation Expansion Results (Top 20 by citations)")
    table.add_column("#", justify="right")
    table.add_column("Title")
    table.add_column("Authors")
    table.add_column("Year", justify="right")
    table.add_column("Venue")
    table.add_column("Citations", justify="right")

    for index, paper in enumerate(display_papers, start=1):
        authors = ", ".join(paper.authors)
        table.add_row(
            str(index),
            _truncate(paper.title, 60),
            _truncate(authors, 30),
            str(paper.year or "-"),
            _truncate(paper.venue, 20),
            str(paper.citation_count or 0),
        )

    console.print(
        "Seeds: "
        f"{len(traversal.seed_papers)} resolved, {len(traversal.failed_seeds)} failed | "
        f"Raw: {traversal.total_raw} -> Deduped: {traversal.total_deduped} | "
        f"citations={traversal.relationship_stats.get('citations', 0)} "
        f"references={traversal.relationship_stats.get('references', 0)}"
    )
    if traversal.failed_seeds:
        console.print(f"Failed seeds: {', '.join(traversal.failed_seeds)}")
    console.print(table)
    console.print(f"[bold]Output directory:[/bold] {output_path}")


@main.command()
@click.pass_context
@click.option(
    "--stats",
    "stats_mode",
    is_flag=True,
    default=False,
    help="Print complete lint statistics JSON to stdout.",
)
@click.option(
    "--fix",
    "fix_mode",
    is_flag=True,
    default=False,
    help="Generate auto-fixes. Defaults to dry-run preview mode.",
)
@click.option(
    "--no-dry-run",
    is_flag=True,
    default=False,
    help="Apply fixes to files instead of previewing them.",
)
@click.option(
    "--backup",
    is_flag=True,
    default=False,
    help="Create .bak backups before writing fixes.",
)
@click.option(
    "--rules",
    type=str,
    default=None,
    help="Comma-separated lint rule filter, e.g. L01,L04,L07.",
)
@click.option(
    "--bib",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Explicit .bib file path. If omitted, infer from \\bibliography{}.",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Explicit LaTeX project root directory.",
)
@click.option(
    "--venue",
    type=str,
    default=None,
    help="Venue profile name.",
)
@click.argument(
    "path",
    type=click.Path(path_type=Path),
    required=False,
)
def lint(
    ctx: click.Context,
    stats_mode: bool,
    fix_mode: bool,
    no_dry_run: bool,
    backup: bool,
    rules: str | None,
    bib: Path | None,
    project_dir: Path | None,
    venue: str | None,
    path: Path | None,
) -> None:
    """Extract and report LaTeX structure lint issues."""
    if no_dry_run and not fix_mode:
        raise click.ClickException("--no-dry-run requires --fix")
    if backup and not fix_mode:
        raise click.ClickException("--backup requires --fix")
    if backup and not no_dry_run:
        raise click.ClickException("--backup requires --fix --no-dry-run")

    config_start_dir = project_dir or (path.parent if path is not None else None)
    config = _load_command_config(start_dir=config_start_dir)
    venue_profile = _resolve_venue_profile(cli_venue=venue, config=config)
    selected_rules = _resolve_lint_rules(
        cli_rules=_parse_rules_option(rules),
        config=config,
    )
    resolved_project_dir = project_dir.resolve() if project_dir is not None else None
    if path is None:
        if config.project.main_file is None:
            raise click.ClickException("PATH is required unless config.project.main_file is set")
        config_base_dir = config.config_path.parent if config.config_path is not None else Path.cwd()
        base_dir = (
            (config_base_dir / config.project.src_dir).resolve()
            if config.project.src_dir
            else config_base_dir.resolve()
        )
        path = (base_dir / config.project.main_file).resolve()
    project = _resolve_project_arg(path, project_dir=resolved_project_dir, config=config)
    default_bib = config.project.bib_files[0] if config.project.bib_files else None
    resolved_bib = _resolve_optional_file(
        bib if _cli_value_provided(ctx, "bib") else (Path(default_bib) if default_bib else None),
        project_dir=project.project_dir,
        must_exist=True,
    )
    stats = extract_stats(
        project.root_file,
        bib_path=resolved_bib,
        project=project,
        venue=venue_profile,
        strict_doi=config.verify.strict_doi,
    )
    display_stats = _apply_severity_overrides(stats, config)
    show_file = stats.project is not None

    if fix_mode:
        fixes = generate_fixes(
            stats,
            project=project,
            rules=_resolve_fix_rules(
                cli_rules=_parse_rules_option(rules),
                config=config,
            ),
        )
        report = apply_fixes(
            fixes,
            project=project,
            dry_run=not no_dry_run,
            backup=backup and no_dry_run is False,
        )
        if stats_mode:
            click.echo(report.to_json(), nl=False)
        else:
            for line in _render_fix_report(report, show_file=show_file):
                click.echo(line)
        raise click.exceptions.Exit(1 if report.errors else 0)

    if stats_mode:
        click.echo(display_stats.to_json(selected_rules), nl=False)
        raise click.exceptions.Exit(_lint_exit_code(stats, selected_rules))

    issues = display_stats.filtered_issues(selected_rules)
    if issues:
        for issue in issues:
            click.echo(_format_lint_issue(issue, show_file=show_file))
    else:
        click.echo("No issues found.")

    summary = display_stats.summary(selected_rules)
    click.echo(
        f"Summary: {summary['errors']} errors, {summary['warnings']} warnings, {summary['info']} info"
    )
    raise click.exceptions.Exit(_lint_exit_code(stats, selected_rules))


@main.command()
@click.pass_context
@click.option(
    "--no-dry-run",
    is_flag=True,
    default=False,
    help="Apply fixes to files instead of previewing them.",
)
@click.option(
    "--backup",
    is_flag=True,
    default=False,
    help="Create .bak backups before writing fixes.",
)
@click.option(
    "--lint-only",
    is_flag=True,
    default=False,
    help="Only run lint/fix stages and skip verification.",
)
@click.option(
    "--no-fix",
    is_flag=True,
    default=False,
    help="Skip auto-fix and only report lint results.",
)
@click.option(
    "--no-verify",
    is_flag=True,
    default=False,
    help="Skip citation verification stage.",
)
@click.option(
    "--rules",
    type=str,
    default=None,
    help="Comma-separated fix rule filter, e.g. L01,L04.",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Explicit LaTeX project root directory.",
)
@click.option(
    "--venue",
    type=str,
    default=None,
    help="Venue profile name.",
)
@click.option(
    "--bib",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Explicit .bib file path override.",
)
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    default=False,
    help="Print JSON only.",
)
@click.option(
    "--no-save",
    is_flag=True,
    default=False,
    help="Do not save a JSON report file.",
)
@click.argument(
    "path",
    type=click.Path(path_type=Path),
)
def check(
    ctx: click.Context,
    no_dry_run: bool,
    backup: bool,
    lint_only: bool,
    no_fix: bool,
    no_verify: bool,
    rules: str | None,
    project_dir: Path | None,
    venue: str | None,
    bib: Path | None,
    json_mode: bool,
    no_save: bool,
    path: Path,
) -> None:
    """Run the full writing-quality check pipeline."""
    if backup and not no_dry_run:
        raise click.ClickException("--backup requires --no-dry-run")

    config_start_dir = project_dir or path.parent
    config = _load_command_config(start_dir=config_start_dir)
    venue_profile = _resolve_venue_profile(cli_venue=venue, config=config)
    resolved_project_dir = project_dir.resolve() if project_dir is not None else None
    resolved_path = _resolve_optional_file(path, project_dir=resolved_project_dir, must_exist=True)
    assert resolved_path is not None
    selected_fix_rules = _parse_rules_option(rules)

    if bib is not None and config.project.bib_files != [bib.as_posix()]:
        config.project.bib_files = [bib.as_posix()]

    try:
        report = run_check(
            resolved_path,
            config=config,
            fix=not no_fix,
            dry_run=not no_dry_run,
            backup=backup,
            lint_only=lint_only,
            no_fix=no_fix,
            verify=not no_verify,
            rules=sorted(selected_fix_rules) if selected_fix_rules is not None else None,
            save_report=not no_save,
            venue=venue_profile,
        )
    except Exception as exc:
        click.echo(str(exc), err=True)
        raise click.exceptions.Exit(2)

    if json_mode:
        click.echo(report.to_json(), nl=False)
    else:
        click.echo(render_check_report(report))
    raise click.exceptions.Exit(check_exit_code(report))


@main.command()
@click.pass_context
@click.option(
    "--stats",
    "stats_mode",
    is_flag=True,
    default=False,
    help="Print complete verification JSON to stdout.",
)
@click.option(
    "--tex",
    type=click.Path(path_type=Path),
    default=None,
    help="Optional .tex file or directory. Only verify cited keys from this path.",
)
@click.option(
    "--project-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Explicit LaTeX project root directory. Auto-discovers main .tex and .bib files.",
)
@click.option(
    "--venue",
    type=str,
    default=None,
    help="Venue profile name.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Optional output file path.",
)
@click.option(
    "--keys",
    type=str,
    default=None,
    help="Comma-separated cite keys to verify, e.g. cinnamon2025,f1wrong.",
)
@click.argument(
    "bib",
    type=click.Path(dir_okay=False, path_type=Path),
    required=False,
)
def verify(
    ctx: click.Context,
    stats_mode: bool,
    tex: Path | None,
    project_dir: Path | None,
    venue: str | None,
    output: Path | None,
    keys: str | None,
    bib: Path | None,
) -> None:
    """Verify citation metadata in a BibTeX file."""
    config_start_dir = project_dir or tex or bib
    config = _load_command_config(start_dir=config_start_dir)
    venue_profile = _resolve_venue_profile(cli_venue=venue, config=config)
    selected_keys = _parse_keys_option(keys)
    resolved_project_dir = project_dir.resolve() if project_dir is not None else None
    default_tex = None
    if tex is None and config.project.main_file and config.config_path is not None:
        config_base_dir = config.config_path.parent
        base_dir = (config_base_dir / config.project.src_dir).resolve() if config.project.src_dir else config_base_dir
        default_tex = base_dir / config.project.main_file
    resolved_tex = _resolve_optional_file(tex or default_tex, project_dir=resolved_project_dir, must_exist=True)
    project = None
    if resolved_tex is not None:
        project = _resolve_project_arg(resolved_tex, config=config)
    elif resolved_project_dir is not None:
        project = _resolve_project_root_only(resolved_project_dir, config=config)

    config_base_dir = config.config_path.parent.resolve() if config.config_path is not None else None
    bib_base_dir = project.project_dir if project is not None else (resolved_project_dir or config_base_dir)
    default_bib = Path(config.project.bib_files[0]) if config.project.bib_files else None
    resolved_bib = _resolve_optional_file(
        bib if _cli_value_provided(ctx, "bib") else default_bib,
        project_dir=bib_base_dir,
        must_exist=True,
    )
    discovered_bib_paths = [] if resolved_bib is not None else (
        list(project.bib_files)
        if project is not None
        else [
            _resolve_existing_path(Path(bib_file), project_dir=bib_base_dir)
            for bib_file in config.project.bib_files
        ]
    )
    if resolved_bib is None and not discovered_bib_paths:
        raise click.ClickException("Provide a .bib path or a LaTeX project with discoverable bibliography files.")

    total_to_verify = _estimate_verify_total(
        resolved_bib,
        discovered_bib_paths if resolved_bib is None else None,
        resolved_tex,
        project,
        selected_keys,
        config.verify.skip_keys,
    )
    progress_state = {"count": 0}

    def progress_callback(result: object) -> None:
        progress_state["count"] += 1
        source = getattr(result, "remote_source", None) or "—"
        status = getattr(result, "status")
        if status == "verified":
            suffix = f"verified ({source})"
            icon = "✅"
        elif status == "mismatch":
            mismatches = getattr(result, "mismatches", [])
            suffix = f"mismatch ({mismatches[0]})" if mismatches else "mismatch"
            icon = "⚠️"
        elif status == "not_found":
            suffix = "not found"
            icon = "❌"
        elif status == "uncertain":
            suffix = getattr(result, "notes", None) or "uncertain"
            icon = "❓"
        elif status == "rate_limited":
            suffix = getattr(result, "notes", None) or "rate limited"
            icon = "⏳"
        else:
            suffix = getattr(result, "notes", None) or "error"
            icon = "💥"
        click.echo(
            f"  [{progress_state['count']}/{total_to_verify}] {getattr(result, 'bib_key')} {icon} {suffix}",
            err=True,
        )

    click.echo(f"Verifying {total_to_verify} entries...", err=True)
    tex_argument = None
    if tex is not None:
        tex_argument = tex.as_posix() if resolved_project_dir is None else resolved_tex.as_posix()
    report = asyncio.run(
        verify_bib(
            resolved_bib.as_posix() if resolved_bib is not None else None,
            bib_paths=[path.as_posix() for path in discovered_bib_paths] if resolved_bib is None else None,
            tex_path=tex_argument,
            project=project,
            keys=selected_keys,
            s2_api_key=config.verify.s2_api_key,
            timeout=config.verify.timeout,
            skip_keys=config.verify.skip_keys,
            max_concurrent=config.verify.max_concurrent,
            max_requests_per_second=config.verify.max_requests_per_second,
            venue=venue_profile,
            strict_doi=config.verify.strict_doi,
            progress_callback=progress_callback,
        )
    )

    rendered = report.to_json() if stats_mode else report.to_markdown()
    if output is not None:
        output.write_text(rendered, encoding="utf-8")
    else:
        click.echo(rendered, nl=False)
    raise click.exceptions.Exit(_verify_exit_code(report))


if __name__ == "__main__":
    main()
