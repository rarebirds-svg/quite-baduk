# 익명 페이지 방문 1건을 담는 테이블 — 원본 IP 미저장, 국가·해시만 기록한다.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class VisitHit(Base):
    __tablename__ = "visit_hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    referrer_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    visitor_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    device: Mapped[str | None] = mapped_column(String(16), nullable=True)
