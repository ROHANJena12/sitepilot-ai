"""In-process fake async Redis for unit tests (no real Redis server)."""

from __future__ import annotations

import asyncio
from typing import Any


class FakeAsyncRedis:
    """Minimal async Redis stand-in covering RedisQueue operations."""

    def __init__(self) -> None:
        self._zsets: dict[str, dict[str, float]] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._kv: dict[str, str] = {}
        self._ttls: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self.now: float | None = None  # optional clock override for TTL tests

    def _time(self) -> float:
        import time

        return self.now if self.now is not None else time.time()

    def _expire_keys(self) -> None:
        now = self._time()
        expired = [k for k, exp in self._ttls.items() if exp <= now]
        for k in expired:
            self._kv.pop(k, None)
            self._ttls.pop(k, None)

    async def zadd(self, name: str, mapping: dict[str, float]) -> int:
        async with self._lock:
            bucket = self._zsets.setdefault(name, {})
            added = 0
            for member, score in mapping.items():
                if member not in bucket:
                    added += 1
                bucket[member] = float(score)
            return added

    async def zpopmax(self, name: str, count: int = 1) -> list[Any]:
        async with self._lock:
            bucket = self._zsets.get(name, {})
            if not bucket:
                return []
            ordered = sorted(bucket.items(), key=lambda kv: kv[1], reverse=True)
            out: list[Any] = []
            for member, score in ordered[:count]:
                del bucket[member]
                out.append((member, score))
            return out

    async def zrange(self, name: str, start: int, end: int, **kwargs: Any) -> list[Any]:
        async with self._lock:
            bucket = self._zsets.get(name, {})
            ordered = sorted(bucket.items(), key=lambda kv: kv[1])
            members = [m for m, _ in ordered]
            # Redis end is inclusive; support negative indexes like -1.
            n = len(members)
            if n == 0:
                return []
            if start < 0:
                start = n + start
            if end < 0:
                end = n + end
            start = max(0, start)
            end = min(n - 1, end)
            if start > end:
                return []
            return members[start : end + 1]

    async def zcard(self, name: str) -> int:
        async with self._lock:
            return len(self._zsets.get(name, {}))

    async def zrem(self, name: str, *values: str) -> int:
        async with self._lock:
            bucket = self._zsets.get(name, {})
            removed = 0
            for v in values:
                if v in bucket:
                    del bucket[v]
                    removed += 1
            return removed

    async def hset(
        self,
        name: str,
        key: str | None = None,
        value: str | None = None,
        mapping: dict[str, str] | None = None,
    ) -> int:
        async with self._lock:
            bucket = self._hashes.setdefault(name, {})
            written = 0
            if mapping:
                for k, v in mapping.items():
                    if k not in bucket:
                        written += 1
                    bucket[k] = str(v)
            elif key is not None and value is not None:
                if key not in bucket:
                    written += 1
                bucket[key] = str(value)
            return written

    async def hget(self, name: str, key: str) -> str | None:
        async with self._lock:
            return self._hashes.get(name, {}).get(key)

    async def hdel(self, name: str, *keys: str) -> int:
        async with self._lock:
            bucket = self._hashes.get(name, {})
            removed = 0
            for k in keys:
                if k in bucket:
                    del bucket[k]
                    removed += 1
            return removed

    async def hgetall(self, name: str) -> dict[str, str]:
        async with self._lock:
            return dict(self._hashes.get(name, {}))

    async def set(
        self,
        name: str,
        value: str,
        *,
        nx: bool = False,
        ex: int | None = None,
    ) -> bool | None:
        async with self._lock:
            self._expire_keys()
            if nx and name in self._kv:
                return None
            self._kv[name] = value
            if ex is not None:
                self._ttls[name] = self._time() + float(ex)
            else:
                self._ttls.pop(name, None)
            return True

    async def delete(self, *names: str) -> int:
        async with self._lock:
            removed = 0
            for name in names:
                if name in self._kv:
                    del self._kv[name]
                    self._ttls.pop(name, None)
                    removed += 1
            return removed

    async def get(self, name: str) -> str | None:
        async with self._lock:
            self._expire_keys()
            return self._kv.get(name)
