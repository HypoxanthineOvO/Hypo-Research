"""Severity grading helpers for writing diagnostics."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from hypo_research.writing.venue import VenueProfile


class Severity(str, Enum):
    """Severity levels for lint and verify outputs."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    UNCERTAIN = "uncertain"


def coerce_severity(value: str | Severity) -> Severity:
    """Normalize strings and enums into a Severity value."""
    if isinstance(value, Severity):
        return value
    return Severity(str(value).lower())


def resolve_severity(
    rule_id: str,
    default: Severity,
    *,
    venue: VenueProfile | None = None,
    config_overrides: dict[str, str] | None = None,
) -> tuple[Severity, str]:
    """Resolve severity with config overrides taking precedence over venue."""
    severity = default
    source = ""

    if venue is not None and rule_id in venue.severity_overrides:
        severity = coerce_severity(venue.severity_overrides[rule_id])
        source = venue.name

    if config_overrides is not None and rule_id in config_overrides:
        severity = coerce_severity(config_overrides[rule_id])
        source = "config"

    return severity, source
