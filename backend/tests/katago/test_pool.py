"""Unit tests for KataGoPool. We inject MockKataGoAdapter via the
``adapter_factory`` parameter so no real KataGo subprocess is spawned."""
from __future__ import annotations

import pytest

from app.core.katago.mock import MockKataGoAdapter
from app.core.katago.pool import KataGoPool


def _mock_pool(size: int = 4) -> KataGoPool:
    return KataGoPool(size=size, adapter_factory=MockKataGoAdapter)


def test_pool_size_matches_constructor_argument() -> None:
    pool = _mock_pool(size=4)
    assert pool.size == 4


def test_pool_rejects_zero_or_negative_size() -> None:
    with pytest.raises(ValueError):
        KataGoPool(size=0, adapter_factory=MockKataGoAdapter)
    with pytest.raises(ValueError):
        KataGoPool(size=-1, adapter_factory=MockKataGoAdapter)


@pytest.mark.asyncio
async def test_adapter_for_returns_same_adapter_for_same_game() -> None:
    pool = _mock_pool(size=4)
    a1 = await pool.adapter_for(game_id=42)
    a2 = await pool.adapter_for(game_id=42)
    assert a1 is a2


@pytest.mark.asyncio
async def test_adapter_for_balances_across_workers() -> None:
    """First 4 distinct games should land on 4 distinct adapters
    (least-loaded picks idx 0, 1, 2, 3 in turn since each starts empty)."""
    pool = _mock_pool(size=4)
    seen = set()
    for gid in (1, 2, 3, 4):
        a = await pool.adapter_for(gid)
        seen.add(id(a))
    assert len(seen) == 4


@pytest.mark.asyncio
async def test_adapter_for_5th_game_reuses_least_loaded() -> None:
    pool = _mock_pool(size=4)
    for gid in (1, 2, 3, 4):
        await pool.adapter_for(gid)
    a5 = await pool.adapter_for(5)
    assert any(a5 is adapter for adapter in pool._adapters)


@pytest.mark.asyncio
async def test_release_clears_assignment() -> None:
    pool = _mock_pool(size=2)
    await pool.adapter_for(game_id=1)
    await pool.release(game_id=1)
    a1_after = await pool.adapter_for(game_id=1)
    assert pool._game_assignment[1] in (0, 1)
    assert a1_after in pool._adapters


@pytest.mark.asyncio
async def test_start_all_starts_every_adapter() -> None:
    pool = _mock_pool(size=3)
    await pool.start_all()
    for a in pool._adapters:
        assert a.started is True


@pytest.mark.asyncio
async def test_stop_all_swallows_per_adapter_errors() -> None:
    """One adapter blowing up on stop must not abort the others."""
    pool = _mock_pool(size=3)
    await pool.start_all()

    async def explode() -> None:
        raise RuntimeError("boom")

    pool._adapters[1].stop = explode  # type: ignore[method-assign]
    await pool.stop_all()
    assert pool._adapters[0].started is False
    assert pool._adapters[2].started is False
