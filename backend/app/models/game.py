from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.session import Session


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable so a game row survives after its originating session is
    # deleted. This preserves the admin console's audit trail even when
    # users log out or get idle-purged. The display nickname is
    # independently snapshotted in `user_nickname` below.
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ai_rank: Mapped[str] = mapped_column(String(8), nullable=False)
    ai_style: Mapped[str] = mapped_column(
        String(16), nullable=False, default="balanced", server_default="balanced"
    )
    ai_player: Mapped[str | None] = mapped_column(String(32), nullable=True)
    handicap: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    board_size: Mapped[int] = mapped_column(Integer, nullable=False)
    komi: Mapped[float] = mapped_column(Float, nullable=False, default=6.5)
    user_color: Mapped[str] = mapped_column(String(8), nullable=False)  # 'black' | 'white'
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active"
    )  # active|finished|resigned|abandoned|suspended
    result: Mapped[str | None] = mapped_column(String(16), nullable=True)  # 'B+R', 'W+12.5'
    winner: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 'user'|'ai'
    move_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    undo_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    hint_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    # Consecutive post-AI plies where the deep (200-visit) analysis said
    # AI winrate < 1%. Auto-resign only fires when the streak hits 3,
    # protecting against single-read noise (especially on 9x9).
    loss_streak: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    user_nickname: Mapped[str | None] = mapped_column(String(32), nullable=True)
    user_rank: Mapped[str | None] = mapped_column(String(8), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sgf_cache: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[Session] = relationship("Session", back_populates="games")
