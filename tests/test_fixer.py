"""Tests for lint auto-fix generation and application."""

from __future__ import annotations

import shutil
from pathlib import Path

from hypo_research.writing.fixer import apply_fixes, generate_fixes
from hypo_research.writing.project import resolve_project
from hypo_research.writing.stats import extract_stats


FIX_BUGGY = "tests/fixtures/fix_buggy.tex"
FIX_EXPECTED = "tests/fixtures/fix_expected.tex"


def test_generate_fixes_finds_all_rules() -> None:
    stats = extract_stats(FIX_BUGGY)
    fixes = generate_fixes(stats)
    rules_found = {fix.rule for fix in fixes}
    assert "L01" in rules_found
    assert "L02" in rules_found
    assert "L03" in rules_found
    assert "L04" in rules_found
    assert "L05" in rules_found
    assert "L06" in rules_found
    assert "L11" in rules_found
    assert "L13" in rules_found


def test_generate_fixes_rule_filter() -> None:
    stats = extract_stats(FIX_BUGGY)
    fixes = generate_fixes(stats, rules=["L01"])
    assert fixes
    assert all(fix.rule == "L01" for fix in fixes)
    assert len(fixes) >= 2


def test_generate_fixes_sorted_by_file_line() -> None:
    stats = extract_stats(FIX_BUGGY)
    fixes = generate_fixes(stats)
    for index in range(len(fixes) - 1):
        assert (fixes[index].file, fixes[index].line) <= (fixes[index + 1].file, fixes[index + 1].line)


def test_dry_run_does_not_modify_file(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)
    original_content = src.read_text(encoding="utf-8")

    stats = extract_stats(src)
    fixes = generate_fixes(stats)
    report = apply_fixes(fixes, dry_run=True)

    assert report.dry_run is True
    assert src.read_text(encoding="utf-8") == original_content
    assert report.fixes


def test_apply_fixes_modifies_file(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)

    stats = extract_stats(src)
    fixes = generate_fixes(stats)
    report = apply_fixes(fixes, dry_run=False)

    assert report.dry_run is False
    assert src.read_text(encoding="utf-8") != Path(FIX_BUGGY).read_text(encoding="utf-8")


def test_apply_fixes_backup(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)

    stats = extract_stats(src)
    fixes = generate_fixes(stats)
    apply_fixes(fixes, dry_run=False, backup=True)

    bak = tmp_path / "test.tex.bak"
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == Path(FIX_BUGGY).read_text(encoding="utf-8")


def test_apply_all_fixes_matches_expected(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)

    stats = extract_stats(src)
    fixes = generate_fixes(stats)
    apply_fixes(fixes, dry_run=False)

    actual = src.read_text(encoding="utf-8")
    expected = Path(FIX_EXPECTED).read_text(encoding="utf-8")
    assert actual == expected


def test_fix_l01_ref_to_cref(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)

    stats = extract_stats(src)
    fixes = generate_fixes(stats, rules=["L01"])
    apply_fixes(fixes, dry_run=False)

    content = src.read_text(encoding="utf-8")
    assert "\\ref{" not in content
    assert "\\cref{fig:test}" in content
    assert "\\cref{sec:method}" in content


def test_fix_l04_float_placement(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)

    stats = extract_stats(src)
    fixes = generate_fixes(stats, rules=["L04"])
    apply_fixes(fixes, dry_run=False)

    content = src.read_text(encoding="utf-8")
    assert "\\begin{figure}[htbp]" in content
    assert "\\begin{table}[htbp]" in content


def test_fix_l06_orphan_label(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)

    stats = extract_stats(src)
    fixes = generate_fixes(stats, rules=["L06"])
    apply_fixes(fixes, dry_run=False)

    content = src.read_text(encoding="utf-8")
    assert "orphan:unused" not in content
    assert "\\label{sec:intro}" in content
    assert "\\label{fig:test}" in content


def test_fix_l11_tblr_hline(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)

    stats = extract_stats(src)
    fixes = generate_fixes(stats, rules=["L11"])
    apply_fixes(fixes, dry_run=False)

    content = src.read_text(encoding="utf-8")
    assert "\\toprule" not in content
    assert "\\midrule" not in content
    assert "\\bottomrule" not in content
    assert content.count("\\hline") >= 3


def test_multifile_fix_cross_file(tmp_path) -> None:
    src_dir = tmp_path / "multifile"
    shutil.copytree("tests/fixtures/multifile", src_dir)

    project = resolve_project(src_dir / "main.tex")
    stats = extract_stats(src_dir / "main.tex", project=project)
    fixes = generate_fixes(stats, project=project)

    assert fixes
    assert len({fix.file for fix in fixes}) >= 1
    report = apply_fixes(fixes, project=project, dry_run=True)
    assert report.dry_run is True


def test_multifile_fix_apply(tmp_path) -> None:
    src_dir = tmp_path / "multifile"
    shutil.copytree("tests/fixtures/multifile", src_dir)

    project = resolve_project(src_dir / "main.tex")
    stats = extract_stats(src_dir / "main.tex", project=project)
    fixes = generate_fixes(stats, project=project, rules=["L01"])
    apply_fixes(fixes, project=project, dry_run=False)

    eval_content = (src_dir / "sections" / "eval.tex").read_text(encoding="utf-8")
    assert "\\ref{" not in eval_content


def test_fix_mismatch_original_skipped(tmp_path) -> None:
    src = tmp_path / "test.tex"
    shutil.copy(FIX_BUGGY, src)

    stats = extract_stats(src)
    fixes = generate_fixes(stats, rules=["L01"])
    content = src.read_text(encoding="utf-8").replace("\\ref{fig:test}", "\\cref{fig:test}")
    src.write_text(content, encoding="utf-8")

    report = apply_fixes(fixes, dry_run=False)
    assert report.errors
