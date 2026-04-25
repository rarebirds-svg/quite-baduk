"""Append-only login audit log — see migration 0009."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SessionHistory(Base):
    __tablename__ = "session_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Not a FK — the row must survive the session being deleted.
    session_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    nickname: Mapped[str] = mapped_column(String(32), nullable=False)
    nickname_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # "logout" | "idle_purge" | "replaced" | None (still active)
    end_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)
