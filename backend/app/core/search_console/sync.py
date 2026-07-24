# GSC 응답 행을 search_queries에 upsert하는 동기화 로직.
from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.search_console.gsc import GscRow
from app.models.search_query import SearchQuery


async def sync_gsc(db: AsyncSession, rows: list[GscRow]) -> int:
    for r in rows:
        d = date_type.fromisoformat(r.date)
        existing = (await db.execute(
            select(SearchQuery).where(
                SearchQuery.source == "google",
                SearchQuery.query == r.query,
                SearchQuery.page == r.page,
                SearchQuery.date == d,
            )
        )).scalars().first()
        if existing is None:
            db.add(SearchQuery(source="google", query=r.query, page=r.page,
                               clicks=r.clicks, impressions=r.impressions,
                               ctr=r.ctr, position=r.position, date=d))
        else:
            existing.clicks = r.clicks
            existing.impressions = r.impressions
            existing.ctr = r.ctr
            existing.position = r.position
    await db.commit()
    return len(rows)
