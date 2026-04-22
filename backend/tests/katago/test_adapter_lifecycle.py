"""Contract: KataGoAdapter.start() must never leave the subprocess in a
state that diverges from the rules engine — after start() the subprocess
is either already running with the same state, or freshly spawned and
replayed from the cached _ReplayState.

Regression guard for AI_ILLEGAL_MOVE caused by _sync_adapter's fast path
calling start() on a dead subprocess, which used to spawn a fresh blank
KataGo without replaying the move history.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.katago.adapter import KataGoAdapter


@pytest.mark.asyncio
async def test_start_replays_state_when_subprocess_was_never_started() -> None:
    """First start on a fresh adapter must replay (noop replay for empty state)
    so later reuses don't rely on GTP defaults."""
    adapter = KataGoAdapter()
    assert adapter._proc is None

    async def spawn_side_effect() -> None:
        adapter._proc = Mock(returncode=None)  # type: ignore[assignment]

    with patch.object(adapter, "_spawn", new=AsyncMock(side_effect=spawn_side_effect)) as mock_spawn, \
         patch.object(adapter, "_replay_state", new=AsyncMock()) as mock_replay:
        await adapter.start()

    mock_spawn.assert_awaited_once()
    mock_replay.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_replays_cached_history_when_subprocess_died() -> None:
    """If the subprocess ended and start() is called again, it must respawn
    AND replay the accumulated _ReplayState so callers don't see a blank
    board."""
    adapter = KataGoAdapter()
    adapter._replay.plays = [("B", "Q16"), ("W", "D17"), ("B", "D4")]
    adapter._replay.boardsize = 19
    # Simulate a terminated subprocess: proc is set but returncode is non-None.
    adapter._proc = Mock(returncode=0)  # type: ignore[assignment]
    assert not adapter.is_alive

    async def spawn_side_effect() -> None:
        adapter._proc = Mock(returncode=None)  # type: ignore[assignment]

    with patch.object(adapter, "_spawn", new=AsyncMock(side_effect=spawn_side_effect)) as mock_spawn, \
         patch.object(adapter, "_replay_state", new=AsyncMock()) as mock_replay:
        await adapter.start()

    mock_spawn.assert_awaited_once()
    mock_replay.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_is_noop_when_subprocess_already_alive() -> None:
    """If the subprocess is running, start() must not spawn or replay."""
    adapter = KataGoAdapter()
    adapter._proc = Mock(returncode=None)  # type: ignore[assignment]
    assert adapter.is_alive

    with patch.object(adapter, "_spawn", new=AsyncMock()) as mock_spawn, \
         patch.object(adapter, "_replay_state", new=AsyncMock()) as mock_replay:
        await adapter.start()

    mock_spawn.assert_not_awaited()
    mock_replay.assert_not_awaited()
