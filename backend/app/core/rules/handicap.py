"""Handicap stone placement for 9x9, 13x13, 19x19.

Korean convention (GTP coordinates):

9x9  (2-5 stones, 5 star points total):
  2: C3, G7
  3: + G3
  4: + C7
  5: + E5 (tengen)

13x13 (2-9 stones):
  2: D4, K10
  3: + K4
  4: + D10
  5: + G7 (tengen)
  6: 4 corners + D7, K7  (tengen removed)
  7: + G7 (tengen back)
  8: 4 corners + 4 sides (D7, K7, G4, G10) — no tengen
  9: all 9 star points (adds G7 tengen)

19x19 (2-9 stones) — unchanged from 0.1.0.
"""

from __future__ import annotations

from app.core.rules.board import BLACK, Board
from app.core.rules.sgf_coord import gtp_to_xy

HANDICAP_TABLES: dict[int, dict[int, list[str]]] = {
    9: {
        2: ["C3", "G7"],
        3: ["C3", "G7", "G3"],
        4: ["C3", "G7", "G3", "C7"],
        5: ["C3", "G7", "G3", "C7", "E5"],
    },
    13: {
        2: ["D4", "K10"],
        3: ["D4", "K10", "K4"],
        4: ["D4", "K10", "K4", "D10"],
        5: ["D4", "K10", "K4", "D10", "G7"],
        6: ["D4", "K10", "K4", "D10", "D7", "K7"],
        7: ["D4", "K10", "K4", "D10", "D7", "K7", "G7"],
        8: ["D4", "K10", "K4", "D10", "D7", "K7", "G4", "G10"],
        9: ["D4", "K10", "K4", "D10", "D7", "K7", "G4", "G10", "G7"],
    },
    19: {
        2: ["D16", "Q4"],
        3: ["D16", "Q4", "Q16"],
        4: ["D4", "D16", "Q4", "Q16"],
        5: ["D4", "D16", "Q4", "Q16", "K10"],
        6: ["D4", "D16", "Q4", "Q16", "D10", "Q10"],
        7: ["D4", "D16", "Q4", "Q16", "D10", "Q10", "K10"],
        8: ["D4", "D16", "Q4", "Q16", "D10", "Q10", "K4", "K16"],
        9: ["D4", "D16", "Q4", "Q16", "D10", "Q10", "K4", "K10", "K16"],
    },
}


def apply_handicap(board: Board, stones: int) -> Board:
    """Place handicap stones on board. Returns new board.

    stones=0 is a no-op. Raises ValueError for invalid (size, stones) pairs.
    """
    if stones == 0:
        return board
    size = board.size
    if size not in HANDICAP_TABLES or stones not in HANDICAP_TABLES[size]:
        raise ValueError(f"Invalid handicap for {size}x{size}: {stones}")
    for coord in HANDICAP_TABLES[size][stones]:
        xy = gtp_to_xy(coord, size)
        assert xy is not None
        x, y = xy
        board = board.place(x, y, BLACK)
    return board


def supported_handicaps(size: int) -> list[int]:
    """Return sorted list of valid handicap stone counts for a given size (excludes 0)."""
    return sorted(HANDICAP_TABLES.get(size, {}).keys())
