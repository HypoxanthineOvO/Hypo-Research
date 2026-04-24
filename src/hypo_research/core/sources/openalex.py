"""OpenAlex source adapter."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import httpx

from hypo_research.core.models import PaperResult, SearchParams, VerificationLevel
from hypo_research.core.rate_limiter import RateLimiter

from . import RateLimitError, SourceError
from .base import BaseSource

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int | None], None]


def restore_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """Restore abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return None

    max_position = max(
        (position for positions in inverted_index.values() for position in positions),
        default=-1,
    )
    if max_position < 0:
        return None

    words = [""] * (max_position + 1)
    for token, positions in inverted_index.items():
        for position in positions:
            if 0 <= position <= max_position:
                words[position] = token

    restored = " ".join(word for word in words if word)
    return restored or None


class OpenAlexSource(BaseSource):
    """OpenAlex adapter."""

    SOURCE_NAME = "openalex"
    BASE_URL = "https://api.openalex.org"
    DEFAULT_SELECT = (
        "id,doi,title,authorships,publication_year,primary_location,"
        "cited_by_count,abstract_inverted_index,referenced_works,type"
    )
    PAGE_SIZE = 50
    CITATION_PAGE_SIZE = 200
    REFERENCE_BATCH_SIZE = 50
    MAX_RETRIES = 3

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        email: str | None = None,
        timeout: float = 30.0,
    ):
        self.email = email or os.getenv("OPENALEX_EMAIL") or "hyx021203@163.com"
        headers = {
            "Accept": "application/json",
            "User-Agent": "hypo-research/0.1.0",
        }
        if self.email:
            headers["User-Agent"] = f"hypo-research/0.1.0 (mailto:{self.email})"
            headers["From"] = self.email

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=timeout,
        )
        self._limiter = rate_limiter or RateLimiter(
            max_tokens=10 if self.email else 1,
            refill_period=1.0,
            name=self.SOURCE_NAME,
        )
        self._progress_callback: ProgressCallback | None = None

    @property
    def name(self) -> str:
        """Source identifier."""
        return self.SOURCE_NAME

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Set a callback invoked after each search page."""
        self._progress_callback = callback

    async def search(self, params: SearchParams) -> list[PaperResult]:
        """Search OpenAlex works."""
        papers: list[PaperResult] = []
        cursor = "*"

        while len(papers) < params.max_results:
            page_size = min(self.PAGE_SIZE, params.max_results - len(papers))
            request_params: dict[str, Any] = {
                "search": params.query,
                "per_page": page_size,
                "cursor": cursor,
                "select": self.DEFAULT_SELECT,
                "sort": self._sort_value(params),
            }

            filters = self._build_filters(params)
            if filters:
                request_params["filter"] = ",".join(filters)

            payload = await self._request_json("/works", params=request_params)
            results = payload.get("results", [])
            if not results:
                break

            papers.extend(self._paper_from_payload(item) for item in results)
            cursor = payload.get("meta", {}).get("next_cursor")

            if self._progress_callback is not None:
                self._progress_callback(len(papers), None)

            if not cursor:
                break

        return papers[: params.max_results]

    async def get_paper(self, paper_id: str) -> PaperResult | None:
        """Fetch a single work by OpenAlex ID."""
        try:
            payload = await self._get_work_payload(paper_id)
        except SourceError as exc:
            if exc.status_code == 404:
                return None
            raise
        return self._paper_from_payload(payload)

    async def get_citations(self, paper_id: str, limit: int = 500) -> list[PaperResult]:
        """Return works citing the given paper."""
        filter_value = self._citation_filter_value(paper_id)
        citations: list[PaperResult] = []
        cursor = "*"

        while len(citations) < limit:
            page_size = min(self.CITATION_PAGE_SIZE, limit - len(citations))
            payload = await self._request_json(
                "/works",
                params={
                    "filter": f"cites:{filter_value}",
                    "select": self.DEFAULT_SELECT,
                    "per_page": page_size,
                    "cursor": cursor,
                },
            )
            results = payload.get("results", [])
            if not results:
                break

            citations.extend(
                self._paper_from_payload(item)
                for item in results
                if isinstance(item, dict)
            )
            cursor = payload.get("meta", {}).get("next_cursor")
            if not cursor:
                break

        return citations[:limit]

    async def get_references(self, paper_id: str, limit: int = 500) -> list[PaperResult]:
        """Return works referenced by the given paper."""
        try:
            payload = await self._get_work_payload(paper_id)
        except SourceError as exc:
            if exc.status_code == 404:
                return []
            raise

        references = payload.get("referenced_works", [])
        if not references:
            return []
        normalized_references = [
            self._canonical_openalex_id(reference)
            for reference in references
            if reference
        ][:limit]

        results: list[PaperResult] = []
        for index in range(0, len(normalized_references), self.REFERENCE_BATCH_SIZE):
            batch = normalized_references[index : index + self.REFERENCE_BATCH_SIZE]
            response = await self._request_json(
                "/works",
                params={
                    "filter": f"openalex:{'|'.join(batch)}",
                    "select": self.DEFAULT_SELECT,
                    "per_page": len(batch),
                },
            )
            results.extend(
                self._paper_from_payload(item)
                for item in response.get("results", [])
                if isinstance(item, dict)
            )

        return results[:limit]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    def _build_filters(self, params: SearchParams) -> list[str]:
        filters: list[str] = []
        if params.year_range is not None:
            filters.append(
                f"publication_year:{params.year_range[0]}-{params.year_range[1]}"
            )
        return filters

    @staticmethod
    def _sort_value(params: SearchParams) -> str:
        if params.sort_by == "citation_count":
            return "cited_by_count:desc"
        if params.sort_by == "year":
            return "publication_year:desc"
        return "relevance_score:desc"

    async def _request_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        retries = 0
        while True:
            async with self._limiter:
                try:
                    response = await self._client.get(path, params=params)
                except httpx.RequestError as exc:
                    raise SourceError(self.name, f"request failed: {exc}") from exc

            if response.status_code == 429:
                if retries >= self.MAX_RETRIES:
                    raise RateLimitError(
                        self.name,
                        "rate limit exceeded and retries exhausted",
                        status_code=429,
                    )
                retries += 1
                retry_after = self._parse_retry_after(response)
                logger.warning(
                    "[%s] rate limited, retrying in %.2fs (%s/%s)",
                    self.name,
                    retry_after,
                    retries,
                    self.MAX_RETRIES,
                )
                await asyncio.sleep(retry_after)
                continue

            if 500 <= response.status_code < 600:
                if retries >= self.MAX_RETRIES:
                    raise SourceError(
                        self.name,
                        f"server error after retries: {response.status_code}",
                        status_code=response.status_code,
                    )
                backoff = float(2**retries)
                retries += 1
                logger.warning(
                    "[%s] server error %s, retrying in %.2fs (%s/%s)",
                    self.name,
                    response.status_code,
                    backoff,
                    retries,
                    self.MAX_RETRIES,
                )
                await asyncio.sleep(backoff)
                continue

            if response.status_code >= 400:
                raise SourceError(
                    self.name,
                    f"HTTP {response.status_code}",
                    status_code=response.status_code,
                )

            try:
                return response.json()
            except ValueError as exc:
                raise SourceError(self.name, "invalid JSON response") from exc

    async def _get_work_payload(self, paper_id: str) -> dict[str, Any]:
        identifier = self._identifier_for_path(paper_id)
        return await self._request_json(f"/works/{identifier}")

    def _paper_from_payload(self, payload: dict[str, Any]) -> PaperResult:
        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in payload.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        openalex_id = payload.get("id")
        primary_location = payload.get("primary_location") or {}
        source = primary_location.get("source") or {}
        doi = self._normalize_doi(payload.get("doi"))

        return PaperResult(
            title=payload.get("title", ""),
            authors=authors,
            year=payload.get("publication_year"),
            venue=source.get("display_name"),
            abstract=restore_abstract(payload.get("abstract_inverted_index")),
            doi=doi,
            openalex_id=self._normalize_openalex_id(openalex_id) if openalex_id else None,
            url=primary_location.get("landing_page_url") or openalex_id or "https://openalex.org",
            citation_count=payload.get("cited_by_count"),
            reference_count=len(payload.get("referenced_works", []) or []),
            source_api=self.name,
            sources=[self.name],
            verification=VerificationLevel.SINGLE_SOURCE,
            raw_response=dict(payload),
        )

    @staticmethod
    def _normalize_doi(doi: str | None) -> str | None:
        if not doi:
            return None
        cleaned = doi.strip().lower()
        return cleaned.removeprefix("https://doi.org/")

    @staticmethod
    def _normalize_openalex_id(openalex_id: str) -> str:
        if not openalex_id:
            return openalex_id
        if "openalex.org" not in openalex_id:
            return openalex_id.rstrip("/")
        return openalex_id.rstrip("/").rsplit("/", 1)[-1]

    @staticmethod
    def _canonical_openalex_id(openalex_id: str) -> str:
        normalized = OpenAlexSource._normalize_openalex_id(openalex_id)
        return f"https://openalex.org/{normalized}"

    @staticmethod
    def _normalize_doi_identifier(identifier: str) -> str:
        cleaned = identifier.strip()
        lowered = cleaned.lower()
        if lowered.startswith("doi:"):
            cleaned = cleaned[4:]
            lowered = cleaned.lower()
        if lowered.startswith("https://doi.org/"):
            return "https://doi.org/" + cleaned[len("https://doi.org/") :]
        if lowered.startswith("http://doi.org/"):
            return "https://doi.org/" + cleaned[len("http://doi.org/") :]
        if lowered.startswith("http://dx.doi.org/"):
            return "https://doi.org/" + cleaned[len("http://dx.doi.org/") :]
        return f"https://doi.org/{cleaned}"

    def _identifier_for_path(self, paper_id: str) -> str:
        cleaned = paper_id.strip()
        lowered = cleaned.lower()
        if cleaned.startswith("W") and cleaned[1:].isdigit():
            return cleaned
        if "openalex.org" in lowered:
            return self._normalize_openalex_id(cleaned)
        if "/" in cleaned or lowered.startswith("doi:"):
            return quote(self._normalize_doi_identifier(cleaned), safe=":/")
        return quote(cleaned, safe=":/")

    def _citation_filter_value(self, paper_id: str) -> str:
        cleaned = paper_id.strip()
        lowered = cleaned.lower()
        if cleaned.startswith("W") and cleaned[1:].isdigit():
            return cleaned
        if "openalex.org" in lowered:
            return self._normalize_openalex_id(cleaned)
        return self._normalize_doi_identifier(cleaned)

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float:
        raw_value = response.headers.get("Retry-After", "1")
        try:
            return max(float(raw_value), 0.0)
        except ValueError:
            return 1.0
