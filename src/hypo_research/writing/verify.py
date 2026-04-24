"""Citation verification against Semantic Scholar and OpenAlex."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from hypo_research.core.models import PaperResult, SearchParams
from hypo_research.core.sources import OpenAlexSource, RateLimitError, SemanticScholarSource, SourceError
from hypo_research.writing.bib_parser import BibEntryInfo, parse_bib, parse_bib_files
from hypo_research.writing.project import TexProject
from hypo_research.writing.stats import extract_stats


logger = logging.getLogger(__name__)


NON_INDEXED_TYPES = {
    "techreport",
    "misc",
    "manual",
    "book",
    "booklet",
    "inbook",
    "incollection",
    "phdthesis",
    "mastersthesis",
    "unpublished",
    "online",
}
INDEXED_TYPES = {"article", "inproceedings", "conference"}


class VerifyStatus(str, Enum):
    """Verification result states."""

    VERIFIED = "verified"
    MISMATCH = "mismatch"
    NOT_FOUND = "not_found"
    UNCERTAIN = "uncertain"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class VerificationResult:
    """Verification result for a single BibTeX entry."""

    bib_key: str
    status: VerifyStatus
    local_title: str
    local_year: str
    local_doi: str | None
    local_authors: str | None
    local_venue: str | None
    remote_title: str | None
    remote_year: int | None
    remote_doi: str | None
    remote_authors: list[str] | None
    remote_venue: str | None
    remote_citation_count: int | None
    remote_source: str | None
    mismatches: list[str]
    title_similarity: float | None
    notes: str | None


@dataclass
class VerifyReport:
    """Aggregated citation verification report."""

    total: int
    verified: int
    mismatch: int
    not_found: int
    uncertain: int
    rate_limited: int
    error: int
    results: list[VerificationResult]
    skipped: list[str]

    def to_payload(self) -> dict[str, Any]:
        """Convert report to a JSON-serializable dictionary."""
        return {
            "summary": {
                "total": self.total,
                "verified": self.verified,
                "mismatch": self.mismatch,
                "not_found": self.not_found,
                "uncertain": self.uncertain,
                "rate_limited": self.rate_limited,
                "error": self.error,
                "skipped": len(self.skipped),
            },
            "results": [asdict(result) for result in self.results],
            "skipped": self.skipped,
        }

    def to_json(self) -> str:
        """Serialize report as readable JSON."""
        return json.dumps(self.to_payload(), ensure_ascii=False, indent=2)

    def to_markdown(self) -> str:
        """Render report as a Markdown summary."""
        lines = [
            "# Citation Verification Report",
            "",
            "## Summary",
            "",
            "| Status | Count |",
            "|--------|-------|",
            f"| ✅ Verified | {self.verified} |",
            f"| ⚠️ Mismatch | {self.mismatch} |",
            f"| ❌ Not Found | {self.not_found} |",
            f"| ❓ Uncertain | {self.uncertain} |",
            f"| ⏳ Rate Limited | {self.rate_limited} |",
            f"| 💥 Error | {self.error} |",
            "",
        ]

        problem_results = [
            result
            for result in self.results
            if result.status in {
                VerifyStatus.MISMATCH,
                VerifyStatus.NOT_FOUND,
                VerifyStatus.UNCERTAIN,
                VerifyStatus.RATE_LIMITED,
                VerifyStatus.ERROR,
            }
        ]
        if problem_results:
            lines.extend(["## Issues", ""])
            for result in problem_results:
                icon = {
                    VerifyStatus.MISMATCH: "⚠️",
                    VerifyStatus.NOT_FOUND: "❌",
                    VerifyStatus.UNCERTAIN: "❓",
                    VerifyStatus.RATE_LIMITED: "⏳",
                    VerifyStatus.ERROR: "💥",
                }.get(result.status, "•")
                lines.append(f"### {icon} {result.status.replace('_', ' ').title()}: {result.bib_key}")
                lines.append(
                    f"- **Local:** {result.local_title or 'N/A'} "
                    f"(year={result.local_year or 'N/A'}, venue={result.local_venue or 'N/A'})"
                )
                if result.remote_title:
                    lines.append(
                        f"- **Remote:** {result.remote_title} "
                        f"(year={result.remote_year or 'N/A'}, venue={result.remote_venue or 'N/A'})"
                    )
                if result.mismatches:
                    for mismatch in result.mismatches:
                        lines.append(f"- **Issue:** {mismatch}")
                if result.notes:
                    lines.append(f"- **Note:** {result.notes}")
                lines.append("")

        lines.extend(
            [
                "## All Results",
                "",
                "| Key | Status | Title (truncated) | Year | Source |",
                "|-----|--------|--------------------|------|--------|",
            ]
        )
        for result in self.results:
            status_icon = {
                VerifyStatus.VERIFIED: "✅",
                VerifyStatus.MISMATCH: "⚠️",
                VerifyStatus.NOT_FOUND: "❌",
                VerifyStatus.UNCERTAIN: "❓",
                VerifyStatus.RATE_LIMITED: "⏳",
                VerifyStatus.ERROR: "💥",
            }.get(result.status, "•")
            year_display = result.local_year or "—"
            if result.remote_year is not None and str(result.remote_year) != year_display:
                year_display = f"{year_display}→{result.remote_year}"
            lines.append(
                "| {key} | {status} | {title} | {year} | {source} |".format(
                    key=result.bib_key,
                    status=status_icon,
                    title=_truncate_markdown(result.local_title, 32),
                    year=year_display,
                    source=result.remote_source or "—",
                )
            )
        if self.skipped:
            lines.extend(
                [
                    "",
                    "## Skipped",
                    "",
                    ", ".join(self.skipped),
                ]
            )
        return "\n".join(lines).rstrip() + "\n"


_TITLE_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "for",
    "of",
    "on",
    "in",
    "with",
    "to",
    "by",
}
_TITLE_EXPANSIONS = {
    "fhe": ["fully", "homomorphic", "encryption"],
    "llm": ["large", "language", "model"],
    "gpu": ["graphics", "processing", "unit"],
    "fpga": ["field", "programmable", "gate", "array"],
    "ntt": ["number", "theoretic", "transform"],
}


async def verify_bib(
    bib_path: str | Path | None = None,
    *,
    bib_paths: list[str | Path] | None = None,
    tex_path: str | Path | None = None,
    project: TexProject | None = None,
    keys: list[str] | None = None,
    skip_keys: list[str] | None = None,
    s2_api_key: str | None = None,
    timeout: int = 30,
    max_concurrent: int | None = None,
    max_requests_per_second: float | None = None,
    s2_source: SemanticScholarSource | None = None,
    openalex_source: OpenAlexSource | None = None,
    progress_callback: Any | None = None,
) -> VerifyReport:
    """Verify BibTeX entries against Semantic Scholar and OpenAlex."""
    resolved_bib_paths = _resolve_verify_bib_paths(
        bib_path=bib_path,
        bib_paths=bib_paths,
        project=project,
    )
    if not resolved_bib_paths:
        raise ValueError("No BibTeX files provided or discovered for verification")

    existing_bib_paths = [path for path in resolved_bib_paths if path.exists()]
    if len(existing_bib_paths) > 1:
        entries = parse_bib_files(existing_bib_paths)
    elif existing_bib_paths:
        entries = parse_bib(existing_bib_paths[0].as_posix())
    else:
        entries = []
    selected_entries, skipped = _select_entries(
        entries,
        tex_path=tex_path,
        project=project,
        keys=keys,
        skip_keys=skip_keys,
    )

    owns_s2 = s2_source is None
    owns_openalex = openalex_source is None
    semantic_scholar = s2_source or SemanticScholarSource(
        api_key=s2_api_key,
        timeout=timeout,
        max_requests_per_second=max_requests_per_second or 1.0,
    )
    openalex = openalex_source or OpenAlexSource(timeout=timeout)
    max_concurrency = (
        max_concurrent
        if max_concurrent is not None
        else 1
    )
    semaphore = asyncio.Semaphore(max_concurrency)

    async def verify_single(entry: BibEntryInfo) -> VerificationResult:
        async with semaphore:
            result = await _verify_entry(entry, semantic_scholar, openalex)
            if progress_callback is not None:
                progress_callback(result)
            return result

    try:
        results = await asyncio.gather(*(verify_single(entry) for entry in selected_entries))
    finally:
        close_tasks = []
        if owns_s2:
            close_tasks.append(semantic_scholar.close())
        if owns_openalex:
            close_tasks.append(openalex.close())
        if close_tasks:
            await asyncio.gather(*close_tasks)

    return VerifyReport(
        total=len(selected_entries),
        verified=sum(1 for result in results if result.status == VerifyStatus.VERIFIED),
        mismatch=sum(1 for result in results if result.status == VerifyStatus.MISMATCH),
        not_found=sum(1 for result in results if result.status == VerifyStatus.NOT_FOUND),
        uncertain=sum(1 for result in results if result.status == VerifyStatus.UNCERTAIN),
        rate_limited=sum(1 for result in results if result.status == VerifyStatus.RATE_LIMITED),
        error=sum(1 for result in results if result.status == VerifyStatus.ERROR),
        results=sorted(results, key=lambda result: result.bib_key),
        skipped=sorted(skipped),
    )


def title_similarity(a: str, b: str) -> float:
    """Compute word-level Jaccard similarity for paper titles."""
    left_tokens = set(_normalize_title_tokens(a))
    right_tokens = set(_normalize_title_tokens(b))
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(intersection) / len(union)


async def _verify_entry(
    entry: BibEntryInfo,
    semantic_scholar: SemanticScholarSource,
    openalex: OpenAlexSource,
) -> VerificationResult:
    local_title = entry.fields.get("title", "")
    local_year = entry.fields.get("year", "")
    local_doi = _normalize_doi(entry.fields.get("doi"))
    local_authors = entry.fields.get("author")
    local_venue = entry.fields.get("booktitle") or entry.fields.get("journal")

    if not local_title and not local_doi:
        status, notes = _missing_remote_status(
            entry=entry,
            local_title=local_title,
            local_authors=local_authors,
            rate_limited=False,
        )
        return VerificationResult(
            bib_key=entry.key,
            status=status,
            local_title=local_title,
            local_year=local_year,
            local_doi=local_doi,
            local_authors=local_authors,
            local_venue=local_venue,
            remote_title=None,
            remote_year=None,
            remote_doi=None,
            remote_authors=None,
            remote_venue=None,
            remote_citation_count=None,
            remote_source=None,
            mismatches=[],
            title_similarity=None,
            notes=notes or "insufficient metadata",
        )

    try:
        remote = await _lookup_remote_record(
            entry=entry,
            semantic_scholar=semantic_scholar,
            openalex=openalex,
            local_doi=local_doi,
            local_title=local_title,
        )
    except SourceError as exc:
        return VerificationResult(
            bib_key=entry.key,
            status=VerifyStatus.ERROR,
            local_title=local_title,
            local_year=local_year,
            local_doi=local_doi,
            local_authors=local_authors,
            local_venue=local_venue,
            remote_title=None,
            remote_year=None,
            remote_doi=None,
            remote_authors=None,
            remote_venue=None,
            remote_citation_count=None,
            remote_source=None,
            mismatches=[],
            title_similarity=None,
            notes=str(exc),
        )

    if remote.remote is None:
        status, notes = _missing_remote_status(
            entry=entry,
            local_title=local_title,
            local_authors=local_authors,
            rate_limited=remote.rate_limited,
        )
        return VerificationResult(
            bib_key=entry.key,
            status=status,
            local_title=local_title,
            local_year=local_year,
            local_doi=local_doi,
            local_authors=local_authors,
            local_venue=local_venue,
            remote_title=None,
            remote_year=None,
            remote_doi=None,
            remote_authors=None,
            remote_venue=None,
            remote_citation_count=None,
            remote_source=None,
            mismatches=[],
            title_similarity=None,
            notes=notes,
        )

    similarity = title_similarity(local_title, remote.remote.title) if local_title else None
    mismatches: list[str] = []
    notes: str | None = None

    if local_title and similarity is not None and similarity < 0.8:
        mismatches.append(
            f"title similarity below threshold: local='{local_title}', remote='{remote.remote.title}'"
        )

    if local_year and remote.remote.year is not None:
        try:
            local_year_int = int(local_year)
        except ValueError:
            mismatches.append(f"year: local={local_year}, remote={remote.remote.year}")
        else:
            if abs(local_year_int - remote.remote.year) > 1:
                mismatches.append(f"year: local={local_year_int}, remote={remote.remote.year}")

    if local_doi and remote.remote.doi and local_doi.lower() != remote.remote.doi.lower():
        mismatches.append(f"doi: local={local_doi}, remote={remote.remote.doi}")

    if local_authors and remote.remote.authors and not _authors_match(local_authors, remote.remote.authors):
        mismatches.append(
            f"authors: local first-author='{_first_author_surname(local_authors)}', "
            f"remote='{', '.join(remote.remote.authors[:3])}'"
        )

    if local_venue and remote.remote.venue and not _venues_match(local_venue, remote.remote.venue):
        mismatches.append(f"venue: local={local_venue}, remote={remote.remote.venue}")

    status = VerifyStatus.VERIFIED if not mismatches else VerifyStatus.MISMATCH
    if status == VerifyStatus.MISMATCH and any(mismatch.startswith("year:") for mismatch in mismatches):
        notes = (
            f"Year discrepancy: local .bib says {local_year}, "
            f"but remote metadata reports {remote.remote.year}"
        )

    return VerificationResult(
        bib_key=entry.key,
        status=status,
        local_title=local_title,
        local_year=local_year,
        local_doi=local_doi,
        local_authors=local_authors,
        local_venue=local_venue,
        remote_title=remote.remote.title,
        remote_year=remote.remote.year,
        remote_doi=remote.remote.doi,
        remote_authors=remote.remote.authors or None,
        remote_venue=remote.remote.venue,
        remote_citation_count=remote.remote.citation_count,
        remote_source=remote.remote.source,
        mismatches=mismatches,
        title_similarity=similarity,
        notes=notes,
    )


@dataclass
class _RemoteRecord:
    title: str
    year: int | None
    doi: str | None
    authors: list[str]
    venue: str | None
    citation_count: int | None
    source: str


@dataclass
class _LookupResult:
    remote: _RemoteRecord | None
    rate_limited: bool = False


async def _lookup_remote_record(
    entry: BibEntryInfo,
    semantic_scholar: SemanticScholarSource,
    openalex: OpenAlexSource,
    local_doi: str | None,
    local_title: str,
) -> _LookupResult:
    s2_result: PaperResult | None = None
    openalex_result: PaperResult | None = None
    s2_rate_limited = False

    if local_doi:
        s2_identifier = f"DOI:{local_doi}"
        openalex_identifier = f"https://doi.org/{local_doi}"
        s2_response, openalex_response = await asyncio.gather(
            semantic_scholar.get_paper(s2_identifier),
            openalex.get_paper(openalex_identifier),
            return_exceptions=True,
        )
        s2_result, s2_rate_limited = _unwrap_remote_response(s2_response)
        openalex_result, _ = _unwrap_remote_response(openalex_response)
        if s2_result is not None and s2_result.doi and _normalize_doi(s2_result.doi) != local_doi:
            s2_result = None
        if (
            openalex_result is not None
            and openalex_result.doi
            and _normalize_doi(openalex_result.doi) != local_doi
        ):
            openalex_result = None
    else:
        try:
            s2_result = await _search_best_match(semantic_scholar, local_title)
        except RateLimitError:
            s2_rate_limited = True
            s2_result = None
        openalex_result = await _search_best_match(openalex, local_title)

    if s2_result is None and openalex_result is None:
        return _LookupResult(remote=None, rate_limited=s2_rate_limited)

    source = (
        "both"
        if s2_result is not None and openalex_result is not None
        else ("s2" if s2_result is not None else "openalex")
    )
    candidates = [candidate for candidate in [s2_result, openalex_result] if candidate is not None]
    primary = max(
        candidates,
        key=lambda candidate: _remote_candidate_score(
            candidate,
            local_title=local_title,
            local_doi=local_doi,
        ),
    )
    secondary = next((candidate for candidate in candidates if candidate is not primary), None)

    citation_count = max(
        [
            count
            for count in [primary.citation_count, secondary.citation_count if secondary else None]
            if count is not None
        ],
        default=None,
    )

    return _LookupResult(
        remote=_RemoteRecord(
            title=primary.title,
            year=primary.year,
            doi=primary.doi or (secondary.doi if secondary else None),
            authors=primary.authors or (secondary.authors if secondary else []),
            venue=primary.venue or (secondary.venue if secondary else None),
            citation_count=citation_count,
            source=source,
        ),
        rate_limited=s2_rate_limited,
    )
async def _search_best_match(source: Any, query: str) -> PaperResult | None:
    results = await source.search(
        SearchParams(query=query, max_results=5, sort_by="citation_count")
    )
    best: tuple[float, PaperResult] | None = None
    for result in results:
        similarity = title_similarity(query, result.title)
        if best is None or similarity > best[0]:
            best = (similarity, result)
    if best is None or best[0] < 0.8:
        return None
    return best[1]


def _select_entries(
    entries: list[BibEntryInfo],
    *,
    tex_path: str | Path | None,
    project: TexProject | None,
    keys: list[str] | None,
    skip_keys: list[str] | None,
) -> tuple[list[BibEntryInfo], list[str]]:
    skipped: list[str] = []
    entries_by_key = {entry.key: entry for entry in entries}
    selected_keys: set[str] | None = None

    if project is not None or tex_path is not None:
        project_tex_path = (
            Path(tex_path)
            if tex_path is not None
            else (project.root_file if project is not None else None)
        )
        assert project_tex_path is not None
        stats = extract_stats(project_tex_path, project=project)
        cited_keys = {citation.key for citation in stats.citations}
        selected_keys = cited_keys if selected_keys is None else selected_keys & cited_keys

    if keys is not None:
        requested_keys = {key.strip() for key in keys if key.strip()}
        selected_keys = requested_keys if selected_keys is None else selected_keys & requested_keys
    if skip_keys is not None:
        skip_key_set = {key.strip() for key in skip_keys if key.strip()}
        if selected_keys is None:
            selected_keys = {entry.key for entry in entries} - skip_key_set
        else:
            selected_keys -= skip_key_set

    selected_entries = entries
    if selected_keys is not None:
        selected_entries = [entry for entry in entries if entry.key in selected_keys]
        skipped.extend(entry.key for entry in entries if entry.key not in selected_keys)

    return selected_entries, list(dict.fromkeys(skipped))


def _resolve_verify_bib_paths(
    *,
    bib_path: str | Path | None,
    bib_paths: list[str | Path] | None,
    project: TexProject | None,
) -> list[Path]:
    if bib_paths:
        return [Path(path) for path in bib_paths]
    if bib_path is not None:
        return [Path(bib_path)]
    if project is not None:
        return list(project.bib_files)
    return []


def _normalize_title_tokens(value: str) -> list[str]:
    cleaned = re.sub(r"[{}\\$~]", " ", value.lower())
    cleaned = re.sub(r"[^a-z0-9\s:-]", " ", cleaned)
    tokens: list[str] = []
    for token in cleaned.replace(":", " ").split():
        if not token or token in _TITLE_STOPWORDS:
            continue
        tokens.extend(_TITLE_EXPANSIONS.get(token, [token]))
    return tokens


def _normalize_doi(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    cleaned = cleaned.removeprefix("https://doi.org/")
    cleaned = cleaned.removeprefix("http://doi.org/")
    cleaned = cleaned.removeprefix("http://dx.doi.org/")
    cleaned = cleaned.removeprefix("doi:")
    return cleaned or None


def _authors_match(local_authors: str, remote_authors: list[str]) -> bool:
    local_surname = _first_author_surname(local_authors)
    remote_surnames = {_author_surname(author) for author in remote_authors}
    return bool(local_surname) and local_surname in remote_surnames


def _first_author_surname(local_authors: str) -> str:
    first_author = local_authors.split(" and ")[0].strip()
    return _author_surname(first_author)


def _author_surname(author: str) -> str:
    cleaned = re.sub(r"[{}]", "", author).strip().lower()
    if "," in cleaned:
        return cleaned.split(",", 1)[0].strip()
    parts = [part for part in cleaned.split() if part]
    return parts[-1] if parts else ""


def _venues_match(local_venue: str, remote_venue: str) -> bool:
    local_norm = _normalize_venue(local_venue)
    remote_norm = _normalize_venue(remote_venue)
    if not local_norm or not remote_norm:
        return True
    if local_norm == remote_norm:
        return True
    if local_norm in remote_norm or remote_norm in local_norm:
        return True
    if _normalize_venue(_venue_acronym(remote_venue)) == local_norm:
        return True
    if re.fullmatch(r"[A-Z0-9-]{2,10}", local_venue.strip()):
        return True
    return False


def _normalize_venue(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    cleaned = re.sub(r"\b\d{2,4}\b", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _venue_acronym(value: str) -> str:
    stopwords = {
        "of",
        "the",
        "on",
        "for",
        "and",
        "in",
        "international",
        "conference",
        "proceedings",
        "symposium",
        "workshop",
    }
    tokens = [token for token in _normalize_venue(value).split() if token not in stopwords]
    return "".join(token[0] for token in tokens if token).upper()


def _truncate_markdown(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 3]}..."


def _unwrap_remote_response(
    response: PaperResult | None | Exception,
) -> tuple[PaperResult | None, bool]:
    if isinstance(response, Exception):
        if isinstance(response, RateLimitError):
            return None, True
        if isinstance(response, SourceError):
            raise response
        raise SourceError("verify", str(response))
    return response, False


def _missing_remote_status(
    *,
    entry: BibEntryInfo,
    local_title: str,
    local_authors: str | None,
    rate_limited: bool,
) -> tuple[VerifyStatus, str]:
    entry_type = (entry.entry_type or "").lower()
    if rate_limited:
        logger.warning("Verification deferred for %s due to Semantic Scholar rate limiting", entry.key)
        return (
            VerifyStatus.RATE_LIMITED,
            "verification deferred because Semantic Scholar rate limit was exhausted",
        )
    if entry_type in NON_INDEXED_TYPES:
        logger.info("Marking %s as uncertain because @%s is typically non-indexed", entry.key, entry_type)
        return (
            VerifyStatus.UNCERTAIN,
            f"uncertain: @{entry_type} not indexed by Semantic Scholar",
        )
    if entry_type in INDEXED_TYPES:
        return (
            VerifyStatus.NOT_FOUND,
            "No matching indexed paper found on Semantic Scholar or OpenAlex.",
        )
    if local_title.strip() and (local_authors or "").strip():
        descriptor = f"@{entry_type}" if entry_type else "unknown entry type"
        logger.info("Marking %s as uncertain because entry type is %s", entry.key, descriptor)
        return (
            VerifyStatus.UNCERTAIN,
            f"uncertain: {descriptor} may not be indexed by Semantic Scholar",
        )
    return (
        VerifyStatus.NOT_FOUND,
        "No matching indexed paper found on Semantic Scholar or OpenAlex.",
    )


def _remote_candidate_score(
    candidate: PaperResult,
    *,
    local_title: str,
    local_doi: str | None,
) -> tuple[int, float, int]:
    doi_match = 1 if local_doi and candidate.doi and _normalize_doi(candidate.doi) == local_doi else 0
    similarity = title_similarity(local_title, candidate.title) if local_title else 0.0
    citation_count = candidate.citation_count or 0
    return (doi_match, similarity, citation_count)
