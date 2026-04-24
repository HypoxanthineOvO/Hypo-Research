"""Auto-fix engine for LaTeX lint issues."""

from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from hypo_research.writing.project import TexProject
from hypo_research.writing.stats import TexStats


_FIXABLE_RULES = {"L01", "L02", "L03", "L04", "L05", "L06", "L11", "L13"}
_RULE_PRIORITY = {
    "L03": 10,
    "L01": 20,
    "L02": 30,
    "L04": 40,
    "L05": 50,
    "L06": 60,
    "L11": 70,
    "L13": 80,
}
_REDUNDANT_PREFIX_WORDS = (
    "Figure",
    "Fig\\.",
    "Table",
    "Tab\\.",
    "Section",
    "Sec\\.",
    "Equation",
    "Eq\\.",
    "Algorithm",
    "Alg\\.",
    "Theorem",
    "Lemma",
    "Chapter",
    "Appendix",
)
_REDUNDANT_PREFIX_RE = re.compile(
    rf"(?P<prefix>{'|'.join(_REDUNDANT_PREFIX_WORDS)})\s*~?\s*(?P<command>\\(?:ref|cref|autoref)\{{[^}}]+\}})"
)
_REF_RE = re.compile(r"(?<![A-Za-z])\\ref\{([^}]+)\}")
_REF_CAP_RE = re.compile(r"(?<![A-Za-z])\\Ref\{([^}]+)\}")
_FLOAT_RE = re.compile(r"(?P<prefix>\s*\\begin\{(?P<name>figure\*?|table\*?)\})(?P<suffix>\s*)$")
_SECTION_CMD_RE = re.compile(
    r"(?P<indent>\s*)\\(?P<command>section|subsection|subsubsection)\*?\{(?P<title>[^}]*)\}"
)
_CAPTION_CMD_RE = re.compile(
    r"(?P<indent>\s*)\\caption(?:\[[^\]]*\])?\{(?P<title>[^}]*)\}"
)
_LABEL_RE = re.compile(r"\\label\{(?P<label>[^}]+)\}")
_TBLR_BEGIN_RE = re.compile(r"\\begin\{tblr\}")
_TBLR_END_RE = re.compile(r"\\end\{tblr\}")
_BOOKTABS_TO_HLINE = {
    r"\toprule": r"\hline",
    r"\midrule": r"\hline",
    r"\bottomrule": r"\hline",
}
_SMALL_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "but",
    "or",
    "nor",
    "for",
    "yet",
    "so",
    "in",
    "on",
    "at",
    "to",
    "of",
    "by",
    "up",
    "as",
    "is",
    "if",
}


class FixAction(Enum):
    """Auto-fix operation kinds."""

    REPLACE = "replace"
    DELETE_LINE = "delete"
    INSERT = "insert"


@dataclass
class Fix:
    """A single auto-fix operation."""

    rule: str
    file: str
    line: int
    action: FixAction
    original: str
    replacement: str
    description: str
    abs_path: str = field(default="", repr=False)


@dataclass
class FixReport:
    """Summary of all fixes applied or proposed."""

    fixes: list[Fix]
    files_modified: list[str]
    backup_paths: list[str] = field(default_factory=list)
    dry_run: bool = True
    errors: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "fixes": [
                {
                    "rule": fix.rule,
                    "file": fix.file,
                    "line": fix.line,
                    "action": fix.action.value,
                    "original": fix.original,
                    "replacement": fix.replacement,
                    "description": fix.description,
                }
                for fix in self.fixes
            ],
            "files_modified": self.files_modified,
            "backup_paths": self.backup_paths,
            "dry_run": self.dry_run,
            "errors": self.errors,
            "total_fixes": len(self.fixes),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), ensure_ascii=False, indent=2)


