"""Tests for venue profiles, severity grading, and venue-aware behavior."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest
import respx
from click.testing import CliRunner

from hypo_research.cli import main
from hypo_research.writing.check import render_check_report, run_check, submission_readiness
from hypo_research.writing.config import load_config_from_file
from hypo_research.writing.severity import Severity, resolve_severity
from hypo_research.writing.stats import extract_stats
from hypo_research.writing.venue import get_venue, list_venues
from hypo_research.writing.verify import VerifyStatus, verify_bib


def test_get_venue_ieee_journal() -> None:
    venue = get_venue("ieee_journal")
    assert venue.name == "ieee_journal"
    assert venue.display_name == "IEEE Journal"
    assert "[t]" in venue.accepted_float_placements


def test_get_venue_fallback_generic() -> None:
    venue = get_venue("nonexistent")
    assert venue.name == "generic"


def test_list_venues_contains_builtins() -> None:
    assert list_venues() == [
        "acm",
        "arxiv",
        "generic",
        "ieee_conference",
        "ieee_journal",
        "neurips",
        "thesis",
    ]


def test_resolve_severity_prefers_venue_then_config() -> None:
    venue = get_venue("ieee_journal")
    severity, source = resolve_severity("L04", Severity.WARNING, venue=venue)
    assert severity == Severity.INFO
    assert source == "ieee_journal"

    severity, source = resolve_severity(
        "L04",
        Severity.WARNING,
        venue=venue,
        config_overrides={"L04": "warning"},
    )
    assert severity == Severity.WARNING
    assert source == "config"


def test_ieee_journal_t_float_downgrades_to_info(tmp_path) -> None:
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"""\documentclass{article}
\begin{document}
\begin{figure}[t]
\caption{Overview}
\label{fig:overview}
\end{figure}
\end{document}
""",
        encoding="utf-8",
    )
    stats = extract_stats(tex, venue=get_venue("ieee_journal"))
    l04 = next(issue for issue in stats.issues if issue.rule == "L04")
    assert l04.severity == Severity.INFO
    assert l04.severity_source == "ieee_journal"
    assert hasattr(l04, "severity")


def test_generic_t_float_remains_warning(tmp_path) -> None:
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"""\documentclass{article}
\begin{document}
\begin{figure}[t]
\caption{Overview}
\label{fig:overview}
\end{figure}
\end{document}
""",
        encoding="utf-8",
    )
    stats = extract_stats(tex, venue=get_venue("generic"))
    l04 = next(issue for issue in stats.issues if issue.rule == "L04")
    assert l04.severity == Severity.WARNING


def test_ieee_journal_missing_doi_suppressed() -> None:
    stats = extract_stats(
        "tests/fixtures/lint_fixed.tex",
        bib_path="tests/fixtures/multifile/refs.bib",
        venue=get_venue("ieee_journal"),
        strict_doi=False,
    )
    assert not any(issue.rule == "L12" and "doi" in issue.message for issue in stats.issues)


def test_strict_doi_overrides_venue_suppression() -> None:
    stats = extract_stats(
        "tests/fixtures/lint_fixed.tex",
        bib_path="tests/fixtures/multifile/refs.bib",
        venue=get_venue("ieee_journal"),
        strict_doi=True,
    )
    assert any(issue.rule == "L12" and "doi" in issue.message for issue in stats.issues)


@pytest.mark.asyncio
@respx.mock
async def test_verify_generic_missing_doi_warns(tmp_path) -> None:
    bib = tmp_path / "refs.bib"
    bib.write_text(
        """@article{cinnamon2025,
  title={Cinnamon: A Large-Scale Hardware Accelerator for Fully Homomorphic Encryption},
  author={Samardzic, Nikola and others},
  journal={ASPLOS},
  year={2025}
}
""",
        encoding="utf-8",
    )
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json={"total": 1, "data": [{
            "paperId": "cinnamon",
            "title": "Cinnamon: A Large-Scale Hardware Accelerator for Fully Homomorphic Encryption",
            "year": 2025,
            "venue": "ASPLOS",
            "authors": [{"name": "Nikola Samardzic"}],
            "externalIds": {"DOI": "10.1145/3582016.3582066"},
            "citationCount": 10,
        }]})
    )
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})
    )
    report = await verify_bib(bib, venue=get_venue("generic"))
    assert report.results[0].status == VerifyStatus.VERIFIED
    assert report.results[0].severity == Severity.WARNING
    assert "missing DOI" in (report.results[0].notes or "")


@pytest.mark.asyncio
@respx.mock
async def test_verify_ieee_journal_missing_doi_skipped(tmp_path) -> None:
    bib = tmp_path / "refs.bib"
    bib.write_text(
        """@article{cinnamon2025,
  title={Cinnamon: A Large-Scale Hardware Accelerator for Fully Homomorphic Encryption},
  author={Samardzic, Nikola and others},
  journal={ASPLOS},
  year={2025}
}
""",
        encoding="utf-8",
    )
    respx.get("https://api.semanticscholar.org/graph/v1/paper/search").mock(
        return_value=httpx.Response(200, json={"total": 1, "data": [{
            "paperId": "cinnamon",
            "title": "Cinnamon: A Large-Scale Hardware Accelerator for Fully Homomorphic Encryption",
            "year": 2025,
            "venue": "ASPLOS",
            "authors": [{"name": "Nikola Samardzic"}],
            "externalIds": {"DOI": "10.1145/3582016.3582066"},
            "citationCount": 10,
        }]})
    )
    respx.get("https://api.openalex.org/works").mock(
        return_value=httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})
    )
    report = await verify_bib(bib, venue=get_venue("ieee_journal"))
    assert report.results[0].status == VerifyStatus.VERIFIED
    assert report.results[0].severity == Severity.INFO


def test_check_report_includes_venue_and_bottom_line(tmp_path) -> None:
    src = tmp_path / "paper.tex"
    shutil.copy("tests/fixtures/fix_buggy.tex", src)
    report = run_check(src, verify=False, save_report=False, venue=get_venue("ieee_journal"))
    rendered = render_check_report(report)
    assert "Venue: IEEE Journal" in rendered
    assert "Bottom Line:" in rendered


def test_check_json_contains_venue_and_submission_readiness(tmp_path) -> None:
    src = tmp_path / "paper.tex"
    shutil.copy("tests/fixtures/fix_buggy.tex", src)
    report = run_check(src, verify=False, save_report=False, venue=get_venue("ieee_journal"))
    payload = report.to_payload()
    assert payload["venue"] == "ieee_journal"
    assert payload["venue_display"] == "IEEE Journal"
    assert "summary" in payload
    assert payload["submission_readiness"] in {"fail", "review", "pass"}


def test_submission_readiness_logic() -> None:
    src = Path("tests/fixtures/fix_buggy.tex")
    report = run_check(src, no_fix=True, verify=False, save_report=False, venue=get_venue("generic"))
    assert submission_readiness(report) in {"fail", "review"}


def test_cli_invalid_venue_errors() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["lint", "--venue", "bad-venue", "tests/fixtures/lint_buggy.tex"])
    assert result.exit_code != 0
    assert "Available:" in result.output


def test_init_template_contains_venue(tmp_path) -> None:
    config = tmp_path / ".hypo-research.toml"
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    content = config.read_text(encoding="utf-8")
    assert 'venue = "generic"' in content
    assert "venue options:" in content


def test_check_cli_json_includes_venue_fields(tmp_path) -> None:
    src = tmp_path / "paper.tex"
    shutil.copy("tests/fixtures/fix_buggy.tex", src)
    result = subprocess.run(
        ["uv", "run", "hypo-research", "check", "--json", "--no-verify", "--no-save", "--venue", "ieee_journal", str(src)],
        capture_output=True,
        text=True,
        check=False,
    )
    data = json.loads(result.stdout)
    assert data["venue"] == "ieee_journal"
    assert data["venue_display"] == "IEEE Journal"


def test_cli_venue_overrides_config(tmp_path) -> None:
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"""\documentclass{article}
\begin{document}
\begin{figure}[t]
\caption{Overview}
\label{fig:overview}
\end{figure}
\end{document}
""",
        encoding="utf-8",
    )
    (tmp_path / ".hypo-research.toml").write_text('[project]\nvenue = "ieee_journal"\n', encoding="utf-8")
    result = subprocess.run(
        ["uv", "run", "hypo-research", "lint", "--venue", "generic", str(tex)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "warning" in result.stdout.lower()
