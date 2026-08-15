# 방문자 해시 결정성·일일 솔트 영속화 검증.
from __future__ import annotations

from sqlalchemy import select

from app.core.analytics import hashing
from app.core.analytics.hashing import daily_salt, visitor_hash
from app.models.analytics_salt import AnalyticsSalt


def test_visitor_hash_deterministic():
    assert visitor_hash("1.2.3.4", "salt") == visitor_hash("1.2.3.4", "salt")


def test_visitor_hash_differs_by_ip_and_salt():
    assert visitor_hash("1.2.3.4", "s") != visitor_hash("9.9.9.9", "s")
    assert visitor_hash("1.2.3.4", "s1") != visitor_hash("1.2.3.4", "s2")


async def test_daily_salt_stable_per_day_rotates_across_days(db_session):
    hashing._salts.clear()
    assert await daily_salt(db_session, "2026-07-24") == await daily_salt(db_session, "2026-07-24")
    assert await daily_salt(db_session, "2026-07-24") != await daily_salt(db_session, "2026-07-25")


async def test_daily_salt_survives_process_restart(db_session):
    """캐시를 비워 재시작을 흉내내도 같은 날이면 DB에서 같은 솔트를 되찾는다."""
    hashing._salts.clear()
    first = await daily_salt(db_session, "2026-07-24")

    hashing._salts.clear()
    second = await daily_salt(db_session, "2026-07-24")

    assert second == first
    assert visitor_hash("1.2.3.4", second) == visitor_hash("1.2.3.4", first)


async def test_daily_salt_persisted_once(db_session):
    hashing._salts.clear()
    await daily_salt(db_session, "2026-07-24")
    hashing._salts.clear()
    await daily_salt(db_session, "2026-07-24")

    rows = (await db_session.execute(select(AnalyticsSalt))).scalars().all()
    assert [(r.day, len(r.salt)) for r in rows] == [("2026-07-24", 32)]


async def test_daily_salt_pk_conflict_reuses_existing(db_session, monkeypatch):
    """다른 워커가 먼저 INSERT해 PK가 충돌하면 롤백 후 그 행을 재조회해 쓴다."""
    hashing._salts.clear()
    db_session.add(AnalyticsSalt(day="2026-07-24", salt="deadbeef"))
    await db_session.commit()

    real_select = hashing._select_salt
    calls = {"n": 0}

    async def flaky_select(db, day):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # 경합 상대의 커밋을 아직 못 본 상태를 흉내낸다.
        return await real_select(db, day)

    monkeypatch.setattr(hashing, "_select_salt", flaky_select)

    assert await daily_salt(db_session, "2026-07-24") == "deadbeef"
    assert calls["n"] == 2
