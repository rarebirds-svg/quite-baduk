import pytest
from app.core.rules.board import BLACK, EMPTY, WHITE, Board, BOARD_SIZE


def test_empty_board():
    b = Board()
    assert b.get(0, 0) == EMPTY
    assert b.get(18, 18) == EMPTY


def test_board_size():
    b = Board()
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
            assert b.get(x, y) == EMPTY


def test_place_stone():
    b = Board().place(3, 3, BLACK)
    assert b.get(3, 3) == BLACK
    assert b.get(3, 4) == EMPTY


def test_place_returns_new_board():
    b1 = Board()
    b2 = b1.place(0, 0, BLACK)
    assert b1.get(0, 0) == EMPTY  # original unchanged
    assert b2.get(0, 0) == BLACK


def test_remove_stone():
    b = Board().place(3, 3, BLACK)
    b2 = b.remove(3, 3)
    assert b2.get(3, 3) == EMPTY


def test_is_empty():
    b = Board()
    assert b.is_empty(0, 0)
    b2 = b.place(0, 0, BLACK)
    assert not b2.is_empty(0, 0)


def test_in_bounds():
    b = Board()
    assert b.in_bounds(0, 0)
    assert b.in_bounds(18, 18)
    assert not b.in_bounds(19, 0)
    assert not b.in_bounds(0, 19)
    assert not b.in_bounds(-1, 0)
    assert not b.in_bounds(0, -1)


def test_neighbors_corner():
    b = Board()
    assert set(b.neighbors(0, 0)) == {(1, 0), (0, 1)}


def test_neighbors_edge():
    b = Board()
    assert set(b.neighbors(0, 1)) == {(1, 1), (0, 0), (0, 2)}


def test_neighbors_center():
    b = Board()
    assert set(b.neighbors(9, 9)) == {(10, 9), (8, 9), (9, 10), (9, 8)}


def test_neighbors_bottom_right_corner():
    b = Board()
    assert set(b.neighbors(18, 18)) == {(17, 18), (18, 17)}


def test_group_single():
    b = Board().place(3, 3, BLACK)
    assert b.group(3, 3) == {(3, 3)}


def test_group_connected():
    b = Board().place(3, 3, BLACK).place(4, 3, BLACK)
    assert b.group(3, 3) == {(3, 3), (4, 3)}


def test_group_not_same_color():
    b = Board().place(3, 3, BLACK).place(4, 3, WHITE)
    assert b.group(3, 3) == {(3, 3)}


def test_group_empty():
    b = Board()
    assert b.group(0, 0) == set()


def test_group_larger():
    b = (Board()
         .place(3, 3, BLACK)
         .place(4, 3, BLACK)
         .place(5, 3, BLACK)
         .place(5, 4, BLACK))
    assert b.group(3, 3) == {(3, 3), (4, 3), (5, 3), (5, 4)}


def test_liberties_center():
    b = Board().place(9, 9, BLACK)
    g = b.group(9, 9)
    assert len(b.liberties(g)) == 4


def test_liberties_corner():
    b = Board().place(0, 0, BLACK)
    g = b.group(0, 0)
    assert len(b.liberties(g)) == 2


def test_liberties_surrounded():
    b = (Board()
         .place(9, 9, BLACK)
         .place(10, 9, WHITE)
         .place(8, 9, WHITE)
         .place(9, 10, WHITE)
         .place(9, 8, WHITE))
    g = b.group(9, 9)
    assert len(b.liberties(g)) == 0


def test_is_alive_true():
    b = Board().place(9, 9, BLACK)
    assert b.is_alive(9, 9)


def test_is_alive_false():
    b = (Board()
         .place(9, 9, BLACK)
         .place(10, 9, WHITE).place(8, 9, WHITE)
         .place(9, 10, WHITE).place(9, 8, WHITE))
    assert not b.is_alive(9, 9)


def test_board_equality():
    b1 = Board().place(3, 3, BLACK)
    b2 = Board().place(3, 3, BLACK)
    assert b1 == b2


def test_board_inequality():
    b1 = Board().place(3, 3, BLACK)
    b2 = Board().place(3, 3, WHITE)
    assert b1 != b2


def test_board_not_equal_other_type():
    b = Board()
    assert (b == "not a board") is False


def test_board_hash():
    b1 = Board().place(3, 3, BLACK)
    b2 = Board().place(3, 3, BLACK)
    assert hash(b1) == hash(b2)


def test_remove_group():
    b = Board().place(3, 3, BLACK).place(4, 3, BLACK)
    b2 = b.remove_group({(3, 3), (4, 3)})
    assert b2.get(3, 3) == EMPTY
    assert b2.get(4, 3) == EMPTY


def test_board_with_explicit_cells():
    # Create a board via explicit cells tuple
    cells = (EMPTY,) * (BOARD_SIZE * BOARD_SIZE)
    b = Board(cells)
    assert b.get(0, 0) == EMPTY
