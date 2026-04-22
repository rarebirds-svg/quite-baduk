from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
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
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sgf_cache: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="games")  # noqa: F821
