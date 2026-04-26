from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, Cookie, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy import update as _sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rules.engine import GameState
from app.deps import COOKIE_SESSION, get_db
from app.models import Game, Session
from app.services.game_service import GameError, place_move, score_by_request, undo_move

router = APIRouter(tags=["ws"])

_connections: dict[int, WebSocket] = {}


def _serialize_points(pts: frozenset[tuple[int, int]]) -> list[list[int]]:
    """Convert a frozenset of (x, y) coords to JSON-friendly [[x, y], ...]."""
    return [[x, y] for (x, y) in sorted(pts)]


def _serialize_board(state: GameState) -> str:
    cells: list[str] = []
    b = state.board
    for y in range(b.size):
        for x in range(b.size):
            cells.append(b.get(x, y))
    return "".join(cells)


async def _state_payload(
    state: GameState,
    move_count: int,
    winrate_black: float | None = None,
    undo_count: int | None = None,
    score_lead_black: float | None = None,
    endgame_phase: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "state",
        "board": _serialize_board(state),
        "board_size": state.board.size,
        "to_move": state.to_move,
        "move_count": move_count,
        "captures": state.captures,
    }
    if winrate_black is not None:
        payload["winrate_black"] = winrate_black
    if undo_count is not None:
        payload["undo_count"] = undo_count
    if score_lead_black is not None:
        payload["score_lead_black"] = score_lead_black
    if endgame_phase is not None:
        payload["endgame_phase"] = endgame_phase
    return payload


async def _authenticate_ws(token: str | None, db: AsyncSession) -> Session | None:
    if not token:
        return None
    res = await db.execute(select(Session).where(Session.token == token))
    sess = res.scalar_one_or_none()
    if sess is None:
        return None
    # Direct UPDATE so a concurrent DELETE (logout, idle purge) doesn't
    # trigger SQLAlchemy's optimistic-lock StaleDataError.
    upd = await db.execute(
        _sa_update(Session)
        .where(Session.id == sess.id)
        .values(last_seen_at=dt.datetime.now(dt.UTC))
    )
    await db.commit()
    if upd.rowcount == 0:
        return None
    return sess


