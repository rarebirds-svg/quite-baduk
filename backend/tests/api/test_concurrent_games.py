"""Integration test: two simultaneous games on a 4-worker mock pool
must land on different adapter instances and not interfere with each
other's GameState cache."""
from __future__ import annotations

import asyncio
import secrets

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.katago.mock import MockKataGoAdapter
from app.core.katago.pool import KataGoPool
from app.engine_pool import get_pool, set_pool
from app.models import Session
from app.services.game_service import create_game, place_move


def _mock_pool(size: int = 4) -> KataGoPool:
    return KataGoPool(size=size, adapter_factory=MockKataGoAdapter)


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
async def test_two_games_use_different_adapters(
    db_session: AsyncSession,
) -> None:
    """First two games on a fresh 4-slot pool must occupy distinct
    adapters via least-loaded picking."""
    set_pool(_mock_pool(size=4))
    pool = get_pool()
    await pool.start_all()

    s1 = await _make_session(db_session, nickname="p1")
    s2 = await _make_session(db_session, nickname="p2")

    g1 = await create_game(
        db_session, session=s1, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )
    g2 = await create_game(
        db_session, session=s2, ai_rank="5k", handicap=0,
        user_color="black", board_size=9,
    )

    a1 = await pool.adapter_for(g1.id)
    a2 = await pool.adapter_for(g2.id)
    assert a1 is not a2, (
        "Pool gave the same adapter to two distinct games — pool is "
        "not balancing."
    )


@pytest.mark.asyncio
async def test_concurrent_moves_do_not_corrupt_state(
    db_engine,
) -> None:
    """Two games make moves at the same time; each must end with the
    correct piece on the correct intersection in its own state cache.

    Each game is driven through its own ``AsyncSession`` — a single
    SQLAlchemy session can't handle two concurrent commits, but the
    pool/state caches we're exercising are process-wide, so isolated
    DB sessions still cover the same race surface."""
    set_pool(_mock_pool(size=4))
    await get_pool().start_all()

    factory = async_sessionmaker(
        db_engine, expire_on_commit=False, class_=AsyncSession
    )

    async with factory() as setup_db:
        s1 = await _make_session(setup_db, nickname="cm1")
        s2 = await _make_session(setup_db, nickname="cm2")
        g1 = await create_game(
            setup_db, session=s1, ai_rank="5k", handicap=0,
            user_color="black", board_size=9,
        )
        g2 = await create_game(
            setup_db, session=s2, ai_rank="5k", handicap=0,
            user_color="black", board_size=9,
        )

    async def _move(game, sess, coord):  # type: ignore[no-untyped-def]
        async with factory() as db:
            return await place_move(db, game=game, session=sess, coord=coord)

    r1, r2 = await asyncio.gather(
        _move(g1, s1, "D4"),
        _move(g2, s2, "E5"),
    )
    assert r1.game_state.board.size == 9
    assert r2.game_state.board.size == 9
    # Each game's user move must persist in the right state.
    # D4 in 9x9: x=3, y=5 (D=col index 3, 4 from bottom = row index 5)
    # E5 in 9x9: x=4, y=4
    assert r1.game_state.board.get(3, 5) == "B"
    assert r2.game_state.board.get(4, 4) == "B"
