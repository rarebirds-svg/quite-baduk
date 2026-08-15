# 방문자 해시용 일별 솔트를 보관하는 테이블 — 프로세스가 재시작해도 같은 날 해시를 유지한다.
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AnalyticsSalt(Base):
    __tablename__ = "analytics_salts"

    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