def generate_fixes(
    stats: TexStats,
    project: TexProject | None = None,
    rules: list[str] | None = None,
) -> list[Fix]:
    """Generate auto-fix operations from lint statistics and source files."""
    enabled_rules = _normalize_rules(rules)
    file_infos = _collect_file_infos(stats, project)
    deletable_orphan_labels = {
        label.name
        for label in stats.labels
        if label.name in set(stats.orphan_labels) and not label.name.startswith("sec:")
    }
    fixes: list[Fix] = []

    for file_info in file_infos:
        fixes.extend(
            _generate_file_fixes(
                file_info=file_info,
                orphan_labels=deletable_orphan_labels,
                enabled_rules=enabled_rules,
            )
        )

    fixes.sort(
        key=lambda fix: (
            fix.file,
            fix.line,
            _RULE_PRIORITY.get(fix.rule, 999),
        )
    )
    return _dedupe_and_validate_fixes(fixes)


def apply_fixes(
    fixes: list[Fix],
    project: TexProject | None = None,
    *,
    dry_run: bool = True,
    backup: bool = False,
) -> FixReport:
    """Apply generated fixes to source files."""
    grouped: dict[str, list[Fix]] = defaultdict(list)
    for fix in fixes:
        abs_path = _resolve_fix_path(fix, project)
        grouped[abs_path.as_posix()].append(fix)

    backup_paths: list[str] = []
    files_modified: list[str] = []
    errors: list[str] = []

    for abs_path_str, file_fixes in grouped.items():
        file_path = Path(abs_path_str)
        if not file_path.exists():
            errors.append(f"Missing file for fixes: {file_path}")
            continue

        original_lines = file_path.read_text(encoding="utf-8").splitlines()
        lines = list(original_lines)
        changed = False
        fixes_by_line: dict[int, list[Fix]] = defaultdict(list)
        for fix in sorted(
            file_fixes,
            key=lambda item: (item.line, _RULE_PRIORITY.get(item.rule, 999)),
            reverse=True,
        ):
            fixes_by_line[fix.line].append(fix)

        for line_number in sorted(fixes_by_line, reverse=True):
            line_index = line_number - 1
            if not (0 <= line_index < len(lines)):
                errors.append(f"Line out of range for {file_path}: {line_number}")
                continue

            current_line = lines[line_index]
            line_changed = False
            deleted_line = False
            for fix in sorted(
                fixes_by_line[line_number],
                key=lambda item: _RULE_PRIORITY.get(item.rule, 999),
            ):
                if fix.action == FixAction.DELETE_LINE:
                    if current_line != fix.original:
                        errors.append(_mismatch_message(file_path, fix, current_line))
                        continue
                    del lines[line_index]
                    if (
                        0 < line_index < len(lines)
                        and lines[line_index - 1].strip() == ""
                        and lines[line_index].strip() == ""
                    ):
                        del lines[line_index]
                    current_line = ""
                    changed = True
                    line_changed = True
                    deleted_line = True
                    break

                if fix.action == FixAction.INSERT:
                    insertion_index = min(line_index + 1, len(lines))
                    lines.insert(insertion_index, fix.replacement)
                    changed = True
                    line_changed = True
                    continue

                if fix.original not in current_line:
                    errors.append(_mismatch_message(file_path, fix, current_line))
                    continue
                current_line = current_line.replace(fix.original, fix.replacement, 1)
                lines[line_index] = current_line
                changed = True
                line_changed = True

            if line_changed and not deleted_line and line_index < len(lines):
                lines[line_index] = current_line

        if not changed:
            continue

        files_modified.append(_display_file_for_report(file_fixes[0], file_path, project))
        if dry_run:
            continue

        if backup:
            backup_path = Path(f"{file_path.as_posix()}.bak")
            shutil.copy2(file_path, backup_path)
            backup_paths.append(backup_path.as_posix())

        file_path.write_text(_join_lines_preserve_trailing_newline(lines, original_lines), encoding="utf-8")

    return FixReport(
        fixes=fixes,
        files_modified=files_modified,
        backup_paths=backup_paths,
        dry_run=dry_run,
        errors=errors,
    )


