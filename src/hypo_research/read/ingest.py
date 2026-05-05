"""PDF ingestion for PaperReadArtifact v0."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from hypo_research.read.artifact import PaperReadArtifact, ReadImage, ReadSection


RAW_TEXT_LIMIT = 250_000


def ingest_pdf(pdf_path: str | Path, output_dir: str | Path) -> PaperReadArtifact:
    """Ingest a PDF and write artifact.json under output_dir."""
    source = Path(pdf_path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    artifact = _ingest_with_pymupdf(source)
    if artifact is None:
        artifact = _ingest_with_poppler(source)

    (out / "artifact.json").write_text(
        json.dumps(artifact.to_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return artifact


def outline_artifact(artifact_path: str | Path) -> str:
    """Render a concise outline from artifact.json."""
    payload = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    lines = [
        f"Title: {payload.get('title') or 'Unknown'}",
        f"Source: {payload['source_path']}",
        f"Backend: {payload['backend']}",
        f"Pages: {payload['page_count']}",
        f"Text length: {payload['text_length']}",
        f"Images: {len(payload.get('images') or [])}",
        f"Extraction quality: {payload['extraction_quality']}",
        "",
        "Sections:",
    ]
    sections = payload.get("sections") or []
    if not sections:
        lines.append("- No rough sections detected")
    for section in sections[:20]:
        lines.append(f"- {section['title']} (line {section['start_line']})")
    return "\n".join(lines)


def _ingest_with_pymupdf(source: Path) -> PaperReadArtifact | None:
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception:
        return None

    document = fitz.open(source)
    page_texts = [page.get_text("text") for page in document]
    raw_text = "\n".join(page_texts)
    images: list[ReadImage] = []
    for page_index, page in enumerate(document, start=1):
        for image_index, image in enumerate(page.get_images(full=True), start=1):
            width = int(image[2]) if len(image) > 2 else None
            height = int(image[3]) if len(image) > 3 else None
            images.append(ReadImage(page=page_index, index=image_index, width=width, height=height))
    metadata = {key: value for key, value in (document.metadata or {}).items() if value}
    return _artifact(
        source=source,
        backend="pymupdf",
        raw_text=raw_text,
        page_count=document.page_count,
        images=images,
        metadata=metadata,
    )


def _ingest_with_poppler(source: Path) -> PaperReadArtifact:
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        raise RuntimeError("PDF ingestion requires PyMuPDF or system pdftotext")

    text_result = subprocess.run(
        [pdftotext, "-layout", str(source), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if text_result.returncode != 0:
        raise RuntimeError(text_result.stderr.strip() or "pdftotext failed")
    raw_text = text_result.stdout
    page_count = raw_text.count("\f") + 1 if raw_text else 0
    images = _poppler_images(source)
    return _artifact(
        source=source,
        backend="pdftotext",
        raw_text=raw_text,
        page_count=page_count,
        images=images,
        metadata={},
    )


def _poppler_images(source: Path) -> list[ReadImage]:
    pdfimages = shutil.which("pdfimages")
    if pdfimages is None:
        return []
    result = subprocess.run(
        [pdfimages, "-list", str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    images: list[ReadImage] = []
    for line in result.stdout.splitlines()[2:]:
        parts = line.split()
        if len(parts) < 4 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        width = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
        height = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None
        images.append(
            ReadImage(
                page=int(parts[0]),
                index=int(parts[1]),
                kind=parts[2],
                width=width,
                height=height,
            )
        )
    return images


def _artifact(
    *,
    source: Path,
    backend: str,
    raw_text: str,
    page_count: int,
    images: list[ReadImage],
    metadata: dict[str, Any],
) -> PaperReadArtifact:
    cleaned = raw_text[:RAW_TEXT_LIMIT]
    sections = _rough_sections(cleaned)
    title = _title_from_metadata_or_text(metadata, cleaned, source)
    quality = "high" if sections and images else "medium" if cleaned else "low"
    return PaperReadArtifact(
        source_path=source.as_posix(),
        source_hash=_sha256(source),
        backend=backend,
        title=title,
        page_count=page_count,
        text_length=len(raw_text),
        raw_text=cleaned,
        sections=sections,
        images=images,
        metadata=metadata,
        extraction_quality=quality,
    )


def _rough_sections(text: str) -> list[ReadSection]:
    sections: list[ReadSection] = []
    heading_re = re.compile(
        r"^\s*((?:[IVX]+\.|\d+(?:\.\d+)*\.?)\s+[A-Z][A-Za-z0-9 ,:/&()_-]{2,90}|[A-Z][A-Z ,:/&()_-]{4,90})\s*$"
    )
    for index, line in enumerate(text.splitlines(), start=1):
        title = " ".join(line.split())
        if heading_re.match(title):
            sections.append(ReadSection(title=title, level=1, start_line=index))
        if len(sections) >= 80:
            break
    return sections


def _title_from_metadata_or_text(metadata: dict[str, Any], text: str, source: Path) -> str:
    title = str(metadata.get("title") or "").strip()
    if title:
        return title
    for line in text.splitlines():
        cleaned = " ".join(line.split())
        if len(cleaned) >= 12 and not cleaned.isdigit():
            return cleaned[:200]
    return source.stem


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
