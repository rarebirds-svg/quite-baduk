# 검색어 조회 엔드포인트: 소스 필터·정렬·403 검증.
from __future__ import annotations

from datetime import date

import pytest

from app.models.search_query import SearchQuery

ADMIN_NICK = "대공"


async def _signup(client, nickname):
    assert (await client.post("/api/session", json={"nickname": nickname})).status_code == 201


@pytest.mark.asyncio
async def test_list_search_queries(client):
    from app.db import AsyncSessionLocal  # 픽스처가 패치한 세션팩토리를 실행 시점에 참조

    async with AsyncSessionLocal() as db:
        db.add(SearchQuery(source="google", query="바둑 사활", page="/g/s",
                           clicks=5, impressions=50, ctr=0.1, position=3.0, date=date(2026, 7, 22)))
        db.add(SearchQuery(source="naver", query="접바둑 덤", page=None,
                           clicks=3, impressions=40, ctr=0.075, position=None, date=date(2026, 7, 22)))
        await db.commit()
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/search-queries?source=all&days=90&top=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["query"] == "바둑 사활"  # 클릭 내림차순
    r2 = await client.get("/api/admin/search-queries?source=naver")
    assert {x["query"] for x in r2.json()} == {"접바둑 덤"}


@pytest.mark.asyncio
async def test_list_forbidden(client):
    await _signup(client, "손님")
    assert (await client.get("/api/admin/search-queries")).status_code == 403
