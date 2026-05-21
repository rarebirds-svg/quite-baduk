# SGF import 모듈(파싱·정제·메타 추출) 단위 테스트
from __future__ import annotations

from datetime import date

import pytest

from app.core.sgf.import_sgf import InvalidProSgf, parse_pro_sgf

_GAME = (
    "(;GM[1]FF[4]CA[UTF-8]SZ[19]KM[6.5]"
    "PB[Test Black]PW[Test White]BR[9p]WR[9p]"
    "EV[Test Cup]DT[2026-01-15]RE[B+R]"
    ";B[pd];W[dp];B[pp]C[good move];W[dd])"
)
_WITH_VARIATION = "(;GM[1]SZ[19];B[pd];W[dp](;B[pp])(;B[dd]))"


def test_parse_extracts_metadata() -> None:
    parsed = parse_pro_sgf(_GAME)
    assert parsed.black_player == "Test Black"
    assert parsed.white_player == "Test White"
    assert parsed.black_rank == "9p"
    assert parsed.event == "Test Cup"
    assert parsed.game_date == date(2026, 1, 15)
    assert parsed.result == "B+R"
    assert parsed.board_size == 19
    assert parsed.move_count == 4


def test_parse_produces_gtp_coords() -> None:
    parsed = parse_pro_sgf(_GAME)
    first = parsed.moves[0]
    assert first.move_number == 1
    assert first.color == "B"
    # SGF [pd] = col 15, row 15 (0-indexed from bottom) -> GTP Q16
    assert first.coord == "Q16"


def test_clean_sgf_strips_comments() -> None:
    parsed = parse_pro_sgf(_GAME)
    assert "C[good move]" not in parsed.clean_sgf
    assert "good move" not in parsed.clean_sgf


def test_variations_ignored_main_line_only() -> None:
    parsed = parse_pro_sgf(_WITH_VARIATION)
    # root + B[pd] + W[dp] + B[pp] (first variation) = 3 moves
    assert parsed.move_count == 3


def test_content_hash_is_stable() -> None:
    a = parse_pro_sgf(_GAME)
    b = parse_pro_sgf(_GAME)
    assert a.content_hash == b.content_hash
    assert len(a.content_hash) == 64


def test_empty_sgf_rejected() -> None:
    with pytest.raises(InvalidProSgf):
        parse_pro_sgf("(;GM[1]SZ[19])")


def test_bad_board_size_rejected() -> None:
    with pytest.raises(InvalidProSgf):
        parse_pro_sgf("(;GM[1]SZ[12];B[aa])")


def test_garbage_input_rejected() -> None:
    with pytest.raises(InvalidProSgf):
        parse_pro_sgf("this is not sgf at all")
