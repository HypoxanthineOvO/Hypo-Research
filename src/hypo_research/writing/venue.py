"""Venue profiles for venue-aware writing checks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VenueProfile:
    """Venue-specific writing and verification behavior."""

    name: str
    display_name: str
    accepted_float_placements: list[str]
    extra_label_prefixes: dict[str, str] = field(default_factory=dict)
    severity_overrides: dict[str, str] = field(default_factory=dict)
    warn_missing_doi: bool = True
    bilingual_mode: str = "english_final_with_comments"


VENUE_PROFILES: dict[str, VenueProfile] = {
    "generic": VenueProfile(
        name="generic",
        display_name="Generic LaTeX",
        accepted_float_placements=["[htbp]"],
        warn_missing_doi=True,
        bilingual_mode="english_final_with_comments",
    ),
    "ieee_journal": VenueProfile(
        name="ieee_journal",
        display_name="IEEE Journal",
        accepted_float_placements=["[t]", "[!t]", "[tb]", "[tbp]", "[htbp]"],
        severity_overrides={"L04": "info"},
        warn_missing_doi=False,
        bilingual_mode="english_final_with_comments",
    ),
    "ieee_conference": VenueProfile(
        name="ieee_conference",
        display_name="IEEE Conference",
        accepted_float_placements=["[t]", "[!t]", "[tb]", "[tbp]", "[htbp]"],
        severity_overrides={"L04": "info"},
        warn_missing_doi=False,
        bilingual_mode="english_final_with_comments",
    ),
    "acm": VenueProfile(
        name="acm",
        display_name="ACM",
        accepted_float_placements=["[t]", "[tbp]", "[htbp]"],
        warn_missing_doi=True,
        bilingual_mode="english_final_with_comments",
    ),
    "neurips": VenueProfile(
        name="neurips",
        display_name="NeurIPS / ICML / ICLR",
        accepted_float_placements=["[t]", "[tbp]", "[htbp]"],
        warn_missing_doi=False,
        bilingual_mode="english_final_with_comments",
    ),
    "arxiv": VenueProfile(
        name="arxiv",
        display_name="arXiv Preprint",
        accepted_float_placements=["[htbp]"],
        warn_missing_doi=False,
        bilingual_mode="english_final_with_comments",
    ),
    "thesis": VenueProfile(
        name="thesis",
        display_name="Thesis / Dissertation",
        accepted_float_placements=["[htbp]"],
        warn_missing_doi=True,
        bilingual_mode="strict",
    ),
}


def get_venue(name: str | None) -> VenueProfile:
    """Return a built-in venue profile or fall back to generic."""
    if name is None:
        return VENUE_PROFILES["generic"]
    return VENUE_PROFILES.get(name, VENUE_PROFILES["generic"])


def list_venues() -> list[str]:
    """List all built-in venue profile names."""
    return sorted(VENUE_PROFILES)
