# SGF 파싱·정제·메타 추출 — 프로 기보를 본선 수순만 남긴 정제 SGF로 변환한다.
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from sgfmill import sgf

# GTP 열 문자 — 'I'를 건너뛴다.
_GTP_COLS = "ABCDEFGHJKLMNOPQRST"
_VALID_SIZES = {9, 13, 19}


class InvalidProSgf(ValueError):
    """SGF를 프로 기보로 적재할 수 없을 때 발생."""


@dataclass(frozen=True)
class ProMove:
    move_number: int
    color: str  # 'B' | 'W'
    coord: str | None  # GTP 좌표, 패스는 None


@dataclass(frozen=True)
class ParsedProGame:
    black_player: str
    white_player: str
    black_rank: str | None
    white_rank: str | None
    event: str | None
    game_date: date | None
    result: str | None
    board_size: int
    handicap: int
    komi: float
    move_count: int
    clean_sgf: str
    content_hash: str
    moves: list[ProMove]


def _point_to_gtp(point: tuple[int, int] | None) -> str | None:
    if point is None:
        return None
    row, col = point
    return f"{_GTP_COLS[col]}{row + 1}"


def _parse_dt(dt: str | None) -> date | None:
    if not dt:
        return None
    head = dt.split(",")[0].strip()
    try:
        return date.fromisoformat(head)
    except ValueError:
        return None


def _build_clean_sgf(
    *,
    size: int,
    komi: float,
    handicap: int,
    setup_black: list[tuple[int, int]],
    moves: list[tuple[str, tuple[int, int] | None]],
    meta: dict[str, str | None],
) -> bytes:
    """본선 수순과 화이트리스트 메타만 담은 새 SGF를 직렬화한다.
    변화도·해설은 새로 만든 게임 객체엔 애초에 들어가지 않는다."""
    g = sgf.Sgf_game(size=size)
    root = g.get_root()
    root.set("KM", komi)
    for ident, val in meta.items():
        if val:
            root.set(ident, val)
    if handicap:
        root.set("HA", handicap)
    if setup_black:
        root.set("AB", setup_black)
    for color, point in moves:
        node = g.extend_main_sequence()
        node.set_move(color, point)
    return bytes(g.serialise())


def parse_pro_sgf(sgf_text: str) -> ParsedProGame:
    """SGF 텍스트를 파싱해 정제·메타·수순을 담은 ParsedProGame을 반환.
    적재 불가능한 입력은 InvalidProSgf를 던진다."""
    try:
        game = sgf.Sgf_game.from_bytes(sgf_text.encode("utf-8"))
    except ValueError as e:
        raise InvalidProSgf(f"SGF 파싱 실패: {e}") from e

    size = game.get_size()
    if size not in _VALID_SIZES:
        raise InvalidProSgf(f"지원하지 않는 판 크기: {size}")

    root = game.get_root()

    def _opt(ident: str) -> str | None:
        if root.has_property(ident):
            text = str(root.get(ident)).strip()
            return text or None
        return None

    black_player = _opt("PB") or "흑"
    white_player = _opt("PW") or "백"
    dt_raw = _opt("DT")
    black_rank = _opt("BR")
    white_rank = _opt("WR")
    event = _opt("EV")
    result = _opt("RE")

    # get_komi()은 KM이 없으면 ValueError가 아니라 0.0을 돌려준다.
    # KM 자체가 없으면 한국 룰 기본값 6.5로 폴백한다.
    if root.has_property("KM"):
        try:
            komi = game.get_komi()
        except ValueError:
            komi = 6.5
    else:
        komi = 6.5
    handicap = game.get_handicap() or 0

    raw_moves: list[tuple[str, tuple[int, int] | None]] = []
    for node in game.get_main_sequence():
        color, point = node.get_move()
        if color is None:
            continue
        raw_moves.append((color, point))
    if not raw_moves:
        raise InvalidProSgf("착수가 없는 SGF")

    setup_black, _white, _empty = root.get_setup_stones()

    clean_bytes = _build_clean_sgf(
        size=size,
        komi=komi,
        handicap=handicap,
        setup_black=sorted(setup_black),
        moves=raw_moves,
        meta={
            "PB": black_player,
            "PW": white_player,
            "BR": black_rank,
            "WR": white_rank,
            "EV": event,
            "DT": dt_raw,
            "RE": result,
        },
    )
    clean_sgf = clean_bytes.decode("utf-8")

    moves = [
        ProMove(
            move_number=i + 1,
            color=color.upper(),
            coord=_point_to_gtp(point),
        )
        for i, (color, point) in enumerate(raw_moves)
    ]

    return ParsedProGame(
        black_player=black_player,
        white_player=white_player,
        black_rank=black_rank,
        white_rank=white_rank,
        event=event,
        game_date=_parse_dt(dt_raw),
        result=result,
        board_size=size,
        handicap=handicap,
        komi=komi,
        move_count=len(moves),
        clean_sgf=clean_sgf,
        content_hash=hashlib.sha256(clean_bytes).hexdigest(),
        moves=moves,
    )
