"""Semantic Scholar source adapter."""

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


class SemanticScholarSource(BaseSource):
    """Semantic Scholar API adapter."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    DEFAULT_FIELDS = (
        "title,authors,year,venue,abstract,externalIds,"
        "citationCount,referenceCount,url"
    )
    MAX_PAGE_SIZE = 100
    RELATIONSHIP_PAGE_SIZE = 1000
    MAX_RETRIES = 3

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "hypo-research/0.1.0",
        }
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=self.headers,
            timeout=30.0,
        )
        self.rate_limiter = RateLimiter(
            max_tokens=10 if self.api_key else 1,
            refill_period=1.0,
            name="semantic_scholar",
        )
        self._limiter = self.rate_limiter
        self._progress_callback: ProgressCallback | None = None

    @property
    def name(self) -> str:
        """Source identifier."""
        return "semantic_scholar"

    def set_progress_callback(self, callback: ProgressCallback | None) -> None:
        """Set a callback invoked after each search page."""
        self._progress_callback = callback

    async def search(self, params: SearchParams) -> list[PaperResult]:
        """Search Semantic Scholar for papers matching parameters."""
        papers: list[PaperResult] = []
        offset = 0
        total: int | None = None

        while len(papers) < params.max_results:
            limit = min(self.MAX_PAGE_SIZE, params.max_results - len(papers))
            request_params: dict[str, Any] = {
                "query": params.query,
                "offset": offset,
                "limit": limit,
                "fields": self.DEFAULT_FIELDS,
            }
            if params.year_range is not None:
                request_params["year"] = f"{params.year_range[0]}-{params.year_range[1]}"
            if params.fields_of_study:
                request_params["fieldsOfStudy"] = ",".join(params.fields_of_study)
            if params.venue_filter:
                request_params["venue"] = ",".join(params.venue_filter)

            payload = await self._request_json(
                "GET",
                "/paper/search",
                params=request_params,
            )
            batch = payload.get("data", [])
            total = payload.get("total", total)
            if not batch:
                break

            papers.extend(self._paper_from_payload(item) for item in batch)
            offset += len(batch)

            if self._progress_callback is not None:
                self._progress_callback(len(papers), total)

            if len(batch) < limit:
                break
            if total is not None and offset >= total:
                break

        if params.sort_by == "citation_count":
            papers.sort(key=lambda paper: paper.citation_count or -1, reverse=True)
        elif params.sort_by == "year":
            papers.sort(key=lambda paper: paper.year or -1, reverse=True)

        return papers[: params.max_results]

    async def get_paper(self, paper_id: str) -> PaperResult | None:
        """Fetch a single paper by Semantic Scholar-compatible paper ID."""
        encoded_id = quote(paper_id, safe=":")
        try:
            payload = await self._request_json(
                "GET",
                f"/paper/{encoded_id}",
                params={"fields": self.DEFAULT_FIELDS},
            )
        except SourceError as exc:
            if exc.status_code == 404:
                return None
            raise
        return self._paper_from_payload(payload)

    async def get_citations(self, paper_id: str, limit: int = 500) -> list[PaperResult]:
        """Return papers that cite the given paper."""
        return await self._get_relationship_papers(
            paper_id=paper_id,
            endpoint="citations",
            nested_key="citingPaper",
            limit=limit,
        )

    async def get_references(self, paper_id: str, limit: int = 500) -> list[PaperResult]:
        """Return papers referenced by the given paper."""
        return await self._get_relationship_papers(
            paper_id=paper_id,
            endpoint="references",
            nested_key="citedPaper",
            limit=limit,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _get_relationship_papers(
        self,
        paper_id: str,
        endpoint: str,
        nested_key: str,
        limit: int,
    ) -> list[PaperResult]:
        encoded_id = quote(paper_id, safe=":")
        offset = 0
        results: list[PaperResult] = []

        while len(results) < limit:
            page_limit = min(self.RELATIONSHIP_PAGE_SIZE, limit - len(results))
            try:
                payload = await self._request_json(
                    "GET",
                    f"/paper/{encoded_id}/{endpoint}",
                    params={
                        "fields": self._prefixed_relationship_fields(nested_key),
                        "offset": offset,
                        "limit": page_limit,
                    },
                )
            except SourceError as exc:
                if exc.status_code == 404:
                    return []
                raise
            batch = payload.get("data", [])
            if not batch:
                break

            for item in batch:
                paper = item.get(nested_key, item)
                if not isinstance(paper, dict):
                    continue
                results.append(self._paper_from_payload(paper))

            offset += len(batch)
            if len(batch) < page_limit:
                break

        return results[:limit]

    def _prefixed_relationship_fields(self, prefix: str) -> str:
        fields = ["paperId", *self.DEFAULT_FIELDS.split(",")]
        return ",".join(f"{prefix}.{field}" for field in fields)

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        retries = 0
        while True:
            async with self._limiter:
                try:
                    response = await self._client.request(method, path, params=params)
                except httpx.RequestError as exc:
                    raise SourceError(self.name, f"request failed: {exc}") from exc

            if response.status_code == 429:
                if retries >= self.MAX_RETRIES:
                    raise RateLimitError(
                        self.name,
                        "rate limit exceeded and retries exhausted",
                        status_code=429,
                    )
                retry_after = self._parse_retry_after(response)
                retries += 1
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
                message = self._extract_error_message(response)
                logger.error("[%s] request failed: %s", self.name, message)
                raise SourceError(
                    self.name,
                    message,
                    status_code=response.status_code,
                )

            try:
                return response.json()
            except ValueError as exc:
                raise SourceError(self.name, "invalid JSON response") from exc

    def _paper_from_payload(self, payload: dict[str, Any]) -> PaperResult:
        external_ids = payload.get("externalIds") or {}
        paper_id = payload.get("paperId")
        url = payload.get("url") or self._build_default_url(paper_id)
        doi = external_ids.get("DOI")
        verification = (
            VerificationLevel.SINGLE_SOURCE
            if doi
            else VerificationLevel.UNVERIFIED
        )

        return PaperResult(
            title=payload.get("title", ""),
            authors=[
                author.get("name", "")
                for author in payload.get("authors", [])
                if author.get("name")
            ],
            year=payload.get("year"),
            venue=payload.get("venue"),
            abstract=payload.get("abstract"),
            doi=doi,
            s2_paper_id=paper_id,
            arxiv_id=external_ids.get("ArXiv"),
            url=url,
            citation_count=payload.get("citationCount"),
            reference_count=payload.get("referenceCount"),
            source_api=self.name,
            sources=[self.name],
            verification=verification,
            raw_response=dict(payload),
        )

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float:
        raw_value = response.headers.get("Retry-After", "1")
        try:
            return max(float(raw_value), 0.0)
        except ValueError:
            return 1.0

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return f"HTTP {response.status_code}"

        if isinstance(payload, dict):
            if "error" in payload:
                return str(payload["error"])
            if "message" in payload:
                return str(payload["message"])
        return f"HTTP {response.status_code}"

    @staticmethod
    def _build_default_url(paper_id: str | None) -> str:
        if not paper_id:
            return "https://www.semanticscholar.org"
        return f"https://www.semanticscholar.org/paper/{paper_id}"
