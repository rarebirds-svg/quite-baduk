# 검색 콘솔 검색어 통계 1행 — 구글(API)·네이버(CSV 임포트) 공용 저장소.
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"
    __table_args__ = (
        UniqueConstraint("source", "query", "page", "date", name="uq_search_query"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(255), nullable=False)
    page: Mapped[str | None] = mapped_column(String(512), nullable=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position: Mapped[float | None] = mapped_column(Float, nullable=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
