import pytest
from app.core.rules.board import BLACK, WHITE, Board
from app.core.rules.engine import (
    GameState,
    IllegalMoveError,
    Move,
    build_sgf,
    is_game_over,
    pass_move,
    play,
    score,
)


def test_initial_state():
    state = GameState()
    assert state.to_move == BLACK
    assert state.consecutive_passes == 0
    assert state.captures == {BLACK: 0, WHITE: 0}


def test_play_move():
    state = GameState()
    new_state = play(state, Move(color=BLACK, coord="Q16"))
    assert new_state.to_move == WHITE
    assert new_state.consecutive_passes == 0
    assert len(new_state.move_history) == 1


def test_play_wrong_turn():
    state = GameState()
    with pytest.raises(IllegalMoveError) as exc_info:
        play(state, Move(color=WHITE, coord="Q16"))
    assert exc_info.value.code == "NOT_YOUR_TURN"


def test_play_occupied():
    state = GameState()
    state = play(state, Move(color=BLACK, coord="Q16"))
    state = play(state, Move(color=WHITE, coord="D4"))
    with pytest.raises(IllegalMoveError) as exc_info:
        play(state, Move(color=BLACK, coord="Q16"))
    assert exc_info.value.code == "OCCUPIED"


def test_play_out_of_bounds():
    state = GameState()
    with pytest.raises(IllegalMoveError) as exc_info:
        play(state, Move(color=BLACK, coord="A20"))
    assert exc_info.value.code in ("OUT_OF_BOUNDS", "INVALID_COORD")


def test_play_suicide():
    # Surround corner -- suicide
    # Set up white around A19 (x=0, y=0) corner
    # A19 = (0,0), B19 = (1,0), A18 = (0,1)
    state = GameState()
    state = play(state, Move(color=BLACK, coord="Q16"))  # dummy black
    state = play(state, Move(color=WHITE, coord="B19"))  # B19 is x=1,y=0
    state = play(state, Move(color=BLACK, coord="Q4"))   # dummy black
    state = play(state, Move(color=WHITE, coord="A18"))  # A18 = x=0,y=1
    with pytest.raises(IllegalMoveError) as exc_info:
        play(state, Move(color=BLACK, coord="A19"))  # suicide
    assert exc_info.value.code == "ILLEGAL_SUICIDE"


def test_play_ko():
    # Real ko situation:
    #   . W B .
    #   W . W B
    #   . W B .
    # Black plays at (1,1) capturing the W at (1,1)... let's use classic ko shape.
    # Ko setup:
    #   . B W .
    #   B . B W
    #   . B W .
    # Actually simpler: verify ko_state is updated after a non-pass move.
    state = GameState()
    state0 = state
    new_state = play(state, Move(color=BLACK, coord="Q16"))
    assert new_state.ko_state.previous_board == state0.board


def test_play_ko_violation():
    # Classic ko position at (2,2) and (2,3):
    #   . B W .      (row 0)
    #   B . B W      (row 1)
    #   . B W .      (row 2)
    # Black captures at (row 1, col 1) removing white... we need to construct carefully.
    # Build a simpler ko: manually set ko_state to force a ko violation.
    from app.core.rules.ko import KoState
    # Setup: a state where the next move would recreate the previous board.
    # After black plays somewhere, the board equals previous board => ko violation
    state = GameState()
    # Play Q16 first -- board now has a stone at Q16
    state = play(state, Move(color=BLACK, coord="Q16"))
    # Manually craft ko_state so that any new board different from current raises ko
    # If white plays D4 but ko_state.previous_board equals the post-D4 board, it's ko
    # Easiest: inject a ko_state with previous_board equal to the future board
    from app.core.rules.captures import place_with_captures
    future_board, _ = place_with_captures(state.board, 3, 15, WHITE)  # D4 = x=3,y=15
    state.ko_state = KoState(previous_board=future_board)
    with pytest.raises(IllegalMoveError) as exc_info:
        play(state, Move(color=WHITE, coord="D4"))
    assert exc_info.value.code == "ILLEGAL_KO"


def test_pass_move():
    state = GameState()
    state = pass_move(state, BLACK)
    assert state.to_move == WHITE
    assert state.consecutive_passes == 1


