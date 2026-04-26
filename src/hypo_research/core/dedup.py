"""Cross-source paper deduplication."""

from __future__ import annotations

import re
from collections.abc import Iterable

from hypo_research.core.models import PaperResult


class Deduplicator:
    """Cross-source paper deduplication."""

    _SOURCE_PRIORITY = {
        "semantic_scholar": 3,
        "openalex": 2,
        "arxiv": 1,
    }

    def dedup(
        self,
        papers: list[PaperResult],
    ) -> list[PaperResult]:
        """Deduplicate papers from multiple sources."""
        deduplicated: list[PaperResult] = []
        for paper in papers:
            matched_index = self._find_match_index(deduplicated, paper)
            if matched_index is None:
                deduplicated.append(paper)
                continue

            deduplicated[matched_index] = self._merge_records(
                deduplicated[matched_index],
                paper,
            )

        return deduplicated

    def _find_match_index(
        self,
        existing: list[PaperResult],
        candidate: PaperResult,
    ) -> int | None:
        candidate_doi = self._normalize_doi(candidate.doi)
        candidate_title_key = self._title_author_year_key(candidate)
        candidate_title_tokens = self._title_word_set(candidate.title)

        for index, paper in enumerate(existing):
            if candidate_doi and candidate_doi == self._normalize_doi(paper.doi):
                return index

            if candidate_title_key is not None and candidate_title_key == self._title_author_year_key(paper):
                return index

            if (
                candidate.year is not None
                and candidate.year == paper.year
                and self._jaccard_similarity(
                    candidate_title_tokens,
                    self._title_word_set(paper.title),
                )
                > 0.85
            ):
                return index

        return None

    def _merge_records(self, left: PaperResult, right: PaperResult) -> PaperResult:
        primary, secondary = self._pick_primary(left, right)

        primary.sources = self._merge_unique(primary.sources, secondary.sources)
        primary.matched_queries = self._merge_optional_lists(
            primary.matched_queries,
            secondary.matched_queries,
        )

        if not primary.doi and secondary.doi:
            primary.doi = secondary.doi
        if not primary.s2_paper_id and secondary.s2_paper_id:
            primary.s2_paper_id = secondary.s2_paper_id
        if not primary.arxiv_id and secondary.arxiv_id:
            primary.arxiv_id = secondary.arxiv_id
        if not primary.openalex_id and secondary.openalex_id:
            primary.openalex_id = secondary.openalex_id
        if self._is_better_text(secondary.abstract, primary.abstract):
            primary.abstract = secondary.abstract
        if not primary.venue and secondary.venue:
            primary.venue = secondary.venue
        if primary.year is None and secondary.year is not None:
            primary.year = secondary.year
        if not primary.url and secondary.url:
            primary.url = secondary.url
        if not primary.authors and secondary.authors:
            primary.authors = secondary.authors
        if not primary.title and secondary.title:
            primary.title = secondary.title
        if (
            secondary.citation_count is not None
            and (
                primary.citation_count is None
                or secondary.citation_count > primary.citation_count
            )
        ):
            primary.citation_count = secondary.citation_count
        if (
            secondary.reference_count is not None
            and (
                primary.reference_count is None
                or secondary.reference_count > primary.reference_count
            )
        ):
            primary.reference_count = secondary.reference_count
        if primary.relevance_score is None and secondary.relevance_score is not None:
            primary.relevance_score = secondary.relevance_score
        if not primary.relevance_reason and secondary.relevance_reason:
            primary.relevance_reason = secondary.relevance_reason

        return primary

    def _pick_primary(
        self,
        left: PaperResult,
        right: PaperResult,
    ) -> tuple[PaperResult, PaperResult]:
        left_score = self._record_score(left)
        right_score = self._record_score(right)
        if left_score >= right_score:
            return left, right
        return right, left

    def _record_score(self, paper: PaperResult) -> tuple[int, int]:
        priority = self._SOURCE_PRIORITY.get(paper.source_api, 0)
        richness = sum(
            [
                1 if paper.title else 0,
                1 if paper.abstract else 0,
                1 if paper.venue else 0,
                1 if paper.doi else 0,
                1 if paper.s2_paper_id else 0,
                1 if paper.arxiv_id else 0,
                1 if paper.openalex_id else 0,
                1 if paper.citation_count is not None else 0,
                1 if paper.reference_count is not None else 0,
                len(paper.authors),
            ]
        )
        return priority, richness

    @staticmethod
    def _normalize_doi(doi: str | None) -> str | None:
        if not doi:
            return None
        cleaned = doi.strip().lower()
        cleaned = cleaned.removeprefix("https://doi.org/")
        return cleaned

    @staticmethod
    def _normalize_title(title: str) -> str:
        lowered = title.lower()
        lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def _title_author_year_key(self, paper: PaperResult) -> tuple[str, str, int] | None:
        if not paper.title or not paper.authors or paper.year is None:
            return None
        return (
            self._normalize_title(paper.title),
            self._first_author_last_name(paper.authors[0]),
            paper.year,
        )

    @staticmethod
    def _first_author_last_name(author_name: str) -> str:
        parts = [part for part in author_name.lower().split() if part]
        if not parts:
            return ""
        return parts[-1]

    def _title_word_set(self, title: str) -> set[str]:
        normalized = self._normalize_title(title)
        return {word for word in normalized.split() if word}

    @staticmethod
    def _jaccard_similarity(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    @staticmethod
    def _merge_unique(left: Iterable[str], right: Iterable[str]) -> list[str]:
        return list(dict.fromkeys([*left, *right]))

    def _merge_optional_lists(
        self,
        left: list[str] | None,
        right: list[str] | None,
    ) -> list[str] | None:
        merged = self._merge_unique(left or [], right or [])
        return merged or None

    @staticmethod
    def _is_better_text(candidate: str | None, current: str | None) -> bool:
        """Return whether candidate is a more complete text field."""
        if not candidate:
            return False
        if not current:
            return True
        return len(candidate.strip()) > len(current.strip())