def _generate_file_fixes(
    *,
    file_info: dict[str, Any],
    orphan_labels: set[str],
    enabled_rules: set[str],
) -> list[Fix]:
    raw_lines = file_info["lines"]
    display_file = file_info["file"]
    abs_path = file_info["abs_path"]
    fixes: list[Fix] = []
    in_tblr = False

    for line_number, raw_line in enumerate(raw_lines, start=1):
        current_line = raw_line

        if _TBLR_BEGIN_RE.search(_strip_comments(current_line)):
            in_tblr = True

        if "L03" in enabled_rules:
            updated = _remove_redundant_prefix(current_line)
            if updated != current_line:
                fixes.append(
                    Fix(
                        rule="L03",
                        file=display_file,
                        line=line_number,
                        action=FixAction.REPLACE,
                        original=current_line,
                        replacement=updated,
                        description="Remove redundant prefix before reference",
                        abs_path=abs_path.as_posix(),
                    )
                )
                current_line = updated

        if "L01" in enabled_rules:
            updated = _replace_ref_with_cref(current_line)
            if updated != current_line:
                fixes.append(
                    Fix(
                        rule="L01",
                        file=display_file,
                        line=line_number,
                        action=FixAction.REPLACE,
                        original=current_line,
                        replacement=updated,
                        description="\\ref → \\cref",
                        abs_path=abs_path.as_posix(),
                    )
                )
                current_line = updated

        if "L02" in enabled_rules:
            updated = _insert_nbsp_before_cite(current_line)
            if updated != current_line:
                fixes.append(
                    Fix(
                        rule="L02",
                        file=display_file,
                        line=line_number,
                        action=FixAction.REPLACE,
                        original=current_line,
                        replacement=updated,
                        description="Insert ~ before \\cite",
                        abs_path=abs_path.as_posix(),
                    )
                )
                current_line = updated

        if "L04" in enabled_rules:
            updated = _add_float_placement(current_line)
            if updated != current_line:
                fixes.append(
                    Fix(
                        rule="L04",
                        file=display_file,
                        line=line_number,
                        action=FixAction.REPLACE,
                        original=current_line,
                        replacement=updated,
                        description="Add [htbp] to float environment",
                        abs_path=abs_path.as_posix(),
                    )
                )
                current_line = updated

        if "L05" in enabled_rules:
            updated = _title_case_commands(current_line)
            if updated != current_line:
                fixes.append(
                    Fix(
                        rule="L05",
                        file=display_file,
                        line=line_number,
                        action=FixAction.REPLACE,
                        original=current_line,
                        replacement=updated,
                        description="Normalize title/caption to Title Case",
                        abs_path=abs_path.as_posix(),
                    )
                )
                current_line = updated

        if "L11" in enabled_rules and in_tblr:
            updated = _replace_tblr_rules(current_line)
            if updated != current_line:
                fixes.append(
                    Fix(
                        rule="L11",
                        file=display_file,
                        line=line_number,
                        action=FixAction.REPLACE,
                        original=current_line,
                        replacement=updated,
                        description="Replace booktabs rules with \\hline in tblr",
                        abs_path=abs_path.as_posix(),
                    )
                )
                current_line = updated

        if "L13" in enabled_rules:
            updated = _insert_nbsp_before_cref(current_line)
            if updated != current_line:
                fixes.append(
                    Fix(
                        rule="L13",
                        file=display_file,
                        line=line_number,
                        action=FixAction.REPLACE,
                        original=current_line,
                        replacement=updated,
                        description="Insert ~ before \\cref",
                        abs_path=abs_path.as_posix(),
                    )
                )
                current_line = updated

        if "L06" in enabled_rules:
            fixes.extend(
                _generate_orphan_label_fixes(
                    line=current_line,
                    display_file=display_file,
                    abs_path=abs_path,
                    line_number=line_number,
                    orphan_labels=orphan_labels,
                )
            )

        if _TBLR_END_RE.search(_strip_comments(raw_line)):
            in_tblr = False

    return fixes


