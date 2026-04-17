import pytest
from app.core.rules.sgf_coord import gtp_to_xy, xy_to_gtp, COLS


def test_gtp_to_xy_a1():
    assert gtp_to_xy("A1") == (0, 18)


def test_gtp_to_xy_a19():
    assert gtp_to_xy("A19") == (0, 0)


def test_gtp_to_xy_t19():
    assert gtp_to_xy("T19") == (18, 0)


def test_gtp_to_xy_q16():
    # Q skips I: A=0,B=1,C=2,D=3,E=4,F=5,G=6,H=7,J=8,K=9,L=10,M=11,N=12,O=13,P=14,Q=15
    assert gtp_to_xy("Q16") == (15, 3)


def test_gtp_to_xy_k10():
    # K: A=0..H=7,J=8,K=9 -> x=9; y=19-10=9
    assert gtp_to_xy("K10") == (9, 9)


def test_gtp_to_xy_pass():
    assert gtp_to_xy("pass") is None
    assert gtp_to_xy("PASS") is None


def test_gtp_to_xy_lowercase():
    assert gtp_to_xy("q16") == (15, 3)


def test_gtp_to_xy_invalid_col():
    with pytest.raises(ValueError, match="Invalid column"):
        gtp_to_xy("I10")


def test_gtp_to_xy_invalid_row():
    with pytest.raises(ValueError, match="Row number out of range"):
        gtp_to_xy("A20")


def test_gtp_to_xy_too_short():
    with pytest.raises(ValueError, match="Invalid GTP coordinate"):
        gtp_to_xy("A")


def test_xy_to_gtp_origin():
    assert xy_to_gtp(0, 18) == "A1"


def test_xy_to_gtp_top_right():
    assert xy_to_gtp(18, 0) == "T19"


def test_xy_to_gtp_k10():
    assert xy_to_gtp(9, 9) == "K10"


def test_xy_to_gtp_roundtrip():
    for x in range(19):
        for y in range(19):
            coord = xy_to_gtp(x, y)
            assert gtp_to_xy(coord) == (x, y)


def test_xy_to_gtp_out_of_range():
    with pytest.raises(ValueError):
        xy_to_gtp(19, 0)


def test_xy_to_gtp_out_of_range_y():
    with pytest.raises(ValueError):
        xy_to_gtp(0, 19)


def test_xy_to_gtp_negative():
    with pytest.raises(ValueError):
        xy_to_gtp(-1, 0)


def test_cols_length():
    assert len(COLS) == 19
    assert "I" not in COLS
