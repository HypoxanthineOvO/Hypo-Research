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

from hypo_research.core.models import (
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
    ) -> SearchResult:
        """Execute targeted literature search and persist results."""
        start_time = time.perf_counter()
        output_path = self._resolve_output_dir(params.query, output_dir)
        constraints = self._format_constraints(params)
        self.console.print(
            f"[bold cyan]Starting targeted search[/bold cyan] "
            f"query='{params.query}' constraints={constraints}"
        )

        tasks = [self._search_source(source, params) for source in self.sources]
        source_results = await asyncio.gather(*tasks)
        papers = self._deduplicate(
            paper for papers_from_source in source_results for paper in papers_from_source
        )

        meta = SurveyMeta(
            query=params.query,
            params=params,
            total_results=len(papers),
            sources_used=[source.name for source in self.sources],
            output_dir=str(output_path),
        )
        write_search_output(output_path, meta, papers)

        elapsed = time.perf_counter() - start_time
        self.console.print(
            f"[bold green]Search complete[/bold green] total_results={len(papers)} "
            f"elapsed={elapsed:.2f}s output={output_path}"
        )

        return SearchResult(meta=meta, papers=papers, output_dir=str(output_path))

    async def close(self) -> None:
        """Close all sources."""
        await asyncio.gather(*(source.close() for source in self.sources))

    async def _search_source(
        self, source: BaseSource, params: SearchParams
    ) -> list[PaperResult]:
        if hasattr(source, "set_progress_callback"):
            source.set_progress_callback(
                lambda retrieved, total, source_name=source.name: self.console.print(
                    f"[cyan]{source_name}[/cyan] retrieved {retrieved} / {total or '?'}"
                )
            )

        try:
            return await source.search(params)
        finally:
            if hasattr(source, "set_progress_callback"):
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

    def _deduplicate(self, papers: Iterable[PaperResult]) -> list[PaperResult]:
        ordered: OrderedDict[str, PaperResult] = OrderedDict()
        for paper in papers:
            key = self._paper_key(paper)
            existing = ordered.get(key)
            if existing is None:
                ordered[key] = paper
                continue

            merged_sources = list(dict.fromkeys(existing.sources + paper.sources))
            existing.sources = merged_sources
            if len(merged_sources) >= 2:
                existing.verification = VerificationLevel.VERIFIED
            if not existing.doi and paper.doi:
                existing.doi = paper.doi
            if not existing.arxiv_id and paper.arxiv_id:
                existing.arxiv_id = paper.arxiv_id
            if not existing.abstract and paper.abstract:
                existing.abstract = paper.abstract

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
