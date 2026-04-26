"""Immutable Go board of configurable size.

The board is stored as a flat tuple of size*size cells.
Each cell is EMPTY, BLACK, or WHITE.
"""

from __future__ import annotations

from typing import Literal

EMPTY: Literal["."] = "."
BLACK: Literal["B"] = "B"
WHITE: Literal["W"] = "W"

SUPPORTED_SIZES: tuple[int, ...] = (9, 13, 19)

# Backward-compat alias; removed in a later task once all callers are updated.
BOARD_SIZE = 19


class Board:
    """Immutable board. All mutating methods return a new Board."""

    __slots__ = ("size", "_cells")

    def __init__(self, size: int, cells: tuple[str, ...] | None = None) -> None:
        self.size = size
        total = size * size
        if cells is None:
            self._cells: tuple[str, ...] = (EMPTY,) * total
        else:
            assert len(cells) == total
            self._cells = cells

    def _idx(self, x: int, y: int) -> int:
        return y * self.size + x

    def get(self, x: int, y: int) -> str:
        return self._cells[self._idx(x, y)]

    def is_empty(self, x: int, y: int) -> bool:
        return self._cells[self._idx(x, y)] == EMPTY

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        return [
            (x + dx, y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if self.in_bounds(x + dx, y + dy)
        ]

    def place(self, x: int, y: int, color: str) -> Board:
        cells = list(self._cells)
        cells[self._idx(x, y)] = color
        return Board(self.size, tuple(cells))

    def remove(self, x: int, y: int) -> Board:
        cells = list(self._cells)
        cells[self._idx(x, y)] = EMPTY
        return Board(self.size, tuple(cells))

    def remove_group(self, positions: set[tuple[int, int]]) -> Board:
        cells = list(self._cells)
        for x, y in positions:
            cells[self._idx(x, y)] = EMPTY
        return Board(self.size, tuple(cells))

    def group(self, x: int, y: int) -> set[tuple[int, int]]:
        color = self.get(x, y)
        if color == EMPTY:
            return set()
        visited: set[tuple[int, int]] = set()
        frontier = [(x, y)]
        while frontier:
            cx, cy = frontier.pop()
            if (cx, cy) in visited:  # pragma: no cover
                continue
            visited.add((cx, cy))
            for nx, ny in self.neighbors(cx, cy):
                if (nx, ny) not in visited and self.get(nx, ny) == color:
                    frontier.append((nx, ny))
        return visited

    def liberties(self, group: set[tuple[int, int]]) -> set[tuple[int, int]]:
        libs: set[tuple[int, int]] = set()
        for x, y in group:
            for nx, ny in self.neighbors(x, y):
                if self.get(nx, ny) == EMPTY:
                    libs.add((nx, ny))
        return libs

    def is_alive(self, x: int, y: int) -> bool:
        g = self.group(x, y)
        return len(self.liberties(g)) > 0

    def __hash__(self) -> int:
        return hash((self.size, self._cells))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Board):
            return NotImplemented
        return self.size == other.size and self._cells == other._cells

    def __repr__(self) -> str:  # pragma: no cover
        rows = []
        for y in range(self.size):
            rows.append(" ".join(self._cells[y * self.size : (y + 1) * self.size]))
        return "\n".join(rows)
