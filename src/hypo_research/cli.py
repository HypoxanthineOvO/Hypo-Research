"""CLI entrypoints for Hypo-Research."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

from hypo_research.core.models import SearchParams, SearchResult
from hypo_research.core.sources import SemanticScholarSource, SourceError
from hypo_research.survey.targeted import TargetedSearch


def _truncate(value: str | None, limit: int) -> str:
    if not value:
        return "-"
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


async def _run_search(
    params: SearchParams,
    output_dir: str | None,
    s2_api_key: str | None,
) -> SearchResult:
    searcher = TargetedSearch(sources=[SemanticScholarSource(api_key=s2_api_key)])
    try:
        return await searcher.search(params=params, output_dir=output_dir)
    finally:
        await searcher.close()


@click.group()
def main() -> None:
    """Hypo-Research: Academic research assistant."""


@main.command()
@click.argument("query")
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
    "--s2-api-key",
    envvar="S2_API_KEY",
    default=None,
    help="Semantic Scholar API key",
)
def search(
    query: str,
    year_start: int | None,
    year_end: int | None,
    max_results: int,
    fields: tuple[str, ...],
    sort: str,
    output_dir: str | None,
    s2_api_key: str | None,
) -> None:
    """Run a targeted literature search."""
    if (year_start is None) != (year_end is None):
        raise click.BadParameter(
            "--year-start and --year-end must be provided together"
        )

    params = SearchParams(
        query=query,
        year_range=(year_start, year_end) if year_start is not None else None,
        fields_of_study=list(fields) or None,
        max_results=max_results,
        sort_by=sort,
    )

    try:
        result = asyncio.run(_run_search(params, output_dir, s2_api_key))
    except SourceError as exc:
        raise click.ClickException(str(exc)) from exc

    console = Console()
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
