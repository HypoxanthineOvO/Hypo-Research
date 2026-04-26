"""Tests for core data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hypo_research.core.models import (
    PaperResult,
    SearchParams,
    SurveyMeta,
    VerificationLevel,
)


def test_paper_result_round_trip() -> None:
    paper = PaperResult(
        title="Cryogenic CMOS for Quantum Computing",
        authors=["Alice Smith", "Bob Jones"],
        year=2023,
        venue="ISSCC",
        doi="10.1234/example",
        s2_paper_id="abc123",
        arxiv_id="2301.00001",
        url="https://www.semanticscholar.org/paper/abc123",
        citation_count=42,
        reference_count=30,
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
        verification=VerificationLevel.SINGLE_SOURCE,
        raw_response={"paperId": "abc123"},
    )

    restored = PaperResult.model_validate_json(paper.model_dump_json())

    assert restored == paper
    assert restored.verification is VerificationLevel.SINGLE_SOURCE
    assert hasattr(restored, "abstract")
    assert restored.abstract is None


def test_search_params_defaults() -> None:
    params = SearchParams(query="cryogenic computing")

    assert params.year_range is None
    assert params.venue_filter is None
    assert params.fields_of_study is None
    assert params.max_results == 100
    assert params.sort_by == "relevance"


def test_search_params_validation() -> None:
    with pytest.raises(ValidationError):
        SearchParams(query="   ")

    with pytest.raises(ValidationError):
        SearchParams(query="ok", max_results=0)

    with pytest.raises(ValidationError):
        SearchParams(query="ok", year_range=(2025, 2024))


def test_survey_meta_defaults() -> None:
    params = SearchParams(query="cryogenic computing")
    meta = SurveyMeta(query=params.query, params=params)

    assert meta.mode == "targeted"
    assert meta.total_results == 0
    assert meta.sources_used == []
    assert meta.output_dir == ""
    assert meta.created_at is not None
