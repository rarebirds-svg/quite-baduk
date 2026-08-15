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

세션은 어디에서도 요구하지 않는다. GET 3종은 순수 카탈로그 조회라
익명 공개이고, POST /answer만 세션 유무에 따라 레이트리밋 키·한도를
바꾼다 (익명은 IP당 10회/분).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.client_ip import client_ip
from app.core.rules.board import BLACK, WHITE
from app.core.rules.engine import IllegalMoveError, Move, play
from app.deps import OptionalSession
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
async def todays_challenge() -> dict[str, Any]:
    """Legacy entry point — returns today's puzzle for the cycle. The
    frontend's "다음 문제" flow uses /random with filters instead."""
    return _serialise(get_today())


# Pydantic-style enum validation via Literal — keeps query parsing tight
# without coupling to a global Enum.
_TopicQ = Literal[
    "opening", "joseki", "life_death", "tesuji",
    "middle_game", "endgame", "capturing_race",
]
_DifficultyQ = Literal["easy", "medium", "hard"]


@router.get("/random")
async def random_challenge(
    board_size: Annotated[int | None, Query(ge=9, le=19)] = None,
    difficulty: Annotated[_DifficultyQ | None, Query()] = None,
    topic: Annotated[_TopicQ | None, Query()] = None,
    exclude_id: Annotated[str | None, Query(max_length=64)] = None,
) -> dict[str, Any]:
    """Random puzzle from the catalogue under the supplied filters.

    ``exclude_id`` removes one entry from the pool — used so "다음 문제"
    never returns the puzzle the user just solved. Two distinct 404s:
      * "no_match" — the filter has no puzzles at all.
      * "no_other_match" — the filter has only the excluded puzzle. The
        client can surface "이 조합엔 다른 문제가 없어요" without giving
        up on the current screen.
    """
    # Probe with no exclusion so we can distinguish "filter is empty"
    # from "filter has only the excluded id".
    base_match = pick_random(
        board_size=board_size, difficulty=difficulty, topic=topic
    )
    if base_match is None:
        raise HTTPException(status_code=404, detail="no_match")

    challenge = pick_random(
        board_size=board_size,
        difficulty=difficulty,
        topic=topic,
        exclude_id=exclude_id,
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="no_other_match")
    return _serialise(challenge)


@router.get("/catalogue")
async def catalogue() -> dict[str, Any]:
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
    request: Request,
    body: AnswerRequest,
    sess: OptionalSession,
) -> dict[str, Any]:
    # 채점은 KataGo 분석 2회를 태우는 비싼 경로다. 익명 열람은 허용하되
    # 세션 없는 호출은 IP 단위로 훨씬 좁은 한도를 건다.
    if sess is not None:
        allowed = await rate_limiter.check(
            f"daily_answer:{sess.id}", max_hits=30, window_sec=60
        )
    else:
        allowed = await rate_limiter.check(
            f"daily_answer_anon:{client_ip(request)}", max_hits=10, window_sec=60
        )
    if not allowed:
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
