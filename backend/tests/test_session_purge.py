"""Tests for the session-idle purge path."""
from __future__ import annotations

import datetime as dt

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Game, Session
from app.session_purge import purge_expired_sessions_once
from app.session_registry import registry


@pytest_asyncio.fixture
async def wired_db(db_engine):
    """Wire the module-level AsyncSessionLocal to the test engine so that
    purge_expired_sessions_once can open its own connection."""
    from app import db as _db_mod
    original = _db_mod.AsyncSessionLocal
    _db_mod.AsyncSessionLocal = async_sessionmaker(
        db_engine, expire_on_commit=False, class_=AsyncSession
    )
    yield
    _db_mod.AsyncSessionLocal = original


@pytest.mark.asyncio
async def test_purge_deletes_idle_sessions_and_cascades_games(db_session, wired_db):
    # Fresh (not expired)
    fresh = Session(token="t-fresh", nickname="alice", nickname_key="alice")
    db_session.add(fresh)
    # Stale
    stale = Session(token="t-stale", nickname="bob", nickname_key="bob",
                    last_seen_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=7200))
    db_session.add(stale)
    await db_session.commit()
    await db_session.refresh(fresh)
    await db_session.refresh(stale)

    # Register nicknames in the in-memory registry so we can verify release.
    await registry.claim("alice", fresh.id)
    await registry.claim("bob", stale.id)

    # Game owned by stale session — must be cascade-deleted.
    g = Game(session_id=stale.id, ai_rank="5k", board_size=19,
             handicap=0, komi=6.5, user_color="black", status="active")
    db_session.add(g)
    await db_session.commit()

    n = await purge_expired_sessions_once(ttl_sec=3600)
    assert n == 1

    # Fresh survives; stale is gone.
    res = await db_session.execute(select(Session.token))
    remaining = {r[0] for r in res.all()}
    assert remaining == {"t-fresh"}

    # Game cascade-deleted
    res2 = await db_session.execute(select(Game))
    assert res2.scalars().all() == []

    # Registry released bob but kept alice
    assert await registry.is_taken("alice") is True
    assert await registry.is_taken("bob") is False

    # Cleanup registry so other tests start clean
    await registry.release("alice")


@pytest.mark.asyncio
async def test_purge_noop_when_nothing_stale(db_session, wired_db):
    fresh = Session(token="t-only", nickname="carol", nickname_key="carol")
    db_session.add(fresh)
    await db_session.commit()
    n = await purge_expired_sessions_once(ttl_sec=3600)
    assert n == 0
