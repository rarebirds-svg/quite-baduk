"""When the user picks White (and there is no handicap), the AI plays Black
and must open. Without this the WS handshake just ships `to_move=BLACK` and
the user stares at an empty board indefinitely.

The handicap path doesn't have this issue because handicap > 0 forces
`user_color = "black"` (per `create_game`).
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.models import Move as MoveRow
from app.models import Session
from app.services.game_service import create_game


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
async def test_user_white_creates_game_with_ai_first_move_already_played(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="white1")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="white",
        board_size=9,
    )

    # AI's opening must be persisted before the WS connection sees the game.
    assert game.move_count == 1, (
        "AI (Black) must have played its first move before the user's WS "
        "connection — otherwise the user sees an empty board with `to_move=B` "
        "and waits forever."
    )

    moves = (
        await db_session.execute(
            select(MoveRow).where(MoveRow.game_id == game.id).order_by(
                MoveRow.move_number.asc()
            )
        )
    ).scalars().all()
    assert len(moves) == 1
    assert moves[0].color == "B"
    assert moves[0].coord is not None
    assert moves[0].coord.lower() not in ("pass", "resign")


@pytest.mark.asyncio
async def test_user_black_creates_game_with_no_moves_yet(
    db_session: AsyncSession,
) -> None:
    """Existing flow: user (Black) opens. game.move_count must stay 0."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="black1")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )

    assert game.move_count == 0
    moves = (
        await db_session.execute(
            select(MoveRow).where(MoveRow.game_id == game.id)
        )
    ).scalars().all()
    assert moves == []


@pytest.mark.asyncio
async def test_handicap_creates_game_with_no_moves_yet(
    db_session: AsyncSession,
) -> None:
    """Handicap path forces user_color=black (handicap stones for user) so
    the AI doesn't open — same as the user-black path. Don't regress this."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="hcap1")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=3,
        user_color="white",  # ignored — create_game flips to black for handicap
        board_size=9,
    )

    assert game.user_color == "black"
    assert game.move_count == 0
