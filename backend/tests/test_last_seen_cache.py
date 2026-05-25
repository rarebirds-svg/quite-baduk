# last_seen_cache 모듈 단위 테스트 — stamp / flush_due / lifecycle.
from __future__ import annotations

import datetime as dt

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import last_seen_cache as lsc
from app.models import Session


@pytest_asyncio.fixture(autouse=True)
async def _reset_cache():
    await lsc.stop_flusher()
    lsc._cache.clear()
    yield
    await lsc.stop_flusher()
    lsc._cache.clear()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def seeded_session(session_factory):
    base = dt.datetime(2026, 5, 25, 11, 0, 0, tzinfo=dt.UTC)
    async with session_factory() as s:
        row = Session(
            token="qa-token-1",  # noqa: S106 (test session token, not a password)
            nickname="qa",
            nickname_key="qa",
            created_at=base,
            last_seen_at=base,
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
        return row.id


async def _db_last_seen(factory, sid: int) -> dt.datetime | None:
    async with factory() as s:
        res = await s.execute(select(Session.last_seen_at).where(Session.id == sid))
        return res.scalar_one_or_none()


def test_stamp_sets_cache_entry():
    now = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    lsc.stamp(42, when=now)
    assert 42 in lsc._cache
    seen, flushed = lsc._cache[42]
    assert seen == now
    assert flushed == lsc._EPOCH


def test_stamp_overwrites_seen_keeps_flushed():
    t1 = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t2 = dt.datetime(2026, 5, 25, 12, 0, 5, tzinfo=dt.UTC)
    lsc.stamp(7, when=t1)
    lsc._cache[7] = (t1, t1)  # 가짜 flushed_at 주입
    lsc.stamp(7, when=t2)
    seen, flushed = lsc._cache[7]
    assert seen == t2
    assert flushed == t1


@pytest.mark.asyncio
async def test_flush_due_writes_when_aged(session_factory, seeded_session):
    sid = seeded_session
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush = dt.datetime(2026, 5, 25, 12, 1, 0, tzinfo=dt.UTC)  # +60s
    lsc.stamp(sid, when=t_stamp)
    written = await lsc.flush_due(session_factory, now=t_flush)
    assert written == 1
    # SQLite DateTime column strips tzinfo on read.
    assert await _db_last_seen(session_factory, sid) == t_stamp.replace(tzinfo=None)
    seen, flushed = lsc._cache[sid]
    assert flushed == t_flush


@pytest.mark.asyncio
async def test_flush_due_skips_recent(session_factory, seeded_session):
    """초기 flush 직후 30s 이내 stamp는 다음 flush에서 skip."""
    sid = seeded_session
    # 1단계. 초기 stamp → 첫 flush로 flushed_at 설정.
    t0 = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    lsc.stamp(sid, when=t0)
    written_init = await lsc.flush_due(session_factory, now=t0)
    assert written_init == 1
    seen, flushed = lsc._cache[sid]
    assert flushed == t0

    # 2단계. flushed=t0. 새 stamp(+5s) 후 +30s 시점 flush — flushed가 30s만 묵었으니 skip.
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 5, tzinfo=dt.UTC)
    t_flush = dt.datetime(2026, 5, 25, 12, 0, 30, tzinfo=dt.UTC)
    lsc.stamp(sid, when=t_stamp)
    written = await lsc.flush_due(session_factory, now=t_flush)
    assert written == 0


@pytest.mark.asyncio
async def test_flush_force_writes_all(session_factory, seeded_session):
    sid = seeded_session
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush = dt.datetime(2026, 5, 25, 12, 0, 5, tzinfo=dt.UTC)  # +5s only
    lsc.stamp(sid, when=t_stamp)
    written = await lsc.flush_due(session_factory, force=True, now=t_flush)
    assert written == 1
    assert await _db_last_seen(session_factory, sid) == t_stamp.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_flush_removes_orphan_entry(session_factory):
    orphan_sid = 9999
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush = dt.datetime(2026, 5, 25, 12, 1, 0, tzinfo=dt.UTC)
    lsc.stamp(orphan_sid, when=t_stamp)
    written = await lsc.flush_due(session_factory, now=t_flush)
    assert written == 0
    assert orphan_sid not in lsc._cache


@pytest.mark.asyncio
async def test_flush_repeated_is_noop(session_factory, seeded_session):
    sid = seeded_session
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush1 = dt.datetime(2026, 5, 25, 12, 1, 0, tzinfo=dt.UTC)
    t_flush2 = dt.datetime(2026, 5, 25, 12, 2, 0, tzinfo=dt.UTC)
    lsc.stamp(sid, when=t_stamp)
    written1 = await lsc.flush_due(session_factory, now=t_flush1)
    written2 = await lsc.flush_due(session_factory, now=t_flush2)
    assert written1 == 1
    assert written2 == 0


@pytest.mark.asyncio
async def test_start_and_stop_flusher_idempotent(session_factory):
    lsc.start_flusher(session_factory)
    assert lsc._task is not None
    first = lsc._task
    lsc.start_flusher(session_factory)
    assert lsc._task is first
    await lsc.stop_flusher()
    assert lsc._task is None
    lsc.start_flusher(session_factory)
    assert lsc._task is not None
    await lsc.stop_flusher()


@pytest.mark.asyncio
async def test_session_purge_sees_fresh_value(db_engine, monkeypatch):
    """cache에 fresh stamp를 둔 상태에서 purge가 호출되면 flush_all로
    DB가 갱신된 뒤 cutoff 판정이 이루어져 활성 세션이 살아남는다."""
    from sqlalchemy.ext.asyncio import AsyncSession as _AS
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app import db as db_module
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=_AS)
    # session_purge가 module-level AsyncSessionLocal을 본다 — 테스트에서 주입.
    monkeypatch.setattr(db_module, "AsyncSessionLocal", factory)

    base = dt.datetime(2026, 5, 25, 10, 0, 0, tzinfo=dt.UTC)
    async with factory() as s:
        row = Session(
            token="qa-fresh",  # noqa: S106 (test session token, not a password)
            nickname="qa-fresh",
            nickname_key="qa-fresh",
            created_at=base,
            last_seen_at=base,  # 1h+ 묵음 — DB만 보면 purge 후보
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
        sid = row.id

    # 활발히 활동 중인 척 — cache에 최신 stamp.
    fresh = dt.datetime(2026, 5, 25, 11, 0, 30, tzinfo=dt.UTC)
    lsc.stamp(sid, when=fresh)

    # ttl=3600s, now=fresh → cutoff = 10:00:30. DB의 last_seen_at(=10:00:00) < cutoff
    # 이라 naive purge면 삭제됐을 텐데, flush_all 후 last_seen_at=fresh(11:00:30)이
    # 되어 cutoff보다 커서 살아남아야 한다.
    from app.session_purge import purge_expired_sessions_once
    n_purged = await purge_expired_sessions_once(ttl_sec=3600, now=fresh)
    assert n_purged == 0

    # DB가 fresh로 갱신됐는지 확인. (Session.last_seen_at은 tz-naive 저장.)
    async with factory() as s:
        res = await s.execute(select(Session.last_seen_at).where(Session.id == sid))
        db_val = res.scalar_one_or_none()
    assert db_val is not None
    # SQLite는 tz 정보를 떨군다 — naive로 비교.
    assert db_val.replace(tzinfo=None) == fresh.replace(tzinfo=None)
