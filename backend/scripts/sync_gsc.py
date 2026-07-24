# GSC 검색어를 최근 며칠분 가져와 DB에 동기화하는 크론 엔트리포인트.
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import structlog

from app.core.search_console.gsc import fetch_search_analytics
from app.core.search_console.sync import sync_gsc
from app.db import AsyncSessionLocal

log = structlog.get_logger()


async def main() -> None:
    end = date.today() - timedelta(days=2)   # GSC 2~3일 지연
    start = end - timedelta(days=5)
    rows = await fetch_search_analytics(start.isoformat(), end.isoformat())
    if not rows:
        log.info("gsc_sync_skip", reason="no_rows_or_not_configured")
        return
    async with AsyncSessionLocal() as db:
        n = await sync_gsc(db, rows)
    log.info("gsc_sync_done", rows=n)


if __name__ == "__main__":
    asyncio.run(main())
