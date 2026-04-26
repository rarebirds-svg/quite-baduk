"""In-memory registry of currently-claimed nickname keys.

Single-process, asyncio-protected. Serves as the primary uniqueness
guard for concurrent sessions; the DB ``sessions.nickname_key`` UNIQUE
constraint is a secondary defense for race windows and for any
eventual multi-process deployment.
"""
from __future__ import annotations

import asyncio


class NicknameRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_key: dict[str, int] = {}

    async def claim(self, nickname_key: str, session_id: int) -> bool:
        """Reserve ``nickname_key`` for ``session_id``. Returns False if
        another session already owns it."""
        async with self._lock:
            if nickname_key in self._by_key:
                return False
            self._by_key[nickname_key] = session_id
            return True

    async def release(self, nickname_key: str) -> None:
        """Drop the reservation. No-op if unknown."""
        async with self._lock:
            self._by_key.pop(nickname_key, None)

    async def is_taken(self, nickname_key: str) -> bool:
        async with self._lock:
            return nickname_key in self._by_key


registry = NicknameRegistry()
