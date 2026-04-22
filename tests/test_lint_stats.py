"""Golden tests for LaTeX structure statistic extraction."""

from __future__ import annotations

from hypo_research.writing.stats import extract_stats


def test_buggy_has_ref_violations() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    ref_types = [ref.ref_type for ref in stats.refs]
    assert "ref" in ref_types


def test_buggy_has_missing_placement() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    assert any(float_info.placement == "" for float_info in stats.floats)


def test_buggy_has_label_before_caption() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    assert any(float_info.label_before_caption for float_info in stats.floats)


def test_buggy_has_unprefixed_labels() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    assert any(not label.has_prefix for label in stats.labels)


def test_buggy_has_tabular() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    assert "tabular" in stats.environments


def test_buggy_has_orphan_labels() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    assert len(stats.orphan_labels) > 0
    assert "eq:unused" in stats.orphan_labels


def test_buggy_has_abbreviations() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    abbr_names = [abbr.abbr for abbr in stats.abbreviations]
    assert "FHE" in abbr_names
    assert "NTT" in abbr_names


def test_buggy_has_tilde_issues() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    assert len(stats.tilde_issues) > 0


def test_buggy_has_spacing_issues() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    assert any(issue.issue_type == "multiple_spaces" for issue in stats.spacing_issues)


def test_fixed_no_ref_violations() -> None:
    stats = extract_stats("tests/fixtures/lint_fixed.tex")
    assert all(ref.ref_type == "cref" for ref in stats.refs)


def test_fixed_all_floats_have_placement() -> None:
    stats = extract_stats("tests/fixtures/lint_fixed.tex")
    assert all(float_info.placement != "" for float_info in stats.floats)


def test_fixed_all_labels_have_prefix() -> None:
    stats = extract_stats("tests/fixtures/lint_fixed.tex")
    assert all(label.has_prefix for label in stats.labels)


def test_fixed_no_tabular() -> None:
    stats = extract_stats("tests/fixtures/lint_fixed.tex")
    assert "tabular" not in stats.environments


def test_fixed_no_orphan_labels() -> None:
    stats = extract_stats("tests/fixtures/lint_fixed.tex")
    assert len(stats.orphan_labels) == 0


def test_fixed_no_tilde_issues() -> None:
    stats = extract_stats("tests/fixtures/lint_fixed.tex")
    assert len(stats.tilde_issues) == 0


def test_fixed_no_spacing_issues() -> None:
    stats = extract_stats("tests/fixtures/lint_fixed.tex")
    assert len(stats.spacing_issues) == 0


def test_label_prefix_suggestion() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    overview_label = next(label for label in stats.labels if label.name == "overview")
    assert overview_label.suggested_prefix == "fig:"

    bg_label = next(label for label in stats.labels if label.name == "background")
    assert bg_label.suggested_prefix == "sec:"


def test_orphan_ref_detection() -> None:
    stats = extract_stats("tests/fixtures/lint_buggy.tex")
    assert isinstance(stats.orphan_refs, list)
