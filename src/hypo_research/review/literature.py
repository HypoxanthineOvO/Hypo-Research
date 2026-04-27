"""Literature search support for grounded simulated reviews."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

import httpx

from hypo_research.core.models import PaperResult, SearchParams
from hypo_research.core.sources import SourceError
from hypo_research.core.sources.semantic_scholar import SemanticScholarSource


S2_REQUEST_DELAY = 1.0
S2_MAX_RETRIES = 3
S2_RETRY_BACKOFF = 2.0
SEARCH_QUERY_EXTRACTION_PROMPT = """
你是一个学术文献检索专家。给定一篇论文的标题和摘要，你需要生成 {num_queries} 个搜索查询，
用于在 Semantic Scholar 上检索与该论文最相关的近期工作。

论文标题：{title}
论文摘要：{abstract}

## 要求

1. 每个查询应该是 3-8 个英文关键词（Semantic Scholar 搜索用英文效果最好）
2. 查询应该多样化，覆盖不同角度：
   - 查询 1：核心方法/算法（如 "fully homomorphic encryption hardware accelerator"）
   - 查询 2：问题域 + 最新技术（如 "FHE ASIC design 2024"）
   - 查询 3：竞争方法/替代方案（如 "bootstrapping optimization lattice cryptography"）
   - 查询 4：应用场景（如 "privacy preserving machine learning hardware"）
3. 不要生成太宽泛的查询（如 "deep learning"）
4. 不要生成与论文标题完全一样的查询

