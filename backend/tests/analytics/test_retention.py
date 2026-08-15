# 방문 로그 보존 정리 검증 — 오래된 행만 삭제.
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.analytics.retention import prune_old_visits


@pytest.mark.asyncio
async def test_prune_old_visits(client):
    from app.db import AsyncSessionLocal
    from app.models.visit_hit import VisitHit

    old = datetime.utcnow() - timedelta(days=200)
    recent = datetime.utcnow() - timedelta(days=10)
    async with AsyncSessionLocal() as db:
        db.add(VisitHit(created_at=old, path="/old", source="direct", visitor_hash="a"))
        db.add(VisitHit(created_at=recent, path="/recent", source="direct", visitor_hash="b"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        deleted = await prune_old_visits(db, days=180)
    assert deleted == 1

    async with AsyncSessionLocal() as db:
        paths = [r.path for r in (await db.execute(select(VisitHit))).scalars().all()]
    assert paths == ["/recent"]


@pytest.mark.asyncio
async def test_prune_removes_old_salts_only(client):
    from app.db import AsyncSessionLocal
    from app.models.analytics_salt import AnalyticsSalt

    old_day = (datetime.utcnow() - timedelta(days=200)).strftime("%Y-%m-%d")
    recent_day = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
    async with AsyncSessionLocal() as db:
        db.add(AnalyticsSalt(day=old_day, salt="old"))
        db.add(AnalyticsSalt(day=recent_day, salt="recent"))
        await db.commit()

    async with AsyncSessionLocal() as db:
        await prune_old_visits(db, days=180)

    async with AsyncSessionLocal() as db:
        days = [r.day for r in (await db.execute(select(AnalyticsSalt))).scalars().all()]
    assert days == [recent_day]
