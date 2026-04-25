from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_session, get_db
from app.models import Game, Session

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    sess: Session = Depends(get_current_session),
) -> dict[str, Any]:
    """Per-session summary statistics for the history page dashboard."""
    # Only decisively finished games contribute to win/loss stats.
    finished_filter = (
        Game.session_id == sess.id,
        Game.status.in_(["finished", "resigned"]),
    )

    total_row = (
        await db.execute(
            select(
                func.count(Game.id),
                func.coalesce(
                    func.sum(case((Game.winner == "user", 1), else_=0)), 0
                ),
                func.coalesce(func.sum(Game.move_count), 0),
                func.coalesce(func.sum(Game.undo_count), 0),
                func.coalesce(func.sum(Game.hint_count), 0),
            ).where(*finished_filter)
        )
    ).one()
    total = int(total_row[0])
    wins = int(total_row[1])
    total_moves = int(total_row[2])
    total_undos = int(total_row[3])
    total_hints = int(total_row[4])

    def _bucket(rows: list[Any], key: str) -> list[dict[str, Any]]:
        out = []
        for r in rows:
            n_total = int(r[1])
            n_wins = int(r[2])
            out.append({
                key: r[0],
                "total": n_total,
                "wins": n_wins,
                "losses": n_total - n_wins,
                "winrate": (n_wins / n_total) if n_total else 0.0,
            })
        return out

    by_rank_rows = (
        await db.execute(
            select(
                Game.ai_rank,
                func.count(Game.id),
                func.coalesce(func.sum(case((Game.winner == "user", 1), else_=0)), 0),
            )
            .where(*finished_filter)
            .group_by(Game.ai_rank)
            .order_by(Game.ai_rank)
        )
    ).all()

    by_board_rows = (
        await db.execute(
            select(
                Game.board_size,
                func.count(Game.id),
                func.coalesce(func.sum(case((Game.winner == "user", 1), else_=0)), 0),
            )
            .where(*finished_filter)
            .group_by(Game.board_size)
            .order_by(Game.board_size)
        )
    ).all()

    by_player_rows = (
        await db.execute(
            select(
                Game.ai_player,
                func.count(Game.id),
                func.coalesce(func.sum(case((Game.winner == "user", 1), else_=0)), 0),
            )
            .where(*finished_filter, Game.ai_player.isnot(None))
            .group_by(Game.ai_player)
        )
    ).all()

    breakdown_rows = (
        await db.execute(
            select(
                Game.ai_rank, Game.handicap, Game.winner, func.count(Game.id)
            )
            .where(*finished_filter)
            .group_by(Game.ai_rank, Game.handicap, Game.winner)
        )
    ).all()

    return {
        "total": total,
        "wins": wins,
        "losses": total - wins,
        "winrate": (wins / total) if total else 0.0,
        "total_moves": total_moves,
        "total_undos": total_undos,
        "total_hints": total_hints,
        "avg_moves_per_game": (total_moves / total) if total else 0.0,
        "by_rank": _bucket(by_rank_rows, "ai_rank"),
        "by_board_size": _bucket(by_board_rows, "board_size"),
        "by_ai_player": _bucket(by_player_rows, "ai_player"),
        "breakdown": [
            {"ai_rank": r[0], "handicap": r[1], "winner": r[2], "count": r[3]}
            for r in breakdown_rows
        ],
    }
