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


@pytest.mark.asyncio
async def test_mock_boardsize_resets_and_uses_size_for_genmove():
    a = MockKataGoAdapter()
    await a.start()
    await a.set_boardsize(9)
    assert a.board.size == 9
    # genmove should pick first empty on 9x9 (A9 = top-left), not out-of-range for 9x9
    m = await a.genmove("B")
    assert m == "A9"


@pytest.mark.asyncio
async def test_mock_switches_size_between_games():
    a = MockKataGoAdapter()
    await a.start()
    await a.set_boardsize(19)
    await a.set_boardsize(13)
    assert a.board.size == 13
    m = await a.genmove("B")
    assert m == "A13"


@pytest.mark.asyncio
async def test_mock_genmove_stays_legal_against_rules_engine():
    """Mock must never return a move the rules engine would reject.

    Regression for the 9x9 `AI_ILLEGAL_MOVE` symptom: the old mock picked
    the first empty cell ignoring captures/suicide/ko, so the service layer
    tripped over the engine's validation mid-game.
    """
    from app.core.rules.board import Board
    from app.core.rules.engine import GameState, Move, play

    adapter = MockKataGoAdapter()
    await adapter.start()
    await adapter.set_boardsize(9)

    state = GameState(board=Board(9))
    # Alternate user/AI for a full game. Should never raise, and either side
    # may pass out when no legal move remains.
    for i in range(120):
        color = BLACK if i % 2 == 0 else WHITE
        coord = await adapter.genmove(color)
        if coord.lower() in ("pass", "resign"):
            state = play(state, Move(color=color, coord=coord.lower()))
        else:
            state = play(state, Move(color=color, coord=coord))
        # Adapter board and rules board must agree after every move.
        for y in range(9):
            for x in range(9):
                assert adapter.board.get(x, y) == state.board.get(x, y), (
                    f"divergence at ({x},{y}) after move {i}: "
                    f"adapter={adapter.board.get(x, y)!r}, rules={state.board.get(x, y)!r}"
                )
