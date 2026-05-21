# 명국선 SGF 시드 — data/pro_games/masterpieces/*.sgf 를 멱등 적재한다.
"""명국선 SGF 일괄 적재 스크립트.

Usage (from backend/):

    python -m scripts.seed_pro_games

data/pro_games/masterpieces/ 의 모든 .sgf 를 파싱·정제해 collection=
'masterpiece' 로 적재한다. content_hash 가 이미 있으면 건너뛴다.
깨진 SGF 는 로그를 남기고 스킵하며 배치는 계속 진행한다.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import structlog
from sqlalchemy import select

from app.core.sgf.import_sgf import InvalidProSgf, parse_pro_sgf
from app.db import AsyncSessionLocal
from app.models import ProGame

log = structlog.get_logger()

SEED_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "pro_games"
    / "masterpieces"
)


async def seed() -> None:
    sgf_files = sorted(SEED_DIR.glob("*.sgf"))
    if not sgf_files:
        log.info("seed_pro_games.empty", dir=str(SEED_DIR))
        return

    inserted = 0
    skipped = 0
    failed = 0
    async with AsyncSessionLocal() as db:
        for path in sgf_files:
            try:
                parsed = parse_pro_sgf(path.read_text(encoding="utf-8"))
            except (InvalidProSgf, OSError, UnicodeDecodeError) as e:
                failed += 1
                log.warning("seed_pro_games.parse_failed", file=path.name, error=str(e))
                continue
            dup = (
                await db.execute(
                    select(ProGame.id).where(
                        ProGame.content_hash == parsed.content_hash
                    )
                )
            ).scalar_one_or_none()
            if dup is not None:
                skipped += 1
                continue
            db.add(ProGame.from_parsed(parsed, collection="masterpiece"))
            inserted += 1
        await db.commit()

    log.info(
        "seed_pro_games.done",
        inserted=inserted,
        skipped=skipped,
        failed=failed,
    )


if __name__ == "__main__":
    asyncio.run(seed())
