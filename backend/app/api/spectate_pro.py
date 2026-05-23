# 프로 기보 공개 관전 API — 명국선·최근 기보 목록과 수순 상세를 제공한다.
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, select

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
) -> ProGameList:
    """프로 기보 목록. 닉네임 세션 필요. 최신 대국일 순."""
    stmt = select(ProGame).order_by(
        ProGame.game_date.desc().nullslast(), ProGame.id.desc()
    )
    if collection in ("masterpiece", "recent"):
        stmt = stmt.where(ProGame.collection == collection)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                ProGame.black_player.ilike(like),
                ProGame.white_player.ilike(like),
                ProGame.event.ilike(like),
            )
        )
    stmt = stmt.limit(limit)
    games = (await db.execute(stmt)).scalars().all()
    return ProGameList(
        rows=[ProGameRow.model_validate(g, from_attributes=True) for g in games]
    )


@router.get("/sitemap")
async def pro_sitemap(db: DbSession) -> list[dict[str, Any]]:
    """SEO sitemap용 경량 엔드포인트 — 전체 pro_games의 id·created_at만 반환한다."""
    result = await db.execute(
        select(ProGame.id, ProGame.created_at).order_by(ProGame.id)
    )
    return [
        {"id": row.id, "created_at": row.created_at.isoformat()}
        for row in result.all()
    ]


@router.get("/{game_id}", response_model=ProGameDetail)
async def get_pro_game(
    game_id: int,
    db: DbSession,
) -> ProGameDetail:
    """프로 기보 상세 — 저장된 SGF를 수순으로 파싱해 함께 반환한다.
    공개 endpoint(세션 무관) — SEO 메타·OG 카드 server-side fetch를 위해서.
    pro_games는 CWI 퍼블릭 도메인 콘텐츠라 인증 게이트 불필요.
    """
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
