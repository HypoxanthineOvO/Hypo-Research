"""Tests for the async rate limiter."""

from __future__ import annotations

import asyncio
import time

import pytest

from hypo_research.core.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_acquire_consumes_token() -> None:
    limiter = RateLimiter(max_tokens=2, refill_period=1, name="test")

    await limiter.acquire()

    assert limiter._tokens < 2


@pytest.mark.asyncio
async def test_acquire_waits_when_bucket_is_empty() -> None:
    limiter = RateLimiter(max_tokens=1, refill_period=0.2, name="test")

    start = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.18


@pytest.mark.asyncio
async def test_concurrent_acquire_serializes_waiters() -> None:
    limiter = RateLimiter(max_tokens=2, refill_period=0.2, name="test")
    completion_times: list[float] = []

    async def worker() -> None:
        async with limiter:
            completion_times.append(time.monotonic())

    start = time.monotonic()
    await asyncio.gather(worker(), worker(), worker())
    elapsed = time.monotonic() - start

    assert len(completion_times) == 3
    assert elapsed >= 0.08
