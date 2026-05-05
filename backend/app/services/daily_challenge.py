"""Daily Baduk puzzle catalogue.

Each puzzle is a (color, coord) play sequence so the rules engine can
rebuild the board deterministically. Puzzles carry a topic + difficulty
+ board size, and the API layer can:

  * pick today's puzzle (legacy daily-challenge behaviour),
  * pick a random puzzle within a filter (used by "다음 문제"),
  * grade a candidate move against KataGo.

The catalogue is hand-curated for V1 launch — once the turning-point
extraction pipeline lands, we'll backfill from accumulated games.
"""
from __future__ import annotations

import datetime as _dt
import random
from dataclasses import dataclass

from app.core.rules.board import BLACK, WHITE, Board
from app.core.rules.engine import GameState, Move, play

# Public-set values. Frontend mirrors these strings.
TOPICS: tuple[str, ...] = ("opening", "middle_game", "endgame", "life_death")
DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")
BOARD_SIZES: tuple[int, ...] = (9, 13, 19)


@dataclass(frozen=True)
class DailyChallenge:
    id: str
    board_size: int
    setup: tuple[tuple[str, str], ...]
    to_move: str            # "B" or "W"
    difficulty: str         # "easy" | "medium" | "hard"
    topic: str              # see TOPICS above
    prompt_key: str         # i18n key suffix consumed by the frontend


# V1 catalogue. Hand-authored so each row is a real, gradable puzzle:
# the answer comes from KataGo's analyze() at request time, not from
# the catalogue, so positions only need to be coherent.
CHALLENGES: tuple[DailyChallenge, ...] = (
    # ── 9x9 ─────────────────────────────────────────────────────────────
    DailyChallenge(
        id="ch-001",
        board_size=9,
        setup=(
            ("B", "E5"), ("W", "C3"), ("B", "G7"),
            ("W", "G3"), ("B", "C7"),
        ),
        to_move="W",
        difficulty="easy",
        topic="opening",
        prompt_key="daily.prompts.ch001",
    ),
    DailyChallenge(
        id="ch-002",
        board_size=9,
        setup=(
            ("B", "E5"), ("W", "G5"), ("B", "E7"),
            ("W", "G7"), ("B", "E3"), ("W", "G3"),
        ),
        to_move="B",
        difficulty="medium",
        topic="middle_game",
        prompt_key="daily.prompts.ch002",
    ),
    DailyChallenge(
        id="ch-003",
        board_size=9,
        setup=(
            ("B", "C5"), ("W", "G5"), ("B", "E3"),
            ("W", "E7"), ("B", "G7"), ("W", "C3"),
            ("B", "G3"), ("W", "C7"),
        ),
        to_move="B",
        difficulty="hard",
        topic="middle_game",
        prompt_key="daily.prompts.ch003",
    ),
    DailyChallenge(
        id="ch-004",
        board_size=9,
        setup=(
            ("B", "E5"), ("W", "C5"), ("B", "G5"),
            ("W", "C3"), ("B", "G3"), ("W", "C7"),
            ("B", "G7"),
        ),
        to_move="W",
        difficulty="easy",
        topic="opening",
        prompt_key="daily.prompts.ch004",
    ),
    DailyChallenge(
        id="ch-005",
        board_size=9,
        # Tight cluster: black wraps a corner; white must find a poke
        # before the corner finishes settling.
        setup=(
            ("B", "C7"), ("W", "D7"), ("B", "C8"),
            ("W", "D8"), ("B", "C6"), ("W", "D6"),
            ("B", "B7"), ("W", "E7"),
        ),
        to_move="B",
        difficulty="medium",
        topic="life_death",
        prompt_key="daily.prompts.ch005",
    ),
    DailyChallenge(
        id="ch-006",
        board_size=9,
        # Endgame-flavoured: stones largely settled; one big yose left.
        setup=(
            ("B", "E5"), ("W", "C3"), ("B", "G7"),
            ("W", "G3"), ("B", "C7"), ("W", "E3"),
            ("B", "C5"), ("W", "G5"), ("B", "E7"),
            ("W", "D2"), ("B", "F8"),
        ),
        to_move="W",
        difficulty="medium",
        topic="endgame",
        prompt_key="daily.prompts.ch006",
    ),
    # ── 13x13 ───────────────────────────────────────────────────────────
    DailyChallenge(
        id="ch-101",
        board_size=13,
        setup=(
            ("B", "D4"), ("W", "K10"), ("B", "K4"),
            ("W", "D10"),
        ),
        to_move="B",
        difficulty="easy",
        topic="opening",
        prompt_key="daily.prompts.ch101",
    ),
    DailyChallenge(
        id="ch-102",
        board_size=13,
        setup=(
            ("B", "D4"), ("W", "K10"), ("B", "K4"),
            ("W", "D10"), ("B", "G7"), ("W", "G4"),
            ("B", "G10"),
        ),
        to_move="W",
        difficulty="medium",
        topic="middle_game",
        prompt_key="daily.prompts.ch102",
    ),
    DailyChallenge(
        id="ch-103",
        board_size=13,
        setup=(
            ("B", "D4"), ("W", "K10"), ("B", "K4"),
            ("W", "D10"), ("B", "D7"), ("W", "K7"),
            ("B", "G3"), ("W", "G11"),
        ),
        to_move="B",
        difficulty="hard",
        topic="middle_game",
        prompt_key="daily.prompts.ch103",
    ),
)

# id → challenge for O(1) lookup in the answer endpoint.
_BY_ID: dict[str, DailyChallenge] = {c.id: c for c in CHALLENGES}


def daily_index(today: _dt.date | None = None) -> int:
    """Deterministic index used by the legacy "today's puzzle" endpoint."""
    today = today or _dt.date.today()
    epoch = _dt.date(1970, 1, 1)
    return (today.toordinal() - epoch.toordinal()) % len(CHALLENGES)


def get_today(today: _dt.date | None = None) -> DailyChallenge:
    return CHALLENGES[daily_index(today)]


def get_by_id(challenge_id: str) -> DailyChallenge | None:
    return _BY_ID.get(challenge_id)


def filter_challenges(
    *,
    board_size: int | None = None,
    difficulty: str | None = None,
    topic: str | None = None,
) -> tuple[DailyChallenge, ...]:
    """Return the subset of the catalogue matching every supplied filter.
    Unset filters are wildcards. Returns the matches in catalogue order."""
    return tuple(
        c for c in CHALLENGES
        if (board_size is None or c.board_size == board_size)
        and (difficulty is None or c.difficulty == difficulty)
        and (topic is None or c.topic == topic)
    )


def pick_random(
    *,
    board_size: int | None = None,
    difficulty: str | None = None,
    topic: str | None = None,
    rng: random.Random | None = None,
) -> DailyChallenge | None:
    """Random pick within the filter. None when no match exists so the
    caller can return a graceful "no puzzle for that combo" response."""
    matches = filter_challenges(
        board_size=board_size, difficulty=difficulty, topic=topic
    )
    if not matches:
        return None
    return (rng or random).choice(matches)


def replay_position(challenge: DailyChallenge) -> GameState:
    """Apply the setup plays in order and leave the state with the right
    side-to-move set."""
    state = GameState(board=Board(challenge.board_size), komi=6.5)
    for color, coord in challenge.setup:
        c = BLACK if color == "B" else WHITE
        state = play(state, Move(color=c, coord=coord))
    state.to_move = BLACK if challenge.to_move == "B" else WHITE
    return state
