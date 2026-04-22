"""Tests for citation graph traversal and paper ID resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hypo_research.cite import CitationTraverser
from hypo_research.core.models import PaperResult, SearchParams, SurveyMeta, VerificationLevel
from hypo_research.core.paper_id import resolve_paper_id, resolve_paper_id_async
from hypo_research.core.verifier import Verifier
from hypo_research.output.json_output import write_search_output


def _paper(
    title: str,
    *,
    doi: str | None = None,
    s2_id: str | None = None,
    openalex_id: str | None = None,
    year: int = 2024,
    citation_count: int | None = 10,
    source_api: str = "semantic_scholar",
    sources: list[str] | None = None,
) -> PaperResult:
    return PaperResult(
        title=title,
        authors=["Alice Smith"],
        year=year,
        venue="ASPLOS",
        abstract=f"Abstract for {title}",
        doi=doi,
        s2_paper_id=s2_id,
        openalex_id=openalex_id,
        url=f"https://example.org/{(s2_id or openalex_id or title).replace(' ', '_')}",
        citation_count=citation_count,
        reference_count=5,
        source_api=source_api,
        sources=sources or [source_api],
        verification=VerificationLevel.SINGLE_SOURCE,
    )


class _TitleLookupSource:
    async def search(self, params: SearchParams) -> list[PaperResult]:
        assert params.query == "Cinnamon"
        return [
            _paper(
                "Cinnamon: A Large-Scale FHE Accelerator",
                doi="10.1145/3582016.3582066",
                s2_id="seed-s2",
            )
        ]

    async def close(self) -> None:
        return None


class _TraversalS2Source:
    name = "semantic_scholar"

    def __init__(self) -> None:
        self.seed = _paper(
            "Cinnamon: A Large-Scale FHE Accelerator",
            doi="10.1145/3582016.3582066",
            s2_id="seed-s2",
            citation_count=120,
        )
        self.layer1_shared = _paper(
            "Shared Expansion Paper",
            doi="10.1145/shared.paper",
            s2_id="shared-s2",
            citation_count=80,
        )
        self.layer1_unique = _paper(
            "S2-Only Reference",
            doi="10.1145/s2.reference",
            s2_id="s2-ref",
            citation_count=40,
        )
        self.depth2 = _paper(
            "Depth Two Discovery",
            doi="10.1145/depth.two",
            s2_id="depth-two",
            citation_count=15,
        )

    async def search(self, params: SearchParams) -> list[PaperResult]:
        if params.query == "Cinnamon":
            return [self.seed]
        return []

    async def get_paper(self, paper_id: str) -> PaperResult | None:
        if paper_id in {"seed-s2", "DOI:10.1145/3582016.3582066"}:
            return self.seed
        if paper_id == "shared-s2":
            return self.layer1_shared
        if paper_id == "depth-two":
            return self.depth2
        return None

    async def get_citations(self, paper_id: str, limit: int = 500) -> list[PaperResult]:
        if paper_id in {"seed-s2", "DOI:10.1145/3582016.3582066"}:
            return [self.layer1_shared]
        if paper_id == "shared-s2":
            return [self.depth2]
        return []

    async def get_references(self, paper_id: str, limit: int = 500) -> list[PaperResult]:
        if paper_id in {"seed-s2", "DOI:10.1145/3582016.3582066"}:
            return [self.layer1_unique]
        return []

    async def close(self) -> None:
        return None


class _TraversalOpenAlexSource:
    name = "openalex"

    def __init__(self) -> None:
        self.seed = _paper(
            "Cinnamon: A Large-Scale FHE Accelerator",
            doi="10.1145/3582016.3582066",
            openalex_id="W35820163582066",
            citation_count=125,
            source_api="openalex",
            sources=["openalex"],
        )
        self.layer1_shared = _paper(
            "Shared Expansion Paper",
            doi="10.1145/shared.paper",
            openalex_id="Wshared",
            citation_count=82,
            source_api="openalex",
            sources=["openalex"],
        )

    async def get_paper(self, paper_id: str) -> PaperResult | None:
        if paper_id in {"https://doi.org/10.1145/3582016.3582066", "W35820163582066"}:
            return self.seed
        return None

    async def get_citations(self, paper_id: str, limit: int = 500) -> list[PaperResult]:
        if paper_id in {"https://doi.org/10.1145/3582016.3582066", "W35820163582066"}:
            return [self.layer1_shared]
        return []

    async def get_references(self, paper_id: str, limit: int = 500) -> list[PaperResult]:
        return []

    async def close(self) -> None:
        return None


def test_resolve_doi() -> None:
    result = resolve_paper_id("10.1145/3582016.3582066")
    assert result["s2_id"] == "DOI:10.1145/3582016.3582066"
    assert result["openalex_id"] == "https://doi.org/10.1145/3582016.3582066"


def test_resolve_arxiv() -> None:
    result = resolve_paper_id("2404.12345")
    assert result["s2_id"] == "ARXIV:2404.12345"
    assert result["openalex_id"] is None


@pytest.mark.asyncio
async def test_resolve_title_via_s2_search() -> None:
    result = await resolve_paper_id_async("Cinnamon", s2_source=_TitleLookupSource())
    assert result["s2_id"] == "seed-s2"
    assert result["title"] == "Cinnamon: A Large-Scale FHE Accelerator"


@pytest.mark.asyncio
async def test_traverse_depth1_deduplicates_cross_source_results() -> None:
    traverser = CitationTraverser(
        s2_source=_TraversalS2Source(),
        openalex_source=_TraversalOpenAlexSource(),
    )

    result = await traverser.traverse(
        seeds=["Cinnamon"],
        depth=1,
        direction="both",
    )

    assert result.total_raw == 3
    assert result.total_deduped == 2
    assert len(result.failed_seeds) == 0
    assert result.depth_stats[1] == 2
    assert result.source_stats["semantic_scholar"] == 2
    assert result.source_stats["openalex"] == 1
    assert any(paper.title == "Shared Expansion Paper" for paper in result.expanded_papers)
    shared = next(
        paper for paper in result.expanded_papers if paper.title == "Shared Expansion Paper"
    )
    assert sorted(shared.sources) == ["openalex", "semantic_scholar"]
    assert result.graph_edges


@pytest.mark.asyncio
async def test_traverse_depth2_expands_only_high_citation_frontier() -> None:
    traverser = CitationTraverser(
        s2_source=_TraversalS2Source(),
        openalex_source=_TraversalOpenAlexSource(),
    )

    result = await traverser.traverse(
        seeds=["Cinnamon"],
        depth=2,
        direction="citations",
        min_citations=50,
    )

    titles = {paper.title for paper in result.expanded_papers}
    assert "Shared Expansion Paper" in titles
    assert "Depth Two Discovery" in titles
    assert result.depth_stats[2] == 1


@pytest.mark.asyncio
async def test_output_compatible_with_screen(tmp_path: Path) -> None:
    traverser = CitationTraverser(
        s2_source=_TraversalS2Source(),
        openalex_source=_TraversalOpenAlexSource(),
    )
    result = await traverser.traverse(seeds=["Cinnamon"], depth=1, direction="both")
    papers = Verifier().verify(result.expanded_papers)
    meta = SurveyMeta(
        query="citation graph traversal from 1 seed(s)",
        params=SearchParams(query="citation graph traversal"),
        mode="citation_graph",
        total_results=len(papers),
        sources_used=["semantic_scholar", "openalex"],
        output_dir=str(tmp_path),
        per_source_counts=result.source_stats,
        verified_count=sum(
            1 for paper in papers if paper.verification is VerificationLevel.VERIFIED
        ),
        single_source_count=sum(
            1 for paper in papers if paper.verification is VerificationLevel.SINGLE_SOURCE
        ),
        seed_identifiers=["Cinnamon"],
        seed_resolved_count=1,
        total_raw_results=result.total_raw,
        depth=1,
        direction="both",
        depth_stats={"1": result.depth_stats[1]},
        source_contributions=result.source_stats,
        relationship_contributions=result.relationship_stats,
    )

    write_search_output(tmp_path, meta, papers)

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert payload
    assert {"title", "authors", "year", "sources", "verification"} <= set(payload[0].keys())
