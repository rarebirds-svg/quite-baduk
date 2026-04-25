"""Regression tests for the undo flow. The bug being prevented:

The ``moves`` table has ``UNIQUE(game_id, move_number)``. An older undo
implementation flipped ``is_undone`` to ``True`` and decremented
``game.move_count``, but left the row in place. The next ``place_move``
then tried to INSERT a new row with the same ``move_number`` and hit a
``sqlite3.IntegrityError``, bricking the game. These tests exercise the
full play → undo → play loop at the service layer to make sure the fix
keeps working.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.models import Move, Session
from app.services.game_service import create_game, place_move, undo_move


@pytest.mark.asyncio
async def test_play_after_undo_does_not_collide_on_move_number(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = Session(token="u-t", nickname="undoer", nickname_key="undoer")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    await place_move(db_session, game=game, session=s, coord="E5")
    await place_move(db_session, game=game, session=s, coord="C3")
    assert game.move_count == 4

    await undo_move(db_session, game=game, session=s, steps=2)
    assert game.undo_count == 1
    assert game.move_count == 2

    # The regression: before the fix this raised IntegrityError because
    # move_number=3 still existed in the table as a ghost (is_undone=True).
    result = await place_move(db_session, game=game, session=s, coord="F4")
    assert result.ai_move is not None
    assert game.move_count == 4


@pytest.mark.asyncio
async def test_play_after_undo_heals_legacy_undone_rows(
    db_session: AsyncSession,
) -> None:
    """Games created before the fix have is_undone=True ghost rows that
    still occupy move_number slots. `place_move` should self-heal so users
    can continue those games instead of being permanently stuck."""
    set_adapter(MockKataGoAdapter())
    s = Session(token="u-legacy", nickname="legacy", nickname_key="legacy")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    # Simulate the legacy broken state directly: two undone rows that occupy
    # move_number 1 and 2, matching what the old undo code produced.
    db_session.add(
        Move(
            game_id=game.id,
            move_number=1,
            color="B",
            coord="E5",
            captures=0,
            is_undone=True,
        )
    )
    db_session.add(
        Move(
            game_id=game.id,
            move_number=2,
            color="W",
            coord="A9",
            captures=0,
            is_undone=True,
        )
    )
    game.undo_count = 1
    await db_session.commit()

    # Should succeed even though move_number=1 already exists (is_undone=True).
    await place_move(db_session, game=game, session=s, coord="F4")
    assert game.move_count == 2
    # No stale undone rows remain.
    res = await db_session.execute(
        select(Move).where(Move.game_id == game.id, Move.is_undone.is_(True))
    )
    assert res.scalars().first() is None


@pytest.mark.asyncio
async def test_undo_multiple_times(db_session: AsyncSession) -> None:
    """Repeated undo → play cycles must not leave ghost rows behind."""
    set_adapter(MockKataGoAdapter())
    s = Session(token="u-multi", nickname="multi", nickname_key="multi")
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)

    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    for coord in ("E5", "C3", "G7"):
        await place_move(db_session, game=game, session=s, coord=coord)
        await undo_move(db_session, game=game, session=s, steps=2)
    # After 3 undo cycles, the board should be empty again and the moves
    # table should have 0 rows (no ghosts).
    assert game.move_count == 0
    assert game.undo_count == 3
    res = await db_session.execute(select(Move).where(Move.game_id == game.id))
    assert res.scalars().all() == []
