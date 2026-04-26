"""Tests for meeting glossary management."""

from __future__ import annotations

from pathlib import Path

from hypo_research.meeting.glossary import GlossaryManager, GlossaryTerm


def test_glossary_load_from_file(tmp_path: Path) -> None:
    path = tmp_path / "glossary.toml"
    path.write_text(
        """
[[术语]]
keyword = "全同态加密"
canonical = "全同态加密 (Fully Homomorphic Encryption, FHE)"
aliases = ["同态加密", "FHE"]
category = "crypto"
""",
        encoding="utf-8",
    )

    terms = GlossaryManager(path).load()

    assert terms["全同态加密"].canonical.startswith("全同态加密")
    assert terms["全同态加密"].aliases == ["同态加密", "FHE"]


def test_glossary_load_creates_missing_file(tmp_path: Path) -> None:
    path = tmp_path / ".hypo-research" / "glossary.toml"
    manager = GlossaryManager(path)

    terms = manager.load()

    assert terms == {}
    assert path.exists()
    assert "[[术语]]" in path.read_text(encoding="utf-8")


def test_glossary_lookup_keyword_and_alias_case_insensitive(tmp_path: Path) -> None:
    manager = GlossaryManager(tmp_path / "glossary.toml")
    manager.add_term(
        GlossaryTerm(
            keyword="bootstrapping",
            canonical="Bootstrapping（自举）",
            aliases=["自举", "BOOT"],
            category="crypto",
        )
    )

    assert manager.lookup("bootstrapping").canonical == "Bootstrapping（自举）"
    assert manager.lookup("boot").canonical == "Bootstrapping（自举）"


def test_glossary_add_save_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "glossary.toml"
    manager = GlossaryManager(path)
    manager.add_term(
        GlossaryTerm(
            keyword="NTT",
            canonical="数论变换 (Number Theoretic Transform, NTT)",
            aliases=["数论变换"],
            category="math",
        )
    )
    manager.save()

    loaded = GlossaryManager(path).load()

    assert loaded["NTT"].category == "math"
    assert loaded["NTT"].aliases == ["数论变换"]


def test_glossary_export_for_prompt(tmp_path: Path) -> None:
    manager = GlossaryManager(tmp_path / "glossary.toml")
    manager.add_term(
        GlossaryTerm(
            keyword="FHE",
            canonical="全同态加密 (Fully Homomorphic Encryption, FHE)",
            aliases=["同台加密"],
            category="crypto",
        )
    )

    exported = manager.export_for_prompt()

    assert "FHE [crypto]" in exported
    assert "同台加密" in exported
