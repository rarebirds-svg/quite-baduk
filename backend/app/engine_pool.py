"""Process-wide KataGo + game-state singletons.

* ``_pool`` is a :class:`KataGoPool` of subprocess-backed adapters.
* ``_game_locks`` serializes per-game mutations on top of the pool.
* ``_states`` caches the rules-engine state per game so we don't replay
  SGF from the DB on every move.

Tests can override the engine layer with :func:`set_adapter` (single
mock that all games share) or :func:`set_pool` (full pool replacement).
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import cast

from app.core.katago.adapter import KataGoAdapter
from app.core.katago.pool import KataGoPool
from app.core.rules.engine import GameState

_pool: KataGoPool | None = None
_game_locks: dict[int, asyncio.Lock] = {}
_states: dict[int, GameState] = {}
# Tracks which game id currently owns each adapter slot's GTP state
# (boardsize/komi/move history). Multiple games may share the same slot;
# only the most recent caller to fully reseed the slot is the "owner",
# and other games on that slot must reseed before issuing GTP commands.
# Keyed by slot index -> game_id.
_adapter_owners: dict[int, int] = {}


def get_pool() -> KataGoPool:
    global _pool
    if _pool is None:
        from app.config import settings
        from app.core.katago.mock import MockKataGoAdapter

        # MockKataGoAdapter is duck-typed against the same protocol as
        # KataGoAdapter (start/stop/genmove/...) but doesn't subclass it;
        # cast for the pool's annotated factory signature.
        factory: Callable[[], KataGoAdapter] = cast(
            Callable[[], KataGoAdapter],
            MockKataGoAdapter if settings.katago_mock else KataGoAdapter,
        )
        _pool = KataGoPool(size=settings.katago_pool_size, adapter_factory=factory)
    return _pool


def set_pool(pool: KataGoPool) -> None:
    """Test-only: replace the pool."""
    global _pool
    _pool = pool
    _adapter_owners.clear()


def set_adapter(adapter: KataGoAdapter) -> None:
    """Backwards-compatible single-adapter override used by existing
    tests. Builds a 1-slot pool around the supplied adapter so every
    game shares it."""
    pool = KataGoPool(size=1, adapter_factory=lambda: adapter)
    pool._adapters[0] = adapter
    set_pool(pool)


async def get_adapter(game_id: int | None = None) -> KataGoAdapter:
    """Return the adapter pinned to ``game_id``. When ``game_id`` is
    ``None``, returns the first adapter — used by warm-up paths that
    don't yet have a game id."""
    pool = get_pool()
    if game_id is None:
        return pool._adapters[0]
    return await pool.adapter_for(game_id)


def _slot_for(game_id: int) -> int | None:
    """Best-effort lookup of which pool slot is pinned to ``game_id``.
    Returns ``None`` if the game has not yet been assigned (pre-first
    ``adapter_for`` call) or if there is no pool yet."""
    if _pool is None:
        return None
    return _pool._game_assignment.get(game_id)


def set_adapter_owner(game_id: int | None) -> None:
    """Mark ``game_id`` as the current owner of its pinned slot's GTP
    state. Passing ``None`` clears the entire ownership table — callers
    use this after a multi-step undo to force a fresh reseed on the
    next play across all games."""
    if game_id is None:
        _adapter_owners.clear()
        return
    slot = _slot_for(game_id)
    if slot is None:
        # No assignment yet — nothing to record. The reseed path will
        # set the owner once it acquires the slot.
        return
    _adapter_owners[slot] = game_id


def adapter_owner(game_id: int | None = None) -> int | None:
    """Return the current owner of the slot pinned to ``game_id``.

    Callers compare ``adapter_owner(game.id) == game.id`` to take the
    fast path that skips a clear_board + replay sequence. When called
    with no argument (legacy single-adapter API), returns slot 0's owner."""
    if game_id is None:
        return _adapter_owners.get(0)
    slot = _slot_for(game_id)
    if slot is None:
        return None
    return _adapter_owners.get(slot)


def is_adapter_owner(game_id: int) -> bool:
    return adapter_owner(game_id) == game_id


async def release_game(game_id: int) -> None:
    """Free the pool slot and per-game state when a game finalizes."""
    pool = get_pool()
    slot = _slot_for(game_id)
    await pool.release(game_id)
    _game_locks.pop(game_id, None)
    _states.pop(game_id, None)
    if slot is not None and _adapter_owners.get(slot) == game_id:
        _adapter_owners.pop(slot, None)


@asynccontextmanager
async def game_lock(game_id: int) -> AsyncIterator[None]:
    lock = _game_locks.setdefault(game_id, asyncio.Lock())
    async with lock:
        yield


def cache_state(game_id: int, state: GameState) -> None:
    _states[game_id] = state


def get_cached_state(game_id: int) -> GameState | None:
    return _states.get(game_id)


def clear_cached_state(game_id: int) -> None:
    _states.pop(game_id, None)


# Backwards-compat alias — older code calls drop_state.
drop_state = clear_cached_state
