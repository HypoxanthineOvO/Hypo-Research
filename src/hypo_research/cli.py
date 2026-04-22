"""CLI entrypoints for Hypo-Research."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from hypo_research.core.models import ExpansionTrace, SearchParams, SearchResult
from hypo_research.core.sources import SemanticScholarSource, SourceError
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


async def _run_single_search(
    params: SearchParams,
    output_dir: str | None,
    s2_api_key: str | None,
) -> SearchResult:
    searcher = TargetedSearch(sources=[SemanticScholarSource(api_key=s2_api_key)])
    try:
        return await searcher.search(params=params, output_dir=output_dir)
    finally:
        await searcher.close()


async def _run_multi_query_search(
    queries: list[str],
    base_params: SearchParams,
    output_dir: str | None,
    s2_api_key: str | None,
    expansion_trace: ExpansionTrace | None,
) -> SearchResult:
    searcher = TargetedSearch(sources=[SemanticScholarSource(api_key=s2_api_key)])
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
    "--s2-api-key",
    envvar="S2_API_KEY",
    default=None,
    help="Semantic Scholar API key",
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
    s2_api_key: str | None,
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

    if not queries:
        raise click.ClickException("At least one non-empty query is required")

    base_query = expansion_trace.original_query if expansion_trace else queries[0]
    params = SearchParams(
        query=base_query,
        year_range=(year_start, year_end) if year_start is not None else None,
        fields_of_study=list(fields) or None,
        max_results=max_results,
        sort_by=sort,
    )

    try:
        if len(queries) == 1:
            single_params = params.model_copy(update={"query": queries[0]})
            result = asyncio.run(
                _run_single_search(single_params, output_dir, s2_api_key)
            )
        else:
            result = asyncio.run(
                _run_multi_query_search(
                    queries=queries,
                    base_params=params,
                    output_dir=output_dir,
                    s2_api_key=s2_api_key,
                    expansion_trace=expansion_trace,
                )
            )
    except SourceError as exc:
        raise click.ClickException(str(exc)) from exc

    should_persist = False
    if len(queries) == 1 and expansion_trace is not None:
        result.meta.expansion = expansion_trace
        should_persist = True

    console = Console()
    if relevance_threshold is not None:
        before_count, after_count = _apply_relevance_threshold(result, relevance_threshold)
        console.print(
            f"Relevance filter: {before_count} -> {after_count} (threshold={relevance_threshold})"
        )
        should_persist = True

    if should_persist:
        write_search_output(Path(result.output_dir), result.meta, result.papers)

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
