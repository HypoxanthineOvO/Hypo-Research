"""Project-level configuration loading for Hypo-Research."""

from __future__ import annotations

import copy
import os
import re
import tomllib
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


CONFIG_FILENAME = ".hypo-research.toml"
_DOCUMENTCLASS_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\{[^}]+\}")
_SECTION_FIELDS = {
    "project": {"main_file", "bib_files", "src_dir"},
    "lint": {"disabled_rules", "enabled_rules", "fix_rules", "severity_overrides"},
    "verify": {"s2_api_key", "timeout", "skip_keys", "max_concurrent"},
    "translate": {"target_lang", "glossary"},
    "survey": {"default_topic", "max_results", "sources"},
}


@dataclass
class ProjectConfig:
    """[project] section."""

    main_file: str | None = None
    bib_files: list[str] = field(default_factory=list)
    src_dir: str | None = None


@dataclass
class LintConfig:
    """[lint] section."""

    disabled_rules: list[str] = field(default_factory=list)
    enabled_rules: list[str] = field(default_factory=list)
    fix_rules: list[str] = field(default_factory=list)
    severity_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class VerifyConfig:
    """[verify] section."""

    s2_api_key: str | None = None
    timeout: int = 30
    skip_keys: list[str] = field(default_factory=list)
    max_concurrent: int = 5


@dataclass
class TranslateConfig:
    """[translate] section."""

    target_lang: str = "zh"
    glossary: dict[str, str] = field(default_factory=dict)


@dataclass
class SurveyConfig:
    """[survey] section."""

    default_topic: str | None = None
    max_results: int = 100
    sources: list[str] = field(default_factory=lambda: ["s2", "arxiv"])


@dataclass
class HypoConfig:
    """Root configuration, maps to the full .hypo-research.toml."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    lint: LintConfig = field(default_factory=LintConfig)
    verify: VerifyConfig = field(default_factory=VerifyConfig)
    translate: TranslateConfig = field(default_factory=TranslateConfig)
    survey: SurveyConfig = field(default_factory=SurveyConfig)
    config_path: Path | None = None


def load_config(start_dir: str | Path | None = None) -> HypoConfig:
    """Search upward for a project config file and load it if present."""
    if start_dir is None:
        current_dir = Path.cwd()
    else:
        current_dir = Path(start_dir).expanduser()
        if current_dir.is_file():
            current_dir = current_dir.parent
    current_dir = current_dir.resolve()

    for _ in range(6):
        config_path = current_dir / CONFIG_FILENAME
        if config_path.exists():
            return load_config_from_file(config_path)
        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent
    return HypoConfig()


def load_config_from_file(config_path: str | Path) -> HypoConfig:
    """Load configuration from a specific TOML file."""
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    config = HypoConfig(config_path=path)
    _warn_unknown_sections(data)

    project_data = _coerce_section(data.get("project"), "project")
    lint_data = _coerce_section(data.get("lint"), "lint")
    verify_data = _coerce_section(data.get("verify"), "verify")
    translate_data = _coerce_section(data.get("translate"), "translate")
    survey_data = _coerce_section(data.get("survey"), "survey")

    config.project = ProjectConfig(
        main_file=_coerce_optional_str(project_data.get("main_file")),
        bib_files=_coerce_str_list(project_data.get("bib_files")),
        src_dir=_coerce_optional_str(project_data.get("src_dir")),
    )
    config.lint = LintConfig(
        disabled_rules=_normalize_rule_list(lint_data.get("disabled_rules")),
        enabled_rules=_normalize_rule_list(lint_data.get("enabled_rules")),
        fix_rules=_normalize_rule_list(lint_data.get("fix_rules")),
        severity_overrides=_coerce_str_dict(lint_data.get("severity_overrides")),
    )
    verify_key = _coerce_optional_str(verify_data.get("s2_api_key"))
    config.verify = VerifyConfig(
        s2_api_key=verify_key or os.getenv("S2_API_KEY"),
        timeout=_coerce_int(verify_data.get("timeout"), 30),
        skip_keys=_coerce_str_list(verify_data.get("skip_keys")),
        max_concurrent=_coerce_int(verify_data.get("max_concurrent"), 5),
    )
    config.translate = TranslateConfig(
        target_lang=_coerce_optional_str(translate_data.get("target_lang")) or "zh",
        glossary=_coerce_str_dict(translate_data.get("glossary")),
    )
    config.survey = SurveyConfig(
        default_topic=_coerce_optional_str(survey_data.get("default_topic")),
        max_results=_coerce_int(survey_data.get("max_results"), 100),
        sources=_coerce_str_list(survey_data.get("sources")) or ["s2", "arxiv"],
    )
    return config


def merge_cli_args(config: HypoConfig, cli_args: dict[str, Any]) -> HypoConfig:
    """Overlay CLI arguments onto a loaded config object."""
    merged = copy.deepcopy(config)
    for key, value in cli_args.items():
        if value is None:
            continue
        if key == "bib":
            merged.project.bib_files = [str(value)] if not isinstance(value, list) else [str(item) for item in value]
        elif key == "rules":
            merged.lint.enabled_rules = [str(item).upper() for item in value]
        elif key == "disabled_rules":
            merged.lint.disabled_rules = [str(item).upper() for item in value]
        elif key == "fix_rules":
            merged.lint.fix_rules = [str(item).upper() for item in value]
        elif key == "project_dir":
            merged.project.src_dir = str(value)
        elif key == "main_file":
            merged.project.main_file = str(value)
        elif key == "s2_api_key":
            merged.verify.s2_api_key = str(value)
        elif key == "timeout":
            merged.verify.timeout = int(value)
        elif key == "skip_keys":
            merged.verify.skip_keys = [str(item) for item in value]
        elif key == "max_concurrent":
            merged.verify.max_concurrent = int(value)
        elif key == "target_lang":
            merged.translate.target_lang = str(value)
        elif key == "glossary":
            merged.translate.glossary = {str(k): str(v) for k, v in value.items()}
        elif key == "query":
            merged.survey.default_topic = str(value)
        elif key == "max_results":
            merged.survey.max_results = int(value)
        elif key == "source":
            merged.survey.sources = [str(item) for item in value]
    return merged


def generate_default_config(project_dir: str | Path | None = None) -> str:
    """Generate a commented default config file, with optional project detection."""
    detected_main = None
    detected_bibs: list[str] = []
    if project_dir is not None:
        detected_main, detected_bibs = _detect_project_files(Path(project_dir))

    main_file_value = f'"{detected_main}"' if detected_main else '""'
    bib_files_value = (
        "[" + ", ".join(f'"{bib_file}"' for bib_file in detected_bibs) + "]"
        if detected_bibs
        else "[]"
    )

    return f"""# Hypo-Research project config

