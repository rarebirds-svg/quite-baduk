# GSC 동기화 upsert 검증 — 같은 (query,page,date) 재삽입 시 갱신.
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.search_console.gsc import GscRow
from app.core.search_console.sync import sync_gsc
from app.models.search_query import SearchQuery


@pytest.mark.asyncio
async def test_sync_upsert(client):
    from app.db import AsyncSessionLocal

    rows = [GscRow(query="바둑 사활", page="https://inkbaduk.com/glossary/sahwal",
                   clicks=1, impressions=10, ctr=0.1, position=5.0, date="2026-07-22")]
    async with AsyncSessionLocal() as db:
        n = await sync_gsc(db, rows)
        assert n == 1
    rows2 = [GscRow(query="바둑 사활", page="https://inkbaduk.com/glossary/sahwal",
                    clicks=3, impressions=20, ctr=0.15, position=4.0, date="2026-07-22")]
    async with AsyncSessionLocal() as db:
        await sync_gsc(db, rows2)
        result = await db.execute(select(SearchQuery).where(SearchQuery.source == "google"))
        stored = result.scalars().all()
    assert len(stored) == 1
    assert stored[0].clicks == 3
