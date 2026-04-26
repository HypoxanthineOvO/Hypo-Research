"""Tests for JSON survey output."""

from __future__ import annotations

import json
from pathlib import Path

from hypo_research.core.models import PaperResult, SearchParams, SurveyMeta
from hypo_research.output.json_output import write_search_output


def test_json_output_includes_full_abstract(tmp_path: Path) -> None:
    abstract = "A" * 800
    paper = PaperResult(
        title="Paper",
        authors=["Alice"],
        year=2024,
        venue="ICLR",
        abstract=abstract,
        url="https://example.com",
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
    )
    meta = SurveyMeta(
        query="test",
        params=SearchParams(query="test"),
        sources_used=["semantic_scholar"],
    )

    write_search_output(tmp_path, meta, [paper])

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert payload[0]["abstract"] == abstract
