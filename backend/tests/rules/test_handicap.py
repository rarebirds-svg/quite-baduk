import pytest
from app.core.rules.board import BLACK, EMPTY, Board
from app.core.rules.handicap import HANDICAP_COORDS, apply_handicap
from app.core.rules.sgf_coord import gtp_to_xy


def test_no_handicap_noop():
    b = Board()
    b2 = apply_handicap(b, 0)
    assert b == b2


def test_handicap_2_stones():
    b = apply_handicap(Board(), 2)
    for coord in HANDICAP_COORDS[2]:
        xy = gtp_to_xy(coord)
        assert xy is not None
        assert b.get(*xy) == BLACK


def test_handicap_9_stones():
    b = apply_handicap(Board(), 9)
    stone_count = sum(
        1 for coord in HANDICAP_COORDS[9]
        if b.get(*gtp_to_xy(coord)) == BLACK  # type: ignore[arg-type]
    )
    assert stone_count == 9


@pytest.mark.parametrize("n", [2, 3, 4, 5, 6, 7, 8, 9])
def test_handicap_all_valid(n: int) -> None:
    b = apply_handicap(Board(), n)
    for coord in HANDICAP_COORDS[n]:
        xy = gtp_to_xy(coord)
        assert xy is not None
        assert b.get(*xy) == BLACK


def test_handicap_invalid_raises():
    with pytest.raises(ValueError):
        apply_handicap(Board(), 1)

    with pytest.raises(ValueError):
        apply_handicap(Board(), 10)


def test_handicap_coords_count():
    for n, coords in HANDICAP_COORDS.items():
        assert len(coords) == n


def test_handicap_coords_all_valid_gtp():
    """All handicap coords must parse as valid GTP coordinates."""
    for coords in HANDICAP_COORDS.values():
        for coord in coords:
            xy = gtp_to_xy(coord)
            assert xy is not None
            x, y = xy
            assert 0 <= x < 19
            assert 0 <= y < 19
