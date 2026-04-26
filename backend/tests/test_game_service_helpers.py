"""Unit tests for the pure helpers in game_service — endgame phase
detection and dead-stone inference are easy to drive directly without
spinning up the whole API stack, and they account for ~50 uncovered
statements in coverage."""
from __future__ import annotations

from app.core.rules.board import BLACK, EMPTY, WHITE, Board
from app.core.rules.engine import GameState, Move
from app.services.game_service import (
    _dead_stones_from_ownership,
    _endgame_phase_from_ownership,
)


def _empty_state(size: int = 9) -> GameState:
    return GameState(board=Board(size))


def test_endgame_phase_false_when_too_few_moves() -> None:
    """Below the move-count floor (≈ board side), nothing counts as endgame."""
    state = _empty_state(9)
    # Just 2 moves — nowhere near 9 (size).
    state.move_history = [
        Move(color=BLACK, coord="E5"),
        Move(color=WHITE, coord="E6"),
    ]
    ownership = [0.0] * 81
    assert _endgame_phase_from_ownership(state, ownership) is False


def test_endgame_phase_true_when_ownership_resolved() -> None:
    """Many moves played, all ownership values strongly settled → endgame."""
    state = _empty_state(9)
    # Synth move history of length >= 9 to clear the move-count floor.
    state.move_history = [Move(color=BLACK, coord="A1") for _ in range(20)]
    # All points strongly black-owned (|val| > 0.35) → no contested emptiness.
    ownership = [0.9] * 81
    assert _endgame_phase_from_ownership(state, ownership) is True


def test_endgame_phase_false_when_too_many_contested_points() -> None:
    """Even with enough moves, a board full of |ownership| < 0.35 stays open."""
    state = _empty_state(9)
    state.move_history = [Move(color=BLACK, coord="A1") for _ in range(20)]
    ownership = [0.1] * 81  # all contested
    assert _endgame_phase_from_ownership(state, ownership) is False


def test_dead_stones_from_ownership_marks_opposite_color() -> None:
    """A black stone sitting on a square the engine assigns strongly to White
    is dead from Black's perspective."""
    state = _empty_state(9)
    state.board = state.board.place(2, 2, BLACK)
    ownership = [0.0] * 81
    # (x=2, y=2) → index 2*9 + 2 = 20. Strongly White-owned (-0.9).
    ownership[20] = -0.9
    dead = _dead_stones_from_ownership(state, ownership)
    assert (2, 2) in dead


def test_dead_stones_from_ownership_keeps_alive_when_color_matches() -> None:
    state = _empty_state(9)
    state.board = state.board.place(2, 2, BLACK)
    ownership = [0.0] * 81
    ownership[20] = 0.9  # strongly Black-owned, matches the stone
    dead = _dead_stones_from_ownership(state, ownership)
    assert (2, 2) not in dead


def test_dead_stones_returns_empty_when_ownership_size_mismatched() -> None:
    """Wrong-size ownership vector (defensive — KataGo restart could send a
    truncated payload) returns empty rather than crashing."""
    state = _empty_state(9)
    state.board = state.board.place(2, 2, BLACK)
    bad_ownership = [0.0] * 10  # not 81
    assert _dead_stones_from_ownership(state, bad_ownership) == set()


def test_dead_stones_skips_empty_squares() -> None:
    """Even strongly-owned empty points must not be marked dead."""
    state = _empty_state(9)
    # Don't place anything — all squares empty.
    ownership = [0.99] * 81
    assert _dead_stones_from_ownership(state, ownership) == set()


def test_dead_stones_white_stone_in_black_territory() -> None:
    state = _empty_state(9)
    state.board = state.board.place(5, 5, WHITE)
    ownership = [0.0] * 81
    ownership[5 * 9 + 5] = 0.85  # strongly Black-owned
    dead = _dead_stones_from_ownership(state, ownership)
    assert (5, 5) in dead
    assert state.board.get(5, 5) == WHITE  # still on board
    _ = EMPTY  # silence unused-import warning if ruff later objects
