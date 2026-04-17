from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.katago.strength import SUPPORTED_RANKS

Rank = Literal["18k","15k","12k","10k","7k","5k","3k","1k","1d","3d","5d","7d"]


class CreateGameRequest(BaseModel):
    ai_rank: Rank
    handicap: int = Field(ge=0, le=9)
    user_color: Literal["black", "white"] = "black"


class GameSummary(BaseModel):
    id: int
    ai_rank: str
    handicap: int
    komi: float
    user_color: str
    status: str
    result: str | None
    winner: str | None
    move_count: int
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
