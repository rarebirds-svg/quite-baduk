# seed_pro_games.py 의 멱등성 검증 — 같은 SGF 디렉터리로 두 번 시드해도 행 수가 안정적인지 확인한다.
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import scripts.seed_pro_games as seed_mod
from app.models import ProGame

_SGF_A = "(;GM[1]FF[4]SZ[19]KM[6.5]PB[A]PW[B];B[pd];W[dp];B[pp];W[dd])"
_SGF_B = "(;GM[1]FF[4]SZ[19]KM[6.5]PB[C]PW[D];B[pd];W[dd];B[pp];W[dp])"


@pytest.mark.asyncio
async def test_seed_is_idempotent(
    db_engine: AsyncEngine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 테스트 SGF 디렉터리를 만들고 모듈 전역 SEED_DIR / AsyncSessionLocal 을
    # 임시 테스트 DB 쪽으로 바꿔치기한다.
    (tmp_path / "a.sgf").write_text(_SGF_A, encoding="utf-8")
    (tmp_path / "b.sgf").write_text(_SGF_B, encoding="utf-8")
    monkeypatch.setattr(seed_mod, "SEED_DIR", tmp_path)
    monkeypatch.setattr(
        seed_mod,
        "AsyncSessionLocal",
        async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession),
    )

    async def _count() -> int:
        factory = async_sessionmaker(
            db_engine, expire_on_commit=False, class_=AsyncSession
        )
        async with factory() as db:
            return (
                await db.execute(select(func.count()).select_from(ProGame))
            ).scalar_one()

    # 1차 시드: 두 기보 모두 적재.
    await seed_mod.seed()
    assert await _count() == 2

    # 2차 시드: 동일 디렉터리 → 전부 중복 스킵, 행 수 불변.
    await seed_mod.seed()
    assert await _count() == 2
