"""CLI tests for citation verification."""

from __future__ import annotations

import json

from click.testing import CliRunner

from hypo_research.cli import main
from hypo_research.writing.verify import VerificationResult, VerifyReport


def _sample_report(*, not_found: bool = False) -> VerifyReport:
    results = [
        VerificationResult(
            bib_key="cinnamon2025",
            status="verified",
            local_title="Cinnamon: A Large-Scale Hardware Accelerator for Fully Homomorphic Encryption",
            local_year="2025",
            local_doi="10.1145/3582016.3582066",
            local_authors="Samardzic, Nikola and others",
            local_venue="ASPLOS",
            remote_title="Cinnamon: A Large-Scale Hardware Accelerator for Fully Homomorphic Encryption",
            remote_year=2025,
            remote_doi="10.1145/3582016.3582066",
            remote_authors=["Nikola Samardzic"],
            remote_venue="ASPLOS",
            remote_citation_count=15,
            remote_source="both",
            mismatches=[],
            title_similarity=1.0,
            notes=None,
        )
    ]
    if not_found:
        results.append(
            VerificationResult(
                bib_key="fakepaper2024",
                status="not_found",
                local_title="A Completely Fabricated Paper That Does Not Exist",
                local_year="2024",
                local_doi="10.9999/fake.2024.000",
                local_authors="Nobody, John and Fake, Jane",
                local_venue="Journal of Nonexistence",
                remote_title=None,
                remote_year=None,
                remote_doi=None,
                remote_authors=None,
                remote_venue=None,
                remote_citation_count=None,
                remote_source=None,
                mismatches=[],
                title_similarity=None,
                notes="No matching paper found",
            )
        )
    return VerifyReport(
        total=len(results),
        verified=sum(1 for result in results if result.status == "verified"),
        mismatch=sum(1 for result in results if result.status == "mismatch"),
        not_found=sum(1 for result in results if result.status == "not_found"),
        error=sum(1 for result in results if result.status == "error"),
        results=results,
        skipped=[],
    )


def test_verify_cli_default_mode(monkeypatch) -> None:
    async def fake_verify_bib(*args, **kwargs):
        return _sample_report()

    monkeypatch.setattr("hypo_research.cli.verify_bib", fake_verify_bib)
    runner = CliRunner()
    result = runner.invoke(main, ["verify", "tests/fixtures/lint_buggy.bib"])
    assert result.exit_code == 0
    assert "Citation Verification Report" in result.output
    assert "| Status | Count |" in result.output


def test_verify_cli_stats_mode(monkeypatch) -> None:
    async def fake_verify_bib(*args, **kwargs):
        return _sample_report()

    monkeypatch.setattr("hypo_research.cli.verify_bib", fake_verify_bib)
    runner = CliRunner()
    result = runner.invoke(main, ["verify", "--stats", "tests/fixtures/lint_buggy.bib"])
    assert result.exit_code == 0
    payload = json.loads(result.output[result.output.find("{") :])
    assert "summary" in payload
    assert "results" in payload


def test_verify_cli_with_tex_filter(monkeypatch) -> None:
    seen = {}

    async def fake_verify_bib(*args, **kwargs):
        seen["tex_path"] = kwargs.get("tex_path")
        return _sample_report()

    monkeypatch.setattr("hypo_research.cli.verify_bib", fake_verify_bib)
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["verify", "tests/fixtures/lint_buggy.bib", "--tex", "tests/fixtures/lint_buggy.tex"],
    )
    assert result.exit_code == 0
    assert seen["tex_path"] == "tests/fixtures/lint_buggy.tex"


def test_verify_cli_with_keys_filter(monkeypatch) -> None:
    seen = {}

    async def fake_verify_bib(*args, **kwargs):
        seen["keys"] = kwargs.get("keys")
        return _sample_report()

    monkeypatch.setattr("hypo_research.cli.verify_bib", fake_verify_bib)
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["verify", "tests/fixtures/lint_buggy.bib", "--keys", "cinnamon2025,f1wrong"],
    )
    assert result.exit_code == 0
    assert seen["keys"] == ["cinnamon2025", "f1wrong"]


def test_verify_cli_exit_code_on_not_found(monkeypatch) -> None:
    async def fake_verify_bib(*args, **kwargs):
        return _sample_report(not_found=True)

    monkeypatch.setattr("hypo_research.cli.verify_bib", fake_verify_bib)
    runner = CliRunner()
    result = runner.invoke(main, ["verify", "tests/fixtures/lint_buggy.bib"])
    assert result.exit_code == 1


def test_verify_cli_exit_code_on_all_verified(monkeypatch) -> None:
    async def fake_verify_bib(*args, **kwargs):
        return _sample_report()

    monkeypatch.setattr("hypo_research.cli.verify_bib", fake_verify_bib)
    runner = CliRunner()
    result = runner.invoke(main, ["verify", "tests/fixtures/lint_buggy.bib"])
    assert result.exit_code == 0
