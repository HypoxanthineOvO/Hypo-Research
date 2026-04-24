"""Multi-file LaTeX project resolution helpers."""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass
from pathlib import Path


_DOCUMENTCLASS_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\{[^}]+\}")
_INCLUDE_RE = re.compile(r"\\(?P<kind>input|include)\{(?P<target>[^}]+)\}")
_BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\{(?P<targets>[^}]+)\}")
_ADDBIBRESOURCE_RE = re.compile(r"\\addbibresource(?:\[[^\]]*\])?\{(?P<target>[^}]+)\}")
_RAW_ENV_BEGIN_RE = re.compile(r"\\begin\{(?P<name>[^}]+)\}")
_RAW_ENV_END_RE = re.compile(r"\\end\{(?P<name>[^}]+)\}")
_RAW_ENVIRONMENTS = {"verbatim", "lstlisting", "minted", "Verbatim"}
_FILE_MARKER_TEMPLATE = "%% === FILE: {path} ==="


class CircularInputError(Exception):
    """Raised when \\input/\\include creates a cycle."""


class MultipleMainFilesError(Exception):
    """Raised when multiple \\documentclass files found and none is main.tex."""


@dataclass
class TexFile:
    """A single .tex file within a project."""

    path: Path
    abs_path: Path
    line_offset: int
    line_count: int
    content: str


@dataclass
class TexProject:
    """A resolved multi-file LaTeX project."""

    root_file: Path
    project_dir: Path
    files: list[TexFile]
    bib_files: list[Path]
    merged_content: str


def resolve_project(tex_path: str | Path) -> TexProject:
    """Resolve a LaTeX file into a single-file or multi-file project."""
    input_path = Path(tex_path).expanduser()
    if not input_path.is_absolute():
        input_path = input_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"LaTeX file not found: {tex_path}")
    if input_path.is_dir():
        root_file = _find_main_file_for_directory(input_path)
        if root_file is None:
            raise FileNotFoundError(f"No .tex main file found under: {tex_path}")
        input_path = root_file

    root_file = input_path if _is_main_file(input_path) else _search_main_file(input_path)
    if root_file is None:
        return _build_single_file_project(input_path)

    project = _build_project(root_file.resolve())
    if len(project.files) == 1 and project.files[0].abs_path == root_file.resolve():
        return _build_single_file_project(root_file.resolve())
    return project


def virtual_to_real(project: TexProject, virtual_line: int) -> tuple[str, int]:
    """Map a merged-content line back to its source file and 1-based line number."""
    line_map: list[tuple[str, int] | None] = getattr(project, "_line_map", [])
    if 0 <= virtual_line < len(line_map):
        mapped = line_map[virtual_line]
        if mapped is not None:
            return mapped

    for tex_file in project.files:
        if tex_file.line_offset <= virtual_line < tex_file.line_offset + tex_file.line_count:
            return (
                tex_file.path.as_posix(),
                virtual_line - tex_file.line_offset + 1,
            )

    raise ValueError(f"Virtual line {virtual_line} does not map to a source line")


def _build_project(root_file: Path) -> TexProject:
    project_dir = root_file.parent.resolve()
    file_records: dict[Path, TexFile] = {}
    file_order: list[Path] = []
    merged_lines: list[str] = []
    line_map: list[tuple[str, int] | None] = []

    _expand_file(
        tex_file=root_file,
        project_dir=project_dir,
        file_records=file_records,
        file_order=file_order,
        merged_lines=merged_lines,
        line_map=line_map,
        stack=[],
    )

    files = [file_records[path] for path in file_order]
    for tex_file in files:
        if tex_file.line_offset < 0:
            tex_file.line_offset = 0
    merged_content = "\n".join(merged_lines)
    if merged_lines:
        merged_content += "\n"

    project = TexProject(
        root_file=root_file,
        project_dir=project_dir,
        files=files,
        bib_files=_discover_bib_files(merged_lines, project_dir),
        merged_content=merged_content,
    )
    setattr(project, "_line_map", line_map)
    return project


