# 방문 로그 보존 정리 크론 엔트리포인트 — 180일 지난 visit_hits를 삭제한다.
from __future__ import annotations

import asyncio

import structlog

from app.core.analytics.retention import DEFAULT_RETENTION_DAYS, prune_old_visits
from app.db import AsyncSessionLocal

log = structlog.get_logger()


async def main() -> None:
    async with AsyncSessionLocal() as db:
        deleted = await prune_old_visits(db, DEFAULT_RETENTION_DAYS)
    log.info("visit_prune_done", deleted=deleted, retention_days=DEFAULT_RETENTION_DAYS)


if __name__ == "__main__":
    asyncio.run(main())
