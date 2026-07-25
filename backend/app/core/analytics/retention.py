# 방문 로그 보존 정책 — 오래된 visit_hits 행을 삭제해 무한 증가를 막는다.
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visit_hit import VisitHit

DEFAULT_RETENTION_DAYS = 180


async def prune_old_visits(db: AsyncSession, days: int = DEFAULT_RETENTION_DAYS) -> int:
    """`days`일보다 오래된 visit_hits 행을 삭제하고 삭제 건수를 반환한다."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
    result = await db.execute(delete(VisitHit).where(VisitHit.created_at < cutoff))
    await db.commit()
    # DELETE는 런타임에 CursorResult라 rowcount가 있으나 Result 타입엔 없어 무시.
    return int(result.rowcount or 0)  # type: ignore[attr-defined]
