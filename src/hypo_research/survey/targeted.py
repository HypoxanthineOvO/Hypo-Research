"""Targeted literature search flow."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import OrderedDict
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from hypo_research.core.models import (
    ExpansionTrace,
    PaperResult,
    SearchParams,
    SearchResult,
    SurveyMeta,
    VerificationLevel,
)
from hypo_research.core.sources import BaseSource, SemanticScholarSource
from hypo_research.output.json_output import write_search_output

logger = logging.getLogger(__name__)


def slugify_query(query: str) -> str:
    """Create a filesystem-friendly slug from the first 5 query words."""
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    slug = "-".join(tokens[:5])
    return slug or "search"


class TargetedSearch:
    """Targeted literature search: find papers matching specific criteria."""

    def __init__(self, sources: list[BaseSource] | None = None):
        self.sources = sources or [SemanticScholarSource()]
        self.console = Console()

    async def search(
        self,
        params: SearchParams,
        output_dir: str | None = None,
        progress: Progress | None = None,
    ) -> SearchResult:
        """Execute targeted literature search with a single query."""
        start_time = time.perf_counter()
        output_path = self._resolve_output_dir(params.query, output_dir)
        constraints = self._format_constraints(params)
        self.console.print(
            f"[bold cyan]Starting targeted search[/bold cyan] "
            f"query='{params.query}' constraints={constraints}"
        )

        papers = await self._collect_papers(
            params=params,
            enable_source_progress=progress is None,
        )
        deduplicated = self._dedup_results(papers)

        meta = SurveyMeta(
            query=params.query,
            params=params,
            total_results=len(deduplicated),
            sources_used=[source.name for source in self.sources],
            output_dir=str(output_path),
        )
        write_search_output(output_path, meta, deduplicated)

        elapsed = time.perf_counter() - start_time
        self.console.print(
            f"[bold green]Search complete[/bold green] total_results={len(deduplicated)} "
            f"elapsed={elapsed:.2f}s output={output_path}"
        )

        return SearchResult(
            meta=meta,
            papers=deduplicated,
            output_dir=str(output_path),
        )

    async def multi_query_search(
        self,
        queries: list[str],
        base_params: SearchParams,
        expansion_trace: ExpansionTrace | None = None,
        output_dir: str | None = None,
        progress: Progress | None = None,
    ) -> SearchResult:
        """Execute sequential search across multiple query variants."""
        normalized_queries = self._normalize_queries(queries)
        if not normalized_queries:
            raise ValueError("queries must contain at least one non-empty query")

        start_time = time.perf_counter()
        output_path = self._resolve_output_dir(base_params.query, output_dir)
        self._print_multi_query_header(normalized_queries)

        task_id = None
        if progress is not None:
            task_id = progress.add_task("searching queries", total=len(normalized_queries))

        raw_results: list[PaperResult] = []
        total_queries = len(normalized_queries)
        for index, query in enumerate(normalized_queries, start=1):
            self.console.print(
                f"[{index}/{total_queries}] Searching: {query}",
                markup=False,
            )
            params = base_params.model_copy(update={"query": query})
            query_results = await self._collect_papers(
                params=params,
                enable_source_progress=False,
            )
            for paper in query_results:
                paper.matched_queries = [query]
            raw_results.extend(query_results)

            self.console.print(
                f"[{index}/{total_queries}] Retrieved {len(query_results)} papers for '{query}'",
                markup=False,
            )
            if progress is not None and task_id is not None:
                progress.advance(task_id)

        deduplicated = self._dedup_results(raw_results)
        meta = SurveyMeta(
            query=base_params.query,
            params=base_params,
            total_results=len(deduplicated),
            sources_used=[source.name for source in self.sources],
            output_dir=str(output_path),
            expansion=expansion_trace,
            pre_filter_count=len(deduplicated),
        )
        write_search_output(output_path, meta, deduplicated)

        elapsed = time.perf_counter() - start_time
        self.console.print(
            "[bold green]Search complete:[/bold green] "
            f"{len(normalized_queries)} queries -> {len(raw_results)} raw -> "
            f"{len(deduplicated)} after dedup"
        )
        self.console.print(
            f"[green]Elapsed:[/green] {elapsed:.2f}s [green]Output:[/green] {output_path}"
        )

        return SearchResult(
            meta=meta,
            papers=deduplicated,
            output_dir=str(output_path),
        )

    async def close(self) -> None:
        """Close all sources."""
        await asyncio.gather(*(source.close() for source in self.sources))

    async def _collect_papers(
        self,
        params: SearchParams,
        enable_source_progress: bool,
    ) -> list[PaperResult]:
        source_results = await asyncio.gather(
            *[
                self._search_source(
                    source,
                    params,
                    enable_source_progress=enable_source_progress,
                )
                for source in self.sources
            ]
        )
        return [
            paper
            for papers_from_source in source_results
            for paper in papers_from_source
        ]

    async def _search_source(
        self,
        source: BaseSource,
        params: SearchParams,
        enable_source_progress: bool,
    ) -> list[PaperResult]:
        if enable_source_progress and hasattr(source, "set_progress_callback"):
            source.set_progress_callback(
                lambda retrieved, total, source_name=source.name: self.console.print(
                    f"[cyan]{source_name}[/cyan] retrieved {retrieved} / {total or '?'}"
                )
            )

        try:
            return await source.search(params)
        finally:
            if enable_source_progress and hasattr(source, "set_progress_callback"):
                source.set_progress_callback(None)

    def _resolve_output_dir(self, query: str, output_dir: str | None) -> Path:
        if output_dir:
            path = Path(output_dir)
        else:
            surveys_root = Path("data") / "surveys"
            surveys_root.mkdir(parents=True, exist_ok=True)
            date_prefix = datetime.now()
            path = surveys_root / f"{date_prefix:%Y-%m-%d}_{slugify_query(query)}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _format_constraints(params: SearchParams) -> dict[str, object]:
        return {
            "year_range": params.year_range,
            "venue_filter": params.venue_filter,
            "fields_of_study": params.fields_of_study,
            "max_results": params.max_results,
            "sort_by": params.sort_by,
        }

    @staticmethod
    def _normalize_queries(queries: list[str]) -> list[str]:
        normalized: list[str] = []
        for query in queries:
            cleaned = query.strip()
            if cleaned:
                normalized.append(cleaned)
        return normalized

    def _print_multi_query_header(self, queries: list[str]) -> None:
        self.console.print(
            f"[bold magenta]Multi-query search ({len(queries)} queries):[/bold magenta]"
        )
        total = len(queries)
        for index, query in enumerate(queries, start=1):
            self.console.print(f"  [{index}/{total}] {query}", markup=False)

    def _dedup_results(self, papers: Iterable[PaperResult]) -> list[PaperResult]:
        ordered: OrderedDict[str, PaperResult] = OrderedDict()
        for paper in papers:
            key = self._paper_key(paper)
            existing = ordered.get(key)
            if existing is None:
                ordered[key] = paper
                continue

            existing.sources = list(dict.fromkeys(existing.sources + paper.sources))
            if len(existing.sources) >= 2:
                existing.verification = VerificationLevel.VERIFIED
            if not existing.doi and paper.doi:
                existing.doi = paper.doi
            if not existing.arxiv_id and paper.arxiv_id:
                existing.arxiv_id = paper.arxiv_id
            if not existing.abstract and paper.abstract:
                existing.abstract = paper.abstract
            if existing.relevance_score is None and paper.relevance_score is not None:
                existing.relevance_score = paper.relevance_score
            if not existing.relevance_reason and paper.relevance_reason:
                existing.relevance_reason = paper.relevance_reason

            merged_queries = list(
                dict.fromkeys((existing.matched_queries or []) + (paper.matched_queries or []))
            )
            if merged_queries:
                existing.matched_queries = merged_queries

        return list(ordered.values())

    @staticmethod
    def _paper_key(paper: PaperResult) -> str:
        if paper.doi:
            return f"doi:{paper.doi.lower()}"
        if paper.arxiv_id:
            return f"arxiv:{paper.arxiv_id.lower()}"
        if paper.s2_paper_id:
            return f"s2:{paper.s2_paper_id.lower()}"
        normalized_title = re.sub(r"\s+", " ", paper.title.strip().lower())
        return f"title:{normalized_title}:{paper.year or 'na'}"
