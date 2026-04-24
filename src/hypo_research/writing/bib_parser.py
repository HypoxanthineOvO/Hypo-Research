"""BibTeX parsing helpers for static linting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class BibEntryInfo:
    """Structured BibTeX entry metadata."""

    key: str
    entry_type: str
    fields: dict[str, str]
    missing_fields: list[str]
    file: str = ""
    line: int = 0
    source_file: str = ""


_REQUIRED_FIELDS: dict[str, list[str]] = {
    "article": ["title", "author", "year", "journal", "doi"],
    "inproceedings": ["title", "author", "year", "booktitle", "doi"],
    "misc": ["title", "author", "year"],
    "online": ["title", "author", "year"],
    "book": ["title", "author", "year", "publisher"],
    "phdthesis": ["title", "author", "year", "school"],
    "mastersthesis": ["title", "author", "year", "school"],
}


def parse_bib(path: str) -> list[BibEntryInfo]:
    """Parse a BibTeX file into normalized entry records."""
    bib_path = Path(path)
    text = bib_path.read_text(encoding="utf-8")
    entries: list[BibEntryInfo] = []
    string_macros: dict[str, str] = {}

    for entry_type, start_index, body in _iter_entries(text):
        line = text.count("\n", 0, start_index) + 1
        normalized_type = entry_type.lower()
        if normalized_type in {"comment", "preamble"}:
            continue
        if normalized_type == "string":
            macro_fields = _parse_fields(body, string_macros)
            string_macros.update(macro_fields)
            continue

        key, fields_body = _split_key_and_fields(body)
        if not key:
            continue

        fields = _parse_fields(fields_body, string_macros)
        missing_fields = [
            field_name
            for field_name in _REQUIRED_FIELDS.get(normalized_type, [])
            if not fields.get(field_name)
        ]
        entries.append(
            BibEntryInfo(
                key=key,
                entry_type=normalized_type,
                fields=fields,
                missing_fields=missing_fields,
                file=bib_path.as_posix(),
                line=line,
                source_file=bib_path.as_posix(),
            )
        )

    return entries


def parse_bib_files(bib_paths: list[str | Path]) -> list[BibEntryInfo]:
    """Parse multiple BibTeX files and merge entries by key."""
    merged: dict[str, BibEntryInfo] = {}
    for bib_path in bib_paths:
        for entry in parse_bib(str(bib_path)):
            existing = merged.get(entry.key)
            if existing is None or _entry_completeness(entry) >= _entry_completeness(existing):
                merged[entry.key] = entry
    return sorted(merged.values(), key=lambda entry: entry.key)


def _entry_completeness(entry: BibEntryInfo) -> tuple[int, int]:
    return (len(entry.fields), -len(entry.missing_fields))


def _iter_entries(text: str) -> list[tuple[str, int, str]]:
    entries: list[tuple[str, int, str]] = []
    index = 0
    length = len(text)
    while index < length:
        at_index = text.find("@", index)
        if at_index == -1:
            break
        type_start = at_index + 1
        while type_start < length and text[type_start].isspace():
            type_start += 1
        type_end = type_start
        while type_end < length and (text[type_end].isalpha() or text[type_end] in {"_"}):
            type_end += 1
        entry_type = text[type_start:type_end]
        if not entry_type:
            index = at_index + 1
            continue
        while type_end < length and text[type_end].isspace():
            type_end += 1
        if type_end >= length or text[type_end] not in {"{", "("}:
            index = at_index + 1
            continue
        delimiter = text[type_end]
        closing = "}" if delimiter == "{" else ")"
        body_end = _find_matching_delimiter(text, type_end, delimiter, closing)
        if body_end == -1:
            break
        body = text[type_end + 1 : body_end]
        entries.append((entry_type, at_index, body))
        index = body_end + 1
    return entries


def _find_matching_delimiter(
    text: str,
    open_index: int,
    opening: str,
    closing: str,
) -> int:
    depth = 0
    in_quotes = False
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_quotes = not in_quotes
            continue
        if in_quotes:
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index
    return -1


def _split_key_and_fields(body: str) -> tuple[str, str]:
    in_quotes = False
    depth = 0
    for index, char in enumerate(body):
        if char == '"' and (index == 0 or body[index - 1] != "\\"):
            in_quotes = not in_quotes
            continue
        if in_quotes:
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth = max(depth - 1, 0)
            continue
        if char == "," and depth == 0:
            return body[:index].strip(), body[index + 1 :]
    return body.strip(), ""


def _parse_fields(body: str, string_macros: dict[str, str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    length = len(body)
    while index < length:
        while index < length and (body[index].isspace() or body[index] == ","):
            index += 1
        if index >= length:
            break

        name_start = index
        while index < length and (body[index].isalnum() or body[index] in {"_", "-"}):
            index += 1
        field_name = body[name_start:index].strip().lower()
        if not field_name:
            break

        while index < length and body[index].isspace():
            index += 1
        if index >= length or body[index] != "=":
            break
        index += 1

        value, index = _parse_value_expression(body, index, string_macros)
        fields[field_name] = value

    return fields


def _parse_value_expression(
    body: str,
    index: int,
    string_macros: dict[str, str],
) -> tuple[str, int]:
    parts: list[str] = []
    length = len(body)
    while index < length:
        while index < length and body[index].isspace():
            index += 1
        if index >= length:
            break
        value, index = _parse_single_value(body, index, string_macros)
        if value:
            parts.append(value)
        while index < length and body[index].isspace():
            index += 1
        if index < length and body[index] == "#":
            index += 1
            continue
        break
    return "".join(parts).strip(), index


def _parse_single_value(
    body: str,
    index: int,
    string_macros: dict[str, str],
) -> tuple[str, int]:
    if index >= len(body):
        return "", index

    char = body[index]
    if char == "{":
        end_index = _find_matching_delimiter(body, index, "{", "}")
        if end_index == -1:
            return body[index + 1 :].strip(), len(body)
        value = body[index + 1 : end_index]
        return _strip_outer_braces(value.strip()), end_index + 1

    if char == '"':
        end_index = index + 1
        escaped = False
        while end_index < len(body):
            current = body[end_index]
            if escaped:
                escaped = False
            elif current == "\\":
                escaped = True
            elif current == '"':
                break
            end_index += 1
        value = body[index + 1 : end_index]
        return value.strip(), min(end_index + 1, len(body))

    token_start = index
    while index < len(body) and body[index] not in {",", "#", "\n", "\r"}:
        if body[index].isspace():
            break
        index += 1
    token = body[token_start:index].strip()
    if not token:
        return "", index
    return string_macros.get(token.lower(), token), index


def _strip_outer_braces(value: str) -> str:
    cleaned = value.strip()
    while cleaned.startswith("{") and cleaned.endswith("}") and _is_balanced_braces(cleaned[1:-1]):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _is_balanced_braces(value: str) -> bool:
    depth = 0
    escaped = False
    for char in value:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0
