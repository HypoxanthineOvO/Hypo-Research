"""Heuristic L2 evidence-card extraction from paper read artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class EvidenceCard:
    """A single paper-reading evidence card."""

    kind: str
    title: str
    evidence: str
    confidence: str = "low"
    location: str | None = None


@dataclass
class EvidenceExtractionResult:
    """Grouped evidence cards extracted from a read artifact."""

    method_cards: list[EvidenceCard] = field(default_factory=list)
    dataset_cards: list[EvidenceCard] = field(default_factory=list)
    figure_cards: list[EvidenceCard] = field(default_factory=list)
    claim_cards: list[EvidenceCard] = field(default_factory=list)
    agent_prompt: str = ""

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


def extract_evidence_cards(
    artifact_path: str | Path,
    output_dir: str | Path,
    *,
    focus: list[str] | None = None,
) -> EvidenceExtractionResult:
    """Extract heuristic L2 evidence cards and write JSON/Markdown outputs."""
    payload = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
    text = str(payload.get("raw_text") or "")
    focus_set = set(focus or ["methods", "datasets", "figures", "claims"])
    result = EvidenceExtractionResult()

    if "methods" in focus_set:
        result.method_cards = _method_cards(text)
    if "datasets" in focus_set:
        result.dataset_cards = _dataset_cards(text)
    if "figures" in focus_set:
        result.figure_cards = _figure_cards(text, payload)
    if "claims" in focus_set:
        result.claim_cards = _claim_cards(text)
    result.agent_prompt = _agent_prompt(payload, result)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "cards.json").write_text(
        json.dumps(result.to_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "cards.md").write_text(_render_markdown(payload, result), encoding="utf-8")
    return result


def _method_cards(text: str) -> list[EvidenceCard]:
    cards = []
    for sentence in _sentences(text):
        lowered = sentence.lower()
        if any(pattern in lowered for pattern in ["we propose", "we present", "we introduce", "our method", "our approach"]):
            cards.append(EvidenceCard(kind="method", title="Method candidate", evidence=sentence, confidence="medium"))
        if len(cards) >= 5:
            break
    return cards


def _dataset_cards(text: str) -> list[EvidenceCard]:
    cards = []
    for sentence in _sentences(text):
        lowered = sentence.lower()
        if any(pattern in lowered for pattern in ["dataset", "benchmark", "experiment", "evaluation", "workload"]):
            cards.append(EvidenceCard(kind="dataset", title="Dataset/benchmark candidate", evidence=sentence, confidence="low"))
        if len(cards) >= 6:
            break
    return cards


def _figure_cards(text: str, payload: dict) -> list[EvidenceCard]:
    cards = []
    figure_re = re.compile(r"\b(?:Fig\.|Figure|Table)\s+(?P<label>[\w.-]+)\s*[:.]\s*(?P<caption>[^\n]{10,240})", re.IGNORECASE)
    for match in figure_re.finditer(text):
        cards.append(
            EvidenceCard(
                kind="figure",
                title=f"Figure/Table {match.group('label')}",
                evidence=" ".join(match.group("caption").split()),
                confidence="medium",
            )
        )
        if len(cards) >= 8:
            break
    if not cards and payload.get("images"):
        cards.append(
            EvidenceCard(
                kind="figure",
                title="Image objects detected",
                evidence=f"{len(payload.get('images') or [])} image objects detected; captions require deeper parsing.",
                confidence="low",
            )
        )
    return cards


def _claim_cards(text: str) -> list[EvidenceCard]:
    cards = []
    for sentence in _sentences(text):
        lowered = sentence.lower()
        if any(pattern in lowered for pattern in ["we achieve", "outperform", "speedup", "improve", "state-of-the-art", "reduce"]):
            cards.append(EvidenceCard(kind="claim", title="Claim candidate", evidence=sentence, confidence="low"))
        if len(cards) >= 8:
            break
    return cards


def _sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", cleaned) if len(item.strip()) >= 40]


def _agent_prompt(payload: dict, result: EvidenceExtractionResult) -> str:
    return (
        f"Deep-read paper '{payload.get('title', 'Unknown')}'. "
        "Use the evidence cards to verify methods, datasets/benchmarks, key figures, and claim support. "
        "Mark uncertain claims explicitly and cite section/page hints when available. "
        f"Cards: methods={len(result.method_cards)}, datasets={len(result.dataset_cards)}, "
        f"figures={len(result.figure_cards)}, claims={len(result.claim_cards)}."
    )


def _render_markdown(payload: dict, result: EvidenceExtractionResult) -> str:
    lines = [f"# Evidence Cards: {payload.get('title', 'Unknown')}", ""]
    for heading, cards in [
        ("Methods", result.method_cards),
        ("Datasets / Benchmarks", result.dataset_cards),
        ("Figures / Tables", result.figure_cards),
        ("Claims", result.claim_cards),
    ]:
        lines.extend([f"## {heading}", ""])
        if not cards:
            lines.append("- No candidates found.")
        for card in cards:
            lines.append(f"- **{card.title}** ({card.confidence}): {card.evidence}")
        lines.append("")
    lines.extend(["## Agent Prompt", "", result.agent_prompt, ""])
    return "\n".join(lines)
