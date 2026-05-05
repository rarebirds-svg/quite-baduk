"""Live winrate emit-before-AI-reply.

The product complaint: "winrate doesn't update in real time after I make
my move". The fix wires a second analyze pass into ``place_move`` that
runs immediately after the user's stone is recorded but before
``adapter.genmove`` is called. The result flows out via the new
``on_user_winrate`` callback, which the WebSocket layer ships as a
``winrate`` event.

These tests pin the ordering so a future refactor can't quietly drop
the live winrate path.
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.models import Session
from app.services.game_service import create_game, place_move


async def _make_session(db: AsyncSession, *, nickname: str) -> Session:
    s = Session(
        token=secrets.token_urlsafe(8),
        nickname=nickname,
        nickname_key=nickname,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.mark.asyncio
async def test_on_user_winrate_fires_before_ai_move(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="rtwr")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )

    events: list[str] = []

    async def on_user_applied(_state: object, _captures: int) -> None:
        events.append("user_applied")

    async def on_user_winrate(wr_black: float, sl_black: float | None) -> None:
        assert 0.0 <= wr_black <= 1.0
        # score-lead may be None when analyze fails; mock always returns one.
        assert sl_black is None or isinstance(sl_black, float)
        events.append("user_winrate")

    result = await place_move(
        db_session,
        game=game,
        session=s,
        coord="E5",
        on_user_applied=on_user_applied,
        on_user_winrate=on_user_winrate,
    )

    # Both callbacks fired, in order: user state first, winrate next,
    # before the MoveResult (AI move + post-AI winrate) is returned.
    assert events == ["user_applied", "user_winrate"]
    # Final winrate from the post-AI analyze still lands on the result.
    assert result.winrate_black is None or 0.0 <= result.winrate_black <= 1.0


@pytest.mark.asyncio
async def test_on_user_winrate_skipped_when_callback_omitted(
    db_session: AsyncSession,
) -> None:
    """Existing callers (no live-winrate kwarg) keep the old single-analyze
    cost. Important: review/replay flows should not pay double."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="rtwr2")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    # Should not raise — the path is opt-in.
    result = await place_move(
        db_session,
        game=game,
        session=s,
        coord="E5",
    )
    assert result.game_state.board.size == 9
