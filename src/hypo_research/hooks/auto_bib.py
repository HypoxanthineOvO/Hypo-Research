"""Built-in BibTeX generation hook."""

from __future__ import annotations

from hypo_research.hooks.base import HookContext
from hypo_research.output.bibtex import generate_bibtex


class AutoBibHook:
    """Generate a BibTeX file after output is written."""

    name = "auto_bib"

    def __call__(self, ctx: HookContext) -> None:
        """Generate a BibTeX file for current results."""
        output_path = ctx.output_dir / "references.bib"
        generate_bibtex(ctx.papers, output_path, query=ctx.meta.query)
        content = output_path.read_text(encoding="utf-8")
        entry_count = content.count("\n@")
        if content.startswith("@"):
            entry_count += 1
        ctx.messages.append(
            f"{self.name}: Generated references.bib ({entry_count} entries)"
        )
