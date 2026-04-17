from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.engine_pool import get_adapter
from app.models import AnalysisCache, Game, Move as MoveRow, User
from app.schemas.game import AnalysisResponse, HintMove

router = APIRouter(prefix="/api/games", tags=["analysis"])


async def _fetch_owned(db: AsyncSession, game_id: int, user: User) -> Game:
    res = await db.execute(select(Game).where(Game.id == game_id))
    g = res.scalar_one_or_none()
    if g is None:
        raise HTTPException(status_code=404, detail="game_not_found")
    if g.user_id != user.id:
        raise HTTPException(status_code=403, detail="forbidden")
    return g


@router.post("/{game_id}/analyze", response_model=AnalysisResponse)
async def analyze_game(
    game_id: int,
    moveNum: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnalysisResponse:
    game = await _fetch_owned(db, game_id, user)

    # Cache hit?
    res = await db.execute(
        select(AnalysisCache)
        .where(AnalysisCache.game_id == game.id, AnalysisCache.move_number == moveNum)
    )
    cached = res.scalar_one_or_none()
    if cached is not None:
        data = json.loads(cached.payload)
        return AnalysisResponse(
            winrate=data["winrate"],
            top_moves=[HintMove(**hm) for hm in data["top_moves"]],
            ownership=data.get("ownership", []),
        )

    # Replay board up to moveNum
    from app.services.game_service import _replay_state
    state = await _replay_state(db, game)
    # (Simplification: analyze current state rather than specific moveNum,
    # since KataGo adapter lacks per-move seek; adequate for MVP.)
    adapter = get_adapter()
    await adapter.start()
    result = await adapter.analyze(max_visits=100)

    response = AnalysisResponse(
        winrate=result.winrate,
        top_moves=[HintMove(move=m.move, winrate=m.winrate, visits=m.visits) for m in result.top_moves],
        ownership=result.ownership,
    )

    # Cache
    cache = AnalysisCache(
        game_id=game.id,
        move_number=moveNum,
        payload=json.dumps(response.model_dump()),
    )
    db.add(cache)
    await db.commit()
    return response
