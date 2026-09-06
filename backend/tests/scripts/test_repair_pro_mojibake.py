# repair_pro_mojibake.py — 깨진 기사명 행을 되돌리고, 정상 행·중복 행은 건드리지 않는다.
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

import scripts.repair_pro_mojibake as repair_mod
from app.core.sgf.import_sgf import parse_pro_sgf
from app.models import ProGame

_GOOD = "(;GM[1]FF[4]SZ[19]KM[6.5]PB[國 insei]PW[이창호]EV[명인전];B[pd];W[dp])"
_OTHER = "(;GM[1]FF[4]SZ[19]KM[6.5]PB[A]PW[B];B[pd];W[dd];B[pp];W[dp])"


def _broken_row(sgf_text: str, collection: str = "world") -> ProGame:
    """예전 파서가 만들던 그대로 — UTF-8을 latin-1로 읽어 깨진 메타로 적재된 행."""
    parsed = parse_pro_sgf(sgf_text)
    broken = ProGame.from_parsed(parsed, collection=collection)
    for f in ("black_player", "white_player", "event", "sgf"):
        val = getattr(broken, f)
        setattr(broken, f, val.encode("utf-8").decode("latin-1"))
    broken.content_hash = "broken-" + parsed.content_hash[:16]
    return broken


@pytest.mark.asyncio
async def test_repair_restores_names_and_hash(
    db_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(repair_mod, "AsyncSessionLocal", factory)
    async with factory() as db:
        db.add(_broken_row(_GOOD))
        db.add(ProGame.from_parsed(parse_pro_sgf(_OTHER), collection="world"))
        await db.commit()

    summary = await repair_mod.repair()
    assert summary == {"scanned": 2, "repaired": 1, "skipped_dup": 0, "failed": 0}

    async with factory() as db:
        rows = (await db.execute(select(ProGame).order_by(ProGame.id))).scalars().all()
    fixed, other = rows
    assert (fixed.black_player, fixed.white_player, fixed.event) == (
        "國 insei",
        "이창호",
        "명인전",
    )
    assert fixed.content_hash == parse_pro_sgf(_GOOD).content_hash
    assert "PW[이창호]" in fixed.sgf
    assert other.black_player == "A"


@pytest.mark.asyncio
async def test_repair_dry_run_and_duplicate_skip(
    db_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(repair_mod, "AsyncSessionLocal", factory)
    async with factory() as db:
        # 같은 기보가 정상 인코딩으로 이미 있으면 깨진 행은 복구 대신 건너뛴다.
        db.add(ProGame.from_parsed(parse_pro_sgf(_GOOD), collection="world"))
        db.add(_broken_row(_GOOD))
        await db.commit()

    dry = await repair_mod.repair(dry_run=True)
    assert dry["scanned"] == 2 and dry["skipped_dup"] == 1 and dry["repaired"] == 0

    async with factory() as db:
        rows = (await db.execute(select(ProGame).order_by(ProGame.id))).scalars().all()
    assert rows[1].black_player.startswith("å")  # dry-run이므로 그대로
