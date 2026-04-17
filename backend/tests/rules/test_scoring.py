import pytest
from app.core.rules.board import BLACK, WHITE, Board, BOARD_SIZE
from app.core.rules.scoring import ScoreResult, score_game


def _full_black_board() -> Board:
    """19x19 board fully occupied by black stones."""
    b = Board()
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            b = b.place(x, y, BLACK)
    return b


def test_all_black_territory():
    # Empty board -- all territory is neutral (no stones border any region exclusively)
    b = Board()
    result = score_game(b, 0, 0, 0.0)
    assert result.black_territory == 0
    assert result.white_territory == 0


def test_simple_territory():
    # Black has top-left corner, white has bottom-right
    b = Board()
    # Create a clear 1x1 black territory: surround (1,1) with black
    b = (b
         .place(0, 1, BLACK).place(1, 0, BLACK)
         .place(2, 1, BLACK).place(1, 2, BLACK))
    # (1,1) should be black territory
    result = score_game(b, 0, 0, 0.0)
    assert result.black_territory >= 1


def test_simple_white_territory():
    # Surround a point with white stones
    b = (Board()
         .place(0, 1, WHITE).place(1, 0, WHITE)
         .place(2, 1, WHITE).place(1, 2, WHITE))
    result = score_game(b, 0, 0, 0.0)
    assert result.white_territory >= 1


def test_komi_affects_winner():
    # Equal territory -- komi gives white the win
    b = Board()
    result = score_game(b, 0, 0, 6.5)
    assert result.winner == WHITE
    assert result.margin == 6.5


def test_komi_tie_goes_to_white():
    # Score is equal exactly -- tie break: winner = WHITE
    b = Board()
    result = score_game(b, 0, 0, 0.0)
    assert result.winner == WHITE
    assert result.margin == 0.0


def test_captures_counted():
    b = Board()
    result = score_game(b, 10, 5, 0.0)
    assert result.black_captures == 10
    assert result.white_captures == 5
    assert result.black_score == 10.0
    assert result.white_score == 5.0
    assert result.winner == BLACK


def test_dead_stones_counted():
    # White stone at (5,5) is marked dead
    b = Board().place(5, 5, WHITE)
    dead = {(5, 5)}
    result = score_game(b, 0, 0, 0.0, dead_stones=dead)
    # Black captures the dead white stone
    assert result.black_captures == 1


def test_dead_black_stones_counted():
    # Black stone marked dead - counts as white capture
    b = Board().place(5, 5, BLACK)
    dead = {(5, 5)}
    result = score_game(b, 0, 0, 0.0, dead_stones=dead)
    assert result.white_captures == 1


def test_score_result_structure():
    b = Board()
    result = score_game(b, 3, 2, 6.5)
    assert hasattr(result, "black_territory")
    assert hasattr(result, "white_territory")
    assert hasattr(result, "winner")
    assert hasattr(result, "margin")
    assert result.winner in (BLACK, WHITE)
    assert result.margin >= 0


def test_neutral_dame_not_counted():
    # A region bordered by both colors is dame (neutral)
    # Place a black and white stone with an empty point between that touches both
    b = (Board()
         .place(0, 0, BLACK)
         .place(2, 0, WHITE))
    # (1,0) is adjacent to both black and white -- neutral
    result = score_game(b, 0, 0, 0.0)
    # Neither gets territory from the region containing (1,0)
    # but the rest of the huge empty board is also neutral due to being adjacent to both
    assert result.black_territory == 0
    assert result.white_territory == 0


def test_black_winner_with_higher_score():
    b = Board()
    # Black captures much more than white + komi
    result = score_game(b, 50, 0, 6.5)
    assert result.winner == BLACK
    assert result.margin == 43.5


def test_large_territory_with_komi():
    # Black has 10 captures, komi is 6.5 -> black wins by 3.5
    b = Board()
    result = score_game(b, 10, 0, 6.5)
    assert result.winner == BLACK
    assert result.margin == 3.5
