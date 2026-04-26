"""Capture logic: place a stone and remove captured groups."""

from __future__ import annotations

from app.core.rules.board import BLACK, WHITE, Board


def opponent(color: str) -> str:
    return WHITE if color == BLACK else BLACK


def place_with_captures(
    board: Board, x: int, y: int, color: str
) -> tuple[Board, int]:
    """Place stone at (x,y) with color, remove captured opponent groups.

    Returns (new_board, num_captured).
    Does NOT check legality (ko, occupied, suicide). Caller is responsible.
    """
    # 1. Place stone
    new_board = board.place(x, y, color)
    opp = opponent(color)

    # 2. Collect opponent groups adjacent to the placed stone
    captured_positions: set[tuple[int, int]] = set()
    for nx, ny in new_board.neighbors(x, y):
        if new_board.get(nx, ny) == opp and (nx, ny) not in captured_positions:
            g = new_board.group(nx, ny)
            if len(new_board.liberties(g)) == 0:
                captured_positions |= g

    # 3. Remove captured stones
    final_board = new_board.remove_group(captured_positions)
    return final_board, len(captured_positions)


def is_suicide(board: Board, x: int, y: int, color: str) -> bool:
    """Return True if placing color at (x,y) would be a suicide (no liberties after captures)."""
    new_board, captures = place_with_captures(board, x, y, color)
    if captures > 0:
        return False  # captured some enemy stones -- not suicide
    g = new_board.group(x, y)
    return len(new_board.liberties(g)) == 0
