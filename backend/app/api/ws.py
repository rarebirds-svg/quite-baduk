from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Cookie, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models import Game, User
from app.security import decode_token
from app.services.game_service import GameError, place_move, undo_move
from app.core.rules.engine import GameState

router = APIRouter(tags=["ws"])

_connections: dict[int, WebSocket] = {}


def _serialize_board(state: GameState) -> str:
    """Flatten to a size*size char string of '.', 'B', 'W'."""
    cells: list[str] = []
    b = state.board
    for y in range(b.size):
        for x in range(b.size):
            cells.append(b.get(x, y))
    return "".join(cells)


async def _state_payload(state: GameState, move_count: int) -> dict[str, Any]:
    return {
        "type": "state",
        "board": _serialize_board(state),
        "board_size": state.board.size,
        "to_move": state.to_move,
        "move_count": move_count,
        "captures": state.captures,
    }


async def _authenticate_ws(access_token: str | None, db: AsyncSession) -> User | None:
    if not access_token:
        return None
    try:
        payload = decode_token(access_token)
        if payload.get("type") != "access":
            return None
        user_id = int(payload["sub"])
    except Exception:
        return None
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()


@router.websocket("/api/ws/games/{game_id}")
async def ws_game(
    websocket: WebSocket,
    game_id: int,
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await _authenticate_ws(access_token, db)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    res = await db.execute(select(Game).where(Game.id == game_id))
    game = res.scalar_one_or_none()
    if game is None or game.user_id != user.id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Single session policy
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
        # Send initial state
        from app.engine_pool import get_cached_state
        from app.services.game_service import _replay_state

        state = get_cached_state(game.id)
        if state is None:
            state = await _replay_state(db, game)
        await websocket.send_json(await _state_payload(state, game.move_count))

        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")
            try:
                if mtype == "move":
                    coord = msg.get("coord", "")
                    result = await place_move(db, game=game, user=user, coord=coord)
                    await websocket.send_json(await _state_payload(result.game_state, game.move_count))
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
                    result = await place_move(db, game=game, user=user, coord="pass")
                    await websocket.send_json(await _state_payload(result.game_state, game.move_count))
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
                    new_state = await undo_move(db, game=game, user=user, steps=steps)
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