@router.websocket("/api/ws/games/{game_id}")
async def ws_game(
    websocket: WebSocket,
    game_id: int,
    baduk_session: str | None = Cookie(default=None, alias=COOKIE_SESSION),
    db: AsyncSession = Depends(get_db),
) -> None:
    sess = await _authenticate_ws(baduk_session, db)
    if sess is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    res = await db.execute(select(Game).where(Game.id == game_id))
    game = res.scalar_one_or_none()
    if game is None or game.session_id != sess.id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    existing = _connections.get(game_id)
    if existing is not None:
        try:
            await existing.send_json({"type": "error", "code": "SESSION_REPLACED"})
            await existing.close()
        except Exception:
            pass

    await websocket.accept()
    _connections[game_id] = websocket

    try:
        from app.engine_pool import get_cached_state
        from app.services.game_service import _replay_state

        state = get_cached_state(game.id)
        if state is None:
            state = await _replay_state(db, game)

        await websocket.send_json(
            await _state_payload(state, game.move_count, undo_count=game.undo_count)
        )

        try:
            from app.core.rules.board import BLACK as _BLACK
            from app.engine_pool import get_adapter

            adapter = get_adapter()
            await adapter.start()
            analysis = await adapter.analyze(side=state.to_move, max_visits=32)
            wr = float(analysis.winrate)
            sl = float(analysis.score_lead)
            winrate_black_init = wr if state.to_move == _BLACK else 1.0 - wr
            score_lead_black_init = sl if state.to_move == _BLACK else -sl
            await websocket.send_json(
                {
                    "type": "winrate",
                    "winrate_black": winrate_black_init,
                    "score_lead_black": score_lead_black_init,
                }
            )
        except Exception:
            pass

        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")
            try:
                if mtype in ("move", "pass"):
                    coord = msg.get("coord", "") if mtype == "move" else "pass"

                    async def _flush_user_state(
                        user_state: GameState, _user_captures: int
                    ) -> None:
                        await websocket.send_json(
                            await _state_payload(
                                user_state, game.move_count, undo_count=game.undo_count
                            )
                        )

                    result = await place_move(
                        db,
                        game=game,
                        session=sess,
                        coord=coord,
                        on_user_applied=_flush_user_state,
                    )
                    await websocket.send_json(
                        await _state_payload(
                            result.game_state,
                            game.move_count,
                            result.winrate_black,
                            undo_count=game.undo_count,
                            score_lead_black=result.score_lead_black,
                            endgame_phase=result.endgame_phase,
                        )
                    )
                    if result.ai_move is not None:
                        await websocket.send_json({
                            "type": "ai_move",
                            "coord": result.ai_move,
                            "captures": result.captured_by_ai,
                        })
                    # If the AI's pass triggered an automatic scoring, ship
                    # the breakdown before the game_over event so the client
                    # can open the scoring modal and know how the game ended.
                    if result.ai_passed_scored is not None:
                        d = result.ai_passed_scored
                        await websocket.send_json({
                            "type": "score_result",
                            "black_territory": d.black_territory,
                            "white_territory": d.white_territory,
                            "black_captures": d.black_captures,
                            "white_captures": d.white_captures,
                            "komi": d.komi,
                            "black_score": d.black_score,
                            "white_score": d.white_score,
                            "winner": d.winner,
                            "margin": d.margin,
                            "result": d.result_str,
                            "reason": "ai_passed",
                            "black_points": _serialize_points(d.black_points),
                            "white_points": _serialize_points(d.white_points),
                            "dame_points": _serialize_points(d.dame_points),
                            "dead_stones": _serialize_points(d.dead_stones),
                        })
                    if result.game_over:
                        # Annotate how the game ended so the client can pick
                        # the right message. "ai_resigned" triggers a special
                        # modal; "ai_passed" uses the scoring breakdown;
                        # other cases fall through to the generic result.
                        reason = None
                        if game.status == "resigned" and game.winner == "user":
                            reason = "ai_resigned"
                        elif result.ai_passed_scored is not None:
                            reason = "ai_passed"
                        payload: dict[str, Any] = {
                            "type": "game_over",
                            "result": result.result_str or "",
                            "winner": game.winner or "",
                        }
                        if reason is not None:
                            payload["reason"] = reason
                        await websocket.send_json(payload)
                elif mtype == "score_request":
                    detail = await score_by_request(db, game=game, session=sess)
                    await websocket.send_json({
                        "type": "score_result",
                        "black_territory": detail.black_territory,
                        "white_territory": detail.white_territory,
                        "black_captures": detail.black_captures,
                        "white_captures": detail.white_captures,
                        "komi": detail.komi,
                        "black_score": detail.black_score,
                        "white_score": detail.white_score,
                        "winner": detail.winner,
                        "margin": detail.margin,
                        "result": detail.result_str,
                        "black_points": _serialize_points(detail.black_points),
                        "white_points": _serialize_points(detail.white_points),
                        "dame_points": _serialize_points(detail.dame_points),
                        "dead_stones": _serialize_points(detail.dead_stones),
                    })
                    await websocket.send_json({
                        "type": "game_over",
                        "result": detail.result_str,
                        "winner": game.winner or "",
                    })
                elif mtype == "undo":
                    steps = int(msg.get("steps", 2))
                    new_state = await undo_move(db, game=game, session=sess, steps=steps)
                    await websocket.send_json(
                        await _state_payload(
                            new_state, game.move_count, undo_count=game.undo_count
                        )
                    )
                else:
                    await websocket.send_json({"type": "error", "code": "UNKNOWN_MESSAGE"})
            except GameError as e:
                await websocket.send_json({"type": "error", "code": e.code, "detail": e.detail})
    except WebSocketDisconnect:
        pass
    finally:
        if _connections.get(game_id) is websocket:
            _connections.pop(game_id, None)
