from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.models import Game, Move as MoveRow, User
from app.schemas.game import (
    CreateGameRequest,
    GameDetail,
    GameSummary,
    HintMove,
    HintResponse,
    MoveEntry,
)
from app.services.game_service import (
    GameError,
    create_game,
    hint as hint_service,
    resign_game,
)
from app.core.rules.engine import build_sgf
from app.engine_pool import get_cached_state

router = APIRouter(prefix="/api/games", tags=["games"])


async def _fetch_owned_game(db: AsyncSession, game_id: int, user: User) -> Game:
    res = await db.execute(select(Game).where(Game.id == game_id))
    game = res.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="game_not_found")
    if game.user_id != user.id:
        raise HTTPException(status_code=403, detail="forbidden")
    return game


@router.post("", status_code=201, response_model=GameSummary)
async def create(
    body: CreateGameRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GameSummary:
    try:
        game = await create_game(
            db, user=user, ai_rank=body.ai_rank, handicap=body.handicap, user_color=body.user_color
        )
    except GameError as e:
        raise HTTPException(status_code=400, detail=e.code)
    return GameSummary.model_validate(game, from_attributes=True)


@router.get("", response_model=list[GameSummary])
async def list_games(
    status_: str | None = None,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[GameSummary]:
    q = select(Game).where(Game.user_id == user.id).order_by(Game.started_at.desc())
    if status_:
        q = q.where(Game.status == status_)
    q = q.limit(50).offset((page - 1) * 50)
    res = await db.execute(q)
    return [GameSummary.model_validate(g, from_attributes=True) for g in res.scalars().all()]


@router.get("/{game_id}", response_model=GameDetail)
async def get_game(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GameDetail:
    game = await _fetch_owned_game(db, game_id, user)
    res = await db.execute(
        select(MoveRow).where(MoveRow.game_id == game.id).order_by(MoveRow.move_number.asc())
    )
    moves = [
        MoveEntry(
            move_number=m.move_number,
            color=m.color,
            coord=m.coord,
            captures=m.captures,
            is_undone=m.is_undone,
        )
        for m in res.scalars().all()
    ]
    base = GameSummary.model_validate(game, from_attributes=True)
    return GameDetail(**base.model_dump(), moves=moves)


@router.delete("/{game_id}", status_code=204)
async def delete_game(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    game = await _fetch_owned_game(db, game_id, user)
    await db.delete(game)
    await db.commit()
    return Response(status_code=204)


@router.post("/{game_id}/resign", response_model=GameSummary)
async def resign(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GameSummary:
    game = await _fetch_owned_game(db, game_id, user)
    try:
        await resign_game(db, game=game, user=user)
    except GameError as e:
        raise HTTPException(status_code=400, detail=e.code)
    return GameSummary.model_validate(game, from_attributes=True)


@router.get("/{game_id}/sgf", response_class=PlainTextResponse)
async def download_sgf(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> str:
    game = await _fetch_owned_game(db, game_id, user)
    if game.sgf_cache:
        return game.sgf_cache
    state = get_cached_state(game.id)
    if state is None:
        from app.services.game_service import _replay_state as replay
        state = await replay(db, game)
    return build_sgf(state, result=game.result or "")


@router.post("/{game_id}/hint", response_model=HintResponse)
async def hint_endpoint(
    game_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HintResponse:
    game = await _fetch_owned_game(db, game_id, user)
    moves = await hint_service(game)
    return HintResponse(
        hints=[HintMove(move=m.move, winrate=m.winrate, visits=m.visits) for m in moves]
    )
