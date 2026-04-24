"""Tests for project-level configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from hypo_research.cli import main
from hypo_research.writing.config import (
    CONFIG_FILENAME,
    generate_default_config,
    load_config,
    load_config_from_file,
    merge_cli_args,
)


def test_load_basic_config() -> None:
    config = load_config_from_file("tests/fixtures/config/basic.toml")
    assert config.project.main_file == "main.tex"
    assert config.project.bib_files == ["refs.bib"]
    assert config.lint.disabled_rules == ["L09"]
    assert config.verify.timeout == 60
    assert config.verify.max_requests_per_second == 1.0


def test_load_full_config() -> None:
    config = load_config_from_file("tests/fixtures/config/full.toml")
    assert config.project.main_file == "paper.tex"
    assert config.project.bib_files == ["refs.bib", "extra.bib"]
    assert config.project.src_dir == "src"
    assert config.lint.disabled_rules == ["L09", "L10"]
    assert config.lint.fix_rules == ["L01", "L04"]
    assert config.lint.severity_overrides == {"L05": "warning"}
    assert config.verify.s2_api_key == "test-key-123"
    assert config.verify.skip_keys == ["draft2025"]
    assert config.verify.max_requests_per_second == 0.5
    assert config.translate.target_lang == "zh"
    assert config.translate.glossary["bootstrapping"] == "自举"
    assert config.survey.default_topic == "FHE accelerator"
    assert config.survey.max_results == 200


def test_load_empty_config() -> None:
    config = load_config_from_file("tests/fixtures/config/empty.toml")
    assert config.project.main_file is None
    assert config.project.bib_files == []
    assert config.lint.disabled_rules == []
    assert config.verify.timeout == 30
    assert config.translate.target_lang == "zh"


def test_unknown_fields_no_error() -> None:
    config = load_config_from_file("tests/fixtures/config/unknown_fields.toml")
    assert config.project.main_file == "main.tex"


def test_missing_file_returns_default() -> None:
    with pytest.raises(FileNotFoundError):
        load_config_from_file("tests/fixtures/config/nonexistent.toml")


def test_load_config_uses_env_s2_api_key(monkeypatch) -> None:
    monkeypatch.setenv("S2_API_KEY", "env-key-456")
    config = load_config_from_file("tests/fixtures/config/basic.toml")
    assert config.verify.s2_api_key == "env-key-456"


def test_load_config_from_dir(tmp_path) -> None:
    config_file = tmp_path / CONFIG_FILENAME
    config_file.write_text('[project]\nmain_file = "main.tex"\n', encoding="utf-8")

    config = load_config(tmp_path)
    assert config.project.main_file == "main.tex"
    assert config.config_path == config_file


def test_load_config_from_subdir(tmp_path) -> None:
    config_file = tmp_path / CONFIG_FILENAME
    config_file.write_text('[project]\nmain_file = "main.tex"\n', encoding="utf-8")
    subdir = tmp_path / "sections"
    subdir.mkdir()

    config = load_config(subdir)
    assert config.project.main_file == "main.tex"
    assert config.config_path == config_file


def test_load_config_no_file(tmp_path) -> None:
    config = load_config(tmp_path)
    assert config.config_path is None
    assert config.project.main_file is None


def test_merge_cli_overrides_config() -> None:
    config = load_config_from_file("tests/fixtures/config/full.toml")
    merged = merge_cli_args(config, {"bib": "override.bib", "rules": ["L01"]})
    assert merged.project.bib_files == ["override.bib"]
    assert merged.lint.enabled_rules == ["L01"]


def test_merge_cli_none_keeps_config() -> None:
    config = load_config_from_file("tests/fixtures/config/full.toml")
    merged = merge_cli_args(config, {})
    assert merged.verify.timeout == 30


def test_generate_default_config() -> None:
    content = generate_default_config()
    assert "[project]" in content
    assert "[lint]" in content
    assert "[verify]" in content
    assert "[translate]" in content
    assert "[survey]" in content
    import tomllib

    data = tomllib.loads(content)
    assert "project" in data


def test_generate_default_config_with_detection(tmp_path) -> None:
    (tmp_path / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")
    (tmp_path / "refs.bib").write_text("@article{test, title={Test}}\n", encoding="utf-8")

    content = generate_default_config(project_dir=tmp_path)
    assert 'main_file = "main.tex"' in content
    assert '"refs.bib"' in content


def test_init_creates_config(tmp_path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / CONFIG_FILENAME).exists()


def test_init_no_overwrite(tmp_path) -> None:
    config_file = tmp_path / CONFIG_FILENAME
    config_file.write_text("# existing\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--dir", str(tmp_path)])
    assert result.exit_code != 0
    assert config_file.read_text(encoding="utf-8") == "# existing\n"


def test_init_force_overwrite(tmp_path) -> None:
    config_file = tmp_path / CONFIG_FILENAME
    config_file.write_text("# existing\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["init", "--force", "--dir", str(tmp_path)])
    assert result.exit_code == 0
    assert config_file.read_text(encoding="utf-8") != "# existing\n"
