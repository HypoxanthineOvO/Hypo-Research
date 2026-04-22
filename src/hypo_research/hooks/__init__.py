"""Built-in hooks and hook manager exports."""

from hypo_research.hooks.auto_bib import AutoBibHook
from hypo_research.hooks.auto_report import AutoReportHook
from hypo_research.hooks.auto_verify import AutoVerifyHook
from hypo_research.hooks.base import Hook, HookContext, HookEvent, HookManager

__all__ = [
    "AutoBibHook",
    "AutoReportHook",
    "AutoVerifyHook",
    "Hook",
    "HookContext",
    "HookEvent",
    "HookManager",
]
