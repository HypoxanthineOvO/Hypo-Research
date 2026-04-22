"""Hook infrastructure for the search pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol

from rich.console import Console

from hypo_research.core.models import PaperResult, SurveyMeta

logger = logging.getLogger(__name__)


class HookEvent(str, Enum):
    """Pipeline events that hooks can listen to."""

    POST_SEARCH = "post_search"
    POST_DEDUP = "post_dedup"
    POST_VERIFY = "post_verify"
    POST_OUTPUT = "post_output"


@dataclass
class HookContext:
    """Context passed to hooks at each event."""

    papers: list[PaperResult]
    meta: SurveyMeta
    output_dir: Path
    event: HookEvent
    console: Console | None = None
    messages: list[str] = field(default_factory=list)


class Hook(Protocol):
    """Hook protocol."""

    name: str

    def __call__(self, ctx: HookContext) -> None:
        """Execute hook logic."""


class HookManager:
    """Registry and executor for hooks."""

    def __init__(self) -> None:
        self._hooks: dict[HookEvent, list[Hook]] = {event: [] for event in HookEvent}

    def register(self, event: HookEvent, hook: Hook) -> None:
        """Register a hook for a specific event."""
        self._hooks[event].append(hook)

    def trigger(self, event: HookEvent, ctx: HookContext) -> list[str]:
        """Trigger all hooks for an event."""
        ran: list[str] = []
        for hook in self._hooks.get(event, []):
            if ctx.console is not None:
                ctx.console.print(f"Running hook: {hook.name}...", markup=False)
            try:
                hook(ctx)
            except Exception as exc:  # pragma: no cover
                logger.warning("hook %s failed during %s: %s", hook.name, event.value, exc)
                continue
            ran.append(hook.name)
        return ran

    def register_defaults(self) -> None:
        """Register built-in hooks."""
        from hypo_research.hooks.auto_bib import AutoBibHook
        from hypo_research.hooks.auto_report import AutoReportHook
        from hypo_research.hooks.auto_verify import AutoVerifyHook

        self.register(HookEvent.POST_VERIFY, AutoVerifyHook())
        self.register(HookEvent.POST_OUTPUT, AutoBibHook())
        self.register(HookEvent.POST_OUTPUT, AutoReportHook())
