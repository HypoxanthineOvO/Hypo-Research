"""Citation graph traversal engine."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from hypo_research.core.dedup import Deduplicator
from hypo_research.core.models import PaperResult
from hypo_research.core.paper_id import resolve_paper_id_async
from hypo_research.core.sources import OpenAlexSource, SemanticScholarSource, SourceError

logger = logging.getLogger(__name__)


@dataclass
class GraphEdge:
    """A directed edge discovered during citation traversal."""

    from_title: str
    to_title: str
    relationship: str
    depth: int
    source: str
    seed_titles: list[str] = field(default_factory=list)


@dataclass
class TraversalResult:
    """Result bundle for citation traversal."""

    seed_papers: list[PaperResult]
    expanded_papers: list[PaperResult]
    total_raw: int
    total_deduped: int
    depth_stats: dict[int, int]
    source_stats: dict[str, int]
    relationship_stats: dict[str, int]
    failed_seeds: list[str]
    graph_edges: list[GraphEdge]


class CitationTraverser:
    """Traverse citation and reference graphs from seed papers."""

    MAX_DEPTH = 2
    MAX_DEPTH2_FRONTIER = 25

    def __init__(
        self,
        *,
        s2_source: SemanticScholarSource | None = None,
        openalex_source: OpenAlexSource | None = None,
    ) -> None:
        self._owns_s2_source = s2_source is None
        self._owns_openalex_source = openalex_source is None
        self.s2_source = s2_source or SemanticScholarSource()
        self.openalex_source = openalex_source or OpenAlexSource()
        self.deduplicator = Deduplicator()

    async def traverse(
        self,
        seeds: list[str],
        depth: int = 1,
        direction: str = "both",
        min_citations: int = 0,
        year_range: tuple[int, int] | None = None,
        max_papers: int = 2000,
    ) -> TraversalResult:
        """Traverse citation relationships from seed papers."""
        if depth < 1 or depth > self.MAX_DEPTH:
            raise ValueError(f"depth must be between 1 and {self.MAX_DEPTH}")
        if direction not in {"citations", "references", "both"}:
            raise ValueError("direction must be one of: citations, references, both")
        if max_papers <= 0:
            raise ValueError("max_papers must be positive")

        seed_papers, failed_seeds = await self._resolve_seed_papers(seeds)
        if not seed_papers:
            return TraversalResult(
                seed_papers=[],
                expanded_papers=[],
                total_raw=0,
                total_deduped=0,
                depth_stats={},
                source_stats={"semantic_scholar": 0, "openalex": 0},
                relationship_stats={"citations": 0, "references": 0},
                failed_seeds=failed_seeds,
                graph_edges=[],
            )

        source_stats = {"semantic_scholar": 0, "openalex": 0}
        relationship_stats = {"citations": 0, "references": 0}
        depth_stats: dict[int, int] = {}
        graph_edges: list[GraphEdge] = []
        raw_layers: list[PaperResult] = []
        seed_keys = {self._paper_identity_key(paper) for paper in seed_papers}

        layer1_raw = await self._expand_layer(
            frontier=seed_papers,
            depth=1,
            direction=direction,
            source_stats=source_stats,
            relationship_stats=relationship_stats,
            graph_edges=graph_edges,
        )
        filtered_layer1 = self._filter_papers(
            layer1_raw,
            year_range=year_range,
            exclude_keys=seed_keys,
        )
        depth_stats[1] = len(self.deduplicator.dedup(list(filtered_layer1)))
        raw_layers.extend(filtered_layer1)

        if depth >= 2 and len(raw_layers) < max_papers:
            frontier = self._select_depth2_frontier(
                filtered_layer1,
                min_citations=min_citations,
            )
            layer2_raw = await self._expand_layer(
                frontier=frontier,
                depth=2,
                direction=direction,
                source_stats=source_stats,
                relationship_stats=relationship_stats,
                graph_edges=graph_edges,
            )
            layer1_keys = {self._paper_identity_key(paper) for paper in filtered_layer1}
            filtered_layer2 = self._filter_papers(
                layer2_raw,
                year_range=year_range,
                exclude_keys=seed_keys | layer1_keys,
            )
            depth_stats[2] = len(self.deduplicator.dedup(list(filtered_layer2)))
            raw_layers.extend(filtered_layer2)

        total_raw = len(raw_layers)
        deduped = self.deduplicator.dedup(raw_layers)
        deduped = deduped[:max_papers]
        return TraversalResult(
            seed_papers=seed_papers,
            expanded_papers=deduped,
            total_raw=total_raw,
            total_deduped=len(deduped),
            depth_stats=depth_stats,
            source_stats=source_stats,
            relationship_stats=relationship_stats,
            failed_seeds=failed_seeds,
            graph_edges=graph_edges,
        )

    async def close(self) -> None:
        """Close owned HTTP clients."""
        tasks: list[Awaitable[None]] = []
        if self._owns_s2_source:
            tasks.append(self.s2_source.close())
        if self._owns_openalex_source:
            tasks.append(self.openalex_source.close())
        if tasks:
            await asyncio.gather(*tasks)

    async def _resolve_seed_papers(
        self,
        seeds: list[str],
    ) -> tuple[list[PaperResult], list[str]]:
        resolved_papers: list[PaperResult] = []
        failed_seeds: list[str] = []

        for seed in seeds:
            try:
                resolved = await resolve_paper_id_async(seed, s2_source=self.s2_source)
            except SourceError as exc:
                logger.warning("failed to resolve seed title %s: %s", seed, exc)
                failed_seeds.append(seed)
                continue
            variants: list[PaperResult] = []
            if resolved["s2_id"]:
                paper = await self._safe_get_paper(self.s2_source, resolved["s2_id"])
                if paper is not None:
                    variants.append(paper)
            if resolved["openalex_id"]:
                paper = await self._safe_get_paper(self.openalex_source, resolved["openalex_id"])
                if paper is not None:
                    variants.append(paper)

            if not variants:
                failed_seeds.append(seed)
                continue

            merged_seed = self.deduplicator.dedup(variants)[0]
            merged_seed.seed_papers = [seed]
            merged_seed.discovery_paths = [f"seed:{seed}"]
            resolved_papers.append(merged_seed)

        deduped_seeds = self.deduplicator.dedup(resolved_papers)
        return deduped_seeds, failed_seeds

    async def _safe_get_paper(
        self,
        source: SemanticScholarSource | OpenAlexSource,
        paper_id: str,
    ) -> PaperResult | None:
        try:
            return await source.get_paper(paper_id)
        except SourceError as exc:
            logger.warning("[%s] failed to resolve seed %s: %s", source.name, paper_id, exc)
            return None

    async def _expand_layer(
        self,
        *,
        frontier: list[PaperResult],
        depth: int,
        direction: str,
        source_stats: dict[str, int],
        relationship_stats: dict[str, int],
        graph_edges: list[GraphEdge],
    ) -> list[PaperResult]:
        tasks = [
            self._expand_from_paper(
                paper=paper,
                depth=depth,
                direction=direction,
            )
            for paper in frontier
        ]
        results = await asyncio.gather(*tasks)
        collected: list[PaperResult] = []
        for papers, edges, local_source_stats, local_relationship_stats in results:
            collected.extend(papers)
            graph_edges.extend(edges)
            for key, value in local_source_stats.items():
                source_stats[key] = source_stats.get(key, 0) + value
            for key, value in local_relationship_stats.items():
                relationship_stats[key] = relationship_stats.get(key, 0) + value
        return collected

    async def _expand_from_paper(
        self,
        *,
        paper: PaperResult,
        depth: int,
        direction: str,
    ) -> tuple[list[PaperResult], list[GraphEdge], dict[str, int], dict[str, int]]:
        tasks: list[tuple[str, str, asyncio.Future[list[PaperResult]]]] = []
        s2_identifier = self._best_s2_identifier(paper)
        openalex_identifier = self._best_openalex_identifier(paper)

        if s2_identifier:
            if direction in {"citations", "both"}:
                tasks.append(
                    (
                        "semantic_scholar",
                        "citations",
                        asyncio.create_task(
                            self._safe_relationship_fetch(
                                self.s2_source.get_citations,
                                s2_identifier,
                            )
                        ),
                    )
                )
            if direction in {"references", "both"}:
                tasks.append(
                    (
                        "semantic_scholar",
                        "references",
                        asyncio.create_task(
                            self._safe_relationship_fetch(
                                self.s2_source.get_references,
                                s2_identifier,
                            )
                        ),
                    )
                )

        if openalex_identifier:
            if direction in {"citations", "both"}:
                tasks.append(
                    (
                        "openalex",
                        "citations",
                        asyncio.create_task(
                            self._safe_relationship_fetch(
                                self.openalex_source.get_citations,
                                openalex_identifier,
                            )
                        ),
                    )
                )
            if direction in {"references", "both"}:
                tasks.append(
                    (
                        "openalex",
                        "references",
                        asyncio.create_task(
                            self._safe_relationship_fetch(
                                self.openalex_source.get_references,
                                openalex_identifier,
                            )
                        ),
                    )
                )

        collected: list[PaperResult] = []
        edges: list[GraphEdge] = []
        source_stats = {"semantic_scholar": 0, "openalex": 0}
        relationship_stats = {"citations": 0, "references": 0}
        seed_titles = paper.seed_papers or [paper.title]

        for source_name, relationship, task in tasks:
            discovered = await task
            source_stats[source_name] += len(discovered)
            relationship_stats[relationship] += len(discovered)
            for discovered_paper in discovered:
                discovered_paper.seed_papers = self._merge_unique_lists(
                    discovered_paper.seed_papers,
                    seed_titles,
                )
                discovered_paper.discovery_paths = self._merge_unique_lists(
                    discovered_paper.discovery_paths,
                    [f"depth{depth}:{relationship}:{source_name}:{paper.title}"],
                )
                collected.append(discovered_paper)
                edges.append(
                    GraphEdge(
                        from_title=paper.title,
                        to_title=discovered_paper.title,
                        relationship=relationship,
                        depth=depth,
                        source=source_name,
                        seed_titles=list(seed_titles),
                    )
                )

        return collected, edges, source_stats, relationship_stats

    async def _safe_relationship_fetch(
        self,
        method: Callable[[str], Awaitable[list[PaperResult]]],
        paper_id: str,
    ) -> list[PaperResult]:
        try:
            return await method(paper_id)
        except SourceError as exc:
            logger.warning("relationship fetch failed for %s: %s", paper_id, exc)
            return []

    def _select_depth2_frontier(
        self,
        papers: list[PaperResult],
        *,
        min_citations: int,
    ) -> list[PaperResult]:
        deduped = self.deduplicator.dedup(list(papers))
        candidates = [
            paper
            for paper in deduped
            if (paper.citation_count or 0) >= min_citations
        ]
        candidates.sort(key=lambda paper: paper.citation_count or 0, reverse=True)
        return candidates[: self.MAX_DEPTH2_FRONTIER]

    def _filter_papers(
        self,
        papers: list[PaperResult],
        *,
        year_range: tuple[int, int] | None,
        exclude_keys: set[str],
    ) -> list[PaperResult]:
        filtered: list[PaperResult] = []
        for paper in papers:
            if year_range is not None:
                if paper.year is None or not (year_range[0] <= paper.year <= year_range[1]):
                    continue
            key = self._paper_identity_key(paper)
            if key in exclude_keys:
                continue
            filtered.append(paper)
        return filtered

    @staticmethod
    def _merge_unique_lists(
        left: list[str] | None,
        right: list[str] | None,
    ) -> list[str] | None:
        merged = list(dict.fromkeys([*(left or []), *(right or [])]))
        return merged or None

    @staticmethod
    def _best_s2_identifier(paper: PaperResult) -> str | None:
        if paper.s2_paper_id:
            return paper.s2_paper_id
        if paper.doi:
            return f"DOI:{paper.doi}"
        if paper.arxiv_id:
            return f"ARXIV:{paper.arxiv_id}"
        return None

    @staticmethod
    def _best_openalex_identifier(paper: PaperResult) -> str | None:
        if paper.openalex_id:
            return paper.openalex_id
        if paper.doi:
            return f"https://doi.org/{paper.doi}"
        return None

    @staticmethod
    def _paper_identity_key(paper: PaperResult) -> str:
        if paper.doi:
            return f"doi:{paper.doi.lower()}"
        if paper.s2_paper_id:
            return f"s2:{paper.s2_paper_id.lower()}"
        if paper.openalex_id:
            return f"openalex:{paper.openalex_id.lower()}"
        if paper.arxiv_id:
            return f"arxiv:{paper.arxiv_id.lower()}"
        return f"title:{paper.title.lower()}:{paper.year}"
