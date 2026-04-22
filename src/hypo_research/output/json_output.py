"""JSON output helpers for search results."""

from __future__ import annotations

import json
from pathlib import Path

from hypo_research.core.models import PaperResult, SurveyMeta


def write_search_output(
    output_dir: Path,
    meta: SurveyMeta,
    papers: list[PaperResult],
) -> None:
    """Write survey metadata, normalized results, and raw responses."""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    meta_payload = meta.model_dump(mode="json")
    results_payload = [
        paper.model_dump(mode="json", exclude={"raw_response"}) for paper in papers
    ]

    _write_json(output_dir / "meta.json", meta_payload)
    _write_json(output_dir / "results.json", results_payload)

    grouped: dict[str, list[dict]] = {source_name: [] for source_name in meta.sources_used}
    for paper in papers:
        grouped.setdefault(paper.source_api, []).append(paper.model_dump(mode="json"))

    for source_name, payload in grouped.items():
        raw_payload = {
            "source": source_name,
            "count": len(payload),
            "papers": payload,
        }
        _write_json(raw_dir / f"{source_name}.json", raw_payload)


def _write_json(path: Path, payload: dict | list[dict]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
