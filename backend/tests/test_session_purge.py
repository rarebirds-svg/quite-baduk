"""Tests for the session-idle purge path."""
from __future__ import annotations

import datetime as dt

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.models import Game, Session
from app.session_purge import purge_expired_sessions_once


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
async def test_purge_deletes_idle_sessions_preserves_game_history(db_session, wired_db):
    """Idle sessions are purged but their games are preserved (session_id
    detaches via SET NULL) so the admin console's audit trail persists."""
    ttl = settings.session_ttl_sec  # 7일 슬라이딩
    # Fresh — 6일 전 방문이면 아직 살아 있어야 한다.
    fresh = Session(token="t-fresh", nickname="alice", nickname_key="alice",  # noqa: S106 (test session token, not a password)
                    last_seen_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=6))
    db_session.add(fresh)
    # Stale — 8일 전 방문.
    stale = Session(token="t-stale", nickname="bob", nickname_key="bob",  # noqa: S106 (test session token, not a password)
                    last_seen_at=dt.datetime.now(dt.UTC) - dt.timedelta(days=8))
    db_session.add(stale)
    await db_session.commit()
    await db_session.refresh(fresh)
    await db_session.refresh(stale)

    # Game owned by stale session — must survive the purge via SET NULL.
    g = Game(session_id=stale.id, user_nickname="bob", ai_rank="5k",
             board_size=19, handicap=0, komi=6.5, user_color="black",
             status="active")
    db_session.add(g)
    await db_session.commit()

    n = await purge_expired_sessions_once(ttl_sec=ttl)
    assert n == 1

    # Fresh survives; stale is gone.
    res = await db_session.execute(select(Session.token))
    remaining = {r[0] for r in res.all()}
    assert remaining == {"t-fresh"}

    # Game persists with session_id detached; nickname snapshot intact.
    # expire_all() so the test's Session re-fetches from the DB (the purge
    # runs on a different AsyncSession wired via _db_mod.AsyncSessionLocal).
    db_session.expire_all()
    res2 = await db_session.execute(select(Game))
    games = res2.scalars().all()
    assert len(games) == 1
    assert games[0].session_id is None
    assert games[0].user_nickname == "bob"


@pytest.mark.asyncio
async def test_purge_noop_when_nothing_stale(db_session, wired_db):
    fresh = Session(token="t-only", nickname="carol", nickname_key="carol")  # noqa: S106 (test session token, not a password)
    db_session.add(fresh)
    await db_session.commit()
    n = await purge_expired_sessions_once(ttl_sec=settings.session_ttl_sec)
    assert n == 0
