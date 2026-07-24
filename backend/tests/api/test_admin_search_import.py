# 네이버 CSV 임포트 엔드포인트: 적재·스냅샷 교체·403 검증.
from __future__ import annotations

import pytest
from sqlalchemy import select

ADMIN_NICK = "대공"
CSV = "검색어,클릭,노출,CTR(%)\n바둑 사활,2,40,5\n삼삼,3,8,37.5\n"


async def _signup(client, nickname):
    assert (await client.post("/api/session", json={"nickname": nickname})).status_code == 201


@pytest.mark.asyncio
async def test_import_naver_csv(client):
    await _signup(client, ADMIN_NICK)
    r = await client.post("/api/admin/search-queries/import",
                          files={"file": ("naver.csv", CSV, "text/csv")})
    assert r.status_code == 200
    assert r.json()["imported"] == 2
    from app.db import AsyncSessionLocal
    from app.models.search_query import SearchQuery
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(SearchQuery).where(SearchQuery.source == "naver"))).scalars().all()
    assert {x.query for x in rows} == {"바둑 사활", "삼삼"}


@pytest.mark.asyncio
async def test_import_forbidden(client):
    await _signup(client, "손님")
    r = await client.post("/api/admin/search-queries/import",
                          files={"file": ("n.csv", CSV, "text/csv")})
    assert r.status_code == 403
