"""Pydantic models used across the project."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VerificationLevel(str, Enum):
    """Verification status for a paper record."""

    VERIFIED = "verified"
    SINGLE_SOURCE = "single_source"
    UNVERIFIED = "unverified"
    SUSPICIOUS = "suspicious"


class PaperResult(BaseModel):
    """Normalized paper record returned by a source adapter."""

    title: str
    authors: list[str]
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    doi: str | None = None
    s2_paper_id: str | None = None
    arxiv_id: str | None = None
    url: str
    citation_count: int | None = None
    reference_count: int | None = None
    source_api: str
    sources: list[str] = Field(default_factory=list)
    verification: VerificationLevel = VerificationLevel.UNVERIFIED
    raw_response: dict = Field(default_factory=dict, repr=False)


class SearchParams(BaseModel):
    """Search parameters accepted by literature search flows."""

    query: str
    year_range: tuple[int, int] | None = None
    venue_filter: list[str] | None = None
    fields_of_study: list[str] | None = None
    max_results: int = Field(default=100, ge=1)
    sort_by: Literal["relevance", "citation_count", "year"] = "relevance"

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Require a non-empty query string."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("query must not be empty")
        return cleaned

    @field_validator("year_range")
    @classmethod
    def validate_year_range(
        cls, value: tuple[int, int] | None
    ) -> tuple[int, int] | None:
        """Ensure year ranges are ascending and positive."""
        if value is None:
            return value
        start, end = value
        if start > end:
            raise ValueError("year_range start must be <= end")
        if start <= 0 or end <= 0:
            raise ValueError("year_range values must be positive")
        return value

    @field_validator("venue_filter", "fields_of_study")
    @classmethod
    def clean_filters(cls, value: list[str] | None) -> list[str] | None:
        """Normalize list filters and collapse empty lists to None."""
        if value is None:
            return None
        cleaned = [item.strip() for item in value if item and item.strip()]
        return cleaned or None


class SurveyMeta(BaseModel):
    """Metadata saved alongside a survey run."""

    query: str
    params: SearchParams
    mode: Literal["targeted", "comprehensive"] = "targeted"
    created_at: datetime = Field(default_factory=datetime.now)
    total_results: int = 0
    sources_used: list[str] = Field(default_factory=list)
    output_dir: str = ""


class SearchResult(BaseModel):
    """Search output bundle returned by search flows."""

    meta: SurveyMeta
    papers: list[PaperResult]
    output_dir: str
