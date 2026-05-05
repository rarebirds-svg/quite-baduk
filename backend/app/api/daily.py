"""Daily challenge endpoints.

Endpoints:

  GET  /api/daily-challenge                 — today's puzzle (legacy)
  GET  /api/daily-challenge/random          — random puzzle within filters
  GET  /api/daily-challenge/catalogue       — option lists (topics, sizes,
                                              difficulties + per-combo
                                              availability counts)
  POST /api/daily-challenge/answer          — grade a candidate move

Grading is a fresh KataGo analyse + a play — no DB persistence, no
per-user attempt log (V1 deliberate non-goal). Anonymous-friendly.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.rules.board import BLACK, WHITE
from app.core.rules.engine import IllegalMoveError, Move, play
from app.deps import CurrentSession
from app.engine_pool import get_adapter
from app.rate_limit import rate_limiter
from app.services.daily_challenge import (
    BOARD_SIZES,
    DIFFICULTIES,
    TOPICS,
    DailyChallenge,
    filter_challenges,
    get_by_id,
    get_today,
    pick_random,
    replay_position,
)

router = APIRouter(prefix="/api/daily-challenge", tags=["daily"])

_ANALYSIS_VISITS = 100


def _serialise(challenge: DailyChallenge) -> dict[str, Any]:
    return {
        "id": challenge.id,
        "board_size": challenge.board_size,
        "setup": [{"color": c, "coord": k} for c, k in challenge.setup],
        "to_move": challenge.to_move,
        "difficulty": challenge.difficulty,
        "topic": challenge.topic,
        "prompt_key": challenge.prompt_key,
    }


@router.get("")
async def todays_challenge(sess: CurrentSession) -> dict[str, Any]:
    """Legacy entry point — returns today's puzzle for the cycle. The
    frontend's "다음 문제" flow uses /random with filters instead."""
    return _serialise(get_today())


# Pydantic-style enum validation via Literal — keeps query parsing tight
# without coupling to a global Enum.
_TopicQ = Literal["opening", "middle_game", "endgame", "life_death"]
_DifficultyQ = Literal["easy", "medium", "hard"]


@router.get("/random")
async def random_challenge(
    sess: CurrentSession,
    board_size: Annotated[int | None, Query(ge=9, le=19)] = None,
    difficulty: Annotated[_DifficultyQ | None, Query()] = None,
    topic: Annotated[_TopicQ | None, Query()] = None,
) -> dict[str, Any]:
    """Random puzzle from the catalogue under the supplied filters. 404
    when no row matches so the UI can surface "이 조합엔 아직 문제 없음"."""
    challenge = pick_random(
        board_size=board_size, difficulty=difficulty, topic=topic
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="no_match")
    return _serialise(challenge)


@router.get("/catalogue")
async def catalogue(sess: CurrentSession) -> dict[str, Any]:
    """Option lists + a sparse availability matrix so the UI can disable
    filter combinations that have no puzzles instead of letting the user
    hit a 404. Avoids surprising dead-ends in the picker."""
    counts: dict[str, int] = {}
    for size in BOARD_SIZES:
        for diff in DIFFICULTIES:
            for topic in TOPICS:
                key = f"{size}|{diff}|{topic}"
                counts[key] = len(
                    filter_challenges(
                        board_size=size, difficulty=diff, topic=topic
                    )
                )
    return {
        "board_sizes": list(BOARD_SIZES),
        "difficulties": list(DIFFICULTIES),
        "topics": list(TOPICS),
        "counts": counts,
    }


class AnswerRequest(BaseModel):
    challenge_id: str
    coord: str = Field(min_length=1, max_length=4)


@router.post("/answer")
async def grade_answer(
    body: AnswerRequest,
    sess: CurrentSession,
) -> dict[str, Any]:
    if not await rate_limiter.check(
        f"daily:{sess.id}", max_hits=30, window_sec=60
    ):
        raise HTTPException(status_code=429, detail="rate_limited")

    # The daily limit is gone — any catalogue id is gradable, not just
    # today's. Lookup is O(1) via the by-id index.
    challenge = get_by_id(body.challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="challenge_not_found")

    state = replay_position(challenge)

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

    user_wr_before = before.winrate
    user_wr_after = 1.0 - after.winrate
    drop = user_wr_before - user_wr_after

    if user_coord in top_coords:
        verdict = "best"
    elif drop < 0.05:
        verdict = "ok"
    elif drop < 0.15:
        verdict = "weak"
    else:
        verdict = "miss"

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
