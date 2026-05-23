# 프로 기보 SGF 시드 — data/pro_games/<디렉터리>/*.sgf 를 컬렉션별로 멱등 적재한다.
"""프로 기보 SGF 일괄 적재 스크립트.

Usage (from backend/):

    python -m scripts.seed_pro_games

data/pro_games/ 하위 시드 디렉터리의 모든 .sgf 를 파싱·정제해 컬렉션별로
적재한다. content_hash 가 이미 있으면 건너뛴다 (DB 기적재분·배치 내
중복 모두). 깨진 SGF 는 로그를 남기고 스킵하며 배치는 계속 진행한다.

- masterpieces/  -> 'masterpiece' (명국선)
- world_finals/  -> 'world'       (빅6 세계 기전 결승)
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

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "pro_games"

# (디렉터리명, collection 값)
SEED_SETS: list[tuple[str, str]] = [
    ("masterpieces", "masterpiece"),
    ("world_finals", "world"),
]


async def seed() -> None:
    # 배치 내 중복 적재 방지 — 같은 content_hash 가 커밋 전이라
    # DB 조회로는 안 잡힌다.
    seen: set[str] = set()
    async with AsyncSessionLocal() as db:
        for subdir, collection in SEED_SETS:
            seed_dir = DATA_DIR / subdir
            sgf_files = sorted(seed_dir.glob("*.sgf"))
            if not sgf_files:
                log.info("seed_pro_games.empty", dir=str(seed_dir))
                continue

            inserted = skipped = failed = 0
            for path in sgf_files:
                try:
                    parsed = parse_pro_sgf(
                        path.read_text(encoding="utf-8", errors="replace")
                    )
                except (InvalidProSgf, OSError) as e:
                    failed += 1
                    log.warning(
                        "seed_pro_games.parse_failed",
                        file=path.name,
                        error=str(e),
                    )
                    continue
                if parsed.content_hash in seen:
                    skipped += 1
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
                db.add(ProGame.from_parsed(parsed, collection=collection))
                seen.add(parsed.content_hash)
                inserted += 1
            await db.commit()
            log.info(
                "seed_pro_games.done",
                collection=collection,
                inserted=inserted,
                skipped=skipped,
                failed=failed,
            )


if __name__ == "__main__":
    asyncio.run(seed())
