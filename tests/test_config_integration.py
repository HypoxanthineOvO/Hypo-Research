"""Integration tests for CLI config support."""

from __future__ import annotations

import json
import shutil
import subprocess
from types import SimpleNamespace

from click.testing import CliRunner

from hypo_research.cli import main
from hypo_research.writing.config import CONFIG_FILENAME


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "hypo-research", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_lint_respects_disabled_rules(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy("tests/fixtures/lint_buggy.tex", src)
    (tmp_path / CONFIG_FILENAME).write_text('[lint]\ndisabled_rules = ["L01"]\n', encoding="utf-8")

    result = run_cli(["lint", str(src)])
    assert "L01" not in result.stdout


def test_lint_fix_uses_config_rules(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy("tests/fixtures/fix_buggy.tex", src)
    (tmp_path / CONFIG_FILENAME).write_text('[lint]\nfix_rules = ["L04"]\n', encoding="utf-8")

    result = run_cli(["lint", "--fix", str(src)])
    assert "L04" in result.stdout
    assert "L01" not in result.stdout


def test_verify_uses_config_timeout(monkeypatch, tmp_path) -> None:
    seen: dict[str, object] = {}

    async def fake_verify_bib(*args, **kwargs):
        seen["timeout"] = kwargs.get("timeout")
        seen["skip_keys"] = kwargs.get("skip_keys")
        seen["max_requests_per_second"] = kwargs.get("max_requests_per_second")
        from hypo_research.writing.verify import VerifyReport

        return VerifyReport(
            total=0,
            verified=0,
            mismatch=0,
            not_found=0,
            uncertain=0,
            rate_limited=0,
            error=0,
            results=[],
            skipped=[],
        )

    monkeypatch.setattr("hypo_research.cli.verify_bib", fake_verify_bib)
    (tmp_path / CONFIG_FILENAME).write_text(
        '[project]\nbib_files = ["refs.bib"]\n[verify]\ntimeout = 60\nskip_keys = ["draft2025"]\n',
        encoding="utf-8",
    )
    (tmp_path / "refs.bib").write_text("@article{test, title={Test}, year={2024}}\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["verify"], catch_exceptions=False)
    assert result.exit_code == 0
    assert seen["timeout"] == 60
    assert seen["skip_keys"] == ["draft2025"]
    assert seen["max_requests_per_second"] == 1.0


def test_config_project_main_file(tmp_path) -> None:
    src_dir = tmp_path / "project"
    shutil.copytree("tests/fixtures/multifile", src_dir)
    (src_dir / CONFIG_FILENAME).write_text('[project]\nmain_file = "main.tex"\n', encoding="utf-8")

    result = run_cli(["lint", "--stats", str(src_dir / "sections" / "intro.tex")])
    data = json.loads(result.stdout)
    assert data.get("project") is not None


def test_search_uses_config_defaults(monkeypatch, tmp_path) -> None:
    seen: dict[str, object] = {}

    async def fake_run_single_search(params, output_dir, sources, hook_manager):
        seen["query"] = params.query
        seen["max_results"] = params.max_results
        seen["sources"] = [source.name for source in sources]
        return SimpleNamespace(papers=[], output_dir="tmp", meta=SimpleNamespace(expansion=None))

    monkeypatch.setattr("hypo_research.cli._run_single_search", fake_run_single_search)
    (tmp_path / CONFIG_FILENAME).write_text(
        '[survey]\ndefault_topic = "FHE accelerator"\nmax_results = 7\nsources = ["s2", "arxiv"]\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["search"], catch_exceptions=False)
    assert result.exit_code == 0
    assert seen["query"] == "FHE accelerator"
    assert seen["max_results"] == 7
    assert seen["sources"] == ["semantic_scholar", "arxiv"]
