from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(32), nullable=False)
    nickname_key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # We intentionally do NOT cascade-delete games when a session ends or is
    # purged — history should survive the session. The DB-level FK is
    # ``ON DELETE SET NULL`` (migration 0008), and the ORM side matches it
    # with a passive default so SQLAlchemy doesn't NULL-set children twice.
    games: Mapped[list["Game"]] = relationship(  # noqa: F821
        "Game", back_populates="session", passive_deletes=True
    )
