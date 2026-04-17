from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ai_rank: Mapped[str] = mapped_column(String(8), nullable=False)
    handicap: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
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
