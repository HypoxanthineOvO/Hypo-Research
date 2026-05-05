"""Tests for PDF read artifacts and CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from hypo_research.read import extract_evidence_cards, ingest_pdf, outline_artifact


SAMPLE_PDF = Path("data/reviews/FRR/FRRPaper.pdf")


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "hypo-research", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_ingest_pdf_writes_artifact(tmp_path: Path) -> None:
    artifact = ingest_pdf(SAMPLE_PDF, tmp_path)

    artifact_path = tmp_path / "artifact.json"
    assert artifact_path.exists()
    assert artifact.source_path.endswith("FRRPaper.pdf")
    assert artifact.page_count > 0
    assert artifact.text_length > 0
    assert artifact.backend
    assert artifact.extraction_quality in {"low", "medium", "high"}


def test_outline_artifact_mentions_sections(tmp_path: Path) -> None:
    artifact = ingest_pdf(SAMPLE_PDF, tmp_path)
    outline = outline_artifact(tmp_path / "artifact.json")

    assert artifact.title in outline
    assert "Pages:" in outline
    assert "Extraction quality:" in outline


def test_read_cli_ingest_and_outline(tmp_path: Path) -> None:
    result = run_cli(["read", "ingest", str(SAMPLE_PDF), "--out", str(tmp_path)])
    assert result.returncode == 0
    assert "artifact.json" in result.stdout

    payload = json.loads((tmp_path / "artifact.json").read_text(encoding="utf-8"))
    assert payload["page_count"] > 0

    outline = run_cli(["read", "outline", str(tmp_path / "artifact.json")])
    assert outline.returncode == 0
    assert "Extraction quality:" in outline.stdout


def test_read_cli_ingest_directory_target(tmp_path: Path) -> None:
    paper_dir = tmp_path / "paper"
    paper_dir.mkdir()
    shutil.copy(SAMPLE_PDF, paper_dir / "paper.pdf")
    out = tmp_path / "out"

    result = run_cli(["read", "ingest", str(paper_dir), "--out", str(out)])

    assert result.returncode == 0
    assert (out / "artifact.json").exists()


def test_read_cli_ingest_zip_target(tmp_path: Path) -> None:
    archive = tmp_path / "paper.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.write(SAMPLE_PDF, "paper/paper.pdf")
    out = tmp_path / "out"

    result = run_cli(["read", "ingest", str(archive), "--out", str(out)])

    assert result.returncode == 0
    assert (out / "artifact.json").exists()


def test_extract_evidence_cards(tmp_path: Path) -> None:
    ingest_pdf(SAMPLE_PDF, tmp_path)
    result = extract_evidence_cards(tmp_path / "artifact.json", tmp_path / "cards")

    assert (tmp_path / "cards" / "cards.json").exists()
    assert (tmp_path / "cards" / "cards.md").exists()
    assert result.method_cards
    assert result.claim_cards
    assert result.agent_prompt


def test_read_cli_extract(tmp_path: Path) -> None:
    ingest_pdf(SAMPLE_PDF, tmp_path)
    out = tmp_path / "cards"
    result = run_cli(["read", "extract", str(tmp_path / "artifact.json"), "--out", str(out)])

    assert result.returncode == 0
    assert "cards.json" in result.stdout
    payload = json.loads((out / "cards.json").read_text(encoding="utf-8"))
    assert "method_cards" in payload
    assert "claim_cards" in payload
