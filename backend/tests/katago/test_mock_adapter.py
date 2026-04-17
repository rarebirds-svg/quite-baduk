import pytest

from app.core.katago.mock import MockKataGoAdapter
from app.core.katago.strength import rank_to_config
from app.core.rules.board import BLACK, EMPTY, WHITE


@pytest.mark.asyncio
async def test_start_stop():
    adapter = MockKataGoAdapter()
    assert not adapter.is_alive
    await adapter.start()
    assert adapter.is_alive
    await adapter.stop()
    assert not adapter.is_alive


@pytest.mark.asyncio
async def test_play_updates_board():
    adapter = MockKataGoAdapter()
    await adapter.start()
    await adapter.play("B", "Q16")
    # Q16 is (15, 3)
    assert adapter.board.get(15, 3) == BLACK


@pytest.mark.asyncio
async def test_genmove_picks_top_left():
    adapter = MockKataGoAdapter()
    await adapter.start()
    move = await adapter.genmove("B")
    assert move == "A19"  # top-left corner
    assert adapter.board.get(0, 0) == BLACK


@pytest.mark.asyncio
async def test_genmove_sequential():
    adapter = MockKataGoAdapter()
    await adapter.start()
    m1 = await adapter.genmove("B")
    m2 = await adapter.genmove("W")
    assert m1 != m2


@pytest.mark.asyncio
async def test_clear_board_resets():
    adapter = MockKataGoAdapter()
    await adapter.start()
    await adapter.play("B", "Q16")
    await adapter.clear_board()
    assert adapter.board.is_empty(15, 3)
    assert adapter.move_history == []


@pytest.mark.asyncio
async def test_undo():
    adapter = MockKataGoAdapter()
    await adapter.start()
    await adapter.play("B", "Q16")
    await adapter.undo()
    assert adapter.board.is_empty(15, 3)
    assert adapter.move_history == []


@pytest.mark.asyncio
async def test_set_komi_and_profile():
    adapter = MockKataGoAdapter()
    await adapter.start()
    await adapter.set_komi(0.5)
    assert adapter.komi == 0.5
    cfg = rank_to_config("5k")
    await adapter.set_profile(cfg)
    assert adapter.profile == ("rank_5k", 8)


@pytest.mark.asyncio
async def test_analyze_returns_hints():
    adapter = MockKataGoAdapter()
    await adapter.start()
    r = await adapter.analyze(max_visits=100)
    assert len(r.top_moves) == 3
    assert len(r.ownership) == 361


@pytest.mark.asyncio
async def test_final_score():
    adapter = MockKataGoAdapter()
    await adapter.start()
    s = await adapter.final_score()
    assert s.startswith("B+") or s.startswith("W+")
