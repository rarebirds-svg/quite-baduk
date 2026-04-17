from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Move(Base):
    __tablename__ = "moves"
    __table_args__ = (UniqueConstraint("game_id", "move_number", name="uq_game_move"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    move_number: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(2), nullable=False)  # 'B' | 'W'
    coord: Mapped[str | None] = mapped_column(
        String(4), nullable=True
    )  # 'Q16' | 'pass' | None(resign)
    captures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_undone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    played_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
