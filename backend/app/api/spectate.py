# 공개 관전 API — 진행 중/종료된 대국을 소유권 없이 열람하는 엔드포인트
"""공개 관전 엔드포인트 — 소유권 없이 진행 중/종료된 대국을 열람한다.

노출 규칙: 정상 종료(finished/resigned)된 대국, 그리고 아직 세션이
살아있는 진행 중(active) 대국만. active이면서 세션이 사라진 대국은
"버려진 대국"이라 목록·상세 모두에서 제외한다.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import ColumnElement, and_, or_, select

from app.deps import CurrentSession, DbSession
from app.models import Game, Move, Session
from app.schemas.game import GameDetail, GameSummary, MoveEntry

router = APIRouter(prefix="/api/spectate", tags=["spectate"])

_FINISHED = ("finished", "resigned")


def _spectatable_clause() -> ColumnElement[bool]:
    """SQLAlchemy WHERE 절: 종료된 대국 OR 세션이 살아있는 진행 중 대국."""
    return or_(
        Game.status.in_(_FINISHED),
        and_(
            Game.status == "active",
            Game.session_id.in_(select(Session.id)),
        ),
    )


class SpectateRow(BaseModel):
    id: int
    user_nickname: str | None
    user_rank: str | None
    user_country: str | None
    ai_player: str | None
    ai_rank: str
    ai_style: str
    board_size: int
    handicap: int
    status: str
    result: str | None
    move_count: int
    started_at: datetime
    finished_at: datetime | None
    is_live: bool  # 진행 중(active + 세션 생존)


class SpectateList(BaseModel):
    rows: list[SpectateRow]


@router.get("", response_model=SpectateList)
async def list_spectatable(
    _: CurrentSession,
    db: DbSession,
    limit: int = 50,
) -> SpectateList:
    """관전 가능 대국 목록. 닉네임 세션은 필요하지만 소유권은 불필요.
    진행 중 대국이 위로 오도록 정렬 (started_at 역순)."""
    effective_limit = max(1, min(limit, 100))
    rows = (
        await db.execute(
            select(Game)
            .where(_spectatable_clause())
            .order_by(Game.started_at.desc())
            .limit(effective_limit)
        )
    ).scalars().all()

    return SpectateList(
        rows=[
            SpectateRow(
                id=g.id,
                user_nickname=g.user_nickname,
                user_rank=g.user_rank,
                user_country=g.user_country,
                ai_player=g.ai_player,
                ai_rank=g.ai_rank,
                ai_style=g.ai_style,
                board_size=g.board_size,
                handicap=g.handicap,
                status=g.status,
                result=g.result,
                move_count=g.move_count,
                started_at=g.started_at,
                finished_at=g.finished_at,
                is_live=g.status == "active",
            )
            for g in rows
        ]
    )


@router.get("/{game_id}", response_model=GameDetail)
async def spectate_game(
    game_id: int,
    _: CurrentSession,
    db: DbSession,
) -> GameDetail:
    """관전 가능한 대국의 상세(수순 포함). 필터를 통과하지 못하면 404 —
    버려진 대국·존재하지 않는 대국 모두 동일하게 숨긴다."""
    game = (
        await db.execute(
            select(Game).where(Game.id == game_id, _spectatable_clause())
        )
    ).scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="game_not_found")

    moves = (
        await db.execute(
            select(Move)
            .where(Move.game_id == game.id)
            .order_by(Move.move_number.asc())
        )
    ).scalars().all()
    move_entries = [
        MoveEntry(
            move_number=m.move_number,
            color=m.color,
            coord=m.coord,
            captures=m.captures,
            is_undone=m.is_undone,
        )
        for m in moves
    ]
    base = GameSummary.model_validate(game, from_attributes=True)
    return GameDetail(**base.model_dump(), moves=move_entries)
