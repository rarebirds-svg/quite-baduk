"""Handicap stone placement for 19x19 board.

Standard Korean handicap positions (using GTP coordinates):
  2: D16, Q4
  3: D16, Q4, Q16
  4: D4,  D16, Q4, Q16
  5: 4-point + K10 (tengen)
  6: D4, D16, Q4, Q16, D10, Q10
  7: 6-point + K10
  8: D4, D16, Q4, Q16, D10, Q10, K4, K16
  9: 8-point + K10
"""

from __future__ import annotations

from app.core.rules.board import BLACK, Board
from app.core.rules.sgf_coord import gtp_to_xy

HANDICAP_COORDS: dict[int, list[str]] = {
    2: ["D16", "Q4"],
    3: ["D16", "Q4", "Q16"],
    4: ["D4", "D16", "Q4", "Q16"],
    5: ["D4", "D16", "Q4", "Q16", "K10"],
    6: ["D4", "D16", "Q4", "Q16", "D10", "Q10"],
    7: ["D4", "D16", "Q4", "Q16", "D10", "Q10", "K10"],
    8: ["D4", "D16", "Q4", "Q16", "D10", "Q10", "K4", "K16"],
    9: ["D4", "D16", "Q4", "Q16", "D10", "Q10", "K4", "K10", "K16"],
}


def apply_handicap(board: Board, stones: int) -> Board:
    """Place handicap stones on board. Returns new board.

    stones=0 means even game (no-op).
    Raises ValueError for invalid stone counts.
    """
    if stones == 0:
        return board
    if stones not in HANDICAP_COORDS:
        raise ValueError(f"Handicap must be 0 or 2-9, got {stones}")
    for coord in HANDICAP_COORDS[stones]:
        xy = gtp_to_xy(coord)
        assert xy is not None
        x, y = xy
        board = board.place(x, y, BLACK)
    return board
