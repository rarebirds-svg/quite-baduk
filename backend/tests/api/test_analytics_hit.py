# 방문 수집 엔드포인트: 정상 저장·봇 스킵·직접유입 분류 검증.
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.visit_hit import VisitHit


@pytest.mark.asyncio
async def test_hit_saves_row(client):
    from app.db import AsyncSessionLocal  # client 픽스처가 리바인딩한 뒤에 임포트해야 함

    r = await client.post("/api/analytics/hit",
                          json={"path": "/glossary/sahwal", "referrer": "https://www.google.com/"},
                          headers={"User-Agent": "Mozilla/5.0 (iPhone) Safari"})
    assert r.status_code == 204
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(VisitHit))).scalars().all()
    assert len(rows) == 1
    assert rows[0].path == "/glossary/sahwal"
    assert rows[0].source == "search"
    assert rows[0].referrer_host == "google.com"


@pytest.mark.asyncio
async def test_hit_skips_bot(client):
    from app.db import AsyncSessionLocal  # client 픽스처가 리바인딩한 뒤에 임포트해야 함

    r = await client.post("/api/analytics/hit",
                          json={"path": "/", "referrer": ""},
                          headers={"User-Agent": "Googlebot/2.1"})
    assert r.status_code == 204
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(VisitHit))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_hit_direct_source(client):
    from app.db import AsyncSessionLocal  # client 픽스처가 리바인딩한 뒤에 임포트해야 함

    await client.post("/api/analytics/hit", json={"path": "/faq", "referrer": ""},
                      headers={"User-Agent": "Mozilla/5.0 (iPhone) Safari"})
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(VisitHit))).scalars().one()
    assert row.source == "direct"
    assert row.referrer_host is None
