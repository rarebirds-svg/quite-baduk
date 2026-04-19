import pytest
from app.core.rules.sgf_coord import gtp_to_xy, xy_to_gtp


def test_gtp_to_xy_pass():
    assert gtp_to_xy("pass", 19) is None


def test_gtp_to_xy_19():
    assert gtp_to_xy("A19", 19) == (0, 0)
    assert gtp_to_xy("T19", 19) == (18, 0)
    assert gtp_to_xy("A1", 19) == (0, 18)
    assert gtp_to_xy("Q16", 19) == (15, 3)


def test_gtp_to_xy_13():
    assert gtp_to_xy("A13", 13) == (0, 0)
    assert gtp_to_xy("N1", 13) == (12, 12)
    assert gtp_to_xy("G7", 13) == (6, 6)


def test_gtp_to_xy_9():
    assert gtp_to_xy("A9", 9) == (0, 0)
    assert gtp_to_xy("J1", 9) == (8, 8)
    assert gtp_to_xy("E5", 9) == (4, 4)


def test_gtp_to_xy_row_out_of_range_raises():
    with pytest.raises(ValueError):
        gtp_to_xy("A20", 19)
    with pytest.raises(ValueError):
        gtp_to_xy("A14", 13)
    with pytest.raises(ValueError):
        gtp_to_xy("A10", 9)


def test_xy_to_gtp_roundtrip():
    for size in (9, 13, 19):
        for x in range(size):
            for y in range(size):
                c = xy_to_gtp(x, y, size)
                assert gtp_to_xy(c, size) == (x, y)


def test_xy_to_gtp_out_of_range_raises():
    with pytest.raises(ValueError):
        xy_to_gtp(9, 0, 9)
    with pytest.raises(ValueError):
        xy_to_gtp(0, 19, 19)
