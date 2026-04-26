"""Tests for presubmit pipeline orchestration."""

from __future__ import annotations

from hypo_research.presubmit.runner import (
    CheckStageResult,
    PresubmitVerdict,
    run_presubmit,
)


def stage(name: str, *, errors: int = 0, warnings: int = 0) -> CheckStageResult:
    return CheckStageResult(
        stage=name,
        passed=errors == 0,
        errors=errors,
        warnings=warnings,
        details=[],
        duration_seconds=0.01,
    )


def test_presubmit_complete_pipeline_executes_all_stages(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        "hypo_research.presubmit.runner._run_check_stage",
        lambda tex_root, venue=None: calls.append("check") or stage("check"),
    )
    monkeypatch.setattr(
        "hypo_research.presubmit.runner._run_lint_stage",
        lambda tex_root, venue=None: calls.append("lint") or stage("lint"),
    )
    monkeypatch.setattr(
        "hypo_research.presubmit.runner._run_verify_stage",
        lambda tex_root, venue=None, bib_file=None: calls.append("verify") or stage("verify"),
    )

    result = run_presubmit("paper.tex")

    assert calls == ["check", "lint", "verify"]
    assert result.verdict is PresubmitVerdict.PASS


def test_presubmit_pass_verdict(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.presubmit.runner._run_check_stage", lambda *a, **k: stage("check"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_lint_stage", lambda *a, **k: stage("lint"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_verify_stage", lambda *a, **k: stage("verify"))

    result = run_presubmit("paper.tex")

    assert result.verdict is PresubmitVerdict.PASS
    assert result.total_errors == 0
    assert result.total_warnings == 0


def test_presubmit_warning_verdict(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.presubmit.runner._run_check_stage", lambda *a, **k: stage("check", warnings=1))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_lint_stage", lambda *a, **k: stage("lint"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_verify_stage", lambda *a, **k: stage("verify"))

    result = run_presubmit("paper.tex")

    assert result.verdict is PresubmitVerdict.WARNING
    assert result.total_warnings == 1


def test_presubmit_fail_verdict(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.presubmit.runner._run_check_stage", lambda *a, **k: stage("check", errors=1))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_lint_stage", lambda *a, **k: stage("lint"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_verify_stage", lambda *a, **k: stage("verify"))

    result = run_presubmit("paper.tex")

    assert result.verdict is PresubmitVerdict.FAIL
    assert result.total_errors == 1


def test_presubmit_skip_stages(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.presubmit.runner._run_check_stage", lambda *a, **k: stage("check"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_lint_stage", lambda *a, **k: stage("lint"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_verify_stage", lambda *a, **k: stage("verify"))

    result = run_presubmit("paper.tex", skip_stages=["lint", "verify"])

    assert [item.stage for item in result.stages] == ["check"]
    assert result.skipped_stages == ["lint", "verify"]


def test_presubmit_stage_exception_does_not_stop_pipeline(monkeypatch) -> None:
    def failing_stage(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("hypo_research.presubmit.runner._run_check_stage", failing_stage)
    monkeypatch.setattr("hypo_research.presubmit.runner._run_lint_stage", lambda *a, **k: stage("lint"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_verify_stage", lambda *a, **k: stage("verify"))

    result = run_presubmit("paper.tex")

    assert result.verdict is PresubmitVerdict.FAIL
    assert [item.stage for item in result.stages] == ["check", "lint", "verify"]
    assert "stage exception" in result.stages[0].details[0]


def test_presubmit_passes_venue_and_bib_file(monkeypatch) -> None:
    seen: dict[str, object] = {}

    monkeypatch.setattr(
        "hypo_research.presubmit.runner._run_check_stage",
        lambda tex_root, venue=None: (
            seen.setdefault("check_venue", venue),
            stage("check"),
        )[1],
    )
    monkeypatch.setattr(
        "hypo_research.presubmit.runner._run_lint_stage",
        lambda tex_root, venue=None: (
            seen.setdefault("lint_venue", venue),
            stage("lint"),
        )[1],
    )
    monkeypatch.setattr(
        "hypo_research.presubmit.runner._run_verify_stage",
        lambda tex_root, venue=None, bib_file=None: (
            seen.setdefault("verify_venue", venue),
            seen.setdefault("bib_file", bib_file),
            stage("verify"),
        )[2],
    )

    run_presubmit("paper.tex", venue="ieee_journal", bib_file="refs.bib")

    assert seen["check_venue"] == "ieee_journal"
    assert seen["lint_venue"] == "ieee_journal"
    assert seen["verify_venue"] == "ieee_journal"
    assert seen["bib_file"] == "refs.bib"


def test_presubmit_records_duration(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.presubmit.runner._run_check_stage", lambda *a, **k: stage("check"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_lint_stage", lambda *a, **k: stage("lint"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_verify_stage", lambda *a, **k: stage("verify"))

    result = run_presubmit("paper.tex")

    assert result.total_duration_seconds >= 0
    assert all(item.duration_seconds >= 0 for item in result.stages)


def test_presubmit_empty_result_passes(monkeypatch) -> None:
    monkeypatch.setattr("hypo_research.presubmit.runner._run_check_stage", lambda *a, **k: stage("check"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_lint_stage", lambda *a, **k: stage("lint"))
    monkeypatch.setattr("hypo_research.presubmit.runner._run_verify_stage", lambda *a, **k: stage("verify"))

    result = run_presubmit("paper.tex")

    assert result.summary == "全部检查通过，可以提交。"
