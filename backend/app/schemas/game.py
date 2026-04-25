from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.katago.strength import SUPPORTED_RANKS

Rank = Literal[
    "9k", "8k", "7k", "6k", "5k", "4k", "3k", "2k", "1k",
    "1d", "2d", "3d", "4d", "5d", "6d", "7d", "8d", "9d",
]
AiStyle = Literal[
    "balanced",
    "territorial",
    "influence",
    "combative",
    "speed",
    "classical",
    "rustic",
]


class CreateGameRequest(BaseModel):
    ai_rank: Rank
    ai_style: AiStyle = "balanced"
    ai_player: str | None = None
    handicap: int = Field(ge=0, le=9)
    user_color: Literal["black", "white"] = "black"
    board_size: Literal[9, 13, 19] = 19
    user_rank: Rank | None = None


class GameSummary(BaseModel):
    id: int
    ai_rank: str
    ai_style: str = "balanced"
    ai_player: str | None = None
    handicap: int
    board_size: int
    komi: float
    user_color: str
    status: str
    result: str | None
    winner: str | None
    move_count: int
    undo_count: int = 0
    hint_count: int = 0
    user_nickname: str | None = None
    user_rank: str | None = None
    started_at: datetime
    finished_at: datetime | None


class MoveEntry(BaseModel):
    move_number: int
    color: str
    coord: str | None
    captures: int
    is_undone: bool


class GameDetail(GameSummary):
    moves: list[MoveEntry]


class HintMove(BaseModel):
    move: str
    winrate: float
    visits: int


class HintResponse(BaseModel):
    hints: list[HintMove]


class AnalysisResponse(BaseModel):
    winrate: float
    top_moves: list[HintMove]
    ownership: list[float]
