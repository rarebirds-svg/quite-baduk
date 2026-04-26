"""Process-wide KataGo adapter singleton + game state cache."""
from __future__ import annotations

import asyncio
from typing import Protocol

from app.config import settings
from app.core.katago.adapter import KataGoAdapter
from app.core.katago.analysis import AnalysisResult
from app.core.katago.mock import MockKataGoAdapter
from app.core.katago.strength import StrengthConfig
from app.core.rules.engine import GameState


class _AdapterProto(Protocol):
    async def clear_board(self) -> None: ...
    async def set_boardsize(self, size: int) -> None: ...
    async def set_komi(self, komi: float) -> None: ...
    async def set_profile(
        self,
        profile_or_config: StrengthConfig | str,
        max_visits: int | None = None,
    ) -> None: ...
    async def play(self, color: str, coord: str) -> None: ...
    async def undo(self) -> None: ...
    async def genmove(self, color: str) -> str: ...
    async def final_score(self) -> str: ...
    async def analyze(
        self, *, side: str = "B", max_visits: int = 100
    ) -> AnalysisResult: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    @property
    def is_alive(self) -> bool: ...


_adapter: _AdapterProto | None = None
_locks: dict[int, asyncio.Lock] = {}
_states: dict[int, GameState] = {}
# Which game_id the shared adapter was last seeded for. Lets callers skip a
# full clear_board + replay when we know the adapter is already in sync.
_adapter_owner: int | None = None


def get_adapter() -> _AdapterProto:
    global _adapter
    if _adapter is None:
        _adapter = MockKataGoAdapter() if settings.katago_mock else KataGoAdapter()
    return _adapter


def set_adapter(a: _AdapterProto) -> None:
    """Test hook."""
    global _adapter, _adapter_owner
    _adapter = a
    _adapter_owner = None


def adapter_owner() -> int | None:
    return _adapter_owner


def set_adapter_owner(game_id: int | None) -> None:
    global _adapter_owner
    _adapter_owner = game_id


def game_lock(game_id: int) -> asyncio.Lock:
    if game_id not in _locks:
        _locks[game_id] = asyncio.Lock()
    return _locks[game_id]


def cache_state(game_id: int, state: GameState) -> None:
    _states[game_id] = state


def get_cached_state(game_id: int) -> GameState | None:
    return _states.get(game_id)


def drop_state(game_id: int) -> None:
    _states.pop(game_id, None)
