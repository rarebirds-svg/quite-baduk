from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.engine_pool import get_adapter

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    db_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    adapter = get_adapter()
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "katago_alive": adapter.is_alive,
    }
