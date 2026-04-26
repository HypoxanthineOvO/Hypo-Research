"""Paper structure parsing for simulated review workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from hypo_research.writing.bib_parser import parse_bib_files
from hypo_research.writing.project import resolve_project


RAW_TEXT_LIMIT = 50_000


@dataclass
class Section:
    """A section of the paper."""

    title: str
    level: int
    content: str
    word_count: int


@dataclass
class Figure:
    """A figure in the paper."""

    label: str | None
    caption: str
    section: str | None


@dataclass
class Table:
    """A table in the paper."""

    label: str | None
    caption: str
    section: str | None


@dataclass
class PaperStructure:
    """Parsed structure of an academic paper."""

    title: str
    abstract: str
    sections: list[Section]
    figures: list[Figure]
    tables: list[Table]
    equations_count: int
    references: list[str]
    claims: list[str]
    word_count: int
    page_count: int | None
    raw_text: str
    source_type: str
    inferred_domain: str | None


_TITLE_RE = re.compile(r"\\title(?:\[[^\]]*\])?\{(?P<title>.*?)\}", re.DOTALL)
_ABSTRACT_RE = re.compile(r"\\begin\{abstract\}(?P<abstract>.*?)\\end\{abstract\}", re.DOTALL)
_SECTION_RE = re.compile(r"\\(?P<kind>section|subsection|subsubsection)\*?\{(?P<title>[^}]*)\}")
_ENV_RE = re.compile(r"\\begin\{(?P<name>figure\*?|table\*?)\}(?P<body>.*?)\\end\{(?P=name)\}", re.DOTALL)
_LABEL_RE = re.compile(r"\\label\{(?P<label>[^}]+)\}")
_BIBITEM_RE = re.compile(r"\\bibitem(?:\[[^\]]*\])?\{[^}]+\}(?P<body>.*?)(?=\\bibitem|\\end\{thebibliography\})", re.DOTALL)
_MATH_ENV_RE = re.compile(r"\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?|displaymath|math)\}")
_CLAIM_PATTERNS = (
    "we achieve",
    "we propose",
    "we present",
    "we introduce",
    "our method",
    "our approach",
    "outperforms",
    "state-of-the-art",
    "state of the art",
    "speedup",
)
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "FHE acceleration": ["fhe", "fully homomorphic", "homomorphic encryption", "bootstrapping", "ntt", "ckks", "tfhe"],
    "EDA": ["eda", "placement", "routing", "logic synthesis", "physical design", "design automation"],
    "circuits": ["circuit", "cmos", "adc", "dac", "pll", "isscc", "tcas", "chip measurement"],
    "computer architecture": ["architecture", "microarchitecture", "cache", "accelerator", "workload", "memory hierarchy"],
    "machine learning": ["neural network", "deep learning", "transformer", "training", "inference", "neurips", "icml"],
    "computer vision": ["image", "vision", "segmentation", "detection", "cvpr", "iccv", "eccv"],
    "graphics": ["rendering", "graphics", "ray tracing", "mesh", "siggraph"],
}


def parse_paper(path: str) -> PaperStructure:
    """Parse a paper from .tex or .pdf file."""
    paper_path = Path(path)
    suffix = paper_path.suffix.lower()
    if suffix == ".tex":
        return _parse_latex(paper_path)
    if suffix == ".pdf":
        return _parse_pdf(paper_path)
    raise ValueError(f"不支持的文件格式: {path}，请使用 .tex 或 .pdf")


def _parse_latex(path: Path) -> PaperStructure:
    project = resolve_project(path)
    latex = _strip_comments(project.merged_content)
    text = _latex_to_text(latex)
    title = _clean_latex(_first_group(_TITLE_RE, latex, "title")) or path.stem
    abstract = _clean_latex(_first_group(_ABSTRACT_RE, latex, "abstract"))
    sections = _extract_latex_sections(latex)
    figures, tables = _extract_latex_floats(latex)
    references = _extract_latex_references(latex, project.bib_files)
    claims = _extract_claims(text)
    raw_text = _truncate_raw(text)
    return PaperStructure(
        title=title,
        abstract=abstract,
        sections=sections,
        figures=figures,
        tables=tables,
        equations_count=_count_equations(latex),
        references=references,
        claims=claims,
        word_count=_word_count(text),
        page_count=None,
        raw_text=raw_text,
        source_type="latex",
        inferred_domain=infer_domain(title, abstract, text),
    )


def _parse_pdf(path: Path) -> PaperStructure:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("PDF 解析需要安装 optional dependency: uv sync --extra review") from exc

    document = fitz.open(path)
    pages = [page.get_text("text") for page in document]
    raw = "\n".join(pages)
    title = _infer_pdf_title(raw, path)
    abstract = _extract_pdf_abstract(raw)
    sections = _extract_pdf_sections(raw)
    figures = [
        Figure(label=match.group("label"), caption=_normalize_space(match.group("caption")), section=None)
        for match in re.finditer(r"\bFigure\s+(?P<label>[\w.-]+)\s*[:.]\s*(?P<caption>[^\n]+)", raw, re.IGNORECASE)
    ]
    tables = [
        Table(label=match.group("label"), caption=_normalize_space(match.group("caption")), section=None)
        for match in re.finditer(r"\bTable\s+(?P<label>[\w.-]+)\s*[:.]\s*(?P<caption>[^\n]+)", raw, re.IGNORECASE)
    ]
    references = _extract_pdf_references(raw)
    claims = _extract_claims(raw)
    return PaperStructure(
        title=title,
        abstract=abstract,
        sections=sections,
        figures=figures,
        tables=tables,
        equations_count=0,
        references=references,
        claims=claims,
        word_count=_word_count(raw),
        page_count=document.page_count,
        raw_text=_truncate_raw(raw),
        source_type="pdf",
        inferred_domain=infer_domain(title, abstract, raw),
    )


def infer_domain(title: str, abstract: str, text: str = "") -> str | None:
    """Infer a coarse research domain from keyword hits."""
    haystack = f"{title}\n{abstract}\n{text[:5000]}".lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in haystack)
        for domain, keywords in _DOMAIN_KEYWORDS.items()
    }
    best_domain, best_score = max(scores.items(), key=lambda item: item[1])
    return best_domain if best_score > 0 else None


def _extract_latex_sections(latex: str) -> list[Section]:
    matches = list(_SECTION_RE.finditer(latex))
    sections: list[Section] = []
    levels = {"section": 1, "subsection": 2, "subsubsection": 3}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(latex)
        content = _clean_latex(latex[start:end])
        sections.append(
            Section(
                title=_clean_latex(match.group("title")),
                level=levels[match.group("kind")],
                content=content,
                word_count=_word_count(content),
            )
        )
    return sections


def _extract_latex_floats(latex: str) -> tuple[list[Figure], list[Table]]:
    section_positions = [(match.start(), _clean_latex(match.group("title"))) for match in _SECTION_RE.finditer(latex)]
    figures: list[Figure] = []
    tables: list[Table] = []
    for match in _ENV_RE.finditer(latex):
        body = match.group("body")
        label_match = _LABEL_RE.search(body)
        item = (
            label_match.group("label") if label_match else None,
            _extract_caption(body),
            _section_for_position(section_positions, match.start()),
        )
        if match.group("name").startswith("figure"):
            figures.append(Figure(label=item[0], caption=item[1], section=item[2]))
        else:
            tables.append(Table(label=item[0], caption=item[1], section=item[2]))
    return figures, tables


def _extract_caption(body: str) -> str:
    start_match = re.search(r"\\caption(?:\[[^\]]*\])?\{", body)
    if start_match is None:
        return ""
    start = start_match.end() - 1
    end = _find_matching_brace(body, start)
    if end == -1:
        return ""
    return _clean_latex(body[start + 1 : end])


def _extract_latex_references(latex: str, bib_files: list[Path]) -> list[str]:
    references: list[str] = []
    for match in _BIBITEM_RE.finditer(latex):
        cleaned = _clean_latex(match.group("body"))
        if cleaned:
            references.append(cleaned[:240])
    existing_bibs = [path for path in bib_files if path.exists()]
    if existing_bibs:
        for entry in parse_bib_files(existing_bibs):
            title = entry.fields.get("title")
            if title:
                references.append(_normalize_space(title))
    return list(dict.fromkeys(references))


def _extract_claims(text: str) -> list[str]:
    claims: list[str] = []
    for sentence in _split_sentences(text):
        lowered = sentence.lower()
        if any(pattern in lowered for pattern in _CLAIM_PATTERNS):
            claims.append(sentence)
    return list(dict.fromkeys(claims))[:30]


def _extract_pdf_sections(raw: str) -> list[Section]:
    heading_re = re.compile(r"^(?P<title>(?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z0-9 ,:/&()_-]{2,80})$", re.MULTILINE)
    matches = [
        match
        for match in heading_re.finditer(raw)
        if _looks_like_pdf_heading(match.group("title"))
    ]
    sections: list[Section] = []
    for index, match in enumerate(matches):
        title = _normalize_space(match.group("title"))
        if title.lower() in {"abstract", "references"}:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw)
        content = _normalize_space(raw[start:end])
        level = 1 + min(title.count("."), 2) if re.match(r"^\d", title) else 1
        sections.append(Section(title=title, level=level, content=content, word_count=_word_count(content)))
    return sections


def _extract_pdf_abstract(raw: str) -> str:
    match = re.search(r"\bAbstract\b\s*(?P<body>.*?)(?=\n\s*(?:1\.?\s+)?Introduction\b|\n\s*Keywords\b)", raw, re.IGNORECASE | re.DOTALL)
    return _normalize_space(match.group("body")) if match else ""


def _extract_pdf_references(raw: str) -> list[str]:
    match = re.search(r"\bReferences\b(?P<body>.*)$", raw, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    body = match.group("body")
    chunks = re.split(r"\n\s*(?:\[\d+\]|\d+\.)\s*", body)
    return [_normalize_space(chunk)[:240] for chunk in chunks if _word_count(chunk) >= 3][:100]


def _infer_pdf_title(raw: str, path: Path) -> str:
    for line in raw.splitlines():
        cleaned = _normalize_space(line)
        if len(cleaned.split()) >= 3 and cleaned.lower() not in {"abstract", "introduction"}:
            return cleaned[:200]
    return path.stem


def _looks_like_pdf_heading(value: str) -> bool:
    cleaned = value.strip()
    if len(cleaned.split()) > 12:
        return False
    lowered = cleaned.lower()
    return bool(re.match(r"^\d+(?:\.\d+)*\s+\w+", cleaned)) or lowered in {
        "abstract",
        "introduction",
        "background",
        "method",
        "methods",
        "evaluation",
        "experiments",
        "results",
        "discussion",
        "conclusion",
        "related work",
        "references",
    }


def _count_equations(latex: str) -> int:
    return len(_MATH_ENV_RE.findall(latex)) + latex.count("\\[") + len(re.findall(r"(?<!\\)\$\$", latex)) // 2


def _section_for_position(section_positions: list[tuple[int, str]], position: int) -> str | None:
    current: str | None = None
    for section_position, title in section_positions:
        if section_position > position:
            break
        current = title
    return current


def _first_group(pattern: re.Pattern[str], text: str, group: str) -> str:
    match = pattern.search(text)
    return match.group(group) if match else ""


def _strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        escaped = False
        kept = []
        for char in line:
            if escaped:
                kept.append(char)
                escaped = False
                continue
            if char == "\\":
                kept.append(char)
                escaped = True
                continue
            if char == "%":
                break
            kept.append(char)
        lines.append("".join(kept))
    return "\n".join(lines)


def _latex_to_text(text: str) -> str:
    cleaned = re.sub(r"\\begin\{(?:figure\*?|table\*?)\}.*?\\end\{(?:figure\*?|table\*?)\}", " ", text, flags=re.DOTALL)
    return _clean_latex(cleaned)


def _clean_latex(text: str) -> str:
    cleaned = re.sub(r"\\(?:cite|ref|eqref|cref|Cref|autoref)\{([^}]*)\}", r"\1", text)
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", cleaned)
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", cleaned)
    cleaned = cleaned.replace("~", " ")
    cleaned = cleaned.replace("{", "").replace("}", "")
    return _normalize_space(cleaned)


def _split_sentences(text: str) -> list[str]:
    protected = text.replace("Fig.", "Fig<DOT>").replace("et al.", "et al<DOT>").replace("e.g.", "e<DOT>g<DOT>")
    sentences = re.split(r"(?<=[.!?])\s+", protected)
    return [
        _normalize_space(sentence.replace("<DOT>", "."))
        for sentence in sentences
        if _word_count(sentence) >= 5
    ]


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text))


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _truncate_raw(text: str) -> str:
    return text[:RAW_TEXT_LIMIT]


def _find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    escaped = False
    for index in range(open_index, len(text)):
        char = text[index]
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
            if depth == 0:
                return index
    return -1
