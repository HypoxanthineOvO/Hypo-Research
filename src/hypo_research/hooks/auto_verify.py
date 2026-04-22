"""Built-in metadata quality verification hook."""

from __future__ import annotations

from hypo_research.core.models import MetadataIssue
from hypo_research.hooks.base import HookContext


class AutoVerifyHook:
    """Check metadata quality after verification."""

    name = "auto_verify"

    def __call__(self, ctx: HookContext) -> None:
        """Inspect paper metadata and record issues."""
        warnings_count = 0
        errors_count = 0
        papers_with_issues = 0

        for paper in ctx.papers:
            issues: list[MetadataIssue] = []

            if not paper.doi:
                issues.append(MetadataIssue(field="doi", severity="warning", message="No DOI available"))
            if not paper.abstract:
                issues.append(MetadataIssue(field="abstract", severity="warning", message="No abstract available"))
            if not paper.year or paper.year == 0:
                issues.append(MetadataIssue(field="year", severity="error", message="Invalid publication year"))
            if not paper.authors:
                issues.append(MetadataIssue(field="authors", severity="error", message="No authors listed"))
            if len(paper.title.strip()) < 10:
                issues.append(MetadataIssue(field="title", severity="warning", message="Suspiciously short title"))
            verification = getattr(paper.verification, "value", paper.verification)
            if verification == "single_source" and not paper.doi:
                issues.append(
                    MetadataIssue(
                        field="verification",
                        severity="warning",
                        message="Unverifiable: single source without DOI",
                    )
                )

            paper.metadata_issues = issues
            if issues:
                papers_with_issues += 1
                warnings_count += sum(1 for issue in issues if issue.severity == "warning")
                errors_count += sum(1 for issue in issues if issue.severity == "error")

        ctx.meta.metadata_warnings_count = warnings_count
        ctx.meta.metadata_errors_count = errors_count
        ctx.meta.papers_with_issues_count = papers_with_issues
        ctx.messages.append(
            f"{self.name}: {warnings_count} warnings, {errors_count} error"
            f"{'' if errors_count == 1 else 's'} across {papers_with_issues} papers"
        )
