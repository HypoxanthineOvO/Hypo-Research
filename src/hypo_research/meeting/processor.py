"""Meeting transcript preprocessing and prompt context preparation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from hypo_research.meeting.glossary import GlossaryManager, GlossaryTerm
from hypo_research.meeting.inference import MeetingInference, infer_meeting_metadata
from hypo_research.meeting.templates import get_template

logger = logging.getLogger(__name__)


@dataclass
class MeetingInput:
    """Input metadata for meeting minutes processing."""

    transcript_path: Path
    meeting_type: str = "group_meeting"
    participants: list[str] | None = None
    date: str = ""
    topic: str = ""
    output_path: Path | None = None


@dataclass
class MeetingOutput:
    """Output metadata from code-level meeting preprocessing."""

    minutes_path: Path
    template_used: str
    terms_corrected: list[str]
    unknown_terms: list[str]
    inference: MeetingInference


class MeetingProcessor:
    """Prepare ASR transcript context for an Agent-written meeting minutes file."""

    _ACRONYM_RE = re.compile(r"\b[A-Z]{2,6}\b")
    _QUOTED_RE = re.compile(r"[\"'“”‘’]([^\"'“”‘’]{2,40})[\"'“”‘’]")

    def __init__(self, glossary: GlossaryManager):
        self.glossary = glossary

    def load_transcript(self, path: Path) -> str:
        """Read ASR transcript file (.txt / .md)."""
        if path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("Transcript file must be .txt or .md")
        return path.read_text(encoding="utf-8")

    def preprocess(self, transcript: str) -> tuple[str, list[str], list[str]]:
        """Apply high-confidence term corrections from glossary."""
        terms = self.glossary.load()
        corrected_text = transcript
        corrected_terms: list[str] = []

        aliases: list[tuple[str, GlossaryTerm]] = []
        for term in terms.values():
            for alias in term.aliases:
                if alias and self.glossary._normalize(
                    alias
                ) != self.glossary._normalize(term.canonical):
                    aliases.append((alias, term))
        aliases.sort(key=lambda item: len(item[0]), reverse=True)

        for alias, term in aliases:
            pattern = re.compile(self._full_token_pattern(alias), flags=re.IGNORECASE)

            def replace(match: re.Match[str]) -> str:
                corrected_terms.append(match.group(0))
                return term.canonical

            corrected_text = pattern.sub(replace, corrected_text)

        unknown_terms = self._detect_unknown_terms(corrected_text)
        return corrected_text, list(dict.fromkeys(corrected_terms)), unknown_terms

    def infer(self, transcript: str) -> MeetingInference:
        """Infer meeting metadata from a transcript."""
        terms = self.glossary.load()
        glossary_terms = []
        for term in terms.values():
            glossary_terms.extend([term.keyword, term.canonical, *term.aliases])
        return infer_meeting_metadata(transcript, glossary_terms=glossary_terms)

    def prepare_prompt_context(self, input: MeetingInput) -> dict:
        """Prepare transcript, template, glossary, and metadata for an Agent."""
        transcript = self.load_transcript(input.transcript_path)
        inference = self.infer(transcript)
        corrected_text, corrected_terms, unknown_terms = self.preprocess(transcript)
        template = get_template(input.meeting_type)
        meeting_date = input.date or date.today().isoformat()
        participants = input.participants or []
        output_path = input.output_path or input.transcript_path.with_name(
            f"{input.transcript_path.stem}_minutes.md"
        )

        return {
            "corrected_transcript": corrected_text,
            "template_skeleton": template.skeleton,
            "template_used": template.name,
            "template_display_name": template.display_name,
            "glossary_excerpt": self.glossary.export_for_prompt(),
            "metadata": {
                "date": meeting_date,
                "participants": participants,
                "topic": input.topic,
                "transcript_path": str(input.transcript_path),
                "output_path": str(output_path),
            },
            "terms_corrected": corrected_terms,
            "unknown_terms": unknown_terms,
            "inference": inference,
        }

    def write_prompt_context(self, input: MeetingInput) -> MeetingOutput:
        """Write code-level context for Agent minutes generation."""
        context = self.prepare_prompt_context(input)
        output_path = Path(context["metadata"]["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self._render_context_markdown(context), encoding="utf-8")
        return MeetingOutput(
            minutes_path=output_path,
            template_used=str(context["template_used"]),
            terms_corrected=list(context["terms_corrected"]),
            unknown_terms=list(context["unknown_terms"]),
            inference=context["inference"],
        )

    def _detect_unknown_terms(self, text: str) -> list[str]:
        unknown: list[str] = []
        for match in self._ACRONYM_RE.findall(text):
            if self.glossary.lookup(match) is None:
                unknown.append(match)
        for match in self._QUOTED_RE.findall(text):
            candidate = match.strip()
            if candidate and self.glossary.lookup(candidate) is None:
                unknown.append(candidate)
        return list(dict.fromkeys(unknown))

    @staticmethod
    def _full_token_pattern(alias: str) -> str:
        escaped = re.escape(alias)
        return (
            rf"(?<![A-Za-z0-9_\u4e00-\u9fff])"
            rf"{escaped}"
            rf"(?![A-Za-z0-9_\u4e00-\u9fff])"
        )

    @staticmethod
    def _render_context_markdown(context: dict) -> str:
        metadata = context["metadata"]
        participants = ", ".join(metadata["participants"]) or "（未提供）"
        corrected_terms = ", ".join(context["terms_corrected"]) or "无"
        unknown_terms = ", ".join(context["unknown_terms"]) or "无"
        glossary = context["glossary_excerpt"] or "（空）"
        return f"""# Meeting Processing Context

## Metadata
- Date: {metadata["date"]}
- Topic: {metadata["topic"] or "（未提供）"}
- Participants: {participants}
- Template: {context["template_used"]} ({context["template_display_name"]})
- Transcript: {metadata["transcript_path"]}

## Terms Corrected
{corrected_terms}

## Unknown Terms
{unknown_terms}

## Inference
- Meeting type: {context["inference"].meeting_type}
- Confidence: {context["inference"].meeting_type_confidence}
- Reason: {context["inference"].meeting_type_reason}
- Participants: {", ".join(context["inference"].participants) or "（未推断）"}
- Topic: {context["inference"].topic or "（未推断）"}
- Domain keywords: {", ".join(context["inference"].domain_keywords) or "（未检测）"}
- Language: {context["inference"].language}

## Glossary Excerpt
{glossary}

## Template Skeleton
```markdown
{context["template_skeleton"].rstrip()}
```

## Corrected Transcript
{context["corrected_transcript"].strip()}
"""
