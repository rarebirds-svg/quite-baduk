from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi import APIRouter, Cookie, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rules.engine import GameState
from app.deps import COOKIE_SESSION, get_db
from app.models import Game, Session
from app.services.game_service import GameError, place_move, undo_move

router = APIRouter(tags=["ws"])

_connections: dict[int, WebSocket] = {}


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
    return payload


async def _authenticate_ws(token: str | None, db: AsyncSession) -> Session | None:
    if not token:
        return None
    res = await db.execute(select(Session).where(Session.token == token))
    sess = res.scalar_one_or_none()
    if sess is None:
        return None
    sess.last_seen_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
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

        await websocket.send_json(await _state_payload(state, game.move_count))

        try:
            from app.core.rules.board import BLACK as _BLACK
            from app.engine_pool import get_adapter

            adapter = get_adapter()
            await adapter.start()
            analysis = await adapter.analyze(side=state.to_move, max_visits=32)
            wr = float(analysis.winrate)
            winrate_black_init = wr if state.to_move == _BLACK else 1.0 - wr
            await websocket.send_json(
                {"type": "winrate", "winrate_black": winrate_black_init}
            )
        except Exception:
            pass

        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")
            try:
                if mtype == "move":
                    coord = msg.get("coord", "")
                    result = await place_move(db, game=game, session=sess, coord=coord)
                    await websocket.send_json(
                        await _state_payload(
                            result.game_state, game.move_count, result.winrate_black
                        )
                    )
                    if result.ai_move is not None:
                        await websocket.send_json({
                            "type": "ai_move",
                            "coord": result.ai_move,
                            "captures": result.captured_by_ai,
                        })
                    if result.game_over:
                        await websocket.send_json({
                            "type": "game_over",
                            "result": result.result_str or "",
                            "winner": game.winner or "",
                        })
                elif mtype == "pass":
                    result = await place_move(db, game=game, session=sess, coord="pass")
                    await websocket.send_json(
                        await _state_payload(
                            result.game_state, game.move_count, result.winrate_black
                        )
                    )
                    if result.ai_move is not None:
                        await websocket.send_json({
                            "type": "ai_move",
                            "coord": result.ai_move,
                            "captures": result.captured_by_ai,
                        })
                    if result.game_over:
                        await websocket.send_json({
                            "type": "game_over",
                            "result": result.result_str or "",
                            "winner": game.winner or "",
                        })
                elif mtype == "undo":
                    steps = int(msg.get("steps", 2))
                    new_state = await undo_move(db, game=game, session=sess, steps=steps)
                    await websocket.send_json(await _state_payload(new_state, game.move_count))
                else:
                    await websocket.send_json({"type": "error", "code": "UNKNOWN_MESSAGE"})
            except GameError as e:
                await websocket.send_json({"type": "error", "code": e.code, "detail": e.detail})
    except WebSocketDisconnect:
        pass
    finally:
        if _connections.get(game_id) is websocket:
            _connections.pop(game_id, None)
