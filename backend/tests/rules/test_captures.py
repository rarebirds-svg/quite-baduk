from app.core.rules.board import BLACK, EMPTY, WHITE, Board
from app.core.rules.captures import is_suicide, opponent, place_with_captures


def test_opponent():
    assert opponent(BLACK) == WHITE
    assert opponent(WHITE) == BLACK


def test_single_stone_capture():
    # Surround white stone at (9,9) with black stones
    b = (Board(19)
         .place(9, 9, WHITE)
         .place(10, 9, BLACK)
         .place(8, 9, BLACK)
         .place(9, 10, BLACK))
    # One more black stone closes the capture
    new_b, captured = place_with_captures(b, 9, 8, BLACK)
    assert captured == 1
    assert new_b.get(9, 9) == EMPTY
    assert new_b.get(9, 8) == BLACK


def test_multi_stone_capture():
    # Horizontal chain of 3 white stones surrounded by black
    b = (Board(19)
         .place(5, 5, WHITE).place(6, 5, WHITE).place(7, 5, WHITE)
         .place(5, 4, BLACK).place(6, 4, BLACK).place(7, 4, BLACK)
         .place(5, 6, BLACK).place(6, 6, BLACK).place(7, 6, BLACK)
         .place(4, 5, BLACK))
    new_b, captured = place_with_captures(b, 8, 5, BLACK)
    assert captured == 3
    assert new_b.get(5, 5) == EMPTY
    assert new_b.get(6, 5) == EMPTY
    assert new_b.get(7, 5) == EMPTY


def test_no_capture_with_liberty():
    b = Board(19).place(9, 9, WHITE)
    new_b, captured = place_with_captures(b, 9, 8, BLACK)
    assert captured == 0
    assert new_b.get(9, 9) == WHITE


def test_capture_before_suicide_check():
    # White group with one liberty; black fills that liberty capturing white
    # Black's own group after capture has liberty (not suicide)
    b = (Board(19)
         .place(0, 1, WHITE)
         .place(1, 0, BLACK).place(1, 1, BLACK)
         .place(0, 2, BLACK))
    # Black plays at (0,0) -- corner -- captures white and gains a liberty via capture
    new_b, captured = place_with_captures(b, 0, 0, BLACK)
    assert captured == 1
    assert new_b.get(0, 1) == EMPTY


def test_is_suicide_true():
    # Simple suicide: corner with white on both neighbors
    b2 = (Board(19)
          .place(1, 0, WHITE).place(0, 1, WHITE))
    assert is_suicide(b2, 0, 0, BLACK)


def test_is_suicide_false_normal():
    b = Board(19)
    assert not is_suicide(b, 9, 9, BLACK)


def test_is_suicide_false_capture():
    # Placing on an empty board with neighbors free is never suicide.
    assert not is_suicide(Board(19), 3, 3, BLACK)


def test_is_suicide_capture_prevents():
    # Build a position where a black move would be suicide except it captures white
    # White at (1,0), (0,1) -- corner (0,0) empty
    # Black at (2,0), (0,2), (1,1) -- surround white on outside
    # Placing black at (0,0) captures white group (1,0)+(0,1) since they have no libs
    b = (Board(19)
         .place(1, 0, WHITE).place(0, 1, WHITE)
         .place(2, 0, BLACK).place(0, 2, BLACK).place(1, 1, BLACK))
    # White group has libs at (0,0) only -- placing black there captures white
    # So placing at (0,0) is NOT suicide
    assert not is_suicide(b, 0, 0, BLACK)
    # And verify capture actually happens
    new_b, captured = place_with_captures(b, 0, 0, BLACK)
    assert captured == 2


def test_place_with_captures_multiple_groups():
    # Single black stone captures two separate white groups simultaneously
    # Setup:
    #   . W . B
    #   B B B B
    #   . W . B
    # A black stone placed at top and bottom to finalize
    # Two isolated white stones at (1,0) and (1,2); each is surrounded by black
    # except for the shared liberty (1,1). Placing black at (1,1) captures both.
    b = (Board(19)
         .place(1, 0, WHITE)
         .place(1, 2, WHITE)
         .place(0, 0, BLACK).place(2, 0, BLACK)
         .place(0, 2, BLACK).place(2, 2, BLACK)
         .place(0, 1, BLACK).place(2, 1, BLACK)
         .place(1, 3, BLACK))  # seals (1,2)'s last non-(1,1) liberty
    new_b, captured = place_with_captures(b, 1, 1, BLACK)
    assert captured == 2
    assert new_b.get(1, 0) == EMPTY
    assert new_b.get(1, 2) == EMPTY
