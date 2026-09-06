"""외부 계정(구글 등) — 닉네임 세션에 옵트인으로 연동해 기기·만료를 넘어
전적을 이어 볼 수 있게 한다. 세션은 여전히 로그인의 단위이고, 계정은
여러 세션과 대국을 묶는 열쇠일 뿐이다."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_sub", name="uq_account_provider_sub"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    # 제공자가 주는 불변 식별자(구글 `sub`). 이메일은 바뀔 수 있어 키로 쓰지 않는다.
    provider_sub: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
