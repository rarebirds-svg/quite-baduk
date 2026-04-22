from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_session, get_db
from app.models import Game, Session

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    sess: Session = Depends(get_current_session),
) -> dict[str, Any]:
    res = await db.execute(
        select(Game.ai_rank, Game.handicap, Game.winner, func.count(Game.id))
        .where(Game.session_id == sess.id, Game.status.in_(["finished", "resigned"]))
        .group_by(Game.ai_rank, Game.handicap, Game.winner)
    )
    rows = res.all()
    breakdown = [
        {"ai_rank": r[0], "handicap": r[1], "winner": r[2], "count": r[3]}
        for r in rows
    ]
    total = sum(r["count"] for r in breakdown)
    wins = sum(r["count"] for r in breakdown if r["winner"] == "user")
    return {"total": total, "wins": wins, "losses": total - wins, "breakdown": breakdown}