def _generate_orphan_label_fixes(
    *,
    line: str,
    display_file: str,
    abs_path: Path,
    line_number: int,
    orphan_labels: set[str],
) -> list[Fix]:
    fixes: list[Fix] = []
    for match in _LABEL_RE.finditer(_strip_comments(line)):
        label_name = match.group("label")
        if label_name not in orphan_labels:
            continue
        label_text = match.group(0)
        stripped = line.strip()
        if stripped == label_text:
            fixes.append(
                Fix(
                    rule="L06",
                    file=display_file,
                    line=line_number,
                    action=FixAction.DELETE_LINE,
                    original=line,
                    replacement="",
                    description=f"Delete orphan label {label_name}",
                    abs_path=abs_path.as_posix(),
                )
            )
        else:
            fixes.append(
                Fix(
                    rule="L06",
                    file=display_file,
                    line=line_number,
                    action=FixAction.REPLACE,
                    original=label_text,
                    replacement="",
                    description=f"Delete orphan label {label_name}",
                    abs_path=abs_path.as_posix(),
                )
            )
    return fixes


def _normalize_rules(rules: list[str] | None) -> set[str]:
    if rules is None:
        return set(_FIXABLE_RULES)
    return {rule.upper() for rule in rules if rule.upper() in _FIXABLE_RULES}


def _collect_file_infos(stats: TexStats, project: TexProject | None) -> list[dict[str, Any]]:
    if project is not None:
        return [
            {
                "file": tex_file.path.as_posix() if len(project.files) > 1 else "",
                "abs_path": tex_file.abs_path,
                "lines": tex_file.content.splitlines(),
            }
            for tex_file in project.files
        ]

    if not stats.files:
        return []

    if len(stats.files) == 1:
        abs_path = Path(stats.files[0]).resolve()
        return [
            {
                "file": "",
                "abs_path": abs_path,
                "lines": abs_path.read_text(encoding="utf-8").splitlines(),
            }
        ]

    return [
        {
            "file": path,
            "abs_path": Path(path).resolve(),
            "lines": Path(path).read_text(encoding="utf-8").splitlines(),
        }
        for path in stats.files
    ]


def _dedupe_and_validate_fixes(fixes: list[Fix]) -> list[Fix]:
    deduped: list[Fix] = []
    seen: set[tuple[str, int, str, str, str, str]] = set()
    for fix in fixes:
        key = (
            fix.abs_path,
            fix.line,
            fix.rule,
            fix.action.value,
            fix.original,
            fix.replacement,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fix)
    return deduped


def _resolve_fix_path(fix: Fix, project: TexProject | None) -> Path:
    if fix.abs_path:
        return Path(fix.abs_path)
    if project is not None and fix.file:
        return (project.project_dir / fix.file).resolve()
    if fix.file:
        return Path(fix.file).resolve()
    raise ValueError("Cannot resolve fix file path")


def _display_file_for_report(fix: Fix, file_path: Path, project: TexProject | None) -> str:
    if fix.file:
        return fix.file
    if project is not None and file_path.is_relative_to(project.project_dir):
        return file_path.relative_to(project.project_dir).as_posix()
    return file_path.as_posix()


def _mismatch_message(file_path: Path, fix: Fix, current_line: str) -> str:
    return (
        f"Skip {fix.rule} at {file_path}:{fix.line}: "
        f"expected {fix.original!r}, found {current_line!r}"
    )


def _join_lines_preserve_trailing_newline(lines: list[str], original_lines: list[str]) -> str:
    text = "\n".join(lines)
    if original_lines:
        text += "\n"
    return text


def _replace_ref_with_cref(line: str) -> str:
    line = _replace_in_code_part(line, lambda code: _REF_RE.sub(r"\\cref{\1}", code))
    return _replace_in_code_part(line, lambda code: _REF_CAP_RE.sub(r"\\Cref{\1}", code))


