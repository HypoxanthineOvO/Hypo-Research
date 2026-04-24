"""Regression tests for writing robustness fixes from real-paper feedback."""

from __future__ import annotations

from pathlib import Path

from hypo_research.writing.check import CheckReport, LintStageResult, VerifyStageResult, check_exit_code
from hypo_research.writing.stats import extract_stats


def test_alg_prefix_is_accepted(tmp_path) -> None:
    tex = tmp_path / "alg.tex"
    tex.write_text(
        r"""\documentclass{article}
\begin{document}
\begin{algorithm}
\label{alg:mirs}
\end{algorithm}
\end{document}
""",
        encoding="utf-8",
    )
    stats = extract_stats(tex)
    assert all(label.has_prefix for label in stats.labels)


def test_lst_and_thm_prefixes_are_accepted(tmp_path) -> None:
    tex = tmp_path / "prefixes.tex"
    tex.write_text(
        r"""\documentclass{article}
\begin{document}
\begin{lstlisting}
\label{lst:code}
\end{lstlisting}
\begin{theorem}
\label{thm:main}
\end{theorem}
\end{document}
""",
        encoding="utf-8",
    )
    stats = extract_stats(tex)
    assert all(label.has_prefix for label in stats.labels)


def test_unprefixed_label_still_warns(tmp_path) -> None:
    tex = tmp_path / "bad.tex"
    tex.write_text(
        r"""\documentclass{article}
\begin{document}
\begin{figure}
\label{overview}
\caption{Overview}
\end{figure}
\end{document}
""",
        encoding="utf-8",
    )
    stats = extract_stats(tex)
    assert any(not label.has_prefix for label in stats.labels)


def test_extended_ref_commands_prevent_orphans(tmp_path) -> None:
    tex = tmp_path / "refs.tex"
    tex.write_text(
        r"""\documentclass{article}
\begin{document}
\section{Intro}
\label{sec:intro}
\begin{figure}\caption{A}\label{fig:a}\end{figure}
\begin{figure}\caption{B}\label{fig:b}\end{figure}
\begin{figure}\caption{C}\label{fig:c}\end{figure}
\begin{table}\caption{T}\label{tab:tbl}\end{table}
\begin{equation}\label{eq:d}x=1\end{equation}
As shown in \Cref{fig:a}, see \autoref{tab:tbl}, \hyperref[sec:intro]{Intro},
\cref{fig:b,fig:c}, and \eqref{eq:d}.
\end{document}
""",
        encoding="utf-8",
    )
    stats = extract_stats(tex)
    assert "fig:a" not in stats.orphan_labels
    assert "fig:b" not in stats.orphan_labels
    assert "fig:c" not in stats.orphan_labels
    assert "tab:tbl" not in stats.orphan_labels
    assert "sec:intro" not in stats.orphan_labels
    assert "eq:d" not in stats.orphan_labels


def test_bilingual_filters_ignore_noise() -> None:
    stats = extract_stats("tests/fixtures/translate_noise.tex")
    assert len(stats.paragraph_pairs) == 1
    assert any("Normal bilingual paragraph." in pair.english for pair in stats.paragraph_pairs)
    assert not any("中文草稿注释" in orphan.text for orphan in stats.orphan_paragraphs)
    assert not any("\\includegraphics" in orphan.text for orphan in stats.orphan_paragraphs)
    assert not any("A & B" in orphan.text for orphan in stats.orphan_paragraphs)
    assert any("no Chinese comment" in orphan.text for orphan in stats.orphan_paragraphs)


def test_check_exit_code_ignores_rate_limited() -> None:
    report = CheckReport(
        lint=LintStageResult(errors=0),
        verify=VerifyStageResult(
            total_entries=1,
            verified=0,
            mismatch=0,
            not_found=0,
            uncertain=0,
            rate_limited=1,
            error=0,
            skipped=0,
        ),
    )
    assert check_exit_code(report) == 0


def test_check_exit_code_fails_on_mismatch() -> None:
    report = CheckReport(
        lint=LintStageResult(errors=0),
        verify=VerifyStageResult(
            total_entries=1,
            verified=0,
            mismatch=1,
            not_found=0,
            uncertain=0,
            rate_limited=0,
            error=0,
            skipped=0,
        ),
    )
    assert check_exit_code(report) == 1
