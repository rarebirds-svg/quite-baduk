# 프로 기보 공개 관전 API — 명국선·세계기전·최근 기보 목록과 수순 상세를 제공한다.
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.core.sgf.import_sgf import parse_pro_sgf
from app.deps import CurrentSession, DbSession
from app.models import ProGame

router = APIRouter(prefix="/api/spectate/pro", tags=["spectate"])


class ProGameRow(BaseModel):
    id: int
    collection: str
    black_player: str
    white_player: str
    black_rank: str | None
    white_rank: str | None
    event: str | None
    game_date: date | None
    result: str | None
    board_size: int
    handicap: int
    move_count: int


class ProGameList(BaseModel):
    rows: list[ProGameRow]
    total: int  # 필터 적용 후 전체 건수 — 페이지네이션용


class ProMoveOut(BaseModel):
    move_number: int
    color: str
    coord: str | None


class ProGameDetail(ProGameRow):
    komi: float
    moves: list[ProMoveOut]


@router.get("", response_model=ProGameList)
async def list_pro_games(
    _: CurrentSession,
    db: DbSession,
    collection: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ProGameList:
    """프로 기보 목록. 닉네임 세션 필요. 최신 대국일 순.

    total 은 limit/offset 적용 전, 필터만 반영한 전체 건수 — 프론트
    페이지네이션이 다음 페이지 유무를 판단하는 데 쓴다.
    """
    filters = []
    if collection in ("masterpiece", "recent", "world"):
        filters.append(ProGame.collection == collection)
    if q and q.strip():
        like = f"%{q.strip()}%"
        filters.append(
            or_(
                ProGame.black_player.ilike(like),
                ProGame.white_player.ilike(like),
                ProGame.event.ilike(like),
            )
        )
    total = (
        await db.execute(
            select(func.count()).select_from(ProGame).where(*filters)
        )
    ).scalar_one()
    stmt = (
        select(ProGame)
        .where(*filters)
        .order_by(ProGame.game_date.desc().nullslast(), ProGame.id.desc())
        .limit(limit)
        .offset(offset)
    )
    games = (await db.execute(stmt)).scalars().all()
    return ProGameList(
        total=total,
        rows=[ProGameRow.model_validate(g, from_attributes=True) for g in games],
    )


@router.get("/{game_id}", response_model=ProGameDetail)
async def get_pro_game(
    game_id: int,
    _: CurrentSession,
    db: DbSession,
) -> ProGameDetail:
    """프로 기보 상세 — 저장된 SGF를 수순으로 파싱해 함께 반환한다."""
    game = (
        await db.execute(select(ProGame).where(ProGame.id == game_id))
    ).scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="pro_game_not_found")

    parsed = parse_pro_sgf(game.sgf)
    base = ProGameRow.model_validate(game, from_attributes=True)
    return ProGameDetail(
        **base.model_dump(),
        komi=game.komi,
        moves=[
            ProMoveOut(move_number=m.move_number, color=m.color, coord=m.coord)
            for m in parsed.moves
        ],
    )
