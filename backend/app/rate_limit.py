"""In-memory sliding-window rate limiter."""
from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    window_sec: float
    max_hits: int
    hits: deque[float] = field(default_factory=deque)


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, max_hits: int, window_sec: float) -> bool:
        """Return True if allowed; False if rate-limited."""
        now = time.monotonic()
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or bucket.max_hits != max_hits or bucket.window_sec != window_sec:
                bucket = _Bucket(window_sec=window_sec, max_hits=max_hits)
                self._buckets[key] = bucket
            # drop old hits
            while bucket.hits and bucket.hits[0] < now - window_sec:
                bucket.hits.popleft()
            if len(bucket.hits) >= max_hits:
                return False
            bucket.hits.append(now)
            return True


rate_limiter = RateLimiter()
