"""Daily Baduk puzzle — one challenge per day, rotating through a small
hand-curated set. Positions are stored as (color, coord) play sequences
so the rules engine can rebuild the board deterministically on each
request.

The grading flow is:

  1. Replay the position on a fresh GameState.
  2. Run KataGo analyze() on that position to get the "blessed" top moves.
  3. Apply the user's move and ask KataGo for the new winrate.
  4. Compare:
       - "correct" if user's move is in top_moves (or winrate close)
       - "ok" if the move dropped < 5% off best
       - "miss" otherwise
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from app.core.rules.board import BLACK, WHITE, Board
from app.core.rules.engine import GameState, Move, play


@dataclass(frozen=True)
class DailyChallenge:
    id: str
    board_size: int
    # Plays applied in order to reach the puzzle position.
    # Each tuple is (color, coord) where color ∈ {"B","W"} and coord is GTP.
    setup: tuple[tuple[str, str], ...]
    to_move: str   # "B" or "W"
    difficulty: str  # "easy" | "medium" | "hard"
    # Used as i18n key suffix on the frontend, e.g. "daily.prompts.ch001".
    prompt_key: str


# V1 launch set — kept tiny on purpose. The cycle index is derived from
# date so the same puzzle is served to every user on a given day. Replace
# / extend with positions extracted from accumulated games (turning points
# where winrate dropped > 15%) once the analytics pipeline lands.
CHALLENGES: tuple[DailyChallenge, ...] = (
    DailyChallenge(
        id="ch-001",
        board_size=9,
        setup=(
            ("B", "E5"),
            ("W", "C3"),
            ("B", "G7"),
            ("W", "G3"),
            ("B", "C7"),
        ),
        to_move="W",
        difficulty="easy",
        prompt_key="daily.prompts.ch001",
    ),
    DailyChallenge(
        id="ch-002",
        board_size=9,
        setup=(
            ("B", "E5"),
            ("W", "G5"),
            ("B", "E7"),
            ("W", "G7"),
            ("B", "E3"),
            ("W", "G3"),
        ),
        to_move="B",
        difficulty="medium",
        prompt_key="daily.prompts.ch002",
    ),
    DailyChallenge(
        id="ch-003",
        board_size=9,
        setup=(
            ("B", "C5"),
            ("W", "G5"),
            ("B", "E3"),
            ("W", "E7"),
            ("B", "G7"),
            ("W", "C3"),
            ("B", "G3"),
            ("W", "C7"),
        ),
        to_move="B",
        difficulty="hard",
        prompt_key="daily.prompts.ch003",
    ),
)


def daily_index(today: _dt.date | None = None) -> int:
    """Deterministic index into CHALLENGES from today's date. Days since
    Unix epoch modulo the catalog size."""
    today = today or _dt.date.today()
    epoch = _dt.date(1970, 1, 1)
    return (today.toordinal() - epoch.toordinal()) % len(CHALLENGES)


def get_today(today: _dt.date | None = None) -> DailyChallenge:
    return CHALLENGES[daily_index(today)]


def replay_position(challenge: DailyChallenge) -> GameState:
    """Apply the setup plays in order and leave the state with the right
    side-to-move set."""
    state = GameState(board=Board(challenge.board_size), komi=6.5)
    for color, coord in challenge.setup:
        # Setup tuples are authored as raw strings; the rules engine wants
        # the Color literal, which BLACK/WHITE expose.
        c = BLACK if color == "B" else WHITE
        state = play(state, Move(color=c, coord=coord))
    # Force the side-to-move to whatever the puzzle asks — `play` already
    # alternates colours, but the setup may have been authored with an
    # odd number of plays for a given to_move target.
    state.to_move = BLACK if challenge.to_move == "B" else WHITE
    return state
