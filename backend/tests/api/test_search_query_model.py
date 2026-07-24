# search_queries 모델 삽입 검증.
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.models.search_query import SearchQuery


@pytest.mark.asyncio
async def test_search_query_insert(client):
    from app.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        db.add(SearchQuery(source="google", query="바둑 단수 뜻", page="/glossary/dansu",
                           clicks=0, impressions=36, ctr=0.0, position=13.2,
                           date=date(2026, 7, 20)))
        await db.commit()
        row = (await db.execute(select(SearchQuery))).scalars().one()
        assert row.query == "바둑 단수 뜻"
        assert row.source == "google"
