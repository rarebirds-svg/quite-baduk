# 프로 기보 공개 관전 API — 명국선·세계기전·최근 기보 목록과 수순 상세를 제공한다.
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select

from app.core.pro.monthly_pick import InvalidYearMonth, pick_for_month
from app.core.pro.themes import THEMES, theme_by_slug, theme_query_clause
from app.core.sgf.import_sgf import parse_pro_sgf
from app.deps import DbSession
from app.models import ProGame
from app.schemas.datetime_utc import utc_iso

router = APIRouter(prefix="/api/spectate/pro", tags=["spectate"])


class ProGameRow(BaseModel):
    id: int
    collection: str
    black_player: str
    white_player: str
    black_rank: str | None
    white_rank: str | None
    event: str | None
    round: str | None
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
    db: DbSession,
    collection: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ProGameList:
    """프로 기보 목록. 비로그인 공개. 최신 대국일 순.

    total 은 limit/offset 적용 전, 필터만 반영한 전체 건수 — 프론트
    페이지네이션이 다음 페이지 유무를 판단하는 데 쓴다.
    """
    filters = []
    if collection == "recent":
        filters.append(ProGame.collection.in_(("recent", "cwi")))
    elif collection in ("masterpiece", "world"):
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


@router.get("/sitemap")
async def pro_sitemap(db: DbSession) -> list[dict[str, Any]]:
    """SEO sitemap용 경량 엔드포인트 — 전체 pro_games의 id·created_at만 반환한다."""
    result = await db.execute(
        select(ProGame.id, ProGame.created_at).order_by(ProGame.id)
    )
    return [
        {"id": row.id, "created_at": utc_iso(row.created_at)}
        for row in result.all()
    ]


@router.get("/themes")
async def list_themes(db: DbSession) -> list[dict[str, Any]]:
    """테마 카탈로그 + 각 테마의 게임 수."""
    out: list[dict[str, Any]] = []
    for t in THEMES:
        clause = theme_query_clause(t["slug"])
        if clause is None:
            continue
        result = await db.execute(
            select(ProGame.id).where(clause)
        )
        count = len(result.scalars().all())
        out.append({
            "slug": t["slug"],
            "label": t["label"],
            "description": t["description"],
            "count": count,
        })
    return out


@router.get("/theme/{slug}")
async def theme_detail(slug: str, db: DbSession) -> dict[str, Any]:
    """테마별 게임 목록 + 메타. 알 수 없는 slug는 404."""
    theme = theme_by_slug(slug)
    if theme is None:
        raise HTTPException(status_code=404, detail="theme_not_found")
    clause = theme_query_clause(slug)
    assert clause is not None  # slug was validated above
    result = await db.execute(
        select(ProGame).where(clause).order_by(ProGame.game_date.desc(), ProGame.id)
    )
    games = result.scalars().all()
    return {
        "slug": theme["slug"],
        "label": theme["label"],
        "description": theme["description"],
        "total": len(games),
        "games": [
            {
                "id": g.id,
                "black_player": g.black_player,
                "white_player": g.white_player,
                "event": g.event,
                "game_date": g.game_date.isoformat() if g.game_date else None,
                "result": g.result,
            }
            for g in games
        ],
    }


@router.get("/pick/monthly/{yyyymm}")
async def pick_monthly(yyyymm: str, db: DbSession) -> dict[str, Any]:
    """결정적 월간 픽. yyyymm=YYYY-MM. 후보 0이면 404, 형식 오류 400."""
    try:
        picked_id = await pick_for_month(db, yyyymm)
    except InvalidYearMonth as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if picked_id is None:
        raise HTTPException(status_code=404, detail="no_candidates")
    game = (
        await db.execute(select(ProGame).where(ProGame.id == picked_id))
    ).scalar_one()
    return {
        "yyyymm": yyyymm,
        "id": game.id,
        "black_player": game.black_player,
        "white_player": game.white_player,
        "event": game.event,
        "game_date": game.game_date.isoformat() if game.game_date else None,
        "result": game.result,
    }


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
