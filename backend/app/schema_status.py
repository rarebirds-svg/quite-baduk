"""DB 스키마가 코드의 마이그레이션 head와 맞는지 확인한다.

OPS-20260907-01: 새 코드(0020 accounts)로 API가 재기동됐지만 `alembic upgrade head`가
빠져 `sessions.account_id`가 없는 채 이틀간 세션 발급이 500으로 실패했다. 헬스체크는
`SELECT 1`만 보고 200을 돌려줘 워치독이 잡지 못했다. 이 모듈은 헬스에 `migrations`
블록을 노출하고 기동 시 경고를 남겨 같은 결손을 즉시 드러낸다.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class MigrationStatus(TypedDict):
    current: str | None
    head: str | None
    # True = alembic_version가 head와 다름(마이그레이션 누락). None = alembic_version
    # 테이블이 없어 판단 불가(테스트의 create_all DB 등).
    pending: bool | None


@lru_cache(maxsize=1)
def head_revision() -> str | None:
    """코드에 들어 있는 최신 마이그레이션 리비전. 스크립트 디렉터리에서 읽는다."""
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "migrations"))
    return ScriptDirectory.from_config(cfg).get_current_head()


async def current_revision(db: AsyncSession) -> str | None:
    try:
        row = (await db.execute(text("SELECT version_num FROM alembic_version"))).first()
    except Exception:  # noqa: BLE001 — 테이블 없음 등: 판단 불가로 취급
        return None
    return str(row[0]) if row else None


async def migration_status(db: AsyncSession) -> MigrationStatus:
    current = await current_revision(db)
    head = head_revision()
    pending = None if current is None or head is None else current != head
    return {"current": current, "head": head, "pending": pending}
