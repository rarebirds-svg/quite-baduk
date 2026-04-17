"""Immutable 19x19 Go board.

The board is stored as a flat tuple of 19*19 cells.
Each cell is EMPTY, BLACK, or WHITE.
"""

from __future__ import annotations

EMPTY = "."
BLACK = "B"
WHITE = "W"
BOARD_SIZE = 19
_TOTAL = BOARD_SIZE * BOARD_SIZE


def _idx(x: int, y: int) -> int:
    return y * BOARD_SIZE + x


class Board:
    """Immutable board. All mutating methods return a new Board."""

    __slots__ = ("_cells",)

    def __init__(self, cells: tuple[str, ...] | None = None) -> None:
        if cells is None:
            self._cells: tuple[str, ...] = (EMPTY,) * _TOTAL
        else:
            assert len(cells) == _TOTAL
            self._cells = cells

    # -- access ---------------------------------------------------------------

    def get(self, x: int, y: int) -> str:
        return self._cells[_idx(x, y)]

    def is_empty(self, x: int, y: int) -> bool:
        return self._cells[_idx(x, y)] == EMPTY

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

    def neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        return [
            (x + dx, y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if self.in_bounds(x + dx, y + dy)
        ]

    # -- mutation (returns new Board) ----------------------------------------

    def place(self, x: int, y: int, color: str) -> "Board":
        """Place a stone without checking legality or captures. Returns new Board."""
        cells = list(self._cells)
        cells[_idx(x, y)] = color
        return Board(tuple(cells))

    def remove(self, x: int, y: int) -> "Board":
        """Remove a stone. Returns new Board."""
        cells = list(self._cells)
        cells[_idx(x, y)] = EMPTY
        return Board(tuple(cells))

    def remove_group(self, positions: set[tuple[int, int]]) -> "Board":
        """Remove all stones at given positions. Returns new Board."""
        cells = list(self._cells)
        for x, y in positions:
            cells[_idx(x, y)] = EMPTY
        return Board(tuple(cells))

    # -- group / liberty logic -----------------------------------------------

    def group(self, x: int, y: int) -> set[tuple[int, int]]:
        """BFS to find all connected stones of the same color as (x,y)."""
        color = self.get(x, y)
        if color == EMPTY:
            return set()
        visited: set[tuple[int, int]] = set()
        frontier = [(x, y)]
        while frontier:
            cx, cy = frontier.pop()
            if (cx, cy) in visited:  # pragma: no cover — defensive; neighbors filter prevents re-push
                continue
            visited.add((cx, cy))
            for nx, ny in self.neighbors(cx, cy):
                if (nx, ny) not in visited and self.get(nx, ny) == color:
                    frontier.append((nx, ny))
        return visited

    def liberties(self, group: set[tuple[int, int]]) -> set[tuple[int, int]]:
        """Return set of empty points adjacent to the group."""
        libs: set[tuple[int, int]] = set()
        for x, y in group:
            for nx, ny in self.neighbors(x, y):
                if self.get(nx, ny) == EMPTY:
                    libs.add((nx, ny))
        return libs

    def is_alive(self, x: int, y: int) -> bool:
        """True if the group containing (x,y) has at least one liberty."""
        g = self.group(x, y)
        return len(self.liberties(g)) > 0

    # -- hashing --------------------------------------------------------------

    def __hash__(self) -> int:
        return hash(self._cells)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Board):
            return NotImplemented
        return self._cells == other._cells

    def __repr__(self) -> str:  # pragma: no cover
        rows = []
        for y in range(BOARD_SIZE):
            rows.append(" ".join(self._cells[y * BOARD_SIZE : (y + 1) * BOARD_SIZE]))
        return "\n".join(rows)
