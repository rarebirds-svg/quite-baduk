# 검색어 임포트·조회 어드민 API — 네이버 CSV 업로드와 통합 조회를 제공한다.
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete

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
