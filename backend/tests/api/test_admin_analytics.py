# 방문 집계 엔드포인트: admin 인증·집계 정확성·403 검증.
from __future__ import annotations

import pytest
from sqlalchemy import select  # noqa: F401

from app.models.visit_hit import VisitHit

ADMIN_NICK = "대공"


async def _signup(client, nickname):
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201


async def _seed(rows):
    from app.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        for r in rows:
            db.add(VisitHit(**r))
        await db.commit()


@pytest.mark.asyncio
async def test_analytics_overview(client):
    await _seed([
        dict(path="/faq", referrer_host="google.com", source="search", country="KR",
             visitor_hash="v1", device="mobile"),
        dict(path="/faq", referrer_host=None, source="direct", country="US",
             visitor_hash="v2", device="desktop"),
        dict(path="/glossary", referrer_host="google.com", source="search", country="KR",
             visitor_hash="v1", device="mobile"),
    ])
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/analytics?days=30&top=10")
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["pageviews"] == 3
    paths = {p["path"]: p["pageviews"] for p in data["top_pages"]}
    assert paths["/faq"] == 2 and paths["/glossary"] == 1
    countries = {c["country"]: c["pageviews"] for c in data["countries"]}
    assert countries["KR"] == 2 and countries["US"] == 1
    sources = {s["source"] for s in data["sources"]}
    assert "search" in sources and "direct" in sources


@pytest.mark.asyncio
async def test_analytics_forbidden_for_non_admin(client):
    await _signup(client, "손님")
    r = await client.get("/api/admin/analytics")
    assert r.status_code == 403
