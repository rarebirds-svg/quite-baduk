# 검색어 임포트·조회 어드민 API — 네이버 CSV 업로드와 통합 조회를 제공한다.
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, select

from app.core.search_console.naver_csv import parse_naver_csv
from app.deps import AdminSession, DbSession
from app.models.search_query import SearchQuery

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ImportResult(BaseModel):
    imported: int


@router.post("/search-queries/import", response_model=ImportResult)
async def import_naver(_: AdminSession, db: DbSession, file: UploadFile) -> ImportResult:
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    rows = parse_naver_csv(raw)
    today = datetime.now(UTC).date()
    # 네이버 스냅샷 교체 — 기존 naver 행 삭제 후 재적재.
    await db.execute(delete(SearchQuery).where(SearchQuery.source == "naver"))
    for r in rows:
        db.add(SearchQuery(source="naver", query=r.query, page=None,
                           clicks=r.clicks, impressions=r.impressions,
                           ctr=r.ctr, position=None, date=today))
    await db.commit()
    return ImportResult(imported=len(rows))


class SearchQueryRow(BaseModel):
    query: str
    page: str | None
    clicks: int
    impressions: int
    ctr: float
    position: float | None
    source: str


@router.get("/search-queries", response_model=list[SearchQueryRow])
async def list_search_queries(
    _: AdminSession, db: DbSession, source: str = "all", days: int = 90, top: int = 50
) -> list[SearchQueryRow]:
    days = max(1, min(days, 480))
    top = max(1, min(top, 200))
    start = datetime.now(UTC).date() - timedelta(days=days)
    stmt = select(SearchQuery).where(SearchQuery.date >= start)
    if source in ("google", "naver"):
        stmt = stmt.where(SearchQuery.source == source)
    stmt = stmt.order_by(SearchQuery.clicks.desc(), SearchQuery.impressions.desc()).limit(top)
    rows = (await db.execute(stmt)).scalars().all()
    return [SearchQueryRow(query=r.query, page=r.page, clicks=r.clicks,
                           impressions=r.impressions, ctr=r.ctr, position=r.position,
                           source=r.source) for r in rows]
