"""Tests for multi-file LaTeX project resolution."""

from __future__ import annotations

import pytest

from hypo_research.writing.project import CircularInputError, resolve_project, virtual_to_real


def test_resolve_project_from_main() -> None:
    project = resolve_project("tests/fixtures/multifile/main.tex")
    assert project.root_file.name == "main.tex"
    file_names = [f.path.as_posix() for f in project.files]
    assert "sections/intro.tex" in file_names
    assert "sections/method.tex" in file_names
    assert "sections/eval.tex" in file_names
    assert "tables/comparison.tex" in file_names
    assert "preamble.tex" in file_names


def test_resolve_project_from_subfile() -> None:
    project = resolve_project("tests/fixtures/multifile/sections/intro.tex")
    assert project.root_file.name == "main.tex"
    assert len(project.files) > 1


def test_nested_input() -> None:
    project = resolve_project("tests/fixtures/multifile/main.tex")
    file_names = [f.path.as_posix() for f in project.files]
    method_idx = file_names.index("sections/method.tex")
    comparison_idx = file_names.index("tables/comparison.tex")
    assert comparison_idx == method_idx + 1


def test_circular_input_detection() -> None:
    with pytest.raises(CircularInputError):
        resolve_project("tests/fixtures/multifile/circular_a.tex")


def test_bib_discovery() -> None:
    project = resolve_project("tests/fixtures/multifile/main.tex")
    bib_names = [p.name for p in project.bib_files]
    assert "refs.bib" in bib_names
    assert "extra.bib" in bib_names


def test_line_number_mapping() -> None:
    project = resolve_project("tests/fixtures/multifile/main.tex")
    intro_file = next(f for f in project.files if "intro" in f.path.as_posix())
    real_file, real_line = virtual_to_real(project, intro_file.line_offset)
    assert "intro" in real_file
    assert real_line == 1


def test_merged_content_contains_all_files() -> None:
    project = resolve_project("tests/fixtures/multifile/main.tex")
    assert "\\section{Introduction}" in project.merged_content
    assert "\\section{Method}" in project.merged_content
    assert "\\section{Evaluation}" in project.merged_content
    assert "Performance Comparison" in project.merged_content


def test_single_file_backward_compat() -> None:
    project = resolve_project("tests/fixtures/lint_buggy.tex")
    assert len(project.files) == 1
    assert project.merged_content == project.files[0].content


def test_input_without_tex_extension() -> None:
    project = resolve_project("tests/fixtures/multifile/main.tex")
    file_names = [f.path.as_posix() for f in project.files]
    assert "sections/intro.tex" in file_names
