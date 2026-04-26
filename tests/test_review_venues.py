"""Tests for review venue profiles."""

from __future__ import annotations

import pytest

from hypo_research.review.venues import VENUES, get_review_venue


def test_venue_profiles_are_complete() -> None:
    assert len(VENUES) >= 20
    for venue_id, venue in VENUES.items():
        assert venue.id == venue_id
        assert venue.name
        assert venue.category
        assert venue.focus
        assert venue.review_criteria


def test_venue_categories_cover_required_types() -> None:
    categories = {venue.category for venue in VENUES.values()}

    assert {"circuits", "eda", "architecture", "ml", "vision", "graphics"} <= categories


def test_venue_lookup() -> None:
    assert get_review_venue("dac").name == "DAC"
    with pytest.raises(KeyError):
        get_review_venue("unknown")
