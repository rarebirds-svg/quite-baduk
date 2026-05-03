"""Coverage for the validation/error paths in
``app.services.game_service``. These exercise the ``GameError`` raises
that no other suite touches:

- ``INVALID_BOARD_SIZE`` / ``INVALID_HANDICAP`` / ``INVALID_COLOR``
  in :func:`create_game`.
- ``FORBIDDEN`` (cross-session play) and ``GAME_NOT_ACTIVE`` (post-finish
  play) in :func:`place_move`.
- The illegal-move re-raise that translates :class:`IllegalMoveError`
  into a :class:`GameError`.

They also drive the ``user_color="white"`` and ``handicap > 0`` branches
that ``test_undo_flow.py`` doesn't, which together account for the bulk
of the remaining uncovered statements in ``create_game``.
"""
from __future__ import annotations

import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.katago.mock import MockKataGoAdapter
from app.engine_pool import set_adapter
from app.models import Session
from app.services.game_service import (
    GameError,
    create_game,
    place_move,
)


async def _make_session(
    db: AsyncSession, *, nickname: str = "errtester"
) -> Session:
    """Insert a fresh session row. The token is randomly generated so
    each call is unique and ruff's S106/S107 hardcoded-password checks
    don't trip on a literal."""
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
async def test_create_game_rejects_unknown_board_size(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session)
    with pytest.raises(GameError) as exc:
        await create_game(
            db_session,
            session=s,
            ai_rank="5k",
            handicap=0,
            user_color="black",
            board_size=11,
        )
    assert exc.value.code == "INVALID_BOARD_SIZE"


@pytest.mark.asyncio
async def test_create_game_rejects_unknown_handicap(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="hcptester")
    with pytest.raises(GameError) as exc:
        await create_game(
            db_session,
            session=s,
            ai_rank="5k",
            handicap=99,
            user_color="black",
            board_size=19,
        )
    assert exc.value.code == "INVALID_HANDICAP"


@pytest.mark.asyncio
async def test_create_game_rejects_unknown_color(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="colortester")
    with pytest.raises(GameError) as exc:
        await create_game(
            db_session,
            session=s,
            ai_rank="5k",
            handicap=0,
            user_color="green",
            board_size=9,
        )
    assert exc.value.code == "INVALID_COLOR"


@pytest.mark.asyncio
async def test_create_game_white_user_color_assigns_white_to_user(
    db_session: AsyncSession,
) -> None:
    """Drives the ``_user_side``/``_ai_side`` branches that mirror black
    when the user picks white."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="whitetester")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="white",
        board_size=9,
    )
    assert game.user_color == "white"
    assert game.komi == 6.5
    assert game.handicap == 0


@pytest.mark.asyncio
async def test_create_game_with_handicap_places_setup_stones(
    db_session: AsyncSession,
) -> None:
    """Drives the handicap path of :func:`create_game` — adapter.play
    for each setup stone + ``state.to_move = WHITE``."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="hcpset")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=4,
        user_color="black",  # ignored when handicap > 0
        board_size=19,
    )
    # Komi flips to 0.5 with handicap; user_color stays black.
    assert game.komi == 0.5
    assert game.handicap == 4
    assert game.user_color == "black"


@pytest.mark.asyncio
async def test_place_move_rejects_cross_session_access(
    db_session: AsyncSession,
) -> None:
    """A move on game A from session B must raise FORBIDDEN."""
    set_adapter(MockKataGoAdapter())
    owner = await _make_session(db_session, nickname="owner")
    intruder = await _make_session(db_session, nickname="intruder")
    game = await create_game(
        db_session,
        session=owner,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    with pytest.raises(GameError) as exc:
        await place_move(db_session, game=game, session=intruder, coord="E5")
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_place_move_rejects_finished_game(
    db_session: AsyncSession,
) -> None:
    """Once a game is no longer ``active`` (resigned / finished) further
    moves must raise GAME_NOT_ACTIVE."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="finished")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    game.status = "resigned"
    await db_session.commit()
    with pytest.raises(GameError) as exc:
        await place_move(db_session, game=game, session=s, coord="E5")
    assert exc.value.code == "GAME_NOT_ACTIVE"


@pytest.mark.asyncio
async def test_place_move_translates_illegal_to_game_error(
    db_session: AsyncSession,
) -> None:
    """Playing on top of an existing stone surfaces as a GameError, not
    a raw IllegalMoveError."""
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="illegal")
    game = await create_game(
        db_session,
        session=s,
        ai_rank="5k",
        handicap=0,
        user_color="black",
        board_size=9,
    )
    # First move is legal; user plays D4.
    await place_move(db_session, game=game, session=s, coord="D4")
    # Now try to play on the same point — must be rejected as a GameError.
    with pytest.raises(GameError):
        await place_move(db_session, game=game, session=s, coord="D4")


@pytest.mark.asyncio
async def test_create_game_rejects_unsupported_rank(
    db_session: AsyncSession,
) -> None:
    set_adapter(MockKataGoAdapter())
    s = await _make_session(db_session, nickname="rankt")
    with pytest.raises(GameError) as exc:
        await create_game(
            db_session,
            session=s,
            ai_rank="7d",
            handicap=0,
            user_color="black",
            board_size=9,
        )
    assert exc.value.code == "INVALID_AI_RANK"
