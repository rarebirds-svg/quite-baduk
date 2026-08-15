# 방문자를 원본 IP 저장 없이 식별하기 위한 일일 솔트 해시 — 익일 재식별 불가.
from __future__ import annotations

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_salt import AnalyticsSalt

_salts: dict[str, str] = {}


async def _select_salt(db: AsyncSession, day: str) -> str | None:
    result = await db.execute(select(AnalyticsSalt.salt).where(AnalyticsSalt.day == day))
    return result.scalar_one_or_none()


async def daily_salt(db: AsyncSession, day: str) -> str:
    """UTC 날짜 문자열(YYYY-MM-DD)별 랜덤 솔트. 메모리 캐시 → DB → 신규 생성 순으로 해소한다."""
    cached = _salts.get(day)
    if cached is not None:
        return cached

    salt = await _select_salt(db, day)
    if salt is None:
        salt = secrets.token_hex(16)
        db.add(AnalyticsSalt(day=day, salt=salt))
        try:
            await db.commit()
        except IntegrityError:
            # 다른 워커가 같은 날 솔트를 먼저 INSERT한 경우 — 롤백 후 그 값을 쓴다.
            await db.rollback()
            existing = await _select_salt(db, day)
            if existing is None:
                raise
            salt = existing

    _salts[day] = salt
    return salt


def visitor_hash(ip: str, salt: str) -> str:
    return hashlib.sha256(f"{ip}:{salt}".encode()).hexdigest()
