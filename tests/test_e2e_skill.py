"""End-to-end integration tests for Skill usage patterns."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest


@pytest.mark.e2e
class TestE2ESkillFlow:
    """Tests that simulate how an Agent would invoke Hypo-Research."""

    @pytest.fixture
    def skill_env(self, tmp_path: Path) -> dict[str, str]:
        server = _FakeApiServer()
        server.start()
        sitecustomize_dir = tmp_path / "sitecustomize"
        sitecustomize_dir.mkdir(parents=True, exist_ok=True)
        (sitecustomize_dir / "sitecustomize.py").write_text(
            textwrap.dedent(
                f"""
                import os
                from hypo_research.core.sources.semantic_scholar import SemanticScholarSource
                from hypo_research.core.sources.openalex import OpenAlexSource
                from hypo_research.core.sources.arxiv import ArxivSource

                SemanticScholarSource.BASE_URL = os.environ["HYPO_TEST_S2_BASE_URL"]
                OpenAlexSource.BASE_URL = os.environ["HYPO_TEST_OPENALEX_BASE_URL"]
                ArxivSource.BASE_URL = os.environ["HYPO_TEST_ARXIV_BASE_URL"]
                """
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(
            [
                str(sitecustomize_dir),
                str(Path.cwd()),
                existing_pythonpath,
            ]
        ).rstrip(os.pathsep)
        env["HYPO_TEST_S2_BASE_URL"] = f"http://127.0.0.1:{server.port}/graph/v1"
        env["HYPO_TEST_OPENALEX_BASE_URL"] = f"http://127.0.0.1:{server.port}"
        env["HYPO_TEST_ARXIV_BASE_URL"] = f"http://127.0.0.1:{server.port}/api/query"

        try:
            yield env
        finally:
            server.stop()

    def test_single_query_produces_all_outputs(self, tmp_path: Path, skill_env: dict[str, str]) -> None:
        output_dir = tmp_path / "single"
        result = _run_cli(["search", "cryogenic computing GPU", "--output-dir", str(output_dir)], skill_env)

        assert result.returncode == 0
        assert (output_dir / "results.json").exists()
        assert (output_dir / "meta.json").exists()
        assert (output_dir / "references.bib").exists()
        assert (output_dir / "results.md").exists()

    def test_multi_query_produces_all_outputs(self, tmp_path: Path, skill_env: dict[str, str]) -> None:
        output_dir = tmp_path / "multi"
        result = _run_cli(
            [
                "search",
                "cryogenic computing GPU",
                "-eq",
                "cryo-CMOS accelerator",
                "-eq",
                "low temperature VLSI GPU",
                "--output-dir",
                str(output_dir),
            ],
            skill_env,
        )

        assert result.returncode == 0
        meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
        assert (output_dir / "references.bib").exists()
        assert (output_dir / "results.md").exists()
        assert meta["expansion"]["original_query"] == "cryogenic computing GPU"

    def test_source_selection(self, tmp_path: Path, skill_env: dict[str, str]) -> None:
        output_dir = tmp_path / "sources"
        result = _run_cli(
            [
                "search",
                "cryogenic computing GPU",
                "--source",
                "s2",
                "--source",
                "arxiv",
                "--output-dir",
                str(output_dir),
            ],
            skill_env,
        )

        assert result.returncode == 0
        meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))
        assert meta["sources_used"] == ["semantic_scholar", "arxiv"]

    def test_no_hooks_skips_bib_and_report(self, tmp_path: Path, skill_env: dict[str, str]) -> None:
        output_dir = tmp_path / "no_hooks"
        result = _run_cli(
            [
                "search",
                "cryogenic computing GPU",
                "--no-hooks",
                "--output-dir",
                str(output_dir),
            ],
            skill_env,
        )

        assert result.returncode == 0
        assert (output_dir / "results.json").exists()
        assert not (output_dir / "references.bib").exists()
        assert not (output_dir / "results.md").exists()

    def test_results_json_schema_valid(self, tmp_path: Path, skill_env: dict[str, str]) -> None:
        output_dir = tmp_path / "schema"
        result = _run_cli(["search", "cryogenic computing GPU", "--output-dir", str(output_dir)], skill_env)

        assert result.returncode == 0
        results = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        meta = json.loads((output_dir / "meta.json").read_text(encoding="utf-8"))

        assert results
        assert {"title", "authors", "year", "sources", "verification"} <= set(results[0].keys())
        assert {"query", "sources_used", "created_at"} <= set(meta.keys())

    def test_bibtex_is_parseable(self, tmp_path: Path, skill_env: dict[str, str]) -> None:
        output_dir = tmp_path / "bib"
        result = _run_cli(["search", "cryogenic computing GPU", "--output-dir", str(output_dir)], skill_env)

        assert result.returncode == 0
        bib = (output_dir / "references.bib").read_text(encoding="utf-8")
        assert "@article{" in bib or "@inproceedings{" in bib or "@misc{" in bib
        assert "title" in bib
        assert "author" in bib
        assert "year" in bib

    def test_markdown_report_has_required_sections(self, tmp_path: Path, skill_env: dict[str, str]) -> None:
        output_dir = tmp_path / "report"
        result = _run_cli(["search", "cryogenic computing GPU", "--output-dir", str(output_dir)], skill_env)

        assert result.returncode == 0
        report = (output_dir / "results.md").read_text(encoding="utf-8")
        assert "# Literature Survey Report" in report
        assert "## Search Summary" in report
        assert "## Results by Verification Status" in report

    def test_exit_code_zero_on_success(self, tmp_path: Path, skill_env: dict[str, str]) -> None:
        result = _run_cli(
            ["search", "cryogenic computing GPU", "--output-dir", str(tmp_path / "ok")],
            skill_env,
        )
        assert result.returncode == 0

    def test_exit_code_nonzero_on_bad_args(self, skill_env: dict[str, str]) -> None:
        result = _run_cli(["search", "--year-start", "2020"], skill_env)
        assert result.returncode != 0


def _run_cli(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("hypo-research")
    if executable:
        command = [executable, *args]
    else:
        command = [sys.executable, "-m", "hypo_research.cli", *args]
    return subprocess.run(
        command,
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class _FakeApiServer:
    """Tiny HTTP server that mimics external research APIs for e2e tests."""

    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeApiHandler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


class _FakeApiHandler(BaseHTTPRequestHandler):
    """Serve canned Semantic Scholar, OpenAlex, and arXiv responses."""

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if parsed.path == "/graph/v1/paper/search":
            self._json_response(_s2_response(params))
            return
        if parsed.path == "/works":
            self._json_response(_openalex_response(params))
            return
        if parsed.path == "/api/query":
            self._text_response(_arxiv_response(params), content_type="application/atom+xml")
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _json_response(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _text_response(self, payload: str, content_type: str) -> None:
        body = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _s2_response(params: dict[str, list[str]]) -> dict:
    query = params.get("query", [""])[0]
    if query == "low temperature VLSI GPU":
        papers = [
            {
                "paperId": "s2-2",
                "title": "Low-Temperature VLSI GPU Front-End",
                "authors": [{"authorId": "2", "name": "Bob Jones"}],
                "year": 2022,
                "venue": "VLSI Symposium",
                "abstract": "VLSI framing.",
                "externalIds": {"DOI": "10.5678/example"},
                "citationCount": 12,
                "referenceCount": 8,
                "url": "https://www.semanticscholar.org/paper/s2-2",
            }
        ]
    else:
        papers = [
            {
                "paperId": "s2-1",
                "title": "Cryogenic CMOS for Quantum Computing",
                "authors": [{"authorId": "1", "name": "Alice Smith"}],
                "year": 2023,
                "venue": "ISSCC Symposium",
                "abstract": "Cryogenic CMOS design for accelerator workloads.",
                "externalIds": {"DOI": "10.1234/example", "ArXiv": "2301.12345"},
                "citationCount": 42,
                "referenceCount": 30,
                "url": "https://www.semanticscholar.org/paper/s2-1",
            }
        ]
    return {"total": len(papers), "offset": 0, "next": None, "data": papers}


def _openalex_response(params: dict[str, list[str]]) -> dict:
    query = params.get("search", [""])[0]
    if query == "low temperature VLSI GPU":
        works = [
            {
                "id": "https://openalex.org/W2",
                "doi": "https://doi.org/10.5678/example",
                "title": "Low-Temperature VLSI GPU Front-End",
                "authorships": [{"author": {"display_name": "Bob Jones"}}],
                "publication_year": 2022,
                "primary_location": {
                    "landing_page_url": "https://example.org/paper2",
                    "source": {"display_name": "VLSI Symposium"},
                },
                "cited_by_count": 14,
                "abstract_inverted_index": {"Low": [0], "Temperature": [1], "VLSI": [2]},
                "referenced_works": [],
                "type": "article",
            }
        ]
    else:
        works = [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1234/example",
                "title": "Cryogenic CMOS for Quantum Computing",
                "authorships": [{"author": {"display_name": "Alice Smith"}}],
                "publication_year": 2023,
                "primary_location": {
                    "landing_page_url": "https://example.org/paper",
                    "source": {"display_name": "ISSCC Symposium"},
                },
                "cited_by_count": 50,
                "abstract_inverted_index": {"Cryogenic": [0], "CMOS": [1], "design": [2]},
                "referenced_works": [],
                "type": "article",
            }
        ]
    return {"results": works, "meta": {"next_cursor": None}}


def _arxiv_response(params: dict[str, list[str]]) -> str:
    query = params.get("search_query", [""])[0].removeprefix("all:")
    if query == "low temperature VLSI GPU":
        return """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom' xmlns:arxiv='http://arxiv.org/schemas/atom'>
  <entry>
    <id>http://arxiv.org/abs/2201.00002v1</id>
    <updated>2022-01-05T00:00:00Z</updated>
    <published>2022-01-01T00:00:00Z</published>
    <title>Low-Temperature VLSI GPU Front-End</title>
    <summary>Auxiliary paper.</summary>
    <author><name>Bob Jones</name></author>
    <link rel='alternate' href='http://arxiv.org/abs/2201.00002v1'/>
    <arxiv:primary_category term='cs.AR'/>
  </entry>
</feed>
"""
    return """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom' xmlns:arxiv='http://arxiv.org/schemas/atom'>
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <updated>2023-01-05T00:00:00Z</updated>
    <published>2023-01-01T00:00:00Z</published>
    <title>Cryogenic CMOS for Quantum Computing</title>
    <summary>Preprint version.</summary>
    <author><name>Alice Smith</name></author>
    <link rel='alternate' href='http://arxiv.org/abs/2301.12345v1'/>
    <arxiv:doi>10.1234/example</arxiv:doi>
    <arxiv:primary_category term='cs.AR'/>
  </entry>
</feed>
"""
