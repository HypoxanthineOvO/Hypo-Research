"""Tests for hook infrastructure."""

from __future__ import annotations

from pathlib import Path

from hypo_research.core.models import PaperResult, SearchParams, SurveyMeta
from hypo_research.hooks.base import HookContext, HookEvent, HookManager


def make_context(event: HookEvent) -> HookContext:
    paper = PaperResult(
        title="Paper",
        authors=["Alice Smith"],
        year=2024,
        venue="ISSCC",
        abstract="Abstract",
        url="https://example.com",
        source_api="semantic_scholar",
        sources=["semantic_scholar"],
    )
    meta = SurveyMeta(
        query="cryogenic computing GPU",
        params=SearchParams(query="cryogenic computing GPU"),
        output_dir="/tmp/out",
    )
    return HookContext(papers=[paper], meta=meta, output_dir=Path("/tmp/out"), event=event)


def test_hook_manager_register_and_trigger() -> None:
    manager = HookManager()
    called: list[str] = []

    class DummyHook:
        name = "dummy"

        def __call__(self, ctx: HookContext) -> None:
            called.append(ctx.event.value)

    manager.register(HookEvent.POST_SEARCH, DummyHook())
    ctx = make_context(HookEvent.POST_SEARCH)
    ran = manager.trigger(HookEvent.POST_SEARCH, ctx)

    assert ran == ["dummy"]
    assert called == ["post_search"]


def test_hook_manager_tolerates_hook_errors() -> None:
    manager = HookManager()
    called: list[str] = []

    class BrokenHook:
        name = "broken"

        def __call__(self, ctx: HookContext) -> None:
            raise RuntimeError("boom")

    class HealthyHook:
        name = "healthy"

        def __call__(self, ctx: HookContext) -> None:
            called.append("healthy")

    manager.register(HookEvent.POST_DEDUP, BrokenHook())
    manager.register(HookEvent.POST_DEDUP, HealthyHook())
    ctx = make_context(HookEvent.POST_DEDUP)
    ran = manager.trigger(HookEvent.POST_DEDUP, ctx)

    assert ran == ["healthy"]
    assert called == ["healthy"]


def test_hook_manager_preserves_registration_order() -> None:
    manager = HookManager()
    order: list[str] = []

    class HookA:
        name = "a"

        def __call__(self, ctx: HookContext) -> None:
            order.append("a")

    class HookB:
        name = "b"

        def __call__(self, ctx: HookContext) -> None:
            order.append("b")

    manager.register(HookEvent.POST_OUTPUT, HookA())
    manager.register(HookEvent.POST_OUTPUT, HookB())
    manager.trigger(HookEvent.POST_OUTPUT, make_context(HookEvent.POST_OUTPUT))

    assert order == ["a", "b"]


def test_register_defaults_registers_builtin_hooks() -> None:
    manager = HookManager()

    manager.register_defaults()

    assert [hook.name for hook in manager._hooks[HookEvent.POST_VERIFY]] == ["auto_verify"]
    assert [hook.name for hook in manager._hooks[HookEvent.POST_OUTPUT]] == [
        "auto_bib",
        "auto_report",
    ]