def test_game_over_two_passes():
    state = GameState()
    state = pass_move(state, BLACK)
    state = pass_move(state, WHITE)
    assert is_game_over(state)


def test_game_not_over_one_pass():
    state = GameState()
    state = pass_move(state, BLACK)
    assert not is_game_over(state)


def test_pass_resets_on_play():
    state = GameState()
    state = pass_move(state, BLACK)
    assert state.consecutive_passes == 1
    state = play(state, Move(color=WHITE, coord="Q16"))
    assert state.consecutive_passes == 0


def test_resign_move():
    state = GameState()
    state = play(state, Move(color=BLACK, coord=None))
    assert state.to_move == WHITE
    assert state.consecutive_passes == 0
    assert len(state.move_history) == 1


def test_score_initial_state():
    state = GameState()
    result = score(state)
    assert result.winner in (BLACK, WHITE)


def test_score_with_dead_stones():
    state = GameState()
    state = play(state, Move(color=BLACK, coord="Q16"))
    state = play(state, Move(color=WHITE, coord="D4"))
    # Mark D4 as dead (D4 = x=3, y=15)
    result = score(state, dead_stones={(3, 15)})
    assert result.black_captures == 1


def test_build_sgf_empty():
    state = GameState()
    sgf = build_sgf(state)
    assert "GM[1]" in sgf
    assert "SZ[19]" in sgf


def test_build_sgf_with_moves():
    state = GameState()
    state = play(state, Move(color=BLACK, coord="Q16"))
    state = play(state, Move(color=WHITE, coord="D4"))
    sgf = build_sgf(state, result="B+R")
    assert ";B[" in sgf
    assert ";W[" in sgf
    assert "RE[B+R]" in sgf


def test_build_sgf_with_pass():
    state = GameState()
    state = pass_move(state, BLACK)
    sgf = build_sgf(state)
    assert ";B[]" in sgf


def test_build_sgf_with_resign():
    state = GameState()
    state = play(state, Move(color=BLACK, coord=None))
    sgf = build_sgf(state)
    # Resign doesn't emit an SGF move node
    assert ";B[" not in sgf


def test_build_sgf_custom_board_size():
    state = GameState()
    sgf = build_sgf(state, board_size=9)
    assert "SZ[9]" in sgf


def test_build_sgf_coordinates():
    # Q16 = x=15, y=3 -> SGF letters: col='p' (15th from 'a'), row='d' (3rd)
    state = GameState()
    state = play(state, Move(color=BLACK, coord="Q16"))
    sgf = build_sgf(state)
    assert ";B[pd]" in sgf


def test_full_mini_game():
    """Simulate a short game to ensure no exceptions."""
    state = GameState()
    moves = [
        ("B", "Q16"), ("W", "D4"), ("B", "Q4"), ("W", "D16"),
        ("B", "Q3"), ("W", "D3"),
    ]
    for color, coord in moves:
        state = play(state, Move(color=color, coord=coord))  # type: ignore[arg-type]
    assert len(state.move_history) == 6


def test_capture_updates_state():
    """Capturing updates capture count and to_move flips."""
    state = GameState()
    # Surround a white stone
    state = play(state, Move(color=BLACK, coord="Q16"))   # (15, 3)
    state = play(state, Move(color=WHITE, coord="K10"))   # (9, 9)
    state = play(state, Move(color=BLACK, coord="K11"))   # (9, 8) N
    state = play(state, Move(color=WHITE, coord="A1"))    # random
    state = play(state, Move(color=BLACK, coord="L10"))   # (10, 9) E
    state = play(state, Move(color=WHITE, coord="A2"))
    state = play(state, Move(color=BLACK, coord="J10"))   # (8, 9) W
    state = play(state, Move(color=WHITE, coord="A3"))
    state = play(state, Move(color=BLACK, coord="K9"))    # (9, 10) S - captures K10
    assert state.captures[BLACK] == 1


def test_illegal_move_error_has_code_and_detail():
    err = IllegalMoveError("TEST_CODE", "test detail")
    assert err.code == "TEST_CODE"
    assert err.detail == "test detail"
    assert "TEST_CODE" in str(err)


def test_illegal_move_error_no_detail():
    err = IllegalMoveError("TEST_CODE")
    assert err.code == "TEST_CODE"
    assert err.detail == ""