def _build_single_file_project(tex_file: Path) -> TexProject:
    abs_path = tex_file.resolve()
    content = abs_path.read_text(encoding="utf-8")
    raw_lines = content.splitlines()
    project = TexProject(
        root_file=abs_path,
        project_dir=abs_path.parent,
        files=[
            TexFile(
                path=Path(abs_path.name),
                abs_path=abs_path,
                line_offset=0,
                line_count=len(raw_lines),
                content=content,
            )
        ],
        bib_files=_discover_bib_files(raw_lines, abs_path.parent),
        merged_content=content,
    )
    setattr(
        project,
        "_line_map",
        [(abs_path.name, line_number) for line_number in range(1, len(raw_lines) + 1)],
    )
    return project


def _expand_file(
    *,
    tex_file: Path,
    project_dir: Path,
    file_records: dict[Path, TexFile],
    file_order: list[Path],
    merged_lines: list[str],
    line_map: list[tuple[str, int] | None],
    stack: list[Path],
) -> None:
    tex_file = tex_file.resolve()
    if tex_file in stack:
        cycle = " -> ".join(path.relative_to(project_dir).as_posix() for path in [*stack, tex_file])
        raise CircularInputError(f"Circular \\input/\\include detected: {cycle}")

    content = tex_file.read_text(encoding="utf-8")
    raw_lines = content.splitlines()
    rel_path = tex_file.relative_to(project_dir)
    file_record = file_records.get(tex_file)
    if file_record is None:
        file_record = TexFile(
            path=rel_path,
            abs_path=tex_file,
            line_offset=-1,
            line_count=len(raw_lines),
            content=content,
        )
        file_records[tex_file] = file_record
        file_order.append(tex_file)

    _append_generated_line(
        _FILE_MARKER_TEMPLATE.format(path=rel_path.as_posix()),
        merged_lines=merged_lines,
        line_map=line_map,
    )

    active_raw_envs: list[str] = []
    stack.append(tex_file)
    try:
        for line_number, raw_line in enumerate(raw_lines, start=1):
            code_line = _strip_comments(raw_line)
            stripped_code = code_line.strip()
            in_raw_env = bool(active_raw_envs)

            if not in_raw_env:
                include_match = _single_include_match(stripped_code)
                if include_match is not None:
                    if include_match.group("kind") == "include":
                        _append_generated_line("\\clearpage", merged_lines=merged_lines, line_map=line_map)
                    target_path = _resolve_tex_target(project_dir, include_match.group("target"))
                    if target_path.exists():
                        _expand_file(
                            tex_file=target_path,
                            project_dir=project_dir,
                            file_records=file_records,
                            file_order=file_order,
                            merged_lines=merged_lines,
                            line_map=line_map,
                            stack=stack,
                        )
                    else:
                        warnings.warn(
                            f"Missing LaTeX input file: {include_match.group('target')}",
                            stacklevel=2,
                        )
                    if include_match.group("kind") == "include":
                        _append_generated_line("\\clearpage", merged_lines=merged_lines, line_map=line_map)
                    continue

            if file_record.line_offset == -1:
                file_record.line_offset = len(merged_lines)

            merged_lines.append(raw_line)
            line_map.append((rel_path.as_posix(), line_number))

            if not in_raw_env:
                begin_match = _RAW_ENV_BEGIN_RE.search(code_line)
                if begin_match and begin_match.group("name") in _RAW_ENVIRONMENTS:
                    active_raw_envs.append(begin_match.group("name"))
            else:
                end_match = _RAW_ENV_END_RE.search(code_line)
                if end_match and active_raw_envs and end_match.group("name") == active_raw_envs[-1]:
                    active_raw_envs.pop()
    finally:
        stack.pop()


def _append_generated_line(
    line: str,
    *,
    merged_lines: list[str],
    line_map: list[tuple[str, int] | None],
) -> None:
    merged_lines.append(line)
    line_map.append(None)


def _single_include_match(stripped_code: str) -> re.Match[str] | None:
    if not stripped_code:
        return None
    match = _INCLUDE_RE.fullmatch(stripped_code)
    return match


