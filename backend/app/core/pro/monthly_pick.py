# 결정적 월간 픽 알고리즘 — SHA256 시드로 후보 풀에서 단일 선택.
"""월간 픽.

`YYYY-MM` 문자열을 받아 결정적으로 한 게임을 고른다. 같은 입력은 같은 결과.
알고리즘 변경 시 SEO 노출에 영향 — 버전 주석 참조.

Version: v1 (2026-05) — sha256(yyyymm) % len(candidates).
"""
from __future__ import annotations

import hashlib
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProGame

_YYYYMM_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


class InvalidYearMonth(ValueError):
    """yyyymm이 YYYY-MM 형식이 아닐 때."""


def parse_yyyymm(yyyymm: str) -> tuple[int, int]:
    m = _YYYYMM_RE.match(yyyymm)
    if m is None:
        raise InvalidYearMonth(f"expected YYYY-MM, got {yyyymm!r}")
    return int(m.group(1)), int(m.group(2))


def pick_index(yyyymm: str, n: int) -> int:
    """결정적 인덱스. n>0 필수."""
    if n <= 0:
        raise ValueError("n must be positive")
    h = hashlib.sha256(yyyymm.encode("utf-8")).hexdigest()
    return int(h, 16) % n


async def candidates_for_month(db: AsyncSession, month: int) -> list[int]:
    """해당 달(1-12)의 후보 ID 리스트. masterpiece 우선, fallback 전체."""
    month_str = f"{month:02d}"
    masterpiece_q = (
        select(ProGame.id)
        .where(
            func.strftime("%m", ProGame.game_date) == month_str,
            ProGame.collection == "masterpiece",
        )
        .order_by(ProGame.id)
    )
    result = await db.execute(masterpiece_q)
    ids = list(result.scalars().all())
    if ids:
        return ids
    all_q = (
        select(ProGame.id)
        .where(func.strftime("%m", ProGame.game_date) == month_str)
        .order_by(ProGame.id)
    )
    result = await db.execute(all_q)
    return list(result.scalars().all())


async def pick_for_month(db: AsyncSession, yyyymm: str) -> int | None:
    """yyyymm → game ID 또는 None(후보 0)."""
    _, month = parse_yyyymm(yyyymm)
    candidates = await candidates_for_month(db, month)
    if not candidates:
        return None
    return candidates[pick_index(yyyymm, len(candidates))]
