"""pro_games 기사명·기전명 인코딩 깨짐(mojibake) 복구.

원인: CA[] 없는 SGF를 sgfmill이 ISO-8859-1로 읽고, 주간 인제스트가 HTTP 헤더
charset을 믿고 디코드하면서 UTF-8 기사명이 'åœ‹æ ¾è ¡' 꼴로 적재됐다.
파서·인제스트는 고쳤으므로 이 스크립트는 이미 적재된 행만 되돌린다.

동작: 저장된 정제 SGF를 latin-1→utf-8로 되돌려 다시 파싱하고, 기사명·기전·
회차·SGF·content_hash를 갱신한다. 복구 후 해시가 다른 행과 겹치면(같은 기보를
정상 인코딩으로 이미 적재) 깨진 행을 건너뛰고 로그로 남긴다.

    python -m scripts.repair_pro_mojibake            # 실제 적용
    python -m scripts.repair_pro_mojibake --dry-run  # 대상만 출력
"""
from __future__ import annotations

import argparse
import asyncio

import structlog
from sqlalchemy import select

from app.core.sgf.import_sgf import InvalidProSgf, parse_pro_sgf, repair_mojibake
from app.db import AsyncSessionLocal
from app.models import ProGame

log = structlog.get_logger()

# 복구 대상 판단에 쓰는 텍스트 필드 — 하나라도 되돌릴 수 있으면 행 전체를 재파싱.
_TEXT_FIELDS = ("black_player", "white_player", "event", "round")


def _needs_repair(row: ProGame) -> bool:
    return any(
        repair_mojibake(val) is not None
        for val in (getattr(row, f) for f in _TEXT_FIELDS)
        if val
    )


async def repair(*, dry_run: bool = False) -> dict[str, int]:
    summary = {"scanned": 0, "repaired": 0, "skipped_dup": 0, "failed": 0}
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(ProGame))).scalars().all()
        existing_hashes = {r.content_hash for r in rows}
        for row in rows:
            summary["scanned"] += 1
            if not _needs_repair(row):
                continue
            fixed_sgf = repair_mojibake(row.sgf)
            if fixed_sgf is None:
                # 메타는 깨졌는데 SGF는 되돌릴 수 없는 이례적 행 — 수동 확인 대상.
                summary["failed"] += 1
                log.warning("repair_pro_mojibake.sgf_unrepairable", id=row.id)
                continue
            try:
                parsed = parse_pro_sgf(fixed_sgf)
            except InvalidProSgf as e:
                summary["failed"] += 1
                log.warning("repair_pro_mojibake.parse_failed", id=row.id, error=str(e))
                continue
            if (
                parsed.content_hash != row.content_hash
                and parsed.content_hash in existing_hashes
            ):
                summary["skipped_dup"] += 1
                log.warning(
                    "repair_pro_mojibake.duplicate_after_repair",
                    id=row.id,
                    black=parsed.black_player,
                    white=parsed.white_player,
                )
                continue
            log.info(
                "repair_pro_mojibake.row",
                id=row.id,
                before=(row.black_player, row.white_player),
                after=(parsed.black_player, parsed.white_player),
                dry_run=dry_run,
            )
            summary["repaired"] += 1
            if dry_run:
                continue
            existing_hashes.discard(row.content_hash)
            existing_hashes.add(parsed.content_hash)
            row.black_player = parsed.black_player
            row.white_player = parsed.white_player
            row.black_rank = parsed.black_rank
            row.white_rank = parsed.white_rank
            row.event = parsed.event
            row.round = parsed.round
            row.sgf = parsed.clean_sgf
            row.content_hash = parsed.content_hash
        if not dry_run:
            await db.commit()
    log.info("repair_pro_mojibake.done", **summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 대상만 출력")
    args = parser.parse_args()
    asyncio.run(repair(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
