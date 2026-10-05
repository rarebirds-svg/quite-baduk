from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.deps import DbSession
from app.engine_pool import get_adapter
from app.schema_status import migration_status

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health(db: DbSession) -> dict[str, Any]:
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    adapter = await get_adapter(None)
    # 마이그레이션 누락은 DB 연결이 살아 있어도 세션 발급이 500으로 죽는 장애다.
    # 워치독·운영 일지가 바로 보도록 degraded로 내리고 리비전을 같이 준다.
    migrations = await migration_status(db) if db_ok else None
    pending = bool(migrations and migrations["pending"])
    return {
        "status": "ok" if db_ok and not pending else "degraded",
        "db": db_ok,
        "katago_alive": adapter.is_alive,
        "migrations": migrations,
    }
