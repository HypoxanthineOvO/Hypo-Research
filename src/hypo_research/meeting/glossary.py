"""Global glossary management for meeting transcript cleanup."""

from __future__ import annotations

import logging
import re
import tomllib
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path

logger = logging.getLogger(__name__)

GLOSSARY_HEADER = """# Hypo-Research global glossary.
# Add terms using:
# uv run hypo-research glossary add --keyword "FHE" \
#   --canonical "Fully Homomorphic Encryption (FHE)" \
#   --aliases "fully homomorphic,encryption"
#
# Format:
# [[术语]]
# keyword = "全同态加密"
# canonical = "全同态加密 (Fully Homomorphic Encryption, FHE)"
# aliases = ["同态加密", "同台加密", "FHE"]
# category = "crypto"
"""


@dataclass
class GlossaryTerm:
    """A single glossary entry."""

    keyword: str
    canonical: str
    aliases: list[str] = field(default_factory=list)
    category: str = ""


class GlossaryManager:
    """Load, query, and update the global glossary."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".hypo-research" / "glossary.toml"
        self.terms: dict[str, GlossaryTerm] = {}

    def load(self) -> dict[str, GlossaryTerm]:
        """Load glossary from ~/.hypo-research/glossary.toml."""
        if not self.path.exists():
            logger.info("Creating empty glossary at %s", self.path)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(GLOSSARY_HEADER + "\n", encoding="utf-8")
            self.terms = {}
            return self.terms

        content = self._normalize_table_names(self.path.read_text(encoding="utf-8"))
        data = tomllib.loads(content)
        entries = data.get("术语", data.get("terms", []))
        loaded: dict[str, GlossaryTerm] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            keyword = str(entry.get("keyword", "")).strip()
            canonical = str(entry.get("canonical", "")).strip()
            if not keyword or not canonical:
                continue
            aliases = [
                str(alias).strip()
                for alias in entry.get("aliases", [])
                if str(alias).strip()
            ]
            loaded[keyword] = GlossaryTerm(
                keyword=keyword,
                canonical=canonical,
                aliases=aliases,
                category=str(entry.get("category", "")).strip(),
            )
        self.terms = loaded
        return self.terms

    def lookup(self, keyword: str) -> GlossaryTerm | None:
        """Lookup by keyword or alias (case-insensitive, fuzzy)."""
        if not self.terms:
            self.load()
        needle = self._normalize(keyword)
        if not needle:
            return None

        for term in self.terms.values():
            if self._normalize(term.keyword) == needle:
                return term
            if any(self._normalize(alias) == needle for alias in term.aliases):
                return term

        candidates: dict[str, GlossaryTerm] = {}
        for term in self.terms.values():
            candidates[self._normalize(term.keyword)] = term
            for alias in term.aliases:
                candidates[self._normalize(alias)] = term
        matches = get_close_matches(needle, list(candidates), n=1, cutoff=0.82)
        if matches:
            return candidates[matches[0]]
        return None

    def add_term(self, term: GlossaryTerm) -> None:
        """Add or update a term in the glossary."""
        if not self.terms:
            self.load()
        self.terms[term.keyword] = term

    def remove_term(self, keyword: str) -> bool:
        """Remove a term by keyword or alias."""
        if not self.terms:
            self.load()
        term = self.lookup(keyword)
        if term is None:
            return False
        self.terms.pop(term.keyword, None)
        return True

    def save(self) -> None:
        """Save glossary back to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self._to_toml(), encoding="utf-8")

    def export_for_prompt(self) -> str:
        """Export glossary as a compact string for inclusion in Agent prompts."""
        if not self.terms:
            self.load()
        lines = []
        for term in sorted(self.terms.values(), key=lambda item: item.keyword.lower()):
            aliases = ", ".join(term.aliases) if term.aliases else "-"
            category = f" [{term.category}]" if term.category else ""
            lines.append(
                f"- {term.keyword}{category}: {term.canonical}; aliases: {aliases}"
            )
        return "\n".join(lines)

    def _to_toml(self) -> str:
        lines = [GLOSSARY_HEADER.rstrip(), ""]
        for term in sorted(self.terms.values(), key=lambda item: item.keyword.lower()):
            lines.append("[[术语]]")
            lines.append(f'keyword = "{self._toml_escape(term.keyword)}"')
            lines.append(f'canonical = "{self._toml_escape(term.canonical)}"')
            aliases = ", ".join(
                f'"{self._toml_escape(alias)}"' for alias in term.aliases
            )
            lines.append(f"aliases = [{aliases}]")
            lines.append(f'category = "{self._toml_escape(term.category)}"')
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _normalize_table_names(content: str) -> str:
        """Allow the documented Chinese table-array spelling before tomllib parse."""
        return re.sub(r"(?m)^(\s*)\[\[术语\]\]", r'\1[["术语"]]', content)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().strip().split())

    @staticmethod
    def _toml_escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')
