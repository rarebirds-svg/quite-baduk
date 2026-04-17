import pytest
from app.core.rules.board import BLACK, WHITE, Board
from app.core.rules.ko import KoState, is_ko_violation
from app.core.rules.captures import place_with_captures


def test_no_ko_initially():
    ko = KoState()
    b = Board().place(9, 9, BLACK)
    assert not is_ko_violation(ko, b)


def test_ko_detected():
    # Position A -> play -> Position B -> try to return to A
    board_a = Board().place(5, 5, BLACK)
    ko = KoState(previous_board=board_a)
    assert is_ko_violation(ko, board_a)


def test_ko_not_triggered_different_position():
    board_a = Board().place(5, 5, BLACK)
    board_b = Board().place(6, 6, BLACK)
    ko = KoState(previous_board=board_a)
    assert not is_ko_violation(ko, board_b)


def test_ko_state_update():
    board_a = Board().place(3, 3, BLACK)
    ko = KoState()
    ko2 = ko.update(board_a)
    assert ko2.previous_board == board_a
    assert ko.previous_board is None  # original unchanged


def test_ko_state_default_none():
    ko = KoState()
    assert ko.previous_board is None
