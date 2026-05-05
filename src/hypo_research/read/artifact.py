"""Data models for paper reading artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ReadSection:
    """A rough section detected from extracted paper text."""

    title: str
    level: int
    start_line: int


@dataclass
class ReadImage:
    """An image object discovered in a PDF."""

    page: int
    index: int
    width: int | None = None
    height: int | None = None
    kind: str = "image"


@dataclass
class PaperReadArtifact:
    """Serializable v0 artifact for a parsed paper."""

    source_path: str
    source_hash: str
    backend: str
    title: str
    page_count: int
    text_length: int
    raw_text: str
    sections: list[ReadSection] = field(default_factory=list)
    images: list[ReadImage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extraction_quality: str = "low"

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
