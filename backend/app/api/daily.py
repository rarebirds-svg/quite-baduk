"""Daily challenge endpoints.

Two operations:

  GET  /api/daily-challenge          — returns today's puzzle (id, board,
                                       setup plays, side-to-move, prompt key).
  POST /api/daily-challenge/answer   — grades a candidate move in real time.

The grading is a fresh KataGo analyse + a play — no DB persistence, no
per-user attempt log (V1 deliberate non-goal). Anonymous-friendly.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.rules.board import BLACK, WHITE
from app.core.rules.engine import IllegalMoveError, Move, play
from app.deps import CurrentSession
from app.engine_pool import get_adapter
from app.rate_limit import rate_limiter
from app.services.daily_challenge import (
    DailyChallenge,
    get_today,
    replay_position,
)

router = APIRouter(prefix="/api/daily-challenge", tags=["daily"])

# Reuse a single shared adapter slot for daily-challenge analyses. The
# challenges are stateless (no game_id), so we route through the legacy
# get_adapter() (no-arg) which returns the pool's least-loaded adapter.
_ANALYSIS_VISITS = 100


def _serialise(challenge: DailyChallenge) -> dict[str, Any]:
    return {
        "id": challenge.id,
        "board_size": challenge.board_size,
        "setup": [{"color": c, "coord": k} for c, k in challenge.setup],
        "to_move": challenge.to_move,
        "difficulty": challenge.difficulty,
        "prompt_key": challenge.prompt_key,
    }


@router.get("")
async def todays_challenge(sess: CurrentSession) -> dict[str, Any]:
    return _serialise(get_today())


class AnswerRequest(BaseModel):
    challenge_id: str
    coord: str = Field(min_length=1, max_length=4)


@router.post("/answer")
async def grade_answer(
    body: AnswerRequest,
    sess: CurrentSession,
) -> dict[str, Any]:
    # 30/min/session — generous enough for repeat tries, tight enough that
    # a script can't grind through the puzzle space.
    if not await rate_limiter.check(
        f"daily:{sess.id}", max_hits=30, window_sec=60
    ):
        raise HTTPException(status_code=429, detail="rate_limited")

    challenge = get_today()
    if body.challenge_id != challenge.id:
        # Race: user opened yesterday's puzzle, submitted today.
        raise HTTPException(status_code=410, detail="challenge_rolled_over")

    state = replay_position(challenge)

    # Adapter for the puzzle. We seed it with the setup so analyze() reads
    # the same position the rules engine has.
    adapter = await get_adapter(None)
    await adapter.start()
    await adapter.clear_board()
    await adapter.set_boardsize(challenge.board_size)
    await adapter.set_komi(state.komi)
    for color, coord in challenge.setup:
        await adapter.play(color, coord)

    side = BLACK if challenge.to_move == "B" else WHITE
    try:
        before = await adapter.analyze(side=side, max_visits=_ANALYSIS_VISITS)
    except Exception as e:
        raise HTTPException(status_code=503, detail="analysis_failed") from e

    top_coords = [m.move.upper() for m in before.top_moves[:5]]
    user_coord = body.coord.upper()

    # Apply the user's move via the rules engine — rejects suicide, ko,
    # occupied — and via the adapter so the analyzer can re-read the
    # position with the new stone.
    user_side = BLACK if challenge.to_move == "B" else WHITE
    try:
        new_state = play(state, Move(color=user_side, coord=body.coord))
    except IllegalMoveError as e:
        return {
            "verdict": "illegal",
            "detail": str(e),
            "top_moves": top_coords,
            "winrate_before": before.winrate,
        }

    try:
        await adapter.play(challenge.to_move, body.coord)
        opp_side = WHITE if challenge.to_move == "B" else BLACK
        after = await adapter.analyze(side=opp_side, max_visits=_ANALYSIS_VISITS)
    except Exception as e:
        raise HTTPException(status_code=503, detail="analysis_failed") from e

    # Normalise both winrates to the answerer's perspective so the drop is
    # signed intuitively (positive drop = user's move was bad).
    user_wr_before = before.winrate
    user_wr_after = 1.0 - after.winrate  # opp's POV → user's POV
    drop = user_wr_before - user_wr_after

    if user_coord in top_coords:
        verdict = "best"
    elif drop < 0.05:
        verdict = "ok"
    elif drop < 0.15:
        verdict = "weak"
    else:
        verdict = "miss"

    # Strictly an opening-style position has no captures; pass it through
    # for completeness in case the catalogue grows fighting puzzles later.
    user_captures = new_state.captures.get(challenge.to_move, 0) - state.captures.get(
        challenge.to_move, 0
    )

    return {
        "verdict": verdict,
        "winrate_before": user_wr_before,
        "winrate_after": user_wr_after,
        "drop": drop,
        "top_moves": top_coords,
        "user_captures": user_captures,
    }
