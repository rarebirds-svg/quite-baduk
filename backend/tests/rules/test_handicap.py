import pytest

from app.core.rules.board import BLACK, Board
from app.core.rules.handicap import HANDICAP_TABLES, apply_handicap
from app.core.rules.sgf_coord import gtp_to_xy


def _black_count(b: Board) -> int:
    return sum(1 for y in range(b.size) for x in range(b.size) if b.get(x, y) == BLACK)


def test_handicap_tables_supported_sizes():
    assert set(HANDICAP_TABLES.keys()) == {9, 13, 19}


def test_handicap_zero_noop():
    for size in (9, 13, 19):
        b = Board(size)
        assert apply_handicap(b, 0) is b


@pytest.mark.parametrize("size,stones", [
    (9, 2), (9, 3), (9, 4), (9, 5),
    (13, 2), (13, 3), (13, 4), (13, 5), (13, 6), (13, 7), (13, 8), (13, 9),
    (19, 2), (19, 3), (19, 4), (19, 5), (19, 6), (19, 7), (19, 8), (19, 9),
])
def test_handicap_places_correct_number_of_black_stones(size, stones):
    b = Board(size)
    b2 = apply_handicap(b, stones)
    assert _black_count(b2) == stones


def test_handicap_9_specific_coords():
    b = apply_handicap(Board(9), 5)
    for coord in ("C3", "G7", "G3", "C7", "E5"):
        xy = gtp_to_xy(coord, 9)
        assert xy is not None
        assert b.get(*xy) == BLACK


def test_handicap_13_9_stones_are_all_stars():
    b = apply_handicap(Board(13), 9)
    for coord in ("D4", "K10", "K4", "D10", "D7", "K7", "G4", "G10", "G7"):
        xy = gtp_to_xy(coord, 13)
        assert xy is not None
        assert b.get(*xy) == BLACK


def test_handicap_invalid_raises():
    with pytest.raises(ValueError):
        apply_handicap(Board(9), 6)        # 9x9 only supports 2-5
    with pytest.raises(ValueError):
        apply_handicap(Board(13), 10)
    with pytest.raises(ValueError):
        apply_handicap(Board(19), 1)
