"""In-memory sliding-window rate limiter."""
from __future__ import annotations

import asyncio
import os
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
        # e2e 테스트 환경에선 9개 스펙이 동일 IP로 다수 세션을 생성한다 —
        # 이때만 BADUK_E2E_RATE_LIMIT_DISABLED=true를 지정해 전 키 우회.
        # prod와 dev에선 미지정이므로 정상 동작.
        if os.environ.get("BADUK_E2E_RATE_LIMIT_DISABLED", "").lower() in ("1", "true", "yes"):
            return True
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
