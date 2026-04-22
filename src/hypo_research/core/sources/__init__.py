"""Source adapters and source-specific exceptions."""


class SourceError(Exception):
    """Base exception for source errors."""

    def __init__(self, source: str, message: str, status_code: int | None = None):
        self.source = source
        self.status_code = status_code
        super().__init__(f"[{source}] {message}")


class RateLimitError(SourceError):
    """Raised when rate limit is exceeded and retries are exhausted."""


from .base import BaseSource
from .arxiv import ArxivSource
from .openalex import OpenAlexSource
from .semantic_scholar import SemanticScholarSource

__all__ = [
    "ArxivSource",
    "BaseSource",
    "OpenAlexSource",
    "RateLimitError",
    "SemanticScholarSource",
    "SourceError",
]
