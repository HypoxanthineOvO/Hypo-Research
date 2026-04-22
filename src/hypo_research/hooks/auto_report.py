"""Built-in Markdown report generation hook."""

from __future__ import annotations

from hypo_research.hooks.base import HookContext
from hypo_research.output.markdown_report import generate_report


class AutoReportHook:
    """Generate a Markdown report after output is written."""

    name = "auto_report"

    def __call__(self, ctx: HookContext) -> None:
        """Generate a Markdown report for current results."""
        output_path = ctx.output_dir / "results.md"
        generate_report(ctx.papers, ctx.meta, output_path)
        ctx.messages.append(f"{self.name}: Generated results.md")
