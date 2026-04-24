"""Tests for the writing pipeline orchestrator."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from hypo_research.writing.check import CheckReport, run_check


FIX_BUGGY = "tests/fixtures/fix_buggy.tex"
MULTIFILE_DIR = "tests/fixtures/multifile"


def test_check_basic(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    report = run_check(str(src), dry_run=True, verify=False, save_report=False)
    assert isinstance(report, CheckReport)
    assert report.lint.total_issues > 0
    assert report.lint.fixes_available > 0
    assert report.verify is None


def test_check_with_fix(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    report = run_check(str(src), fix=True, dry_run=False, verify=False, save_report=False)
    assert report.lint.fixes_applied > 0
    report2 = run_check(str(src), fix=True, dry_run=True, verify=False, save_report=False)
    assert report2.lint.fixes_available < report.lint.fixes_available


def test_check_no_fix(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    original = src.read_text(encoding="utf-8")
    report = run_check(str(src), no_fix=True, verify=False, save_report=False)
    assert src.read_text(encoding="utf-8") == original
    assert report.lint.fixes_applied == 0


def test_check_lint_only(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    report = run_check(str(src), lint_only=True, save_report=False)
    assert report.verify is None


def test_check_multifile(tmp_path) -> None:
    src_dir = tmp_path / "project"
    shutil.copytree(MULTIFILE_DIR, src_dir)
    report = run_check(str(src_dir / "main.tex"), verify=False, save_report=False)
    assert report.stats.total_files > 1


def test_check_saves_report(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    report = run_check(str(src), verify=False, save_report=True)
    assert report.report_path is not None
    report_file = Path(report.report_path)
    assert report_file.exists()
    data = json.loads(report_file.read_text(encoding="utf-8"))
    assert "lint" in data
    assert "stats" in data
    assert "timestamp" in data


def test_check_no_save(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    report = run_check(str(src), verify=False, save_report=False)
    assert report.report_path is None


def test_check_respects_config(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    (tmp_path / ".hypo-research.toml").write_text('[lint]\ndisabled_rules = ["L01"]\n', encoding="utf-8")
    report = run_check(str(src), verify=False, save_report=False)
    assert "L01" not in report.lint.rules_triggered


def test_check_stats_populated(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    report = run_check(str(src), verify=False, save_report=False)
    assert report.stats.total_labels > 0
    assert report.stats.total_refs > 0
    assert report.stats.total_sections > 0