[project]
main_file = {main_file_value}
bib_files = {bib_files_value}
# src_dir = "src"

[lint]
disabled_rules = []
enabled_rules = []
fix_rules = []

[lint.severity_overrides]
# L05 = "warning"

[verify]
# s2_api_key = "your-key-here"
timeout = 30
skip_keys = []
max_concurrent = 5

[translate]
target_lang = "zh"

[translate.glossary]

[survey]
default_topic = ""
max_results = 100
sources = ["s2", "arxiv"]
"""


def detect_project_config_values(project_dir: str | Path) -> tuple[str | None, list[str]]:
    """Detect likely main tex and bib files for config initialization."""
    return _detect_project_files(Path(project_dir))


def _detect_project_files(project_dir: Path) -> tuple[str | None, list[str]]:
    directory = project_dir.expanduser().resolve()
    main_candidates = [
        path.name
        for path in sorted(directory.glob("*.tex"))
        if path.is_file() and _contains_documentclass(path)
    ]
    if "main.tex" in main_candidates:
        main_file = "main.tex"
    else:
        main_file = main_candidates[0] if main_candidates else None
    bib_files = [path.name for path in sorted(directory.glob("*.bib")) if path.is_file()]
    return main_file, bib_files


def _contains_documentclass(tex_file: Path) -> bool:
    text = tex_file.read_text(encoding="utf-8")
    for raw_line in text.splitlines():
        code = raw_line.split("%", 1)[0]
        if _DOCUMENTCLASS_RE.search(code):
            return True
    return False


def _warn_unknown_sections(data: dict[str, Any]) -> None:
    for section_name, section_value in data.items():
        if section_name not in _SECTION_FIELDS:
            warnings.warn(f"Unknown config section: {section_name}", stacklevel=2)
            continue
        if not isinstance(section_value, dict):
            warnings.warn(f"Config section '{section_name}' must be a table", stacklevel=2)
            continue
        for key in section_value:
            if key not in _SECTION_FIELDS[section_name]:
                warnings.warn(
                    f"Unknown config field '{section_name}.{key}'",
                    stacklevel=2,
                )


def _coerce_section(value: Any, section_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        warnings.warn(f"Config section '{section_name}' must be a table", stacklevel=2)
        return {}
    return value


def _coerce_optional_str(value: Any) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _coerce_str_dict(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): str(val) for key, val in value.items()}


def _coerce_int(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_rule_list(value: Any) -> list[str]:
    return [item.upper() for item in _coerce_str_list(value)]
