"""Public Rules Engine API -- game state, move validation, scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.core.rules.board import BLACK, EMPTY, WHITE, Board
from app.core.rules.captures import is_suicide, place_with_captures
from app.core.rules.ko import KoState, is_ko_violation
from app.core.rules.scoring import ScoreResult, score_game
from app.core.rules.sgf_coord import gtp_to_xy, xy_to_gtp

Color = Literal["B", "W"]


@dataclass
class Move:
    color: Color
    coord: str | None  # GTP string like "Q16", "pass", or None (resign)


class IllegalMoveError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass
class GameState:
    board: Board = field(default_factory=lambda: Board(19))
    to_move: Color = BLACK
    captures: dict[str, int] = field(default_factory=lambda: {BLACK: 0, WHITE: 0})
    ko_state: KoState = field(default_factory=KoState)
    move_history: list[Move] = field(default_factory=list)
    consecutive_passes: int = 0
    komi: float = 6.5


def _opponent(color: Color) -> Color:
    return WHITE if color == BLACK else BLACK  # type: ignore[return-value]


def play(state: GameState, move: Move) -> GameState:
    """Apply a move to the game state.

    Raises IllegalMoveError with codes:
      NOT_YOUR_TURN, OCCUPIED, OUT_OF_BOUNDS, ILLEGAL_SUICIDE, ILLEGAL_KO
    """
    if move.color != state.to_move:
        raise IllegalMoveError("NOT_YOUR_TURN", f"expected {state.to_move}")

    if move.coord is None:
        # resign -- just record it
        return GameState(
            board=state.board,
            to_move=_opponent(move.color),
            captures=dict(state.captures),
            ko_state=state.ko_state,
            move_history=state.move_history + [move],
            consecutive_passes=0,
            komi=state.komi,
        )

    if move.coord.lower() == "pass":
        return GameState(
            board=state.board,
            to_move=_opponent(move.color),
            captures=dict(state.captures),
            ko_state=state.ko_state.update(state.board),
            move_history=state.move_history + [move],
            consecutive_passes=state.consecutive_passes + 1,
            komi=state.komi,
        )

    try:
        xy = gtp_to_xy(move.coord, state.board.size)
    except ValueError as e:
        raise IllegalMoveError("OUT_OF_BOUNDS", move.coord) from e
    if xy is None:  # pragma: no cover — pass already handled above
        raise IllegalMoveError("INVALID_COORD", move.coord)
    x, y = xy

    if not state.board.in_bounds(x, y):  # pragma: no cover — gtp_to_xy validates range
        raise IllegalMoveError("OUT_OF_BOUNDS", move.coord)

    if state.board.get(x, y) != EMPTY:
        raise IllegalMoveError("OCCUPIED", move.coord)

    if is_suicide(state.board, x, y, move.color):
        raise IllegalMoveError("ILLEGAL_SUICIDE", move.coord)

    new_board, captured = place_with_captures(state.board, x, y, move.color)

    if is_ko_violation(state.ko_state, new_board):
        raise IllegalMoveError("ILLEGAL_KO", move.coord)

    new_captures = dict(state.captures)
    new_captures[move.color] = new_captures.get(move.color, 0) + captured

    return GameState(
        board=new_board,
        to_move=_opponent(move.color),
        captures=new_captures,
        ko_state=state.ko_state.update(state.board),
        move_history=state.move_history + [move],
        consecutive_passes=0,
        komi=state.komi,
    )


def pass_move(state: GameState, color: Color) -> GameState:
    return play(state, Move(color=color, coord="pass"))


def is_game_over(state: GameState) -> bool:
    return state.consecutive_passes >= 2


def score(state: GameState, dead_stones: set[tuple[int, int]] | None = None) -> ScoreResult:
    return score_game(
        state.board,
        state.captures.get(BLACK, 0),
        state.captures.get(WHITE, 0),
        state.komi,
        dead_stones,
    )


def build_sgf(state: GameState, result: str = "") -> str:
    """Build a minimal SGF string from the game state."""
    komi_str = str(state.komi)
    moves_sgf = ""
    for move in state.move_history:
        if move.coord is None:
            continue  # resign -- no SGF node
        if move.coord.lower() == "pass":
            moves_sgf += f";{move.color}[]"
        else:
            xy = gtp_to_xy(move.coord, state.board.size)
            if xy is None:  # pragma: no cover — pass already handled above
                continue
            x, y = xy
            # SGF uses letters a-s for columns and rows (a=top)
            col = chr(ord("a") + x)
            row = chr(ord("a") + y)
            moves_sgf += f";{move.color}[{col}{row}]"
    result_prop = f"RE[{result}]" if result else ""
    return f"(;GM[1]FF[4]SZ[{state.board.size}]KM[{komi_str}]{result_prop}{moves_sgf})"
