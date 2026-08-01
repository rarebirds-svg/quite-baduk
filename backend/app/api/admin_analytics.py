# 방문 통계 집계 API — 관리자에게 PV·순방문자·유입경로·국가·인기페이지를 반환한다.
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.deps import AdminSession, DbSession
from app.models.visit_hit import VisitHit

router = APIRouter(prefix="/api/admin", tags=["admin"])


class Totals(BaseModel):
    pageviews: int
    unique_visitors: int


class DailyRow(BaseModel):
    date: str
    pageviews: int
    uniques: int


class PageRow(BaseModel):
    path: str
    pageviews: int
    uniques: int


class SourceRow(BaseModel):
    source: str
    referrer_host: str | None
    pageviews: int


class CountryRow(BaseModel):
    country: str | None
    pageviews: int
    uniques: int


class AnalyticsOverview(BaseModel):
    totals: Totals
    daily: list[DailyRow]
    top_pages: list[PageRow]
    sources: list[SourceRow]
    countries: list[CountryRow]


@router.get("/analytics", response_model=AnalyticsOverview)
async def analytics(
    _: AdminSession, db: DbSession, days: int = 30, top: int = 20
) -> AnalyticsOverview:
    days = max(1, min(days, 90))
    top = max(1, min(top, 50))
    start = datetime.utcnow() - timedelta(days=days)
    base = VisitHit.created_at >= start

    pv = (await db.execute(select(func.count(VisitHit.id)).where(base))).scalar_one()
    uv = (
        await db.execute(select(func.count(func.distinct(VisitHit.visitor_hash))).where(base))
    ).scalar_one()

    daily_rows = (
        await db.execute(
            select(
                func.date(VisitHit.created_at).label("d"),
                func.count(VisitHit.id),
                func.count(func.distinct(VisitHit.visitor_hash)),
            )
            .where(base)
            .group_by("d")
            .order_by("d")
        )
    ).all()

    page_rows = (
        await db.execute(
            select(
                VisitHit.path,
                func.count(VisitHit.id),
                func.count(func.distinct(VisitHit.visitor_hash)),
            )
            .where(base)
            .group_by(VisitHit.path)
            .order_by(func.count(VisitHit.id).desc())
            .limit(top)
        )
    ).all()

    source_rows = (
        await db.execute(
            select(VisitHit.source, VisitHit.referrer_host, func.count(VisitHit.id))
            .where(base)
            .group_by(VisitHit.source, VisitHit.referrer_host)
            .order_by(func.count(VisitHit.id).desc())
            .limit(top)
        )
    ).all()

    country_rows = (
        await db.execute(
            select(
                VisitHit.country,
                func.count(VisitHit.id),
                func.count(func.distinct(VisitHit.visitor_hash)),
            )
            .where(base)
            .group_by(VisitHit.country)
            .order_by(func.count(VisitHit.id).desc())
            .limit(top)
        )
    ).all()

    return AnalyticsOverview(
        totals=Totals(pageviews=int(pv), unique_visitors=int(uv)),
        daily=[
            DailyRow(date=str(r[0]), pageviews=int(r[1]), uniques=int(r[2])) for r in daily_rows
        ],
        top_pages=[
            PageRow(path=r[0], pageviews=int(r[1]), uniques=int(r[2])) for r in page_rows
        ],
        sources=[
            SourceRow(source=r[0], referrer_host=r[1], pageviews=int(r[2]))
            for r in source_rows
        ],
        countries=[
            CountryRow(country=r[0], pageviews=int(r[1]), uniques=int(r[2]))
            for r in country_rows
        ],
    )
