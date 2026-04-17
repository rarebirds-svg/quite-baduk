from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class WSMoveIn(BaseModel):
    type: Literal["move"] = "move"
    coord: str


class WSPassIn(BaseModel):
    type: Literal["pass"] = "pass"


class WSUndoIn(BaseModel):
    type: Literal["undo"] = "undo"
    steps: int = 2


class WSStateOut(BaseModel):
    type: Literal["state"] = "state"
    board: str  # 361-char flat string of '.', 'B', 'W'
    to_move: str
    move_count: int
    captures: dict[str, int]


class WSAIMoveOut(BaseModel):
    type: Literal["ai_move"] = "ai_move"
    coord: str
    captures: int


class WSGameOverOut(BaseModel):
    type: Literal["game_over"] = "game_over"
    result: str
    winner: str


class WSErrorOut(BaseModel):
    type: Literal["error"] = "error"
    code: str
    detail: str | None = None
