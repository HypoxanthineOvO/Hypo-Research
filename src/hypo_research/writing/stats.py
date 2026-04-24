"""Static LaTeX structure extraction for linting."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from hypo_research.writing.bib_parser import BibEntryInfo, parse_bib, parse_bib_files
from hypo_research.writing.project import TexProject, resolve_project


_SECTION_RE = re.compile(r"\\(?P<level>section|subsection|subsubsection)\*?\{(?P<title>[^}]*)\}")
_BEGIN_RE = re.compile(r"\\begin\{(?P<name>[^}]+)\}(?P<placement>\[[^\]]*\])?")
_END_RE = re.compile(r"\\end\{(?P<name>[^}]+)\}")
_LABEL_RE = re.compile(r"\\label\{(?P<label>[^}]+)\}")
_CAPTION_RE = re.compile(r"\\caption(?:\[[^\]]*\])?\{")
_REF_RE = re.compile(
    r"\\(?P<kind>ref|cref|Cref|autoref|eqref|pageref|nameref|vref)\{(?P<targets>[^}]+)\}"
)
_HYPERREF_RE = re.compile(r"\\(?P<kind>hyperref)\[(?P<targets>[^\]]+)\]\{(?P<text>[^}]*)\}")
_CITE_RE = re.compile(r"\\cite\{(?P<targets>[^}]+)\}")
_BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\{(?P<targets>[^}]+)\}")
_ADDBIBRESOURCE_RE = re.compile(r"\\addbibresource\{(?P<target>[^}]+)\}")
_ABBR_RE = re.compile(r"\b[A-Z]{2,5}\b")
_EXPANSION_TEMPLATE = r"\b[A-Z][A-Za-z0-9\-]*(?: [A-Z][A-Za-z0-9\-]*){{1,8}} \({abbr}\)"
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_ABBREV_SPACING_PATTERNS = (
    (re.compile(r"\b(Fig|Tab|Eq)\. (?=\S)"), r"\1.\\ "),
    (re.compile(r"\bet al\. (?=\S)", re.IGNORECASE), r"et al.\\ "),
)
_COMMON_NON_ABBREVIATIONS = {
    "AND",
    "THE",
    "FOR",
    "WITH",
    "THIS",
    "THAT",
    "FROM",
    "INTO",
    "ONTO",
    "ARE",
    "WERE",
    "HAVE",
    "HAS",
    "USE",
    "USED",
    "FIG",
    "TAB",
    "EQ",
}
_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
_AUTO_FIXABLE_RULES = {"L01", "L02", "L03", "L04", "L05", "L06", "L11", "L13"}
_SECTION_LEVELS = {"section": 1, "subsection": 2, "subsubsection": 3}
_MATH_ENVIRONMENTS = {
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "math",
    "displaymath",
}
_SENTENCE_PLACEHOLDERS = {
    "Fig.": "Fig<DOT>",
    "Tab.": "Tab<DOT>",
    "Eq.": "Eq<DOT>",
    "et al.": "et al<DOT>",
    "i.e.": "i<DOT>e<DOT>",
    "e.g.": "e<DOT>g<DOT>",
    "vs.": "vs<DOT>",
    "etc.": "etc<DOT>",
}
DEFAULT_LABEL_PREFIXES = {
    "figure": "fig",
    "table": "tab",
    "section": "sec",
    "subsection": "sec",
    "chapter": "ch",
    "equation": "eq",
    "algorithm": "alg",
    "listing": "lst",
    "appendix": "app",
    "theorem": "thm",
    "lemma": "lem",
    "definition": "def",
    "proposition": "prop",
    "corollary": "cor",
    "remark": "rem",
    "example": "ex",
}
_VALID_LABEL_PREFIXES = {f"{prefix}:" for prefix in DEFAULT_LABEL_PREFIXES.values()}
_BILINGUAL_EXCLUDED_ENVIRONMENTS = {
    "tblr",
    "tabular",
    "longtblr",
    "IEEEbiography",
    "IEEEbiographynophoto",
}


@dataclass
class LabelInfo:
    name: str
    file: str = ""
    line: int = 0
    env: str = ""
    has_prefix: bool = False
    suggested_prefix: str = ""


@dataclass
class RefInfo:
    ref_type: str
    target: str
    file: str = ""
    line: int = 0
    has_tilde: bool = False

    @property
    def type(self) -> str:
        return self.ref_type


@dataclass
class FloatInfo:
    float_type: str
    file: str = ""
    line: int = 0
    placement: str = ""
    has_label: bool = False
    has_caption: bool = False
    label_before_caption: bool = False
    label_name: str = ""


@dataclass
class SectionInfo:
    level: str
    title: str
    file: str = ""
    line: int = 0


@dataclass
class ChapterStats:
    """Per-section writing statistics for polish flows."""

    section_title: str
    section_label: str
    level: int
    start_line: int
    end_line: int
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    paragraph_starts: list[str]
    long_sentences: list[dict[str, Any]]
    file: str = ""


@dataclass
class AbbrevInfo:
    abbr: str
    first_occurrence: dict[str, str | int]
    all_occurrences: int
    context_before: str
    context_after: str
    has_expansion: bool
    file: str = ""


@dataclass
class EnvInfo:
    env_name: str
    file: str = ""
    line: int = 0


@dataclass
class TildeIssue:
    issue_type: str
    file: str = ""
    line: int = 0
    context: str = ""


@dataclass
class CitationInfo:
    key: str
    file: str = ""
    line: int = 0
    context: str = ""


@dataclass
class ParagraphPair:
    """A paired Chinese comment plus English paragraph."""

    line_start: int
    line_end: int
    chinese: str
    english: str
    section: str
    file: str = ""


@dataclass
class OrphanParagraph:
    """An unmatched bilingual paragraph block."""

    line_start: int
    line_end: int
    text: str
    type: str
    section: str
    file: str = ""


@dataclass
class SpacingIssue:
    issue_type: str
    file: str
    line: int
    context: str
    suggestion: str


@dataclass
class LintIssue:
    rule: str
    severity: str
    message: str
    file: str
    line: int
    context: str
    auto_fixable: bool


@dataclass
class TexStats:
    """Complete LaTeX project statistics for Agent-side lint judgment."""

    files: list[str]
    labels: list[LabelInfo]
    refs: list[RefInfo]
    orphan_labels: list[str]
    orphan_refs: list[str]
    floats: list[FloatInfo]
    environments: dict[str, list[EnvInfo]]
    sections: list[SectionInfo]
    abbreviations: list[AbbrevInfo]
    citations: list[CitationInfo]
    bib_entries: list[BibEntryInfo]
    tilde_issues: list[TildeIssue]
    spacing_issues: list[SpacingIssue]
    chapter_stats: list[ChapterStats] = field(default_factory=list)
    paragraph_pairs: list[ParagraphPair] = field(default_factory=list)
    orphan_paragraphs: list[OrphanParagraph] = field(default_factory=list)
    project: dict[str, Any] | None = None
    issues: list[LintIssue] = field(default_factory=list, repr=False)

    def filtered_issues(self, rules: set[str] | None = None) -> list[LintIssue]:
        """Return rule issues filtered by rule identifiers when requested."""
        issues = self.issues
        if rules is not None:
            issues = [issue for issue in issues if issue.rule in rules]
        return sorted(
            issues,
            key=lambda issue: (
                _SEVERITY_ORDER.get(issue.severity, 99),
                issue.file,
                issue.line,
                issue.rule,
            ),
        )

    def summary(self, rules: set[str] | None = None) -> dict[str, int]:
        """Return summary counts for JSON/human output."""
        issues = self.filtered_issues(rules)
        return {
            "total_files": len(self.files),
            "total_labels": len(self.labels),
            "total_refs": len(self.refs),
            "total_floats": len(self.floats),
            "total_citations": len(self.citations),
            "total_bib_entries": len(self.bib_entries),
            "issues_found": len(issues),
            "errors": sum(1 for issue in issues if issue.severity == "error"),
            "warnings": sum(1 for issue in issues if issue.severity == "warning"),
            "info": sum(1 for issue in issues if issue.severity == "info"),
        }

    def to_payload(self, rules: set[str] | None = None) -> dict[str, Any]:
        """Convert stats into a JSON-serializable payload."""
        return {
            "summary": self.summary(rules),
            "issues": [asdict(issue) for issue in self.filtered_issues(rules)],
            "files": self.files,
            "labels": [asdict(label) for label in self.labels],
            "refs": [asdict(ref) for ref in self.refs],
            "orphan_labels": self.orphan_labels,
            "orphan_refs": self.orphan_refs,
            "floats": [asdict(float_info) for float_info in self.floats],
            "environments": {
                env_name: [asdict(info) for info in infos]
                for env_name, infos in sorted(self.environments.items())
            },
            "sections": [asdict(section) for section in self.sections],
            "abbreviations": [asdict(abbr) for abbr in self.abbreviations],
            "citations": [asdict(citation) for citation in self.citations],
            "bib_entries": [asdict(entry) for entry in self.bib_entries],
            "tilde_issues": [asdict(issue) for issue in self.tilde_issues],
            "spacing_issues": [asdict(issue) for issue in self.spacing_issues],
            "chapter_stats": [asdict(chapter) for chapter in self.chapter_stats],
            "paragraph_pairs": [asdict(pair) for pair in self.paragraph_pairs],
            "orphan_paragraphs": [asdict(orphan) for orphan in self.orphan_paragraphs],
            "project": self.project,
        }

    def to_json(self, rules: set[str] | None = None) -> str:
        """Serialize stats payload as readable JSON."""
        return json.dumps(self.to_payload(rules), ensure_ascii=False, indent=2)


@dataclass
class _FloatTracker:
    float_type: str
    file: str
    line: int
    placement: str
    has_label: bool = False
    has_caption: bool = False
    label_name: str = ""
    first_label_position: tuple[int, int] | None = None
    first_caption_position: tuple[int, int] | None = None

    def to_float_info(self) -> FloatInfo:
        label_before_caption = False
        if self.first_label_position is not None and self.first_caption_position is not None:
            label_before_caption = self.first_label_position < self.first_caption_position
        return FloatInfo(
            float_type=self.float_type,
            file=self.file,
            line=self.line,
            placement=self.placement,
            has_label=self.has_label,
            has_caption=self.has_caption,
            label_before_caption=label_before_caption,
            label_name=self.label_name,
        )


@dataclass
class _Occurrence:
    file: str
    line: int
    lines: list[str]


@dataclass
class _ParagraphBlock:
    line_start: int
    line_end: int
    text: str
    section: str
    has_chinese_comment: bool = False
    chinese_comment: str = ""


def extract_stats(
    tex_path: str | Path,
    bib_path: str | Path | None = None,
    *,
    project: TexProject | None = None,
    bib_paths: list[str] | None = None,
) -> TexStats:
    """Extract static LaTeX structure statistics from a file or project."""
    target_path = Path(tex_path)
    resolved_project = project
    if resolved_project is None and target_path.exists() and target_path.is_file():
        resolved_project = resolve_project(target_path)

    multi_file = resolved_project is not None and len(resolved_project.files) > 1
    if resolved_project is not None:
        analysis_files = [
            {
                "source_id": tex_file.abs_path.as_posix(),
                "path": tex_file.abs_path,
                "display_file": tex_file.path.as_posix() if multi_file else "",
                "raw_lines": tex_file.content.splitlines(),
            }
            for tex_file in resolved_project.files
        ]
        file_strings = [
            tex_file.path.as_posix() if multi_file else tex_file.abs_path.as_posix()
            for tex_file in resolved_project.files
        ]
    else:
        ordered_files = _ordered_tex_files(target_path)
        analysis_files = [
            {
                "source_id": tex_file.as_posix(),
                "path": tex_file,
                "display_file": tex_file.as_posix(),
                "raw_lines": tex_file.read_text(encoding="utf-8").splitlines(),
            }
            for tex_file in ordered_files
        ]
        file_strings = [file["display_file"] for file in analysis_files]

    raw_lines_by_source: dict[str, list[str]] = {
        str(file_info["source_id"]): list(file_info["raw_lines"]) for file_info in analysis_files
    }
    display_by_source: dict[str, str] = {
        str(file_info["source_id"]): str(file_info["display_file"]) for file_info in analysis_files
    }

    labels: list[LabelInfo] = []
    refs: list[RefInfo] = []
    floats: list[FloatInfo] = []
    sections: list[SectionInfo] = []
    citations: list[CitationInfo] = []
    tilde_issues: list[TildeIssue] = []
    spacing_issues: list[SpacingIssue] = []
    chapter_stats: list[ChapterStats] = []
    paragraph_pairs: list[ParagraphPair] = []
    orphan_paragraphs: list[OrphanParagraph] = []
    environments: dict[str, list[EnvInfo]] = defaultdict(list)
    abbreviation_occurrences: dict[str, list[_Occurrence]] = defaultdict(list)
    labels_by_source: dict[str, list[LabelInfo]] = defaultdict(list)
    sections_by_source: dict[str, list[SectionInfo]] = defaultdict(list)
    discovered_bib_paths: list[Path] = []
    seen_bib_paths: set[Path] = set()

    for file_info in analysis_files:
        source_id = str(file_info["source_id"])
        tex_file = Path(file_info["path"])
        display_file = str(file_info["display_file"])
        raw_lines = list(file_info["raw_lines"])
        code_lines = [_strip_comments(line) for line in raw_lines]
        env_stack: list[tuple[str, str, _FloatTracker | None]] = []
        current_section_env = "other"

        if bib_path is None and bib_paths is None and resolved_project is None:
            for discovered in sorted(_infer_bib_paths(tex_file, raw_lines)):
                if discovered not in seen_bib_paths:
                    discovered_bib_paths.append(discovered)
                    seen_bib_paths.add(discovered)

        for line_number, (raw_line, code_line) in enumerate(
            zip(raw_lines, code_lines, strict=False),
            start=1,
        ):
            _collect_spacing_issues(
                raw_line=raw_line,
                code_line=code_line,
                file=display_file,
                line_number=line_number,
                spacing_issues=spacing_issues,
            )

            _collect_abbreviations(
                raw_lines=raw_lines,
                raw_line=raw_line,
                file=display_file,
                line_number=line_number,
                occurrences=abbreviation_occurrences,
            )

            for match in _SECTION_RE.finditer(code_line):
                section = SectionInfo(
                    level=match.group("level"),
                    title=match.group("title").strip(),
                    file=display_file,
                    line=line_number,
                )
                sections.append(section)
                sections_by_source[source_id].append(section)
                current_section_env = "section"

            for match in _BEGIN_RE.finditer(code_line):
                env_name = match.group("name").strip()
                base_env = _normalize_environment_name(env_name)
                environments[base_env].append(
                    EnvInfo(env_name=base_env, file=display_file, line=line_number)
                )
                float_tracker = None
                if base_env in {"figure", "table"}:
                    float_tracker = _FloatTracker(
                        float_type=base_env,
                        file=display_file,
                        line=line_number,
                        placement=match.group("placement") or "",
                    )
                env_stack.append((env_name, base_env, float_tracker))

            for event_name, event_match in _line_command_events(code_line):
                if event_name == "caption":
                    active_float = _active_float_tracker(env_stack)
                    if active_float is not None:
                        active_float.has_caption = True
                        if active_float.first_caption_position is None:
                            active_float.first_caption_position = (line_number, event_match.start())
                    continue

                if event_name == "label":
                    label_name = event_match.group("label").strip()
                    label_env, suggested_prefix = _infer_label_environment(
                        env_stack=env_stack,
                        current_section_env=current_section_env,
                    )
                    label = LabelInfo(
                        name=label_name,
                        file=display_file,
                        line=line_number,
                        env=label_env,
                        has_prefix=_has_expected_prefix(label_name, suggested_prefix),
                        suggested_prefix=suggested_prefix,
                    )
                    labels.append(label)
                    labels_by_source[source_id].append(label)
                    active_float = _active_float_tracker(env_stack)
                    if active_float is not None:
                        active_float.has_label = True
                        if not active_float.label_name:
                            active_float.label_name = label_name
                        if active_float.first_label_position is None:
                            active_float.first_label_position = (line_number, event_match.start())
                    continue

                if event_name == "ref":
                    ref_kind = event_match.group("kind")
                    has_tilde = _has_nonbreaking_space_before(code_line, event_match.start())
                    requires_tilde = _requires_nonbreaking_space(code_line, event_match.start())
                    for target in _split_csv_targets(event_match.group("targets")):
                        refs.append(
                            RefInfo(
                                ref_type=ref_kind,
                                target=target,
                                file=display_file,
                                line=line_number,
                                has_tilde=has_tilde,
                            )
                        )
                    if ref_kind in {"cref", "Cref"} and requires_tilde and not has_tilde:
                        tilde_issues.append(
                            TildeIssue(
                                issue_type="cref",
                                file=display_file,
                                line=line_number,
                                context=raw_line.strip(),
                            )
                        )
                    continue

                if event_name == "cite":
                    has_tilde = _has_nonbreaking_space_before(code_line, event_match.start())
                    requires_tilde = _requires_nonbreaking_space(code_line, event_match.start())
                    context = _citation_context(raw_lines, line_number)
                    for key in _split_csv_targets(event_match.group("targets")):
                        citations.append(
                            CitationInfo(
                                key=key,
                                file=display_file,
                                line=line_number,
                                context=context,
                            )
                        )
                    if requires_tilde and not has_tilde:
                        tilde_issues.append(
                            TildeIssue(
                                issue_type="cite",
                                file=display_file,
                                line=line_number,
                                context=raw_line.strip(),
                            )
                        )

            for match in _END_RE.finditer(code_line):
                env_name = match.group("name").strip()
                base_env = _normalize_environment_name(env_name)
                end_index = _find_last_matching_env(env_stack, env_name, base_env)
                if end_index is None:
                    continue
                _, _, float_tracker = env_stack.pop(end_index)
                if float_tracker is not None:
                    floats.append(float_tracker.to_float_info())

    label_names = {label.name for label in labels}
    ref_targets = [ref.target for ref in refs]
    ref_target_set = set(ref_targets)
    orphan_labels = sorted(label.name for label in labels if label.name not in ref_target_set)
    orphan_refs = sorted(target for target in ref_target_set if target not in label_names)

    resolved_bib_paths = _resolve_bib_inputs(
        bib_path=bib_path,
        bib_paths=bib_paths,
        project=resolved_project,
        discovered_bib_paths=discovered_bib_paths,
    )
    existing_bib_paths = [path for path in resolved_bib_paths if path.exists()]
    if len(existing_bib_paths) > 1:
        bib_entries = parse_bib_files(existing_bib_paths)
    elif existing_bib_paths:
        bib_entries = parse_bib(existing_bib_paths[0].as_posix())
    else:
        bib_entries = []
    if resolved_project is not None:
        for entry in bib_entries:
            if entry.file:
                entry_path = Path(entry.file)
                if entry_path.is_relative_to(resolved_project.project_dir):
                    entry.file = entry_path.relative_to(resolved_project.project_dir).as_posix()
            if entry.source_file:
                source_path = Path(entry.source_file)
                if source_path.is_relative_to(resolved_project.project_dir):
                    entry.source_file = source_path.relative_to(resolved_project.project_dir).as_posix()

    abbreviations = _build_abbreviation_info(abbreviation_occurrences)
    for abbreviation in abbreviations:
        occurrence_file = abbreviation.first_occurrence.get("file")
        abbreviation.file = str(occurrence_file) if isinstance(occurrence_file, str) else ""

    for file_info in analysis_files:
        source_id = str(file_info["source_id"])
        raw_lines = raw_lines_by_source[source_id]
        display_file = display_by_source[source_id]
        chapter_stats.extend(
            _build_chapter_stats(
                raw_lines=raw_lines,
                sections=sections_by_source[source_id],
                labels=labels_by_source[source_id],
                file=display_file,
            )
        )
        pairs, orphans = _build_paragraph_pairs(
            raw_lines=raw_lines,
            sections=sections_by_source[source_id],
            file=display_file,
        )
        paragraph_pairs.extend(pairs)
        orphan_paragraphs.extend(orphans)

    stats = TexStats(
        files=file_strings,
        labels=labels,
        refs=refs,
        orphan_labels=orphan_labels,
        orphan_refs=orphan_refs,
        floats=floats,
        environments=dict(environments),
        sections=sections,
        abbreviations=abbreviations,
        citations=citations,
        bib_entries=bib_entries,
        tilde_issues=tilde_issues,
        spacing_issues=spacing_issues,
        chapter_stats=chapter_stats,
        paragraph_pairs=paragraph_pairs,
        orphan_paragraphs=orphan_paragraphs,
        project=_stats_project_payload(resolved_project) if multi_file else None,
    )
    stats.issues = _build_issues(stats)
    return stats


def _resolve_bib_inputs(
    *,
    bib_path: str | Path | None,
    bib_paths: list[str] | None,
    project: TexProject | None,
    discovered_bib_paths: list[Path],
) -> list[Path]:
    if bib_paths:
        return [Path(path) for path in bib_paths]
    if bib_path is not None:
        return [Path(bib_path)]
    if project is not None and project.bib_files:
        return list(project.bib_files)
    return discovered_bib_paths


def _stats_project_payload(project: TexProject | None) -> dict[str, Any] | None:
    if project is None or len(project.files) <= 1:
        return None
    return {
        "root_file": project.root_file.relative_to(project.project_dir).as_posix(),
        "files": [tex_file.path.as_posix() for tex_file in project.files],
        "bib_files": [
            bib_file.relative_to(project.project_dir).as_posix()
            if bib_file.is_relative_to(project.project_dir)
            else bib_file.as_posix()
            for bib_file in project.bib_files
        ],
    }


def _ordered_tex_files(target_path: Path) -> list[Path]:
    if target_path.is_file():
        return [target_path]

    tex_files = sorted(target_path.rglob("*.tex"))
    if not tex_files:
        return []

    include_graph: dict[Path, list[Path]] = {}
    referenced: set[Path] = set()
    for tex_file in tex_files:
        include_graph[tex_file] = _extract_includes(tex_file)
        referenced.update(include_graph[tex_file])

    roots = [file for file in tex_files if file not in referenced]
    visited: set[Path] = set()
    ordered: list[Path] = []
    for root in sorted(roots or tex_files):
        _dfs_tex_files(root, include_graph, visited, ordered)
    for tex_file in tex_files:
        _dfs_tex_files(tex_file, include_graph, visited, ordered)
    return ordered


def _dfs_tex_files(
    tex_file: Path,
    include_graph: dict[Path, list[Path]],
    visited: set[Path],
    ordered: list[Path],
) -> None:
    if tex_file in visited or not tex_file.exists():
        return
    visited.add(tex_file)
    ordered.append(tex_file)
    for child in include_graph.get(tex_file, []):
        _dfs_tex_files(child, include_graph, visited, ordered)


def _extract_includes(tex_file: Path) -> list[Path]:
    includes: list[Path] = []
    for raw_line in tex_file.read_text(encoding="utf-8").splitlines():
        code_line = _strip_comments(raw_line)
        for match in re.finditer(r"\\(?:input|include)\{(?P<target>[^}]+)\}", code_line):
            target = match.group("target").strip()
            if not target:
                continue
            include_path = (tex_file.parent / target).with_suffix(".tex") if Path(target).suffix == "" else tex_file.parent / target
            include_path = include_path.resolve()
            if include_path.exists():
                includes.append(include_path)
    return includes


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


def _collect_spacing_issues(
    raw_line: str,
    code_line: str,
    file: str,
    line_number: int,
    spacing_issues: list[SpacingIssue],
) -> None:
    if raw_line.rstrip(" ") != raw_line:
        spacing_issues.append(
            SpacingIssue(
                issue_type="trailing_spaces",
                file=file,
                line=line_number,
                context=raw_line,
                suggestion="Remove trailing spaces.",
            )
        )

    stripped_code = code_line.lstrip()
    if re.search(r"\S {2,}\S", stripped_code):
        spacing_issues.append(
            SpacingIssue(
                issue_type="multiple_spaces",
                file=file,
                line=line_number,
                context=raw_line.strip(),
                suggestion="Collapse consecutive spaces to a single space.",
            )
        )

    for pattern, replacement in _ABBREV_SPACING_PATTERNS:
        if pattern.search(code_line):
            spacing_issues.append(
                SpacingIssue(
                    issue_type="abbrev_spacing",
                    file=file,
                    line=line_number,
                    context=raw_line.strip(),
                    suggestion=f"Use `{replacement}` instead of a normal space after abbreviations.",
                )
            )
            break


def _collect_abbreviations(
    raw_lines: list[str],
    raw_line: str,
    file: str,
    line_number: int,
    occurrences: dict[str, list[_Occurrence]],
) -> None:
    for match in _ABBR_RE.finditer(raw_line):
        abbr = match.group(0)
        if abbr in _COMMON_NON_ABBREVIATIONS:
            continue
        occurrences[abbr].append(
            _Occurrence(
                file=file,
                line=line_number,
                lines=raw_lines,
            )
        )


def _build_abbreviation_info(
    occurrences: dict[str, list[_Occurrence]],
) -> list[AbbrevInfo]:
    abbreviations: list[AbbrevInfo] = []
    for abbr, abbr_occurrences in sorted(occurrences.items()):
        first = abbr_occurrences[0]
        line_index = first.line - 1
        context_before = "\n".join(first.lines[max(0, line_index - 3) : line_index]).strip()
        context_after = "\n".join(first.lines[line_index + 1 : line_index + 4]).strip()
        context_window = "\n".join(first.lines[max(0, line_index - 3) : line_index + 4])
        has_expansion = bool(
            re.search(_EXPANSION_TEMPLATE.format(abbr=re.escape(abbr)), context_window)
        )
        abbreviations.append(
            AbbrevInfo(
                abbr=abbr,
                first_occurrence={"file": first.file, "line": first.line},
                all_occurrences=len(abbr_occurrences),
                context_before=context_before,
                context_after=context_after,
                has_expansion=has_expansion,
            )
        )
    return abbreviations


def _build_chapter_stats(
    raw_lines: list[str],
    sections: list[SectionInfo],
    labels: list[LabelInfo],
    file: str,
) -> list[ChapterStats]:
    chapter_stats: list[ChapterStats] = []
    if not sections:
        return chapter_stats

    label_by_line = {label.line: label.name for label in labels}
    for index, section in enumerate(sections):
        level = _SECTION_LEVELS.get(section.level, 1)
        start_line = section.line
        end_line = len(raw_lines)
        for next_section in sections[index + 1 :]:
            next_level = _SECTION_LEVELS.get(next_section.level, 1)
            if next_level <= level:
                end_line = next_section.line - 1
                break

        section_lines = raw_lines[start_line - 1 : end_line]
        cleaned_lines = _sanitize_writing_lines(section_lines)
        text = "\n".join(line for line in cleaned_lines if line).strip()
        sentences = _split_sentences(text)
        word_count = sum(_count_words(sentence) for sentence in sentences)
        sentence_count = len(sentences)
        avg_sentence_length = (
            round(word_count / sentence_count, 2) if sentence_count else 0.0
        )
        sentence_starts = [
            sentence.split()[0]
            for sentence in sentences
            if sentence.split()
        ]
        paragraph_starts = [
            word
            for word, count in Counter(sentence_starts).items()
            for _ in range(count)
        ]
        long_sentences = []
        for sentence in sentences:
            sentence_word_count = _count_words(sentence)
            if sentence_word_count <= 40:
                continue
            line_offset = _find_sentence_line(section_lines, sentence)
            long_sentences.append(
                {
                    "line": start_line + line_offset,
                    "word_count": sentence_word_count,
                    "text": sentence[:80],
                }
            )

        section_label = _find_section_label(section.line, end_line, label_by_line)
        chapter_stats.append(
            ChapterStats(
                section_title=section.title,
                section_label=section_label,
                level=level,
                start_line=start_line,
                end_line=end_line,
                word_count=word_count,
                sentence_count=sentence_count,
                avg_sentence_length=avg_sentence_length,
                paragraph_starts=paragraph_starts,
                long_sentences=long_sentences,
                file=file,
            )
        )

    return chapter_stats


def _build_paragraph_pairs(
    raw_lines: list[str],
    sections: list[SectionInfo],
    file: str,
) -> tuple[list[ParagraphPair], list[OrphanParagraph]]:
    pairs: list[ParagraphPair] = []
    orphans: list[OrphanParagraph] = []
    line_index = 0
    pending_comment_lines: list[str] = []
    pending_comment_start = 0
    excluded_env_depth = 0

    while line_index < len(raw_lines):
        line_number = line_index + 1
        raw_line = raw_lines[line_index]
        stripped = raw_line.strip()
        code_line = _strip_comments(raw_line).strip()
        begin_match = _BEGIN_RE.match(code_line)
        end_match = _END_RE.match(code_line)

        if excluded_env_depth > 0:
            if end_match and end_match.group("name") in _BILINGUAL_EXCLUDED_ENVIRONMENTS:
                excluded_env_depth = max(excluded_env_depth - 1, 0)
            pending_comment_lines = []
            pending_comment_start = 0
            line_index += 1
            continue

        if begin_match and begin_match.group("name") in _BILINGUAL_EXCLUDED_ENVIRONMENTS:
            excluded_env_depth += 1
            pending_comment_lines = []
            pending_comment_start = 0
            line_index += 1
            continue

        if not stripped:
            pending_comment_lines = []
            pending_comment_start = 0
            line_index += 1
            continue

        if _is_chinese_comment_line(raw_line):
            if not pending_comment_lines:
                pending_comment_start = line_number
            pending_comment_lines.append(stripped.lstrip("%").strip())
            line_index += 1
            continue

        if _is_ignorable_paragraph_line(raw_line):
            pending_comment_lines = []
            pending_comment_start = 0
            line_index += 1
            continue

        block_lines = [stripped]
        block_start = line_number
        block_end = line_number
        line_index += 1
        while line_index < len(raw_lines):
            next_raw = raw_lines[line_index]
            next_stripped = next_raw.strip()
            if not next_stripped or _is_chinese_comment_line(next_raw) or _is_ignorable_paragraph_line(next_raw):
                break
            block_lines.append(next_stripped)
            block_end = line_index + 1
            line_index += 1

        english = " ".join(block_lines).strip()
        section = _section_for_line(sections, block_start)
        if pending_comment_lines:
            pairs.append(
                ParagraphPair(
                    line_start=pending_comment_start,
                    line_end=block_end,
                    chinese=" ".join(pending_comment_lines).strip(),
                    english=english,
                    section=section,
                    file=file,
                )
            )
            pending_comment_lines = []
            pending_comment_start = 0
        else:
            orphans.append(
                OrphanParagraph(
                    line_start=block_start,
                    line_end=block_end,
                    text=english,
                    type="missing_chinese",
                    section=section,
                    file=file,
                )
            )

    return pairs, orphans


def _sanitize_writing_lines(lines: list[str]) -> list[str]:
    cleaned_lines: list[str] = []
    math_depth = 0
    for raw_line in lines:
        code_line = _strip_comments(raw_line)
        stripped = code_line.strip()
        begin_match = _BEGIN_RE.match(stripped)
        end_match = _END_RE.match(stripped)
        if begin_match and begin_match.group("name") in _MATH_ENVIRONMENTS:
            math_depth += 1
            continue
        if end_match and end_match.group("name") in _MATH_ENVIRONMENTS:
            math_depth = max(math_depth - 1, 0)
            continue
        if math_depth > 0:
            continue
        if _is_ignorable_paragraph_line(raw_line):
            cleaned_lines.append("")
            continue
        normalized = code_line
        normalized = re.sub(r"\$[^$]*\$", " ", normalized)
        normalized = re.sub(r"\\\([^)]*\\\)", " ", normalized)
        normalized = re.sub(r"\\\[[^\]]*\\\]", " ", normalized)
        normalized = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?\{[^{}]*\}", " ", normalized)
        normalized = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", " ", normalized)
        normalized = normalized.replace("{", " ").replace("}", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        cleaned_lines.append(normalized)
    return cleaned_lines


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []
    normalized = text.replace("\n", " ")
    for original, placeholder in _SENTENCE_PLACEHOLDERS.items():
        normalized = normalized.replace(original, placeholder)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    pieces = re.split(r"(?<=[.!?])\s+", normalized)
    sentences: list[str] = []
    for piece in pieces:
        restored = piece
        for original, placeholder in _SENTENCE_PLACEHOLDERS.items():
            restored = restored.replace(placeholder, original)
        restored = restored.strip()
        if restored:
            sentences.append(restored)
    return sentences


def _count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z]+(?:[-'][A-Za-z]+)?", text))


def _find_sentence_line(lines: list[str], sentence: str) -> int:
    snippet = sentence[:20]
    for index, raw_line in enumerate(lines):
        if snippet and snippet in raw_line:
            return index
    return 0


def _find_section_label(start_line: int, end_line: int, label_by_line: dict[int, str]) -> str:
    for line_number in range(start_line, min(end_line, start_line + 3) + 1):
        if line_number in label_by_line:
            return label_by_line[line_number]
    return ""


def _section_for_line(sections: list[SectionInfo], line_number: int) -> str:
    current = ""
    for section in sections:
        if section.line > line_number:
            break
        current = section.title
    return current


def _is_chinese_comment_line(raw_line: str) -> bool:
    stripped = raw_line.lstrip()
    return stripped.startswith("%") and bool(_CJK_RE.search(stripped))


def _is_ignorable_paragraph_line(raw_line: str) -> bool:
    code_line = _strip_comments(raw_line).strip()
    if not code_line:
        return True
    if code_line.startswith("%"):
        return True
    ignorable_prefixes = (
        "\\documentclass",
        "\\usepackage",
        "\\section",
        "\\subsection",
        "\\subsubsection",
        "\\label",
        "\\caption",
        "\\bibliography",
        "\\bibliographystyle",
        "\\addbibresource",
        "\\begin",
        "\\end",
        "\\centering",
        "\\includegraphics",
        "\\input",
        "\\include",
        "\\IEEEbiography",
    )
    return code_line.startswith(ignorable_prefixes)


def _line_command_events(code_line: str) -> list[tuple[str, re.Match[str]]]:
    events: list[tuple[str, re.Match[str]]] = []
    for match in _CAPTION_RE.finditer(code_line):
        events.append(("caption", match))
    for match in _LABEL_RE.finditer(code_line):
        events.append(("label", match))
    for match in _REF_RE.finditer(code_line):
        events.append(("ref", match))
    for match in _HYPERREF_RE.finditer(code_line):
        events.append(("ref", match))
    for match in _CITE_RE.finditer(code_line):
        events.append(("cite", match))
    return sorted(events, key=lambda item: item[1].start())


def _active_float_tracker(env_stack: list[tuple[str, str, _FloatTracker | None]]) -> _FloatTracker | None:
    for _, base_env, tracker in reversed(env_stack):
        if base_env in {"figure", "table"} and tracker is not None:
            return tracker
    return None


def _infer_label_environment(
    env_stack: list[tuple[str, str, _FloatTracker | None]],
    current_section_env: str,
) -> tuple[str, str]:
    for _, base_env, _ in reversed(env_stack):
        if base_env in {
            "figure",
            "table",
            "equation",
            "algorithm",
            "algorithm2e",
            "listing",
            "lstlisting",
            "theorem",
            "lemma",
            "definition",
            "proposition",
            "corollary",
            "remark",
            "example",
        }:
            if base_env == "lstlisting":
                normalized_env = "listing"
            elif base_env == "algorithm2e":
                normalized_env = "algorithm"
            else:
                normalized_env = base_env
            prefix = DEFAULT_LABEL_PREFIXES.get(normalized_env, "")
            return normalized_env, f"{prefix}:" if prefix else ""
    if current_section_env == "section":
        return "section", "sec:"
    return "other", ""


def _has_expected_prefix(label_name: str, suggested_prefix: str) -> bool:
    if any(label_name.startswith(prefix) for prefix in _VALID_LABEL_PREFIXES):
        return True
    if not suggested_prefix:
        return True
    return label_name.startswith(suggested_prefix)


def _normalize_environment_name(env_name: str) -> str:
    if env_name.endswith("*"):
        env_name = env_name[:-1]
    if env_name == "subfigure":
        return "figure"
    if env_name == "subtable":
        return "table"
    return env_name


def _find_last_matching_env(
    env_stack: list[tuple[str, str, _FloatTracker | None]],
    env_name: str,
    base_env: str,
) -> int | None:
    normalized_target = _normalize_environment_name(env_name)
    for index in range(len(env_stack) - 1, -1, -1):
        stack_env_name, stack_base_env, _ = env_stack[index]
        if stack_env_name == env_name or stack_base_env == normalized_target or stack_base_env == base_env:
            return index
    return None


def _split_csv_targets(value: str) -> list[str]:
    return [target.strip() for target in value.split(",") if target.strip()]


def _has_nonbreaking_space_before(code_line: str, command_start: int) -> bool:
    prefix = code_line[:command_start].rstrip()
    return bool(prefix) and prefix.endswith("~")


def _requires_nonbreaking_space(code_line: str, command_start: int) -> bool:
    prefix = code_line[:command_start].rstrip()
    if not prefix:
        return False
    return prefix[-1].isalnum() or prefix[-1] in {".", ")", "]", "}"}


def _citation_context(raw_lines: list[str], line_number: int) -> str:
    start = max(0, line_number - 2)
    end = min(len(raw_lines), line_number + 1)
    return "\n".join(raw_lines[start:end]).strip()


def _infer_bib_paths(tex_file: Path, raw_lines: list[str]) -> set[Path]:
    bib_paths: set[Path] = set()
    for raw_line in raw_lines:
        code_line = _strip_comments(raw_line)
        for match in _BIBLIOGRAPHY_RE.finditer(code_line):
            for target in _split_csv_targets(match.group("targets")):
                bib_paths.add(_resolve_bib_path(tex_file, target))
        for match in _ADDBIBRESOURCE_RE.finditer(code_line):
            bib_paths.add(_resolve_bib_path(tex_file, match.group("target")))
    return bib_paths


def _resolve_bib_path(tex_file: Path, target: str) -> Path:
    bib_target = target.strip()
    path = tex_file.parent / bib_target
    if path.suffix != ".bib":
        path = path.with_suffix(".bib")
    return path.resolve()


def _build_issues(stats: TexStats) -> list[LintIssue]:
    issues: list[LintIssue] = []

    for ref in stats.refs:
        if ref.ref_type in {"ref", "autoref"}:
            issues.append(
                _make_issue(
                    rule="L01",
                    severity="error",
                    message=f"Use \\cref instead of \\{ref.ref_type}",
                    file=ref.file,
                    line=ref.line,
                    context=f"\\{ref.ref_type}{{{ref.target}}}",
                )
            )

    for issue in stats.tilde_issues:
        if issue.issue_type == "cref":
            issues.append(
                _make_issue(
                    rule="L02",
                    severity="error",
                    message="Missing ~ before \\cref",
                    file=issue.file,
                    line=issue.line,
                    context=issue.context,
                )
            )
        elif issue.issue_type == "cite":
            issues.append(
                _make_issue(
                    rule="L03",
                    severity="error",
                    message="Missing ~ before \\cite",
                    file=issue.file,
                    line=issue.line,
                    context=issue.context,
                )
            )

    for float_info in stats.floats:
        if float_info.placement != "[htbp]":
            issues.append(
                _make_issue(
                    rule="L04",
                    severity="warning",
                    message="Float missing [htbp] placement",
                    file=float_info.file,
                    line=float_info.line,
                    context=f"\\begin{{{float_info.float_type}}}{float_info.placement}",
                )
            )
        if float_info.has_label and float_info.has_caption and float_info.label_before_caption:
            issues.append(
                _make_issue(
                    rule="L05",
                    severity="warning",
                    message="\\label should appear after \\caption inside floats",
                    file=float_info.file,
                    line=float_info.line,
                    context=float_info.label_name,
                )
            )

    for label in stats.labels:
        if not label.has_prefix and label.suggested_prefix:
            issues.append(
                _make_issue(
                    rule="L06",
                    severity="warning",
                    message=(
                        f"Label '{label.name}' missing prefix "
                        f"(suggest: {label.suggested_prefix}{label.name})"
                    ),
                    file=label.file,
                    line=label.line,
                    context=f"\\label{{{label.name}}}",
                )
            )

    for env_name in ("tabular", "tabularx"):
        for env_info in stats.environments.get(env_name, []):
            issues.append(
                _make_issue(
                    rule="L07",
                    severity="info",
                    message=f"Using {env_name} instead of tblr",
                    file=env_info.file,
                    line=env_info.line,
                    context=f"\\begin{{{env_name}}}",
                )
            )

    for label_name in stats.orphan_labels:
        label = next((item for item in stats.labels if item.name == label_name), None)
        if label is not None:
            issues.append(
                _make_issue(
                    rule="L08",
                    severity="warning",
                    message=f"Label '{label_name}' is never referenced",
                    file=label.file,
                    line=label.line,
                    context=f"\\label{{{label_name}}}",
                )
            )
    for orphan_ref in stats.orphan_refs:
        ref = next((item for item in stats.refs if item.target == orphan_ref), None)
        if ref is not None:
            issues.append(
                _make_issue(
                    rule="L08",
                    severity="error",
                    message=f"Reference target '{orphan_ref}' has no matching label",
                    file=ref.file,
                    line=ref.line,
                    context=f"\\{ref.ref_type}{{{orphan_ref}}}",
                )
            )

    for spacing_issue in stats.spacing_issues:
        if spacing_issue.issue_type == "abbrev_spacing":
            issues.append(
                _make_issue(
                    rule="L11",
                    severity="warning",
                    message="Use \\ or ~ after Fig./Tab./Eq./et al.",
                    file=spacing_issue.file,
                    line=spacing_issue.line,
                    context=spacing_issue.context,
                )
            )
        elif spacing_issue.issue_type in {"multiple_spaces", "trailing_spaces"}:
            message = (
                "Remove multiple consecutive spaces"
                if spacing_issue.issue_type == "multiple_spaces"
                else "Remove trailing spaces"
            )
            issues.append(
                _make_issue(
                    rule="L13",
                    severity="warning",
                    message=message,
                    file=spacing_issue.file,
                    line=spacing_issue.line,
                    context=spacing_issue.context,
                )
            )

    for entry in stats.bib_entries:
        for missing_field in entry.missing_fields:
            issues.append(
                _make_issue(
                    rule="L12",
                    severity="warning",
                    message=f"Entry '{entry.key}' missing field: {missing_field}",
                    file=entry.file,
                    line=entry.line,
                    context=f"@{entry.entry_type}{{{entry.key}, ...}}",
                )
            )

    unique_issues: list[LintIssue] = []
    seen_keys: set[tuple[str, str, int, str]] = set()
    for issue in issues:
        dedup_key = (issue.rule, issue.file, issue.line, issue.message)
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        unique_issues.append(issue)
    return unique_issues


def _make_issue(
    rule: str,
    severity: str,
    message: str,
    file: str,
    line: int,
    context: str,
) -> LintIssue:
    return LintIssue(
        rule=rule,
        severity=severity,
        message=message,
        file=file,
        line=line,
        context=context,
        auto_fixable=rule in _AUTO_FIXABLE_RULES,
    )
