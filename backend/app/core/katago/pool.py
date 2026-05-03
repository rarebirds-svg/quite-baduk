"""Pool of :class:`KataGoAdapter` subprocesses for concurrent game serving.

A single ``KataGoAdapter`` serializes every GTP command through one
``asyncio.Lock``. With one shared adapter, two games running in parallel
block each other on every move. We instead keep ``size`` adapter
instances and pin each game to one of them: the assignment is sticky
per ``game_id``, and the per-game ``asyncio.Lock`` in
:mod:`app.engine_pool` continues to provide turn ordering on the
adapter-shared boardsize/komi state.

When a game first arrives we pick the least-loaded adapter (fewest
already-pinned games). Re-balancing across pool resizes is not handled —
the pool size is fixed at startup.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable

from app.core.katago.adapter import KataGoAdapter


class KataGoPool:
    def __init__(
        self,
        size: int = 4,
        *,
        adapter_factory: Callable[[], KataGoAdapter] | None = None,
    ) -> None:
        if size < 1:
            raise ValueError("KataGoPool size must be >= 1")
        factory = adapter_factory or KataGoAdapter
        self._adapters: list[KataGoAdapter] = [factory() for _ in range(size)]
        self._game_assignment: dict[int, int] = {}
        self._lock = asyncio.Lock()

    @property
    def size(self) -> int:
        return len(self._adapters)

    async def adapter_for(self, game_id: int) -> KataGoAdapter:
        """Return the pinned adapter for ``game_id``. New games are
        assigned to the adapter currently serving the fewest games."""
        async with self._lock:
            idx = self._game_assignment.get(game_id)
            if idx is None:
                counts = [0] * len(self._adapters)
                for assigned_idx in self._game_assignment.values():
                    counts[assigned_idx] += 1
                idx = counts.index(min(counts))
                self._game_assignment[game_id] = idx
            return self._adapters[idx]

    async def release(self, game_id: int) -> None:
        """Drop a game's assignment so the slot can be reused."""
        async with self._lock:
            self._game_assignment.pop(game_id, None)

    async def start_all(self) -> None:
        await asyncio.gather(*(a.start() for a in self._adapters))

    async def stop_all(self) -> None:
        await asyncio.gather(
            *(a.stop() for a in self._adapters),
            return_exceptions=True,
        )
