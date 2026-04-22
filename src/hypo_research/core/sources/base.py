"""Abstract source interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from hypo_research.core.models import PaperResult, SearchParams


class BaseSource(ABC):
    """Abstract base class for paper search sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Source identifier, e.g. 'semantic_scholar'."""

    @abstractmethod
    async def search(self, params: SearchParams) -> list[PaperResult]:
        """Search for papers matching the given parameters."""

    @abstractmethod
    async def get_paper(self, paper_id: str) -> PaperResult | None:
        """Get a single paper by its source-specific ID."""

    @abstractmethod
    async def get_citations(
        self,
        paper_id: str,
        limit: int = 100,
    ) -> list[PaperResult]:
        """Get papers that cite this paper."""

    @abstractmethod
    async def get_references(
        self,
        paper_id: str,
        limit: int = 100,
    ) -> list[PaperResult]:
        """Get papers referenced by this paper."""

    async def close(self) -> None:
        """Cleanup resources such as HTTP clients."""
        return None
