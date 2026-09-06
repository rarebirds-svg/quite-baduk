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
    # three move nodes B[pd], W[dp], B[pp] (first variation) = 3 moves
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


def test_parse_pro_sgf_extracts_round():
    sgf_text = "(;FF[4]GM[1]SZ[19]EV[10th Chunlan Cup Final]RO[3];B[pd];W[dp])"
    parsed = parse_pro_sgf(sgf_text)
    assert parsed.round == "3"


def test_parse_pro_sgf_round_none_when_absent():
    sgf_text = "(;FF[4]GM[1]SZ[19]EV[Dosaku Castle Game];B[pd];W[dp])"
    parsed = parse_pro_sgf(sgf_text)
    assert parsed.round is None


def test_parse_pro_sgf_round_keeps_final_prefix_text():
    sgf_text = "(;FF[4]GM[1]SZ[19]RO[Final 2];B[pd];W[dp])"
    parsed = parse_pro_sgf(sgf_text)
    assert parsed.round == "Final 2"


# --- 인코딩: CA[] 없는 SGF의 비ASCII 기사명이 깨지지 않아야 한다 ---

_SGF_NO_CA = "(;GM[1]FF[4]SZ[19]KM[6.5]PB[國 insei]PW[이창호];B[pd];W[dp])"


def test_parse_keeps_non_ascii_names_without_ca() -> None:
    # sgfmill 기본값(ISO-8859-1)에 맡기면 'å\x9c\x8b insei'로 깨진다.
    parsed = parse_pro_sgf(_SGF_NO_CA)
    assert parsed.black_player == "國 insei"
    assert parsed.white_player == "이창호"
    # 정제 SGF는 CA[UTF-8]을 달고 나가 재파싱이 안정적이다.
    assert "CA[UTF-8]" in parsed.clean_sgf
    assert parse_pro_sgf(parsed.clean_sgf).white_player == "이창호"


def test_decode_sgf_bytes_prefers_ca_then_utf8_then_latin1() -> None:
    from app.core.sgf.import_sgf import decode_sgf_bytes

    # CA[] 선언이 있으면 그 인코딩으로.
    latin = "(;FF[4]CA[ISO-8859-1]SZ[19]PB[Émile];B[pd])".encode("latin-1")
    assert "PB[Émile]" in decode_sgf_bytes(latin)
    # 선언이 없으면 UTF-8 strict — 헤더 charset과 무관하게 한글이 살아난다.
    assert "PW[이창호]" in decode_sgf_bytes(_SGF_NO_CA.encode("utf-8"))
    # UTF-8이 아니면 무손실 폴백(latin-1)으로라도 파싱 가능한 문자열을 준다.
    raw_latin = "(;FF[4]SZ[19]PB[Émile];B[pd])".encode("latin-1")
    assert "PB[Émile]" in decode_sgf_bytes(raw_latin)
    # 알 수 없는 CA 값은 무시하고 다음 단계로 넘어간다.
    weird = "(;FF[4]CA[no-such-codec]SZ[19]PB[이창호];B[pd])".encode()
    assert "PB[이창호]" in decode_sgf_bytes(weird)


def test_repair_mojibake_roundtrip() -> None:
    from app.core.sgf.import_sgf import repair_mojibake

    broken = "國 insei".encode().decode("latin-1")
    assert broken.startswith("å")
    assert repair_mojibake(broken) == "國 insei"
    # 이미 정상인 한글/ASCII는 건드리지 않는다.
    assert repair_mojibake("이창호") is None
    assert repair_mojibake("Lee Changho") is None
