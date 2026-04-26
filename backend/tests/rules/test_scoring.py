import pytest
from app.core.rules.board import BLACK, WHITE, Board, BOARD_SIZE
from app.core.rules.scoring import ScoreResult, score_game


def _full_black_board() -> Board:
    """19x19 board fully occupied by black stones."""
    b = Board(19)
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            b = b.place(x, y, BLACK)
    return b


def test_all_black_territory():
    # Empty board -- all territory is neutral (no stones border any region exclusively)
    b = Board(19)
    result = score_game(b, 0, 0, 0.0)
    assert result.black_territory == 0
    assert result.white_territory == 0


def test_simple_territory():
    # Black has top-left corner, white has bottom-right
    b = Board(19)
    # Create a clear 1x1 black territory: surround (1,1) with black
    b = (b
         .place(0, 1, BLACK).place(1, 0, BLACK)
         .place(2, 1, BLACK).place(1, 2, BLACK))
    # (1,1) should be black territory
    result = score_game(b, 0, 0, 0.0)
    assert result.black_territory >= 1


def test_simple_white_territory():
    # Surround a point with white stones
    b = (Board(19)
         .place(0, 1, WHITE).place(1, 0, WHITE)
         .place(2, 1, WHITE).place(1, 2, WHITE))
    result = score_game(b, 0, 0, 0.0)
    assert result.white_territory >= 1


def test_komi_affects_winner():
    # Equal territory -- komi gives white the win
    b = Board(19)
    result = score_game(b, 0, 0, 6.5)
    assert result.winner == WHITE
    assert result.margin == 6.5


def test_komi_tie_goes_to_white():
    # Score is equal exactly -- tie break: winner = WHITE
    b = Board(19)
    result = score_game(b, 0, 0, 0.0)
    assert result.winner == WHITE
    assert result.margin == 0.0


def test_captures_counted():
    b = Board(19)
    result = score_game(b, 10, 5, 0.0)
    assert result.black_captures == 10
    assert result.white_captures == 5
    assert result.black_score == 10.0
    assert result.white_score == 5.0
    assert result.winner == BLACK


def test_dead_stones_counted():
    # White stone at (5,5) is marked dead
    b = Board(19).place(5, 5, WHITE)
    dead = {(5, 5)}
    result = score_game(b, 0, 0, 0.0, dead_stones=dead)
    # Black captures the dead white stone
    assert result.black_captures == 1


def test_dead_black_stones_counted():
    # Black stone marked dead - counts as white capture
    b = Board(19).place(5, 5, BLACK)
    dead = {(5, 5)}
    result = score_game(b, 0, 0, 0.0, dead_stones=dead)
    assert result.white_captures == 1


def test_score_result_structure():
    b = Board(19)
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
    b = (Board(19)
         .place(0, 0, BLACK)
         .place(2, 0, WHITE))
    # (1,0) is adjacent to both black and white -- neutral
    result = score_game(b, 0, 0, 0.0)
    # Neither gets territory from the region containing (1,0)
    # but the rest of the huge empty board is also neutral due to being adjacent to both
    assert result.black_territory == 0
    assert result.white_territory == 0


def test_black_winner_with_higher_score():
    b = Board(19)
    # Black captures much more than white + komi
    result = score_game(b, 50, 0, 6.5)
    assert result.winner == BLACK
    assert result.margin == 43.5


def test_large_territory_with_komi():
    # Black has 10 captures, komi is 6.5 -> black wins by 3.5
    b = Board(19)
    result = score_game(b, 10, 0, 6.5)
    assert result.winner == BLACK
    assert result.margin == 3.5


def test_score_game_9x9_empty_board_white_wins_by_komi():
    b = Board(9)
    r = score_game(b, black_captures=0, white_captures=0, komi=6.5)
    assert r.black_territory == 0
    assert r.white_territory == 0
    assert r.winner == WHITE
    assert r.margin == 6.5


def test_score_game_13x13_small_territory():
    # Place a single black stone in a corner; all other points go to black.
    b = Board(13).place(0, 0, BLACK)
    r = score_game(b, black_captures=0, white_captures=0, komi=6.5)
    assert r.black_territory == 168


def test_flood_territory_returns_point_sets():
    # 5x5 board with a 1x1 black eye at (1,1) and a 1x1 white eye at (3,3)
    b = Board(5)
    for x, y in [(0, 1), (1, 0), (2, 1), (1, 2)]:
        b = b.place(x, y, BLACK)
    for x, y in [(2, 3), (3, 2), (4, 3), (3, 4)]:
        b = b.place(x, y, WHITE)
    result = score_game(b, 0, 0, 0.0)
    assert (1, 1) in result.black_points
    assert (3, 3) in result.white_points
    # The shared border between the two formations must be neutral (dame)
    assert (2, 2) not in result.black_points
    assert (2, 2) not in result.white_points
    # Sizes must agree with counts
    assert len(result.black_points) == result.black_territory
    assert len(result.white_points) == result.white_territory
    assert len(result.dame_points) > 0
    assert result.black_points.isdisjoint(result.white_points)
    assert result.black_points.isdisjoint(result.dame_points)
    assert result.white_points.isdisjoint(result.dame_points)
