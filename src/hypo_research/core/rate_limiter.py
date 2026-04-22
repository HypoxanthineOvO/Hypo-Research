"""Async rate limiting helpers."""

from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for async HTTP clients."""

    def __init__(self, max_tokens: int, refill_period: float, name: str = ""):
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if refill_period <= 0:
            raise ValueError("refill_period must be positive")

        self.max_tokens = max_tokens
        self.refill_period = refill_period
        self.name = name or "rate_limiter"
        self._refill_rate = max_tokens / refill_period
        self._tokens = float(max_tokens)
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self, now: float) -> None:
        elapsed = now - self._updated_at
        if elapsed <= 0:
            return
        self._tokens = min(
            float(self.max_tokens), self._tokens + (elapsed * self._refill_rate)
        )
        self._updated_at = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume one."""
        while True:
            async with self._lock:
                now = time.monotonic()
                self._refill(now)
                if self._tokens >= 1:
                    self._tokens -= 1
                    logger.debug(
                        "[%s] token acquired; tokens remaining: %.3f/%s",
                        self.name,
                        self._tokens,
                        self.max_tokens,
                    )
                    return

                wait_time = (1 - self._tokens) / self._refill_rate
                logger.debug(
                    "[%s] waiting %.3fs; tokens available: %.3f/%s",
                    self.name,
                    wait_time,
                    self._tokens,
                    self.max_tokens,
                )

            await asyncio.sleep(wait_time)

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None
