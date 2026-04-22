"""Targeted literature search flow."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from hypo_research.core.dedup import Deduplicator
from hypo_research.core.models import ExpansionTrace, PaperResult, SearchParams, SearchResult, SurveyMeta
from hypo_research.core.sources import BaseSource, SemanticScholarSource
from hypo_research.core.verifier import Verifier
from hypo_research.hooks import HookContext, HookEvent, HookManager
from hypo_research.output.json_output import write_search_output

logger = logging.getLogger(__name__)


def slugify_query(query: str) -> str:
    """Create a filesystem-friendly slug from the first 5 query words."""
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    slug = "-".join(tokens[:5])
    return slug or "search"


class TargetedSearch:
    """Targeted literature search: find papers matching specific criteria."""

    def __init__(
        self,
        sources: list[BaseSource] | None = None,
        hook_manager: HookManager | None = None,
    ):
        self.sources = sources or [SemanticScholarSource()]
        self.console = Console()
        self.deduplicator = Deduplicator()
        self.verifier = Verifier()
        if hook_manager is None:
            hook_manager = HookManager()
            hook_manager.register_defaults()
        self.hook_manager = hook_manager

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

        if len(self.sources) > 1:
            self.console.print(
                f"Searching: {params.query} ({len(self.sources)} sources)",
                markup=False,
            )

        hook_messages: list[str] = []
        raw_papers, per_source_counts = await self._collect_papers(
            params=params,
            enable_source_progress=progress is None and len(self.sources) == 1,
            print_source_counts=len(self.sources) > 1,
        )
        meta = SurveyMeta(
            query=params.query,
            params=params,
            sources_used=[source.name for source in self.sources],
            per_source_counts=per_source_counts,
            output_dir=str(output_path),
        )
        hook_messages.extend(
            self._trigger_hooks(HookEvent.POST_SEARCH, raw_papers, meta, output_path)
        )

        deduplicated = self.deduplicator.dedup(raw_papers)
        meta.pre_filter_count = len(deduplicated)
        hook_messages.extend(
            self._trigger_hooks(HookEvent.POST_DEDUP, deduplicated, meta, output_path)
        )

        deduplicated = self.verifier.verify(deduplicated)
        verified_count, single_source_count = self._verification_counts(deduplicated)
        meta.total_results = len(deduplicated)
        meta.verified_count = verified_count
        meta.single_source_count = single_source_count
        hook_messages.extend(
            self._trigger_hooks(HookEvent.POST_VERIFY, deduplicated, meta, output_path)
        )

        write_search_output(output_path, meta, deduplicated)
        hook_messages.extend(
            self._trigger_hooks(HookEvent.POST_OUTPUT, deduplicated, meta, output_path)
        )

        elapsed = time.perf_counter() - start_time
        if len(self.sources) == 1:
            self.console.print(
                f"[bold green]Search complete[/bold green] total_results={len(deduplicated)} "
                f"elapsed={elapsed:.2f}s output={output_path}"
            )
        else:
            self.console.print(
                "[bold green]Search complete:[/bold green] "
                f"1 query x {len(self.sources)} sources -> {len(raw_papers)} raw -> "
                f"{len(deduplicated)} after dedup"
            )
            self.console.print(
                "Verification: "
                f"{verified_count} verified (2+ sources), "
                f"{single_source_count} single-source"
            )
            self.console.print(
                f"[green]Elapsed:[/green] {elapsed:.2f}s [green]Output:[/green] {output_path}"
            )

        self._print_hook_summary(hook_messages)
        return SearchResult(meta=meta, papers=deduplicated, output_dir=str(output_path))

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

        hook_messages: list[str] = []
        raw_results: list[PaperResult] = []
        aggregate_counts: dict[str, int] = {source.name: 0 for source in self.sources}
        meta = SurveyMeta(
            query=base_params.query,
            params=base_params,
            sources_used=[source.name for source in self.sources],
            per_source_counts=aggregate_counts,
            output_dir=str(output_path),
            expansion=expansion_trace,
        )
        total_queries = len(normalized_queries)
        for index, query in enumerate(normalized_queries, start=1):
            self.console.print(
                f"[{index}/{total_queries}] Searching: {query} ({len(self.sources)} sources)",
                markup=False,
            )
            params = base_params.model_copy(update={"query": query})
            query_results, source_counts = await self._collect_papers(
                params=params,
                enable_source_progress=False,
                print_source_counts=True,
            )
            for source_name, count in source_counts.items():
                aggregate_counts[source_name] = aggregate_counts.get(source_name, 0) + count

            for paper in query_results:
                paper.matched_queries = [query]
            raw_results.extend(query_results)
            hook_messages.extend(
                self._trigger_hooks(HookEvent.POST_SEARCH, query_results, meta, output_path)
            )

            if progress is not None and task_id is not None:
                progress.advance(task_id)

        meta.per_source_counts = aggregate_counts
        deduplicated = self.deduplicator.dedup(raw_results)
        meta.pre_filter_count = len(deduplicated)
        hook_messages.extend(
            self._trigger_hooks(HookEvent.POST_DEDUP, deduplicated, meta, output_path)
        )

        deduplicated = self.verifier.verify(deduplicated)
        verified_count, single_source_count = self._verification_counts(deduplicated)
        meta.total_results = len(deduplicated)
        meta.verified_count = verified_count
        meta.single_source_count = single_source_count
        hook_messages.extend(
            self._trigger_hooks(HookEvent.POST_VERIFY, deduplicated, meta, output_path)
        )
        write_search_output(output_path, meta, deduplicated)
        hook_messages.extend(
            self._trigger_hooks(HookEvent.POST_OUTPUT, deduplicated, meta, output_path)
        )

        elapsed = time.perf_counter() - start_time
        self.console.print(
            "[bold green]Search complete:[/bold green] "
            f"{len(normalized_queries)} queries x {len(self.sources)} sources -> "
            f"{len(raw_results)} raw -> {len(deduplicated)} after dedup "
            f"({verified_count} verified, {single_source_count} single-source)"
        )
        self.console.print(
            "Verification: "
            f"{verified_count} verified (2+ sources), "
            f"{single_source_count} single-source"
        )
        self.console.print(
            f"[green]Elapsed:[/green] {elapsed:.2f}s [green]Output:[/green] {output_path}"
        )

        self._print_hook_summary(hook_messages)
        return SearchResult(meta=meta, papers=deduplicated, output_dir=str(output_path))

    async def close(self) -> None:
        """Close all sources."""
        await asyncio.gather(*(source.close() for source in self.sources))

    async def _collect_papers(
        self,
        params: SearchParams,
        enable_source_progress: bool,
        print_source_counts: bool,
    ) -> tuple[list[PaperResult], dict[str, int]]:
        results = await asyncio.gather(
            *[
                self._search_source(
                    source=source,
                    params=params,
                    enable_source_progress=enable_source_progress,
                )
                for source in self.sources
            ],
            return_exceptions=True,
        )

        collected: list[PaperResult] = []
        per_source_counts: dict[str, int] = {}
        for source, result in zip(self.sources, results, strict=False):
            if isinstance(result, Exception):
                logger.warning("[%s] search failed: %s", source.name, result)
                per_source_counts[source.name] = 0
                if print_source_counts:
                    self.console.print(f"  {source.name}: failed")
                continue

            per_source_counts[source.name] = len(result)
            collected.extend(result)
            if print_source_counts:
                self.console.print(f"  {source.name}: {len(result)} papers")

        return collected, per_source_counts

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

    def _trigger_hooks(
        self,
        event: HookEvent,
        papers: list[PaperResult],
        meta: SurveyMeta,
        output_path: Path,
    ) -> list[str]:
        if self.hook_manager is None:
            return []
        ctx = HookContext(
            papers=papers,
            meta=meta,
            output_dir=output_path,
            event=event,
            console=self.console,
        )
        self.hook_manager.trigger(event, ctx)
        return ctx.messages

    def _print_hook_summary(self, messages: list[str]) -> None:
        if not messages:
            return
        self.console.print("Hooks:")
        for message in messages:
            self.console.print(f"  [green]\u2714[/green] {message}")

    @staticmethod
    def _verification_counts(papers: list[PaperResult]) -> tuple[int, int]:
        verified = sum(
            1
            for paper in papers
            if getattr(paper.verification, "value", paper.verification) == "verified"
        )
        single_source = sum(
            1
            for paper in papers
            if getattr(paper.verification, "value", paper.verification) == "single_source"
        )
        return verified, single_source