def _remove_redundant_prefix(line: str) -> str:
    def transform(code: str) -> str:
        return _REDUNDANT_PREFIX_RE.sub(lambda match: match.group("command"), code)

    return _replace_in_code_part(line, transform)


def _insert_nbsp_before_cite(line: str) -> str:
    cite_re = re.compile(r"(?P<prefix>[A-Za-z0-9}])\s*(?P<command>\\cite[a-zA-Z*]*\{)")
    return _replace_in_code_part(
        line,
        lambda code: cite_re.sub(lambda match: f"{match.group('prefix')}~{match.group('command')}", code),
    )


def _insert_nbsp_before_cref(line: str) -> str:
    cref_re = re.compile(r"(?P<prefix>[A-Za-z0-9}])\s+(?P<command>\\[cC]ref\{)")
    return _replace_in_code_part(
        line,
        lambda code: cref_re.sub(lambda match: f"{match.group('prefix')}~{match.group('command')}", code),
    )


def _add_float_placement(line: str) -> str:
    def transform(code: str) -> str:
        match = _FLOAT_RE.match(code)
        if match is None:
            return code
        return f"{match.group('prefix')}[htbp]{match.group('suffix')}"

    return _replace_in_code_part(line, transform)


def _title_case_commands(line: str) -> str:
    line = _replace_in_code_part(
        line,
        lambda code: _SECTION_CMD_RE.sub(
            lambda match: f"{match.group('indent')}\\{match.group('command')}{{{_title_case(match.group('title'))}}}",
            code,
        ),
    )
    return _replace_in_code_part(
        line,
        lambda code: _CAPTION_CMD_RE.sub(
            lambda match: match.group(0).replace(match.group("title"), _title_case(match.group("title")), 1),
            code,
        ),
    )


def _replace_tblr_rules(line: str) -> str:
    def transform(code: str) -> str:
        updated = code
        for original, replacement in _BOOKTABS_TO_HLINE.items():
            updated = updated.replace(original, replacement)
        return updated

    return _replace_in_code_part(line, transform)


def _title_case(text: str) -> str:
    parts = re.split(r"(\s+)", text)
    word_indices = [index for index, part in enumerate(parts) if part and not part.isspace()]
    if not word_indices:
        return text

    first_word_index = word_indices[0]
    last_word_index = word_indices[-1]
    for index in word_indices:
        parts[index] = _title_case_word(
            parts[index],
            force_capitalize=index in {first_word_index, last_word_index},
        )
    return "".join(parts)


def _title_case_word(word: str, *, force_capitalize: bool) -> str:
    stripped = word.strip()
    if not stripped:
        return word
    if stripped.startswith("\\") or stripped.startswith("{") or "$" in stripped:
        return word
    if stripped.isupper():
        return word

    prefix_match = re.match(r"^[^A-Za-z0-9]*", word)
    suffix_match = re.search(r"[^A-Za-z0-9]*$", word)
    prefix = prefix_match.group(0) if prefix_match else ""
    suffix = suffix_match.group(0) if suffix_match else ""
    core = word[len(prefix) : len(word) - len(suffix) if suffix else len(word)]
    if not core:
        return word

    lowered = core.lower()
    if not force_capitalize and lowered in _SMALL_WORDS:
        return f"{prefix}{lowered}{suffix}"
    return f"{prefix}{_capitalize_core(core)}{suffix}"


def _capitalize_core(core: str) -> str:
    pieces = core.split("-")
    capitalized: list[str] = []
    for piece in pieces:
        if not piece:
            capitalized.append(piece)
            continue
        capitalized.append(piece[0].upper() + piece[1:].lower())
    return "-".join(capitalized)


def _replace_in_code_part(line: str, transform: Any) -> str:
    code, comment = _split_comment(line)
    updated_code = transform(code)
    return updated_code + comment


def _split_comment(line: str) -> tuple[str, str]:
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "%":
            return line[:index], line[index:]
    return line, ""


def _strip_comments(line: str) -> str:
    return _split_comment(line)[0]
