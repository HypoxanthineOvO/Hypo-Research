"""CLI entrypoints for Hypo-Research."""

from __future__ import annotations

import asyncio
import ast
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from hypo_research.cite import CitationTraverser
from hypo_research.core.models import (
    ExpansionTrace,
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
from hypo_research.output.json_output import write_search_output
from hypo_research.survey.targeted import TargetedSearch, slugify_query
from hypo_research.writing.bib_parser import parse_bib
from hypo_research.writing.stats import TexStats, extract_stats
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


def _format_lint_issue(issue: object) -> str:
    """Render a human-readable lint issue line."""
    rule = getattr(issue, "rule")
    severity = str(getattr(issue, "severity")).upper()
    file = getattr(issue, "file")
    line = getattr(issue, "line")
    message = getattr(issue, "message")
    return f"[{rule}] {severity} {file}:{line}  {message}"


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
    return 1 if report.not_found > 0 or report.error > 0 else 0


def _estimate_verify_total(
    bib_path: Path,
    tex_path: Path | None,
    keys: list[str] | None,
) -> int:
    """Estimate how many entries will be verified for progress reporting."""
    entries = parse_bib(bib_path.as_posix())
    selected_keys = {key for key in keys or []} if keys else None
    if tex_path is not None:
        cited_keys = {citation.key for citation in extract_stats(tex_path.as_posix()).citations}
        selected_keys = cited_keys if selected_keys is None else selected_keys & cited_keys

    filtered = entries
    if selected_keys is not None:
        filtered = [entry for entry in filtered if entry.key in selected_keys]
    filtered = [entry for entry in filtered if entry.fields.get("title") or entry.fields.get("doi")]
    return len(filtered)


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
@click.argument("query", required=False)
@click.option("--year-start", type=int, default=None, help="Start year (inclusive)")
@click.option("--year-end", type=int, default=None, help="End year (inclusive)")
@click.option("--max-results", type=int, default=100, help="Maximum number of results")
@click.option("--fields", multiple=True, help="Fields of study filter")
@click.option(
    "--sort",
    type=click.Choice(["relevance", "citation_count", "year"]),
    default="relevance",
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
    default=["all"],
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
    if (year_start is None) != (year_end is None):
        raise click.BadParameter(
            "--year-start and --year-end must be provided together"
        )

    expansion_trace: ExpansionTrace | None = None
    if queries_file is not None:
        queries, expansion_trace = _load_queries_payload(queries_file)
    else:
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

    sources = _build_sources(source, s2_api_key, openalex_email)
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
        max_results=max_results,
        sort_by=sort,
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
@click.option(
    "--stats",
    "stats_mode",
    is_flag=True,
    default=False,
    help="Print complete lint statistics JSON to stdout.",
)
@click.option(
    "--rules",
    type=str,
    default=None,
    help="Comma-separated lint rule filter, e.g. L01,L04,L07.",
)
@click.option(
    "--bib",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Explicit .bib file path. If omitted, infer from \\bibliography{}.",
)
@click.argument(
    "path",
    type=click.Path(exists=True, path_type=Path),
)
def lint(
    stats_mode: bool,
    rules: str | None,
    bib: Path | None,
    path: Path,
) -> None:
    """Extract and report LaTeX structure lint issues."""
    selected_rules = _parse_rules_option(rules)
    stats = extract_stats(
        path.as_posix(),
        bib_paths=[bib.as_posix()] if bib is not None else None,
    )

    if stats_mode:
        click.echo(stats.to_json(selected_rules), nl=False)
        raise click.exceptions.Exit(_lint_exit_code(stats, selected_rules))

    issues = stats.filtered_issues(selected_rules)
    if issues:
        for issue in issues:
            click.echo(_format_lint_issue(issue))
    else:
        click.echo("No issues found.")

    summary = stats.summary(selected_rules)
    click.echo(
        f"Summary: {summary['errors']} errors, {summary['warnings']} warnings, {summary['info']} info"
    )
    raise click.exceptions.Exit(_lint_exit_code(stats, selected_rules))


@main.command()
@click.option(
    "--stats",
    "stats_mode",
    is_flag=True,
    default=False,
    help="Print complete verification JSON to stdout.",
)
@click.option(
    "--tex",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Optional .tex file or directory. Only verify cited keys from this path.",
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
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def verify(
    stats_mode: bool,
    tex: Path | None,
    output: Path | None,
    keys: str | None,
    bib: Path,
) -> None:
    """Verify citation metadata in a BibTeX file."""
    selected_keys = _parse_keys_option(keys)
    total_to_verify = _estimate_verify_total(bib, tex, selected_keys)
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
        else:
            suffix = getattr(result, "notes", None) or "error"
            icon = "💥"
        click.echo(
            f"  [{progress_state['count']}/{total_to_verify}] {getattr(result, 'bib_key')} {icon} {suffix}",
            err=True,
        )

    click.echo(f"Verifying {total_to_verify} entries...", err=True)
    report = asyncio.run(
        verify_bib(
            bib.as_posix(),
            tex_path=tex.as_posix() if tex is not None else None,
            keys=selected_keys,
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
