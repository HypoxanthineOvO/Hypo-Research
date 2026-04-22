"""arXiv source adapter."""

from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Any

import httpx

try:
    import feedparser
except ImportError:  # pragma: no cover - fallback is exercised in local env
    feedparser = None

from hypo_research.core.models import PaperResult, SearchParams, VerificationLevel
from hypo_research.core.rate_limiter import RateLimiter

from . import SourceError
from .base import BaseSource

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int | None], None]


class ArxivSource(BaseSource):
    """arXiv adapter."""

    SOURCE_NAME = "arxiv"
    BASE_URL = "https://export.arxiv.org/api/query"
    PAGE_SIZE = 50
    MAX_RETRIES = 2

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
    ):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=20.0),
            follow_redirects=True,
        )
        self._limiter = rate_limiter or RateLimiter(
            max_tokens=1,
            refill_period=3.0,
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
        """Search arXiv Atom feed."""
        papers: list[PaperResult] = []
        start = 0
        arxiv_query = self._build_arxiv_query(params.query, params)

        while len(papers) < params.max_results:
            page_size = min(self.PAGE_SIZE, params.max_results - len(papers))
            payload = await self._request_feed(
                {
                    "search_query": arxiv_query,
                    "start": str(start),
                    "max_results": str(page_size),
                    "sortBy": self._sort_by(params),
                    "sortOrder": "descending",
                }
            )
            entries = payload.get("entries", [])
            if not entries:
                break

            batch = [self._paper_from_entry(entry) for entry in entries]
            if params.year_range is not None:
                batch = [
                    paper
                    for paper in batch
                    if paper.year is not None
                    and params.year_range[0] <= paper.year <= params.year_range[1]
                ]

            papers.extend(batch)
            start += page_size

            if self._progress_callback is not None:
                self._progress_callback(len(papers), None)

            if len(entries) < page_size:
                break

        return papers[: params.max_results]

    async def get_paper(self, paper_id: str) -> PaperResult | None:
        """Fetch a single arXiv paper by ID."""
        payload = await self._request_feed({"id_list": paper_id})
        entries = payload.get("entries", [])
        if not entries:
            return None
        return self._paper_from_entry(entries[0])

    async def get_citations(self, paper_id: str, limit: int = 100) -> list[PaperResult]:
        """Return empty citations because arXiv API does not provide them."""
        return []

    async def get_references(self, paper_id: str, limit: int = 100) -> list[PaperResult]:
        """Return empty references because arXiv API does not provide them."""
        return []

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def _request_feed(self, params: dict[str, str]) -> dict[str, Any]:
        retries = 0
        while True:
            async with self._limiter:
                try:
                    response = await self._client.get(self.BASE_URL, params=params)
                except httpx.RequestError as exc:
                    if retries < self.MAX_RETRIES:
                        retries += 1
                        retry_after = min(1.0 * retries, 3.0)
                        logger.warning(
                            "[%s] request error %s, retrying in %.2fs (%s/%s)",
                            self.name,
                            exc,
                            retry_after,
                            retries,
                            self.MAX_RETRIES,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    logger.warning(
                        "[%s] request failed after retries: %s; returning empty result set",
                        self.name,
                        exc,
                    )
                    return {"entries": []}

            if response.status_code == 200:
                body = response.text
                if not body or not body.strip():
                    logger.warning("[%s] empty response body from arXiv", self.name)
                    return {"entries": []}
                return self._parse_feed(body)

            if response.status_code in {500, 502, 503, 504} and retries < self.MAX_RETRIES:
                retries += 1
                retry_after = self._retry_delay(response, retries)
                logger.warning(
                    "[%s] transient HTTP %s, retrying in %.2fs (%s/%s)",
                    self.name,
                    response.status_code,
                    retry_after,
                    retries,
                    self.MAX_RETRIES,
                )
                await asyncio.sleep(retry_after)
                continue

            logger.warning(
                "[%s] HTTP %s from arXiv; returning empty result set",
                self.name,
                response.status_code,
            )
            return {"entries": []}

    def _parse_feed(self, text: str) -> dict[str, Any]:
        if not text or not text.strip():
            return {"entries": []}

        if feedparser is not None:
            try:
                parsed = feedparser.parse(text)
            except Exception as exc:  # pragma: no cover - parser-specific failure
                logger.warning("[%s] failed to parse arXiv feed: %s", self.name, exc)
                return {"entries": []}

            if getattr(parsed, "bozo", 0) and not getattr(parsed, "entries", []):
                logger.warning(
                    "[%s] invalid arXiv feed content: %s",
                    self.name,
                    getattr(parsed, "bozo_exception", "unknown parse error"),
                )
                return {"entries": []}
            entries = [self._normalize_feedparser_entry(entry) for entry in parsed.entries]
            return {"entries": entries}

        try:
            return {"entries": self._fallback_parse_atom(text)}
        except ET.ParseError as exc:
            logger.warning("[%s] invalid arXiv XML response: %s", self.name, exc)
            return {"entries": []}

    def _normalize_feedparser_entry(self, entry: Any) -> dict[str, Any]:
        links = []
        for link in getattr(entry, "links", []):
            if isinstance(link, dict):
                links.append({"rel": link.get("rel"), "href": link.get("href")})
            else:
                links.append({"rel": getattr(link, "rel", None), "href": getattr(link, "href", None)})

        primary_category = getattr(entry, "arxiv_primary_category", {})
        if not isinstance(primary_category, dict):
            primary_category = {"term": getattr(primary_category, "term", None)}

        return {
            "title": getattr(entry, "title", ""),
            "authors": [
                {"name": getattr(author, "name", "")}
                for author in getattr(entry, "authors", [])
            ],
            "published": getattr(entry, "published", ""),
            "summary": getattr(entry, "summary", ""),
            "arxiv_journal_ref": getattr(entry, "arxiv_journal_ref", None),
            "arxiv_primary_category": primary_category,
            "arxiv_doi": getattr(entry, "arxiv_doi", None),
            "id": getattr(entry, "id", ""),
            "links": links,
        }

    def _fallback_parse_atom(self, text: str) -> list[dict[str, Any]]:
        namespace = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(text)
        entries: list[dict[str, Any]] = []
        for entry in root.findall("atom:entry", namespace):
            entries.append(
                {
                    "title": entry.findtext("atom:title", default="", namespaces=namespace),
                    "authors": [
                        {"name": author.findtext("atom:name", default="", namespaces=namespace)}
                        for author in entry.findall("atom:author", namespace)
                    ],
                    "published": entry.findtext(
                        "atom:published",
                        default="",
                        namespaces=namespace,
                    ),
                    "summary": entry.findtext("atom:summary", default="", namespaces=namespace),
                    "arxiv_journal_ref": entry.findtext(
                        "arxiv:journal_ref",
                        default=None,
                        namespaces=namespace,
                    ),
                    "arxiv_primary_category": {
                        "term": self._element_attr(
                            entry.find("arxiv:primary_category", namespace),
                            "term",
                        )
                    },
                    "arxiv_doi": entry.findtext("arxiv:doi", default=None, namespaces=namespace),
                    "id": entry.findtext("atom:id", default="", namespaces=namespace),
                    "links": [
                        {"rel": link.get("rel"), "href": link.get("href")}
                        for link in entry.findall("atom:link", namespace)
                    ],
                }
            )
        return entries

    def _paper_from_entry(self, entry: dict[str, Any]) -> PaperResult:
        title = self._clean_text(entry.get("title", ""))
        abstract = self._clean_text(entry.get("summary", ""))
        arxiv_id = self._extract_arxiv_id(entry.get("id", ""))
        alternate_url = self._alternate_link(entry.get("links", []))
        journal_ref = entry.get("arxiv_journal_ref")
        primary_category = (entry.get("arxiv_primary_category") or {}).get("term")

        published = entry.get("published", "")
        year = int(published[:4]) if published[:4].isdigit() else None
        doi = entry.get("arxiv_doi")

        return PaperResult(
            title=title,
            authors=[
                author.get("name", "")
                for author in entry.get("authors", [])
                if author.get("name")
            ],
            year=year,
            venue=journal_ref or primary_category,
            abstract=abstract,
            doi=doi,
            arxiv_id=arxiv_id,
            url=alternate_url or entry.get("id", ""),
            citation_count=None,
            reference_count=0,
            source_api=self.name,
            sources=[self.name],
            verification=VerificationLevel.SINGLE_SOURCE,
            raw_response=dict(entry),
        )

    @staticmethod
    def _sort_by(params: SearchParams) -> str:
        if params.sort_by == "year":
            return "submittedDate"
        return "relevance"

    def _build_arxiv_query(self, query: str, params: SearchParams) -> str:
        """Convert a natural-language query into arXiv API query syntax."""
        if any(prefix in query for prefix in ["ti:", "abs:", "all:", "au:", "cat:"]):
            return query

        terms = self._extract_search_terms(query)
        if len(terms) == 1:
            return f'all:"{terms[0]}"'

        parts = [f'all:"{term}"' for term in terms]
        return " AND ".join(parts)

    def _extract_search_terms(self, query: str) -> list[str]:
        """Extract quoted phrases and keyword groups from a query string."""
        quoted_terms = re.findall(r'"([^"]+)"', query)
        remainder = re.sub(r'"[^"]+"', " ", query)
        bare_terms = [term for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\+\.]*", remainder) if term]

        if quoted_terms:
            return quoted_terms + bare_terms
        if len(bare_terms) <= 2:
            combined = " ".join(bare_terms).strip()
            return [combined] if combined else [query.strip()]
        return bare_terms

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _extract_arxiv_id(entry_id: str) -> str | None:
        if not entry_id:
            return None
        tail = entry_id.rstrip("/").rsplit("/", 1)[-1]
        return re.sub(r"v\d+$", "", tail)

    @staticmethod
    def _alternate_link(links: list[dict[str, Any]]) -> str | None:
        for link in links:
            if link.get("rel") == "alternate" and link.get("href"):
                return str(link["href"])
        return None

    @staticmethod
    def _retry_delay(response: httpx.Response, retries: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass
        return min(0.1 * (2** (retries - 1)), 1.0)

    @staticmethod
    def _element_attr(element: ET.Element | None, attr: str) -> str | None:
        if element is None:
            return None
        return element.get(attr)
