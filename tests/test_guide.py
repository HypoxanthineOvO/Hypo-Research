"""Tests for the natural-language guide router."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from hypo_research.cli import main
from hypo_research.core.models import PaperResult, SearchParams, SearchResult, SurveyMeta

from hypo_research.guide import route_request


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "hypo-research", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_route_paper_check_request() -> None:
    route = route_request("我论文快投了，帮我检查一下")

    assert route.category == "check"
    assert route.scenario == "paper_check"
    assert route.confidence >= 0.7
    assert any("check" in command for command in route.suggested_commands)
    assert route.follow_up_questions


def test_route_read_pdf_request() -> None:
    route = route_request("please read this PDF and explain the method")

    assert route.category == "read"
    assert route.scenario == "paper_reading"
    assert any("read ingest" in command for command in route.suggested_commands)


def test_route_review_request() -> None:
    route = route_request("帮我模拟审稿，按 ICML 标准")

    assert route.category == "review"
    assert route.scenario == "simulated_review"
    assert any("review" in command for command in route.suggested_commands)


def test_guide_cli_outputs_route() -> None:
    result = run_cli(["guide", "我论文快投了，帮我检查一下"])

    assert result.returncode == 0
    assert "Route: check" in result.stdout
    assert "Suggested commands" in result.stdout


def test_guide_cli_help_is_registered() -> None:
    result = run_cli(["--help"])

    assert result.returncode == 0
    assert "guide" in result.stdout


def test_guide_execute_check_runs_full_check(tmp_path: Path) -> None:
    src = tmp_path / "paper.tex"
    src.write_text(
        r"""
\documentclass{article}
\begin{document}
\section{Intro}
Text.
\end{document}
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        main,
        ["guide", "我论文快投了，帮我检查一下", "--execute", "--target", str(src)],
    )

    assert result.exit_code == 0
    assert "Executing: hypo-research check" in result.output
    assert "Check Report" in result.output


def test_guide_execute_check_runs_on_zip_target(tmp_path: Path) -> None:
    archive = tmp_path / "paper.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(
            "paper/main.tex",
            r"""
\documentclass{article}
\begin{document}
\section{Intro}
Text.
\end{document}
""",
        )

    result = CliRunner().invoke(
        main,
        ["guide", "我论文快投了，帮我检查一下", "--execute", "--target", str(archive)],
    )

    assert result.exit_code == 0
    assert "Executing: hypo-research check" in result.output
    assert "Check Report" in result.output


def test_guide_execute_read_runs_ingest_and_outline(tmp_path: Path) -> None:
    out = tmp_path / "read"
    result = CliRunner().invoke(
        main,
        [
            "guide",
            "please read this PDF and explain the method",
            "--execute",
            "--target",
            "data/reviews/FRR/FRRPaper.pdf",
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert "Executing: hypo-research read ingest" in result.output
    assert "Executing: hypo-research read outline" in result.output
    assert (out / "artifact.json").exists()
    assert "Extraction quality:" in result.output


def test_guide_execute_review_without_target_suggests_command() -> None:
    result = CliRunner().invoke(
        main,
        ["guide", "帮我模拟审稿，按 ICML 标准", "--execute"],
    )

    assert result.exit_code == 0
    assert "Cannot execute safely" in result.output
    assert "hypo-research review <paper> --venue <venue> --panel full" in result.output


def test_guide_execute_search_with_query_runs_safe_search(tmp_path: Path) -> None:
    output_dir = tmp_path / "survey"

    async def fake_run_single_search(*args, **kwargs):
        paper = PaperResult(
            title="Guide Search Result",
            authors=["Alice"],
            year=2026,
            url="https://example.com/paper",
            citation_count=1,
            source_api="semantic_scholar",
            sources=["semantic_scholar"],
        )
        meta = SurveyMeta(
            query="transformer architecture",
            params=SearchParams(query="transformer architecture"),
            sources_used=["semantic_scholar"],
            output_dir=str(output_dir),
            total_results=1,
        )
        return SearchResult(meta=meta, papers=[paper], output_dir=str(output_dir))

    with patch("hypo_research.cli._run_single_search", side_effect=fake_run_single_search):
        result = CliRunner().invoke(
            main,
            [
                "guide",
                "search transformer architecture literature",
                "--execute",
                "--query",
                "transformer architecture",
                "--out",
                str(output_dir),
            ],
        )

    assert result.exit_code == 0
    assert "Executing: hypo-research search" in result.output