请直接输出查询列表，每行一个，不要编号或其他格式。
"""


@dataclass
class LiteratureReference:
    """A single reference paper retrieved from Semantic Scholar."""

    title: str
    authors: list[str]
    venue: str | None
    year: int
    abstract_snippet: str
    citation_count: int
    s2_paper_id: str
    is_cited_by_paper: bool
    relevance_note: str | None = None


@dataclass
class LiteratureContext:
    """Literature search results to be injected into review prompts."""

    query_terms: list[str]
    references: list[LiteratureReference]
    search_timestamp: str
    year_range: tuple[int, int]
    paper_title: str


def extract_search_queries(
    title: str,
    abstract: str,
    num_queries: int = 4,
) -> list[str]:
    """Extract diverse Semantic Scholar search queries from title and abstract."""
    llm_output = _call_llm_for_queries(title=title, abstract=abstract, num_queries=num_queries)
    queries = _parse_query_lines(llm_output) if llm_output else []
    if not queries:
        queries = _fallback_queries(title, abstract, num_queries)
    normalized: list[str] = []
    title_norm = _normalize_title(title)
    for query in queries:
        cleaned = _clean_query(query)
        if not cleaned:
            continue
        if _normalize_title(cleaned) == title_norm:
            continue
        normalized.append(cleaned)
    return list(dict.fromkeys(normalized))[:num_queries]


def search_literature(
    paper_title: str,
    paper_abstract: str,
    paper_references: list[str] | None = None,
    year_range: int = 3,
    max_results: int = 10,
    queries: list[str] | None = None,
) -> LiteratureContext:
    """Search related literature using Semantic Scholar with graceful fallback."""
    current_year = datetime.now().year
    start_year = max(1900, current_year - max(year_range, 0))
    year_tuple = (start_year, current_year)
    query_terms = queries or extract_search_queries(paper_title, paper_abstract)
    if not query_terms:
        return LiteratureContext([], [], datetime.now().isoformat(timespec="seconds"), year_tuple, paper_title)

    try:
        raw_results = asyncio.run(
            _search_literature_async(
                query_terms=query_terms,
                year_tuple=year_tuple,
                max_results=max(max_results, 1),
            )
        )
        references = _deduplicate_and_rank(
            raw_results=raw_results,
            paper_title=paper_title,
            paper_references=paper_references,
            max_results=max_results,
        )
    except Exception:
        references = []

    return LiteratureContext(
        query_terms=query_terms,
        references=references,
        search_timestamp=datetime.now().isoformat(timespec="seconds"),
        year_range=year_tuple,
        paper_title=paper_title,
    )


async def _search_literature_async(
    query_terms: list[str],
    year_tuple: tuple[int, int],
    max_results: int,
) -> list[PaperResult]:
    source = SemanticScholarSource(timeout=10.0, max_requests_per_second=1.0)
    raw_results: list[PaperResult] = []
    try:
        for query in query_terms:
            params = SearchParams(
                query=query,
                year_range=year_tuple,
                max_results=max(max_results, 10),
                sort_by="relevance",
            )
            try:
                raw_results.extend(await source.search(params))
            except SourceError:
                continue
    finally:
        await source.close()
    return raw_results


def _rate_limited_request(url: str, params: dict) -> dict:
    """Send a rate-limited request to S2 API with retry logic."""
    for attempt in range(S2_MAX_RETRIES):
        time.sleep(S2_REQUEST_DELAY)
        try:
            response = httpx.get(url, params=params, timeout=10)
            if response.status_code == 429:
                time.sleep(S2_RETRY_BACKOFF ** (attempt + 1))
                continue
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            if attempt == S2_MAX_RETRIES - 1:
                raise
            time.sleep(S2_RETRY_BACKOFF ** (attempt + 1))
    return {}


def _deduplicate_and_rank(
    raw_results: list[PaperResult | dict],
    paper_title: str,
    paper_references: list[str] | None,
    max_results: int,
) -> list[LiteratureReference]:
    """Deduplicate, filter self matches, mark cited papers, and rank."""
    seen: dict[str, PaperResult | dict] = {}
    for item in raw_results:
        paper_id = _paper_field(item, "s2_paper_id") or _paper_field(item, "paperId") or _paper_field(item, "paper_id")
        title = _paper_field(item, "title")
        if not paper_id or not title:
            continue
        if _title_similarity(title, paper_title) > 0.9:
            continue
        existing = seen.get(str(paper_id))
        if existing is None or _citation_count(item) > _citation_count(existing):
            seen[str(paper_id)] = item

    references = [
        _to_literature_reference(item, paper_references)
        for item in seen.values()
    ]
    references.sort(key=lambda ref: (ref.is_cited_by_paper, -ref.citation_count, -ref.year))
    return references[:max_results]


def format_literature_context(lit: LiteratureContext) -> str:
    """Format LiteratureContext into Markdown for prompt injection."""
    if not lit.references:
        return ""

    lines = [
        f"## 📚 近期相关工作参考（自动检索，{lit.search_timestamp}）",
        "",
        f"搜索关键词：{' | '.join(lit.query_terms)}",
        f"检索范围：{lit.year_range[0]}-{lit.year_range[1]} 年",
        "",
        "以下论文通过关键词检索自动获取，供评估 novelty 和实验对比参考：",
        "",
    ]
    for index, ref in enumerate(lit.references, start=1):
        cited_mark = "✅ 本文已引用" if ref.is_cited_by_paper else "⚠️ 本文未引用"
        authors_str = ", ".join(ref.authors[:3])
        if len(ref.authors) > 3:
            authors_str += " et al."
        lines.append(
            f"{index}. **{ref.title}** ({ref.venue or '未知venue'} {ref.year}, "
            f"被引 {ref.citation_count} 次) {cited_mark}"
        )
        lines.append(f"   作者：{authors_str or '未知作者'}")
        lines.append(f"   摘要：{ref.abstract_snippet}")
        if ref.relevance_note:
            lines.append(f"   相关性：{ref.relevance_note}")
        lines.append("")

    lines.extend(
        [
            "⚠️ 标记的论文可能是被遗漏的重要相关工作，请重点关注。",
            "",
            "基于以上文献，请额外评估：",
            "- 本文方法与最近工作相比是否有实质性差异？",
            "- 实验中是否遗漏了应该对比的近期 baseline？",
            "- Related Work 部分是否有重要遗漏？",
        ]
    )
    return "\n".join(lines)


def _call_llm_for_queries(title: str, abstract: str, num_queries: int) -> str | None:
    """Hook for tests or agent integrations; production CLI uses fallback extraction."""
    return None


def _parse_query_lines(value: str) -> list[str]:
    lines = []
    for raw_line in value.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", raw_line).strip()
        if cleaned:
            lines.append(cleaned.strip('"'))
    return lines


def _fallback_queries(title: str, abstract: str, num_queries: int) -> list[str]:
    text = f"{title} {abstract}"
    keywords = _keywords(text)
    title_words = _keywords(title)
    abstract_words = [word for word in keywords if word not in title_words]
    candidates = [
        " ".join(title_words[:6]),
        " ".join([*title_words[:3], *abstract_words[:3]]),
        " ".join([word for word in keywords if word in {"accelerator", "hardware", "optimization", "inference", "bootstrapping", "privacy"}][:6]),
        " ".join(keywords[:8]),
    ]
    return [candidate for candidate in candidates if candidate][:num_queries]


def _keywords(text: str) -> list[str]:
    stopwords = {
        "the", "and", "for", "with", "from", "that", "this", "are", "was", "were",
        "paper", "method", "approach", "using", "use", "our", "we", "a", "an", "of",
        "in", "on", "to", "by", "as", "at", "is", "be",
    }
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text)
        if word.lower() not in stopwords
    ]
    return list(dict.fromkeys(words))


def _clean_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip()).strip('"')


def _to_literature_reference(item: PaperResult | dict, paper_references: list[str] | None) -> LiteratureReference:
    authors = _authors(item)
    if len(authors) > 3:
        authors = [*authors[:3], "et al."]
    title = _paper_field(item, "title")
    abstract = _paper_field(item, "abstract") or ""
    return LiteratureReference(
        title=title,
        authors=authors,
        venue=_paper_field(item, "venue") or None,
        year=int(_paper_field(item, "year") or 0),
        abstract_snippet=_truncate_abstract(abstract),
        citation_count=_citation_count(item),
        s2_paper_id=str(_paper_field(item, "s2_paper_id") or _paper_field(item, "paperId") or _paper_field(item, "paper_id")),
        is_cited_by_paper=_is_cited(title, paper_references),
        relevance_note=None,
    )


def _paper_field(item: PaperResult | dict, field_name: str) -> Any:
    if isinstance(item, PaperResult):
        return getattr(item, field_name, None)
    return item.get(field_name)


def _authors(item: PaperResult | dict) -> list[str]:
    raw_authors = _paper_field(item, "authors") or []
    authors: list[str] = []
    for author in raw_authors:
        if isinstance(author, dict):
            name = author.get("name")
        else:
            name = str(author)
        if name:
            authors.append(name)
    return authors


def _citation_count(item: PaperResult | dict) -> int:
    value = _paper_field(item, "citation_count")
    if value is None:
        value = _paper_field(item, "citationCount")
    return int(value or 0)


def _is_cited(title: str, paper_references: list[str] | None) -> bool:
    if not paper_references:
        return False
    normalized_title = _normalize_title(title)
    for reference in paper_references:
        normalized_ref = _normalize_title(reference)
        if normalized_title and (
            normalized_title in normalized_ref
            or normalized_ref in normalized_title
            or _title_similarity(normalized_title, normalized_ref) > 0.82
        ):
            return True
    return False


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


def _normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.lower())).strip()


def _truncate_abstract(abstract: str, limit: int = 200) -> str:
    cleaned = re.sub(r"\s+", " ", abstract).strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3].rstrip()}..."
