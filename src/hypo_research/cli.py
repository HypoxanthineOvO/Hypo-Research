"""CLI entrypoints for Hypo-Research."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from hypo_research.core.models import ExpansionTrace, QueryVariant, SearchParams, SearchResult
from hypo_research.core.sources import (
    ArxivSource,
    BaseSource,
    OpenAlexSource,
    SemanticScholarSource,
    SourceError,
)
from hypo_research.hooks import AutoBibHook, AutoReportHook, AutoVerifyHook, HookContext, HookEvent, HookManager
from hypo_research.output.json_output import write_search_output
from hypo_research.survey.targeted import TargetedSearch


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
    envvar="S2_API_KEY",
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


if __name__ == "__main__":
    main()
