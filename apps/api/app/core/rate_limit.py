"""In-memory sliding-window rate limiter (production-safe for single-process API)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: int
    retry_after: int | None = None


class SlidingWindowRateLimiter:
    """Thread-safe per-key sliding window limiter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.time()
        window_start = now - window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] <= window_start:
                bucket.popleft()
            used = len(bucket)
            reset_at = int(bucket[0] + window_seconds) if bucket else int(now + window_seconds)
            if used >= limit:
                retry_after = max(1, reset_at - int(now))
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                )
            bucket.append(now)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=max(0, limit - len(bucket)),
                reset_at=int(now + window_seconds),
                retry_after=None,
            )


# Process-local singleton — sufficient for single uvicorn worker / local compose.
_limiter = SlidingWindowRateLimiter()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    return _limiter
