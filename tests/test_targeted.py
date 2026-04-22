"""Tests for the targeted search flow."""

from __future__ import annotations

import httpx
import pytest
import respx

from hypo_research.core.models import SearchParams
from hypo_research.core.sources.semantic_scholar import SemanticScholarSource
from hypo_research.survey.targeted import TargetedSearch, slugify_query
from tests.test_semantic_scholar import SAMPLE_S2_SEARCH_RESPONSE


@pytest.mark.asyncio
@respx.mock
async def test_targeted_search_writes_output_files(tmp_path) -> None:
    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json=SAMPLE_S2_SEARCH_RESPONSE)
    )

    searcher = TargetedSearch(sources=[source])
    result = await searcher.search(
        SearchParams(query="cryogenic computing"),
        output_dir=str(tmp_path / "survey"),
    )
    await searcher.close()

    output_dir = tmp_path / "survey"
    assert result.output_dir == str(output_dir)
    assert (output_dir / "meta.json").exists()
    assert (output_dir / "results.json").exists()
    assert (output_dir / "raw" / "semantic_scholar.json").exists()


def test_slugify_query() -> None:
    assert slugify_query("cryogenic computing on GPU") == "cryogenic-computing-on-gpu"
    assert slugify_query("  !! Quantum   CMOS @ 4K ## ") == "quantum-cmos-4k"


@pytest.mark.asyncio
@respx.mock
async def test_targeted_search_creates_output_directory(tmp_path) -> None:
    source = SemanticScholarSource()
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json=SAMPLE_S2_SEARCH_RESPONSE)
    )

    output_dir = tmp_path / "nested" / "survey"
    searcher = TargetedSearch(sources=[source])
    await searcher.search(
        SearchParams(query="cryogenic computing"),
        output_dir=str(output_dir),
    )
    await searcher.close()

    assert output_dir.exists()