def _search_main_file(tex_file: Path) -> Path | None:
    candidate_roots: list[Path] = []
    current_dir = tex_file.parent.resolve()
    for _ in range(4):
        candidate_roots.extend(_find_main_files_in_directory(current_dir))
        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent

    if not candidate_roots:
        return None

    deduped = list(dict.fromkeys(path.resolve() for path in candidate_roots))
    if len(deduped) == 1:
        return deduped[0]

    main_candidates = [path for path in deduped if path.name == "main.tex"]
    if len(main_candidates) == 1:
        return main_candidates[0]

    candidates = ", ".join(path.as_posix() for path in deduped)
    raise MultipleMainFilesError(
        f"Multiple LaTeX main files found: {candidates}. Please specify the root file explicitly."
    )


def _find_main_file_for_directory(project_dir: Path) -> Path | None:
    roots = _find_main_files_in_directory(project_dir.resolve())
    if not roots:
        main_candidate = project_dir / "main.tex"
        return main_candidate.resolve() if main_candidate.exists() else None
    if len(roots) == 1:
        return roots[0]
    named_main = [path for path in roots if path.name == "main.tex"]
    if len(named_main) == 1:
        return named_main[0]
    candidates = ", ".join(path.as_posix() for path in roots)
    raise MultipleMainFilesError(
        f"Multiple LaTeX main files found in {project_dir}: {candidates}."
    )


def _find_main_files_in_directory(directory: Path) -> list[Path]:
    return [
        path.resolve()
        for path in sorted(directory.glob("*.tex"))
        if path.is_file() and _is_main_file(path)
    ]


def _is_main_file(tex_file: Path) -> bool:
    return _contains_documentclass(tex_file.read_text(encoding="utf-8"))


def _contains_documentclass(content: str) -> bool:
    active_raw_envs: list[str] = []
    for raw_line in content.splitlines():
        code_line = _strip_comments(raw_line)
        if active_raw_envs:
            end_match = _RAW_ENV_END_RE.search(code_line)
            if end_match and end_match.group("name") == active_raw_envs[-1]:
                active_raw_envs.pop()
            continue

        if _DOCUMENTCLASS_RE.search(code_line):
            return True

        begin_match = _RAW_ENV_BEGIN_RE.search(code_line)
        if begin_match and begin_match.group("name") in _RAW_ENVIRONMENTS:
            active_raw_envs.append(begin_match.group("name"))
    return False


def _resolve_tex_target(project_dir: Path, target: str) -> Path:
    tex_target = Path(target.strip())
    if tex_target.suffix != ".tex":
        tex_target = tex_target.with_suffix(".tex")
    return (project_dir / tex_target).resolve()


def _discover_bib_files(lines: list[str], project_dir: Path) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()
    for raw_line in lines:
        code_line = _strip_comments(raw_line)
        for match in _BIBLIOGRAPHY_RE.finditer(code_line):
            for target in _split_csv_targets(match.group("targets")):
                _append_bib_target(target, project_dir, discovered, seen)
        for match in _ADDBIBRESOURCE_RE.finditer(code_line):
            _append_bib_target(match.group("target"), project_dir, discovered, seen)
    return discovered


def _append_bib_target(
    target: str,
    project_dir: Path,
    discovered: list[Path],
    seen: set[Path],
) -> None:
    bib_path = _resolve_bib_target(project_dir, target)
    if bib_path not in seen:
        if not bib_path.exists():
            warnings.warn(f"Missing BibTeX file: {bib_path}", stacklevel=2)
        discovered.append(bib_path)
        seen.add(bib_path)


def _resolve_bib_target(project_dir: Path, target: str) -> Path:
    bib_target = Path(target.strip())
    if bib_target.suffix != ".bib":
        bib_target = bib_target.with_suffix(".bib")
    return (project_dir / bib_target).resolve()


def _split_csv_targets(value: str) -> list[str]:
    return [candidate.strip() for candidate in value.split(",") if candidate.strip()]


def _strip_comments(line: str) -> str:
    escaped = False
    result: list[str] = []
    for char in line:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            continue
        if char == "%":
            break
        result.append(char)
    return "".join(result)
