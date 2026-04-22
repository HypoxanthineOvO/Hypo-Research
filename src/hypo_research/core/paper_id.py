"""Helpers for resolving user-provided paper identifiers."""

from __future__ import annotations

import re
from typing import TypedDict

from hypo_research.core.models import PaperResult, SearchParams
from hypo_research.core.sources.semantic_scholar import SemanticScholarSource


class ResolvedPaperId(TypedDict):
    """Resolved identifiers that can be used across source adapters."""

    s2_id: str | None
    openalex_id: str | None
    title: str | None


_DOI_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)?(10\.\d{4,9}/\S+)$", re.I)
_ARXIV_RE = re.compile(
    r"^(?:arxiv:)?([a-z\-]+/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?$",
    re.I,
)
_S2_ID_RE = re.compile(r"^[0-9a-f]{40}$", re.I)
_OPENALEX_ID_RE = re.compile(r"^(?:https?://openalex\.org/)?(W\d+)$", re.I)


def resolve_paper_id(identifier: str) -> ResolvedPaperId:
    """Normalize common paper identifier formats without network access."""
    cleaned = identifier.strip()
    lowered = cleaned.lower()
    if not cleaned:
        return {"s2_id": None, "openalex_id": None, "title": None}

    doi_match = _DOI_RE.match(cleaned)
    if doi_match:
        doi = doi_match.group(1)
        return {
            "s2_id": f"DOI:{doi}",
            "openalex_id": f"https://doi.org/{doi.lower()}",
            "title": None,
        }

    arxiv_match = _ARXIV_RE.match(cleaned)
    if arxiv_match:
        arxiv_id = arxiv_match.group(1)
        return {
            "s2_id": f"ARXIV:{arxiv_id}",
            "openalex_id": None,
            "title": None,
        }

    if _S2_ID_RE.match(cleaned):
        return {"s2_id": cleaned, "openalex_id": None, "title": None}

    openalex_match = _OPENALEX_ID_RE.match(cleaned)
    if openalex_match:
        return {
            "s2_id": None,
            "openalex_id": openalex_match.group(1).upper(),
            "title": None,
        }

    if lowered.startswith("doi:"):
        doi = cleaned[4:]
        return {
            "s2_id": f"DOI:{doi}",
            "openalex_id": f"https://doi.org/{doi.lower()}",
            "title": None,
        }

    return {"s2_id": None, "openalex_id": None, "title": cleaned}


async def resolve_paper_id_async(
    identifier: str,
    *,
    s2_source: SemanticScholarSource | None = None,
) -> ResolvedPaperId:
    """Resolve an identifier, using Semantic Scholar title search when needed."""
    resolved = resolve_paper_id(identifier)
    if resolved["title"] is None:
        return resolved

    owns_source = s2_source is None
    source = s2_source or SemanticScholarSource()
    try:
        candidates = await source.search(
            SearchParams(
                query=resolved["title"],
                max_results=5,
                sort_by="citation_count",
            )
        )
    finally:
        if owns_source:
            await source.close()

    best_match = _select_best_title_match(resolved["title"], candidates)
    if best_match is None:
        return resolved

    return {
        "s2_id": _best_s2_identifier(best_match),
        "openalex_id": best_match.openalex_id
        or (f"https://doi.org/{best_match.doi}" if best_match.doi else None),
        "title": best_match.title or resolved["title"],
    }


def _select_best_title_match(
    title_query: str,
    candidates: list[PaperResult],
) -> PaperResult | None:
    normalized_query = _normalize_title(title_query)
    exact_matches = [
        candidate
        for candidate in candidates
        if _normalize_title(candidate.title) == normalized_query
    ]
    if exact_matches:
        return exact_matches[0]

    substring_matches = [
        candidate
        for candidate in candidates
        if normalized_query in _normalize_title(candidate.title)
    ]
    if substring_matches:
        return substring_matches[0]

    return candidates[0] if candidates else None


def _normalize_title(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _best_s2_identifier(paper: PaperResult) -> str | None:
    if paper.s2_paper_id:
        return paper.s2_paper_id
    if paper.doi:
        return f"DOI:{paper.doi}"
    if paper.arxiv_id:
        return f"ARXIV:{paper.arxiv_id}"
    return None
