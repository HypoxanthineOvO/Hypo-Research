"""Resolve paper targets from files, directories, and archives."""

from __future__ import annotations

import tarfile
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class PaperTargetError(ValueError):
    """Raised when a paper target cannot be resolved unambiguously."""


ARCHIVE_SUFFIXES = {
    ".zip",
    ".tar",
    ".tgz",
    ".tar.gz",
    ".tbz",
    ".tbz2",
    ".tar.bz2",
    ".txz",
    ".tar.xz",
}


@contextmanager
def resolve_paper_target(
    target: str | Path,
    *,
    prefer: tuple[str, ...] = ("latex", "pdf"),
) -> Iterator[Path]:
    """Yield the resolved paper file for a file, directory, or archive target."""
    input_path = Path(target).expanduser()
    if not input_path.is_absolute():
        input_path = input_path.resolve()
    if not input_path.exists():
        raise PaperTargetError(f"Paper target not found: {target}")

    if _is_archive(input_path):
        with tempfile.TemporaryDirectory(prefix="hypo-paper-target-") as tmp:
            extract_dir = Path(tmp)
            _extract_archive(input_path, extract_dir)
            yield _select_from_path(extract_dir, prefer=prefer)
        return

    yield _select_from_path(input_path, prefer=prefer)


def _select_from_path(path: Path, *, prefer: tuple[str, ...]) -> Path:
    if path.is_file():
        kind = _file_kind(path)
        if kind in prefer:
            return path.resolve()
        expected = " or ".join(_suffixes_for_preference(prefer))
        raise PaperTargetError(f"Unsupported paper target file: {path}. Expected {expected}.")

    if not path.is_dir():
        raise PaperTargetError(f"Unsupported paper target: {path}")

    candidates_by_kind = {
        "latex": _latex_candidates(path),
        "pdf": _pdf_candidates(path),
    }
    for kind in prefer:
        candidates = candidates_by_kind.get(kind, [])
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            rendered = ", ".join(_display_path(candidate, path) for candidate in candidates)
            raise PaperTargetError(
                f"Multiple {kind} paper targets found in {path}: {rendered}. "
                "Please specify the exact file."
            )

    expected = " or ".join(_suffixes_for_preference(prefer))
    raise PaperTargetError(f"No {expected} paper target found under: {path}")


def _latex_candidates(directory: Path) -> list[Path]:
    tex_files = [path.resolve() for path in sorted(directory.rglob("*.tex")) if path.is_file()]
    main_files = [path for path in tex_files if _contains_documentclass(path)]
    if not main_files:
        return []
    named = [path for path in main_files if path.name.lower() in {"main.tex", "paper.tex", "ms.tex", "manuscript.tex"}]
    if len(named) == 1:
        return named
    if len(main_files) == 1:
        return main_files
    return main_files


def _pdf_candidates(directory: Path) -> list[Path]:
    return [path.resolve() for path in sorted(directory.rglob("*.pdf")) if path.is_file()]


def _contains_documentclass(path: Path) -> bool:
    try:
        return "\\documentclass" in path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False


def _file_kind(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".tex":
        return "latex"
    if suffix == ".pdf":
        return "pdf"
    return None


def _suffixes_for_preference(prefer: tuple[str, ...]) -> list[str]:
    suffixes = []
    if "latex" in prefer:
        suffixes.append(".tex")
    if "pdf" in prefer:
        suffixes.append(".pdf")
    return suffixes


def _is_archive(path: Path) -> bool:
    name = path.name.lower()
    return any(name.endswith(suffix) for suffix in ARCHIVE_SUFFIXES)


def _extract_archive(archive: Path, destination: Path) -> None:
    if archive.name.lower().endswith(".zip"):
        with zipfile.ZipFile(archive) as handle:
            for member in handle.infolist():
                _validate_archive_member(destination, member.filename)
            handle.extractall(destination)
        return

    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as handle:
            members = handle.getmembers()
            for member in members:
                _validate_archive_member(destination, member.name)
            handle.extractall(destination, members=members)
        return

    raise PaperTargetError(f"Unsupported archive format: {archive}")


def _validate_archive_member(destination: Path, member_name: str) -> None:
    member_path = (destination / member_name).resolve()
    destination_resolved = destination.resolve()
    if member_path != destination_resolved and destination_resolved not in member_path.parents:
        raise PaperTargetError(f"Archive member escapes extraction directory: {member_name}")


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
