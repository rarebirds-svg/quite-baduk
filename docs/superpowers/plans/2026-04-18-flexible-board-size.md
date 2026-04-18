# Flexible Board Size Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users create Go games on 9×9, 13×13, or 19×19 boards (previously 19×19 only).

**Architecture:** Replace the module-level `BOARD_SIZE = 19` constant with a per-`Board` instance attribute. Size flows as data through `Board` → `GameState` → `Game` row → WebSocket payload → frontend store. A single `SUPPORTED_SIZES = (9, 13, 19)` constant is the source of truth for the allowed set.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 async, Alembic, pytest; Next.js 14 + TypeScript + Tailwind + Zustand; Vitest; Playwright.

**Spec:** `docs/superpowers/specs/2026-04-18-flexible-board-size-design.md`

---

## Guidelines For the Engineer

- **TDD always**: write the failing test, see it fail, implement, see it pass, commit.
- **One commit per task.** Each task ends with a `git commit`.
- **No backward-compat shims.** This repo is dev-only and we decided to drop existing DB data. Delete code paths you no longer need.
- **No comments unless the "why" is non-obvious.** No "NEW", "changed", or task-referencing comments.
- **Do not rename things that don't need renaming.** `HANDICAP_COORDS` becomes `HANDICAP_TABLES` because its shape genuinely changed; `Board`/`GameState`/`Game` do not get renamed.
- **Verify before claiming success.** Run the command listed in each step and confirm the actual output matches "Expected" before checking off.

Working directory for backend commands: `backend/`. Working directory for frontend commands: `web/`. Working directory for e2e: `e2e/`. The `backend/` venv is at `backend/.venv311`; activate with `source .venv311/bin/activate` from `backend/`.

---

## Task 1: Add `SUPPORTED_SIZES` constant and refactor `Board` to carry `size`

**Files:**
- Modify: `backend/app/core/rules/board.py`
- Modify: `backend/tests/rules/test_board.py`

- [ ] **Step 1: Write a failing test that creates a 9×9 board**

Append to `backend/tests/rules/test_board.py`:

```python
import pytest
from app.core.rules.board import BLACK, EMPTY, WHITE, Board, SUPPORTED_SIZES


@pytest.mark.parametrize("size", SUPPORTED_SIZES)
def test_empty_board_any_size(size):
    b = Board(size)
    assert b.size == size
    for y in range(size):
        for x in range(size):
            assert b.get(x, y) == EMPTY


@pytest.mark.parametrize("size", SUPPORTED_SIZES)
def test_in_bounds_any_size(size):
    b = Board(size)
    assert b.in_bounds(0, 0)
    assert b.in_bounds(size - 1, size - 1)
    assert not b.in_bounds(-1, 0)
    assert not b.in_bounds(size, 0)


def test_board_equality_respects_size():
    assert Board(9) != Board(13)
    assert Board(19) != Board(9)
    assert Board(9) == Board(9)


def test_supported_sizes_contains_9_13_19():
    assert SUPPORTED_SIZES == (9, 13, 19)
```

Also update the top-of-file imports so existing tests continue to work — change line 2 from:

```python
from app.core.rules.board import BLACK, EMPTY, WHITE, Board, BOARD_SIZE
```

to:

```python
from app.core.rules.board import BLACK, EMPTY, WHITE, Board
```

And update `test_board_size` (around line 11) to use `Board(19)` and a local `SIZE = 19`:

```python
def test_board_size_19():
    SIZE = 19
    b = Board(SIZE)
    for y in range(SIZE):
        for x in range(SIZE):
            assert b.get(x, y) == EMPTY
```

Also review this file and update every other `Board()` call to `Board(19)` (it defaulted to 19 before; we're removing the default).

- [ ] **Step 2: Run the new tests to confirm they fail**

From `backend/` (venv activated):

```bash
pytest tests/rules/test_board.py -v
```

Expected: tests named `test_empty_board_any_size`, `test_in_bounds_any_size`, `test_board_equality_respects_size`, `test_supported_sizes_contains_9_13_19` fail with `ImportError` or `AttributeError` on `SUPPORTED_SIZES`/`size`.

- [ ] **Step 3: Rewrite `backend/app/core/rules/board.py` to carry `size`**

Replace the entire file with:

```python
"""Immutable Go board of configurable size.

The board is stored as a flat tuple of size*size cells.
Each cell is EMPTY, BLACK, or WHITE.
"""

from __future__ import annotations

EMPTY = "."
BLACK = "B"
WHITE = "W"

SUPPORTED_SIZES: tuple[int, ...] = (9, 13, 19)


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

    def place(self, x: int, y: int, color: str) -> "Board":
        cells = list(self._cells)
        cells[self._idx(x, y)] = color
        return Board(self.size, tuple(cells))

    def remove(self, x: int, y: int) -> "Board":
        cells = list(self._cells)
        cells[self._idx(x, y)] = EMPTY
        return Board(self.size, tuple(cells))

    def remove_group(self, positions: set[tuple[int, int]]) -> "Board":
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
```

- [ ] **Step 4: Run the new board tests — they should pass, but the rest of the suite will have errors**

```bash
pytest tests/rules/test_board.py -v
```

Expected: all tests in `test_board.py` pass.

```bash
pytest -q --tb=no 2>&1 | tail -30
```

Expected: lots of failures in other modules (they still `from app.core.rules.board import BOARD_SIZE` and call `Board()` with no args). That's fine — the next tasks fix them.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rules/board.py backend/tests/rules/test_board.py
git commit -m "refactor(rules): carry board size on Board instance, add SUPPORTED_SIZES"
```

---

## Task 2: Make `sgf_coord` size-aware

**Files:**
- Modify: `backend/app/core/rules/sgf_coord.py`
- Modify: `backend/tests/rules/test_sgf_coord.py`

- [ ] **Step 1: Write failing tests for size-parameterized coord conversion**

Replace the content of `backend/tests/rules/test_sgf_coord.py` with:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/rules/test_sgf_coord.py -v
```

Expected: FAIL with TypeError because `gtp_to_xy`/`xy_to_gtp` take only one positional argument.

- [ ] **Step 3: Rewrite `backend/app/core/rules/sgf_coord.py`**

Replace the entire file with:

```python
"""GTP coordinate <-> (x, y) conversion.

GTP coordinate format: letter (A-T, skipping I) + row number (1=bottom).
Internal format: (x, y) where x=column (0=A), y=row (0=top).

Examples (size=19):
  A1  -> (0, 18)   # bottom-left
  A19 -> (0,  0)   # top-left
  T19 -> (18, 0)   # top-right
"""

COLS = "ABCDEFGHJKLMNOPQRST"  # 19 letters, I omitted; sliced by `size`


def gtp_to_xy(coord: str, size: int) -> tuple[int, int] | None:
    """Convert GTP coordinate string to (x, y).

    Returns None for 'pass'. Raises ValueError for invalid input or out-of-range.
    """
    if coord.lower() == "pass":
        return None
    coord = coord.upper()
    if len(coord) < 2:
        raise ValueError(f"Invalid GTP coordinate: {coord!r}")
    col_letter = coord[0]
    cols = COLS[:size]
    if col_letter not in cols:
        raise ValueError(f"Invalid column letter: {col_letter!r}")
    x = cols.index(col_letter)
    row_num = int(coord[1:])
    if not (1 <= row_num <= size):
        raise ValueError(f"Row number out of range: {row_num}")
    y = size - row_num
    return (x, y)


def xy_to_gtp(x: int, y: int, size: int) -> str:
    """Convert (x, y) to GTP coordinate string."""
    if not (0 <= x < size and 0 <= y < size):
        raise ValueError(f"Coordinates out of range: ({x}, {y})")
    cols = COLS[:size]
    col_letter = cols[x]
    row_num = size - y
    return f"{col_letter}{row_num}"
```

- [ ] **Step 4: Run the sgf_coord tests**

```bash
pytest tests/rules/test_sgf_coord.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rules/sgf_coord.py backend/tests/rules/test_sgf_coord.py
git commit -m "refactor(rules): make sgf_coord functions take explicit size"
```

---

## Task 3: Update `handicap.py` with per-size tables

**Files:**
- Modify: `backend/app/core/rules/handicap.py`
- Modify: `backend/tests/rules/test_handicap.py`

- [ ] **Step 1: Write failing tests for 9×9 and 13×13 handicap**

Replace the content of `backend/tests/rules/test_handicap.py` with:

```python
import pytest

from app.core.rules.board import BLACK, EMPTY, Board
from app.core.rules.handicap import HANDICAP_TABLES, apply_handicap
from app.core.rules.sgf_coord import gtp_to_xy


def _black_count(b: Board) -> int:
    return sum(1 for y in range(b.size) for x in range(b.size) if b.get(x, y) == BLACK)


def test_handicap_tables_supported_sizes():
    assert set(HANDICAP_TABLES.keys()) == {9, 13, 19}


def test_handicap_zero_noop():
    for size in (9, 13, 19):
        b = Board(size)
        assert apply_handicap(b, 0) is b


@pytest.mark.parametrize("size,stones", [
    (9, 2), (9, 3), (9, 4), (9, 5),
    (13, 2), (13, 3), (13, 4), (13, 5), (13, 6), (13, 7), (13, 8), (13, 9),
    (19, 2), (19, 3), (19, 4), (19, 5), (19, 6), (19, 7), (19, 8), (19, 9),
])
def test_handicap_places_correct_number_of_black_stones(size, stones):
    b = Board(size)
    b2 = apply_handicap(b, stones)
    assert _black_count(b2) == stones


def test_handicap_9_specific_coords():
    b = apply_handicap(Board(9), 5)
    for coord in ("C3", "G7", "G3", "C7", "E5"):
        xy = gtp_to_xy(coord, 9)
        assert xy is not None
        assert b.get(*xy) == BLACK


def test_handicap_13_9_stones_are_all_stars():
    b = apply_handicap(Board(13), 9)
    for coord in ("D4", "K10", "K4", "D10", "D7", "K7", "G4", "G10", "G7"):
        xy = gtp_to_xy(coord, 13)
        assert xy is not None
        assert b.get(*xy) == BLACK


def test_handicap_invalid_raises():
    with pytest.raises(ValueError):
        apply_handicap(Board(9), 6)        # 9x9 only supports 2-5
    with pytest.raises(ValueError):
        apply_handicap(Board(13), 10)
    with pytest.raises(ValueError):
        apply_handicap(Board(19), 1)
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
pytest tests/rules/test_handicap.py -v
```

Expected: FAIL — `HANDICAP_TABLES` does not exist; `apply_handicap` signature still uses `HANDICAP_COORDS`.

- [ ] **Step 3: Rewrite `backend/app/core/rules/handicap.py`**

Replace the entire file with:

```python
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
```

- [ ] **Step 4: Run handicap tests**

```bash
pytest tests/rules/test_handicap.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rules/handicap.py backend/tests/rules/test_handicap.py
git commit -m "feat(rules): handicap tables for 9x9 and 13x13"
```

---

## Task 4: Update `scoring.py` to use `board.size`

**Files:**
- Modify: `backend/app/core/rules/scoring.py`
- Modify: `backend/tests/rules/test_scoring.py`

- [ ] **Step 1: Add a failing 9×9 scoring test**

Append to `backend/tests/rules/test_scoring.py`:

```python
from app.core.rules.board import BLACK, Board, WHITE
from app.core.rules.scoring import score_game


def test_score_game_9x9_empty_board_white_wins_by_komi():
    b = Board(9)
    r = score_game(b, black_captures=0, white_captures=0, komi=6.5)
    assert r.black_territory == 0
    assert r.white_territory == 0
    assert r.winner == WHITE
    assert r.margin == 6.5


def test_score_game_13x13_small_territory():
    # Place a single black stone in a corner; all other points go to no-one
    # (border_colors contains nothing since there are no white stones).
    b = Board(13).place(0, 0, BLACK)
    r = score_game(b, black_captures=0, white_captures=0, komi=6.5)
    # 13*13 - 1 = 168 empty points; they touch only BLACK → all black territory.
    assert r.black_territory == 168
```

Also update any existing tests in this file that call `Board()` (no args) to `Board(19)`.

- [ ] **Step 2: Run to see the new tests fail**

```bash
pytest tests/rules/test_scoring.py -v
```

Expected: FAIL — `scoring.py` still imports `BOARD_SIZE` and iterates `range(BOARD_SIZE)`.

- [ ] **Step 3: Edit `backend/app/core/rules/scoring.py`**

Change the import at the top from:

```python
from app.core.rules.board import BLACK, EMPTY, WHITE, Board, BOARD_SIZE
```

to:

```python
from app.core.rules.board import BLACK, EMPTY, WHITE, Board
```

And change the flood loop (around lines 60-61) from:

```python
    for y in range(BOARD_SIZE):
        for x in range(BOARD_SIZE):
```

to:

```python
    for y in range(board.size):
        for x in range(board.size):
```

- [ ] **Step 4: Run all scoring tests**

```bash
pytest tests/rules/test_scoring.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rules/scoring.py backend/tests/rules/test_scoring.py
git commit -m "refactor(rules): scoring iterates over board.size"
```

---

## Task 5: Update `engine.py` and `captures.py` call sites

**Files:**
- Modify: `backend/app/core/rules/engine.py`
- Modify: `backend/tests/rules/test_engine.py`
- Modify: `backend/tests/rules/test_captures.py`

(`ko.py` and `captures.py` use only `Board` methods and need no changes themselves; their tests do.)

- [ ] **Step 1: Fix up existing engine/captures tests that call `Board()` or pass `BOARD_SIZE`**

In `backend/tests/rules/test_engine.py` and `backend/tests/rules/test_captures.py`, update every `Board()` to `Board(19)`, remove any `BOARD_SIZE` imports, and replace any `gtp_to_xy(coord)` with `gtp_to_xy(coord, 19)` and any `xy_to_gtp(x, y)` with `xy_to_gtp(x, y, 19)`.

Also add one parameterized integration test at the bottom of `test_engine.py`:

```python
import pytest
from app.core.rules.board import BLACK, Board, SUPPORTED_SIZES
from app.core.rules.engine import GameState, Move, play


@pytest.mark.parametrize("size", SUPPORTED_SIZES)
def test_play_one_move_each_size(size):
    state = GameState(board=Board(size))
    coord = "A" + str(size)  # top-left
    new_state = play(state, Move(color=BLACK, coord=coord))
    assert new_state.board.size == size
    assert new_state.board.get(0, 0) == BLACK
```

- [ ] **Step 2: Run the tests to see what still fails**

```bash
pytest tests/rules/test_engine.py tests/rules/test_captures.py -v
```

Expected: the new `test_play_one_move_each_size` fails because `engine.py` still imports `BOARD_SIZE` and because `gtp_to_xy` is called with one argument inside `engine.play`. Other tests may pass or fail depending on your edits.

- [ ] **Step 3: Edit `backend/app/core/rules/engine.py`**

(a) Change the top import from:

```python
from app.core.rules.board import BLACK, EMPTY, WHITE, Board, BOARD_SIZE
```

to:

```python
from app.core.rules.board import BLACK, EMPTY, WHITE, Board
```

(b) Remove the default `Board()` in the `GameState` dataclass — a game state now always has a specific board. Change:

```python
@dataclass
class GameState:
    board: Board = field(default_factory=Board)
```

to:

```python
@dataclass
class GameState:
    board: Board = field(default_factory=lambda: Board(19))
```

(Dev-convenience default: 19. Production callers always pass a specific board.)

(c) In `play()`, replace `gtp_to_xy(move.coord)` with `gtp_to_xy(move.coord, state.board.size)`.

(d) In `build_sgf`, remove the `board_size` parameter and read the size from state. Change:

```python
def build_sgf(state: GameState, board_size: int = BOARD_SIZE, result: str = "") -> str:
```

to:

```python
def build_sgf(state: GameState, result: str = "") -> str:
```

and update the `gtp_to_xy(move.coord)` call inside to `gtp_to_xy(move.coord, state.board.size)`, and the final return to use `state.board.size`:

```python
    return f"(;GM[1]FF[4]SZ[{state.board.size}]KM[{komi_str}]{result_prop}{moves_sgf})"
```

- [ ] **Step 4: Run the rules suite**

```bash
pytest tests/rules/ -v
```

Expected: all rules tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/rules/engine.py backend/tests/rules/
git commit -m "refactor(rules): engine reads size from state.board; update tests"
```

---

## Task 6: Update KataGo mock to track board size correctly

**Files:**
- Modify: `backend/app/core/katago/mock.py`
- Modify: `backend/tests/katago/test_mock_adapter.py`

- [ ] **Step 1: Add failing tests for size-aware mock**

Append to `backend/tests/katago/test_mock_adapter.py`:

```python
import pytest
from app.core.katago.mock import MockKataGoAdapter


@pytest.mark.asyncio
async def test_mock_boardsize_resets_and_uses_size_for_genmove():
    a = MockKataGoAdapter()
    await a.start()
    await a.set_boardsize(9)
    assert a.board.size == 9
    # genmove should pick first empty on 9x9 (A9 = top-left), not out-of-range for 9x9
    m = await a.genmove("B")
    assert m == "A9"


@pytest.mark.asyncio
async def test_mock_switches_size_between_games():
    a = MockKataGoAdapter()
    await a.start()
    await a.set_boardsize(19)
    await a.set_boardsize(13)
    assert a.board.size == 13
    m = await a.genmove("B")
    assert m == "A13"
```

- [ ] **Step 2: Run to see failures**

```bash
pytest tests/katago/test_mock_adapter.py -v
```

Expected: import error or size mismatch — the current `Board()` call is wrong and `BOARD_SIZE` import will fail.

- [ ] **Step 3: Edit `backend/app/core/katago/mock.py`**

(a) Change the import block at the top:

```python
from app.core.rules.board import BLACK, WHITE, Board, BOARD_SIZE
from app.core.rules.sgf_coord import xy_to_gtp
```

to:

```python
from app.core.rules.board import BLACK, WHITE, Board
from app.core.rules.sgf_coord import gtp_to_xy, xy_to_gtp
```

(b) Change `__init__`:

```python
    def __init__(self) -> None:
        self.board = Board()
        self.board_size = BOARD_SIZE
```

to:

```python
    def __init__(self) -> None:
        self.board_size = 19
        self.board = Board(self.board_size)
```

(c) Change `clear_board`:

```python
    async def clear_board(self) -> None:
        self.board = Board()
        self.move_history.clear()
```

to:

```python
    async def clear_board(self) -> None:
        self.board = Board(self.board_size)
        self.move_history.clear()
```

(d) Change `set_boardsize`:

```python
    async def set_boardsize(self, size: int) -> None:
        self.board_size = size
        self.board = Board()
```

to:

```python
    async def set_boardsize(self, size: int) -> None:
        self.board_size = size
        self.board = Board(size)
        self.move_history.clear()
```

(e) In both `play` and `undo`, change `gtp_to_xy(coord)` to `gtp_to_xy(coord, self.board_size)`. Also change `xy_to_gtp(x, y)` in `genmove` and `analyze` to `xy_to_gtp(x, y, self.board_size)`.

- [ ] **Step 4: Run mock tests**

```bash
pytest tests/katago/test_mock_adapter.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/katago/mock.py backend/tests/katago/test_mock_adapter.py
git commit -m "refactor(katago): mock adapter tracks board_size correctly"
```

---

## Task 7: Threading `board_size` through KataGo real adapter's replay state

**Files:**
- Modify: `backend/app/core/katago/adapter.py`

There are no dedicated adapter tests that exercise the real subprocess (tests use the mock). This change is small, safety-oriented. Review and edit only.

- [ ] **Step 1: Verify current behavior — no new test needed**

Read `backend/app/core/katago/adapter.py` lines 65-73 (the `_ReplayState` dataclass) and lines 214-218 (`set_boardsize`). The replay state already stores `boardsize` and replays it; `set_boardsize` already clears plays. No structural change needed.

Expected conclusion: the real adapter is already size-safe at the boundary. Skip to Step 2 (kept as a verification step — no code change). Do not commit.

- [ ] **Step 2: Move on**

No code or test change here. Proceed to Task 8.

---

## Task 8: Add `board_size` to the DB `Game` model and migration

**Files:**
- Modify: `backend/app/models/game.py`
- Create: `backend/migrations/versions/0002_board_size.py`
- Modify: `backend/tests/test_models.py`

Because Q4=B (drop existing data), the migration is destructive: drop and recreate `games`, `moves`, `analyses`.

- [ ] **Step 1: Add a failing model test**

Append to `backend/tests/test_models.py` (if this file exists; otherwise add it):

```python
import pytest
from sqlalchemy import select

from app.models import Game


@pytest.mark.asyncio
async def test_game_persists_board_size(db_session):
    game = Game(
        user_id=1,
        ai_rank="5k",
        handicap=0,
        komi=6.5,
        user_color="black",
        status="active",
        board_size=9,
    )
    db_session.add(game)
    await db_session.commit()

    res = await db_session.execute(select(Game).where(Game.id == game.id))
    loaded = res.scalar_one()
    assert loaded.board_size == 9
```

If `db_session` is not already a fixture in `conftest.py`, check `backend/tests/conftest.py` — it should provide an async DB session fixture for the FastAPI test client; reuse that pattern.

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL — `Game` has no `board_size` attribute.

- [ ] **Step 3: Add the column to the model**

Edit `backend/app/models/game.py` — insert, right after the `handicap` line:

```python
    board_size: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 4: Write the Alembic migration**

Create `backend/migrations/versions/0002_board_size.py`:

```python
"""Drop legacy tables and add board_size to games.

Dev-only destructive migration: wipes existing games/moves/analyses.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_analyses_game_move", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_moves_game", table_name="moves")
    op.drop_table("moves")
    op.drop_index("ix_games_user_status", table_name="games")
    op.drop_table("games")

    op.create_table(
        "games",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("ai_rank", sa.String(8), nullable=False),
        sa.Column("handicap", sa.Integer, nullable=False, server_default="0"),
        sa.Column("board_size", sa.Integer, nullable=False),
        sa.Column("komi", sa.Float, nullable=False, server_default="6.5"),
        sa.Column("user_color", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("winner", sa.String(8), nullable=True),
        sa.Column("move_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("sgf_cache", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_games_user_status", "games", ["user_id", "status"])

    op.create_table(
        "moves",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("game_id", sa.Integer, nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("color", sa.String(2), nullable=False),
        sa.Column("coord", sa.String(4), nullable=True),
        sa.Column("captures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_undone", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("played_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "move_number", name="uq_game_move"),
    )
    op.create_index("ix_moves_game", "moves", ["game_id", "move_number"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("game_id", sa.Integer, nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "move_number", name="uq_analysis_game_move"),
    )
    op.create_index("ix_analyses_game_move", "analyses", ["game_id", "move_number"])


def downgrade() -> None:
    op.drop_index("ix_analyses_game_move", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_moves_game", table_name="moves")
    op.drop_table("moves")
    op.drop_index("ix_games_user_status", table_name="games")
    op.drop_table("games")

    op.create_table(
        "games",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("ai_rank", sa.String(8), nullable=False),
        sa.Column("handicap", sa.Integer, nullable=False, server_default="0"),
        sa.Column("komi", sa.Float, nullable=False, server_default="6.5"),
        sa.Column("user_color", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("winner", sa.String(8), nullable=True),
        sa.Column("move_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("sgf_cache", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_games_user_status", "games", ["user_id", "status"])

    op.create_table(
        "moves",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("game_id", sa.Integer, nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("color", sa.String(2), nullable=False),
        sa.Column("coord", sa.String(4), nullable=True),
        sa.Column("captures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_undone", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("played_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "move_number", name="uq_game_move"),
    )
    op.create_index("ix_moves_game", "moves", ["game_id", "move_number"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("game_id", sa.Integer, nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "move_number", name="uq_analysis_game_move"),
    )
    op.create_index("ix_analyses_game_move", "analyses", ["game_id", "move_number"])
```

- [ ] **Step 5: Apply the migration locally and run the new test**

```bash
# from backend/
rm -f data/dev.db
alembic upgrade head
pytest tests/test_models.py -v
```

Expected: migration runs clean; test passes.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/game.py backend/migrations/versions/0002_board_size.py backend/tests/test_models.py
git commit -m "feat(db): add board_size column to games (drop+recreate legacy tables)"
```

---

## Task 9: Update `game_service.create_game` to take `board_size`

**Files:**
- Modify: `backend/app/services/game_service.py`

- [ ] **Step 1: Read the service before editing**

Open `backend/app/services/game_service.py` and locate:
- Top imports referring to `HANDICAP_COORDS` (line 22).
- `create_game` (lines 58-101).
- `_replay_state` (lines 276-288) — builds a `GameState` from DB rows; must now pass `Board(game.board_size)`.
- `resign_game` (line 246) — calls `build_sgf(state, result=...)` which lost its `board_size` param.

- [ ] **Step 2: Edit imports**

Change:

```python
from app.core.rules.handicap import apply_handicap, HANDICAP_COORDS
```

to:

```python
from app.core.rules.board import Board
from app.core.rules.handicap import HANDICAP_TABLES, apply_handicap
```

- [ ] **Step 3: Rewrite `create_game`'s signature and body**

Replace the existing `create_game` with:

```python
async def create_game(
    db: AsyncSession,
    *,
    user: User,
    ai_rank: str,
    handicap: int,
    user_color: str,
    board_size: int,
) -> Game:
    if board_size not in HANDICAP_TABLES:
        raise GameError("INVALID_BOARD_SIZE", str(board_size))
    valid_handicaps = (0,) + tuple(HANDICAP_TABLES[board_size].keys())
    if handicap not in valid_handicaps:
        raise GameError("INVALID_HANDICAP", str(handicap))
    if user_color not in ("black", "white"):
        raise GameError("INVALID_COLOR", user_color)
    komi = 0.5 if handicap > 0 else 6.5
    if handicap > 0:
        user_color = "black"

    game = Game(
        user_id=user.id,
        ai_rank=ai_rank,
        handicap=handicap,
        board_size=board_size,
        komi=komi,
        user_color=user_color,
        status="active",
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)

    adapter = get_adapter()
    await adapter.start()
    await adapter.set_boardsize(board_size)
    await adapter.set_komi(komi)
    cfg = rank_to_config(ai_rank)
    await adapter.set_profile(cfg)

    state = GameState(board=Board(board_size), komi=komi)
    if handicap > 0:
        state.board = apply_handicap(state.board, handicap)
        for coord in HANDICAP_TABLES[board_size][handicap]:
            await adapter.play(BLACK, coord)
        state.to_move = WHITE

    cache_state(game.id, state)
    return game
```

Note: we removed the redundant `clear_board()` before `set_boardsize()` — `set_boardsize` already clears the board in both the real and mock adapter.

- [ ] **Step 4: Update `_replay_state` to use `Board(game.board_size)`**

Replace `_replay_state` with:

```python
async def _replay_state(db: AsyncSession, game: Game) -> GameState:
    """Rebuild GameState by replaying non-undone moves."""
    state = GameState(board=Board(game.board_size), komi=game.komi)
    if game.handicap > 0:
        state.board = apply_handicap(state.board, game.handicap)
        state.to_move = WHITE
    res = await db.execute(
        select(MoveRow).where(MoveRow.game_id == game.id, MoveRow.is_undone == False).order_by(MoveRow.move_number.asc())  # noqa: E712
    )
    for m in res.scalars().all():
        coord = m.coord if m.coord else "pass"
        state = play(state, Move(color=m.color, coord=coord))  # type: ignore[arg-type]
    return state
```

- [ ] **Step 5: Sanity check that no call site still passes `board_size=` to `build_sgf`**

```bash
grep -rn "build_sgf(" backend/app
```

Expected: `build_sgf(state, result=...)` everywhere. If any call still passes a positional `board_size`, fix it.

- [ ] **Step 6: Commit (tests come with the API task next)**

```bash
git add backend/app/services/game_service.py
git commit -m "feat(service): create_game takes board_size, threads it to state/adapter"
```

---

## Task 10: Update Pydantic schemas and API endpoint

**Files:**
- Modify: `backend/app/schemas/game.py`
- Modify: `backend/app/api/games.py`
- Modify: `backend/tests/api/test_games.py`

- [ ] **Step 1: Write failing API tests**

Replace the body of `backend/tests/api/test_games.py` (keep the helpers at the top) with tests that cover each size. Full replacement contents:

```python
import pytest
from httpx import AsyncClient


async def _signup(client: AsyncClient, email: str = "p@example.com") -> None:
    await client.post(
        "/api/auth/signup",
        json={"email": email, "password": "password1", "display_name": "P"},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [9, 13, 19])
async def test_create_game_each_size(client: AsyncClient, size: int) -> None:
    await _signup(client, email=f"u{size}@example.com")
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black", "board_size": size},
    )
    assert r.status_code == 201, r.text
    g = r.json()
    assert g["board_size"] == size
    assert g["komi"] == 6.5


@pytest.mark.asyncio
async def test_create_game_default_board_size_is_19(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["board_size"] == 19


@pytest.mark.asyncio
async def test_create_game_rejects_invalid_size(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "5k", "handicap": 0, "user_color": "black", "board_size": 7},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_9x9_rejects_handicap_6(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "1d", "handicap": 6, "user_color": "black", "board_size": 9},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "INVALID_HANDICAP"


@pytest.mark.asyncio
async def test_create_handicap_game_13(client: AsyncClient) -> None:
    await _signup(client)
    r = await client.post(
        "/api/games",
        json={"ai_rank": "1d", "handicap": 4, "user_color": "black", "board_size": 13},
    )
    assert r.status_code == 201
    g = r.json()
    assert g["handicap"] == 4
    assert g["komi"] == 0.5
    assert g["board_size"] == 13


@pytest.mark.asyncio
async def test_list_games(client: AsyncClient) -> None:
    await _signup(client)
    await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    await client.post("/api/games", json={"ai_rank": "1k", "handicap": 2, "user_color": "black", "board_size": 9})
    r = await client.get("/api/games")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_cannot_access_other_users_game(client: AsyncClient) -> None:
    await _signup(client, email="u1@example.com")
    r = await client.post("/api/games", json={"ai_rank": "5k", "handicap": 0, "user_color": "black"})
    game_id = r.json()["id"]
    await client.post("/api/auth/logout")
    await _signup(client, email="u2@example.com")
    r2 = await client.get(f"/api/games/{game_id}")
    assert r2.status_code == 403
```

- [ ] **Step 2: Run to see failures**

```bash
pytest tests/api/test_games.py -v
```

Expected: FAIL — the request schema has no `board_size` field and the response DTO doesn't include it.

- [ ] **Step 3: Edit `backend/app/schemas/game.py`**

Change `CreateGameRequest` to:

```python
class CreateGameRequest(BaseModel):
    ai_rank: Rank
    handicap: int = Field(ge=0, le=9)
    user_color: Literal["black", "white"] = "black"
    board_size: Literal[9, 13, 19] = 19
```

Add `board_size: int` to `GameSummary`:

```python
class GameSummary(BaseModel):
    id: int
    ai_rank: str
    handicap: int
    board_size: int
    komi: float
    user_color: str
    status: str
    result: str | None
    winner: str | None
    move_count: int
    started_at: datetime
    finished_at: datetime | None
```

- [ ] **Step 4: Edit `backend/app/api/games.py`**

Replace the `create_game(...)` call inside the `create` endpoint with the new parameter:

```python
    try:
        game = await create_game(
            db,
            user=user,
            ai_rank=body.ai_rank,
            handicap=body.handicap,
            user_color=body.user_color,
            board_size=body.board_size,
        )
    except GameError as e:
        raise HTTPException(status_code=400, detail=e.code)
```

- [ ] **Step 5: Run the API tests**

```bash
pytest tests/api/test_games.py -v
```

Expected: all pass.

- [ ] **Step 6: Run the full backend suite**

```bash
pytest --cov=app --cov-fail-under=80
```

Expected: all tests pass, coverage ≥ 80%. If the rules engine coverage slipped below 100%, add targeted tests until it is back.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/game.py backend/app/api/games.py backend/tests/api/test_games.py
git commit -m "feat(api): accept board_size on POST /api/games"
```

---

## Task 11: Thread `board_size` through the WebSocket state payload

**Files:**
- Modify: `backend/app/api/ws.py`

- [ ] **Step 1: Replace the hardcoded 19×19 serializer**

Edit the top of `backend/app/api/ws.py`. Change:

```python
def _serialize_board(state: GameState) -> str:
    # 361-char: '.', 'B', 'W'
    cells: list[str] = []
    b = state.board
    for y in range(19):
        for x in range(19):
            cells.append(b.get(x, y))
    return "".join(cells)


async def _state_payload(state: GameState, move_count: int) -> dict[str, Any]:
    return {
        "type": "state",
        "board": _serialize_board(state),
        "to_move": state.to_move,
        "move_count": move_count,
        "captures": state.captures,
    }
```

to:

```python
def _serialize_board(state: GameState) -> str:
    """Flatten to a size*size char string of '.', 'B', 'W'."""
    cells: list[str] = []
    b = state.board
    for y in range(b.size):
        for x in range(b.size):
            cells.append(b.get(x, y))
    return "".join(cells)


async def _state_payload(state: GameState, move_count: int) -> dict[str, Any]:
    return {
        "type": "state",
        "board": _serialize_board(state),
        "board_size": state.board.size,
        "to_move": state.to_move,
        "move_count": move_count,
        "captures": state.captures,
    }
```

- [ ] **Step 2: Run the full backend suite**

```bash
pytest
```

Expected: all pass (no new tests needed — existing WS tests exercise this via integration).

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/ws.py
git commit -m "feat(ws): include board_size in state payload; serializer uses board.size"
```

---

## Task 12: Ruff + mypy pass

**Files:** across `backend/`.

- [ ] **Step 1: Run lint and type check**

```bash
ruff check .
mypy app
```

- [ ] **Step 2: Fix anything ruff/mypy reports**

Common issues from this refactor:
- Unused `BOARD_SIZE` imports in files you edited.
- `Board()` calls that now need a size argument.
- `gtp_to_xy` / `xy_to_gtp` calls missing the `size` argument.

Fix inline.

- [ ] **Step 3: Commit lint/type fixes (if any)**

```bash
git add backend/
git commit -m "chore: ruff/mypy fixes after board-size refactor"
```

If there were no fixes needed, skip the commit.

---

## Task 13: Frontend `lib/board.ts` — size-parameterized helpers

**Files:**
- Modify: `web/lib/board.ts`
- Modify: `web/tests/board.test.ts`

- [ ] **Step 1: Write failing tests**

Replace the content of `web/tests/board.test.ts` with:

```ts
import { describe, it, expect } from "vitest";
import { xyToGtp, gtpToXy, starPoints, totalCells } from "@/lib/board";

describe("coord conversion", () => {
  it("round-trips on 19x19", () => {
    for (let x = 0; x < 19; x++) {
      for (let y = 0; y < 19; y++) {
        const g = xyToGtp(x, y, 19);
        expect(gtpToXy(g, 19)).toEqual([x, y]);
      }
    }
  });

  it("round-trips on 13x13", () => {
    expect(xyToGtp(0, 0, 13)).toBe("A13");
    expect(xyToGtp(12, 12, 13)).toBe("N1");
    expect(gtpToXy("G7", 13)).toEqual([6, 6]);
  });

  it("round-trips on 9x9", () => {
    expect(xyToGtp(0, 0, 9)).toBe("A9");
    expect(xyToGtp(8, 8, 9)).toBe("J1");
    expect(gtpToXy("E5", 9)).toEqual([4, 4]);
  });

  it("pass returns null", () => {
    expect(gtpToXy("pass", 19)).toBeNull();
  });

  it("out-of-range returns null", () => {
    expect(gtpToXy("A14", 13)).toBeNull();
    expect(gtpToXy("K1", 9)).toBeNull(); // col K doesn't exist in 9x9 (A-J)
  });
});

describe("star points", () => {
  it("9x9", () => {
    expect(starPoints(9)).toEqual([2, 4, 6]);
  });
  it("13x13", () => {
    expect(starPoints(13)).toEqual([3, 6, 9]);
  });
  it("19x19", () => {
    expect(starPoints(19)).toEqual([3, 9, 15]);
  });
});

describe("totalCells", () => {
  it("n*n", () => {
    expect(totalCells(9)).toBe(81);
    expect(totalCells(13)).toBe(169);
    expect(totalCells(19)).toBe(361);
  });
});
```

- [ ] **Step 2: Run to see failures**

```bash
npm test -- --run tests/board.test.ts
```

Expected: FAIL — `starPoints`, `totalCells` don't exist; `xyToGtp`/`gtpToXy` take the wrong arity.

- [ ] **Step 3: Rewrite `web/lib/board.ts`**

Replace the entire file with:

```ts
export const COLS = "ABCDEFGHJKLMNOPQRST";
export const SUPPORTED_SIZES = [9, 13, 19] as const;
export type BoardSize = typeof SUPPORTED_SIZES[number];

const STAR_POINTS_BY_SIZE: Record<number, number[]> = {
  9: [2, 4, 6],
  13: [3, 6, 9],
  19: [3, 9, 15],
};

export function starPoints(size: number): number[] {
  return STAR_POINTS_BY_SIZE[size] ?? [];
}

export function totalCells(size: number): number {
  return size * size;
}

export function xyToGtp(x: number, y: number, size: number): string {
  return `${COLS[x]}${size - y}`;
}

export function gtpToXy(coord: string, size: number): [number, number] | null {
  if (coord.toLowerCase() === "pass") return null;
  const m = /^([A-HJ-T])(\d+)$/i.exec(coord);
  if (!m) return null;
  const cols = COLS.slice(0, size);
  const x = cols.indexOf(m[1].toUpperCase());
  if (x < 0) return null;
  const row = parseInt(m[2], 10);
  if (row < 1 || row > size) return null;
  const y = size - row;
  return [x, y];
}

export function parseBoard(flat: string): string[] {
  return flat.split("");
}
```

- [ ] **Step 4: Run the tests**

```bash
npm test -- --run tests/board.test.ts
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add web/lib/board.ts web/tests/board.test.ts
git commit -m "refactor(web): size-parameterized board lib helpers"
```

---

## Task 14: Frontend `Board.tsx` takes `size` prop

**Files:**
- Modify: `web/components/Board.tsx`

- [ ] **Step 1: Rewrite the component**

Replace the entire file with:

```tsx
"use client";
import { starPoints, COLS } from "@/lib/board";

interface Props {
  size: number;
  board: string;               // size*size chars
  lastMove?: { x: number; y: number } | null;
  onClick?(x: number, y: number): void;
  disabled?: boolean;
  overlay?: { x: number; y: number; color: string; label?: string }[];
}

const CELL = 30;
const OFFSET = 24;
const LINE = "#3B2412";
const LABEL = "#4A2F17";

export default function Board({ size, board, lastMove, onClick, disabled, overlay }: Props) {
  const SIZE_PX = OFFSET * 2 + CELL * (size - 1);
  const STONE_R = CELL / 2 - 1;
  const cells = board.split("");
  const stars = starPoints(size);

  return (
    <svg
      viewBox={`0 0 ${SIZE_PX} ${SIZE_PX}`}
      className="w-full max-w-[640px] bg-board-bg dark:bg-board-dark rounded-lg shadow-lg"
      role="grid"
      aria-label={`${size}x${size} Go board`}
    >
      <defs>
        <radialGradient id="black-stone" cx="35%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#5a5a5a" />
          <stop offset="60%" stopColor="#1a1a1a" />
          <stop offset="100%" stopColor="#000000" />
        </radialGradient>
        <radialGradient id="white-stone" cx="35%" cy="35%" r="75%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="70%" stopColor="#f2f0eb" />
          <stop offset="100%" stopColor="#cfcac0" />
        </radialGradient>
      </defs>

      {Array.from({ length: size }, (_, i) => (
        <g key={`g-${i}`}>
          <line
            x1={OFFSET}
            y1={OFFSET + i * CELL}
            x2={OFFSET + (size - 1) * CELL}
            y2={OFFSET + i * CELL}
            stroke={LINE}
            strokeWidth={0.9}
          />
          <line
            y1={OFFSET}
            x1={OFFSET + i * CELL}
            y2={OFFSET + (size - 1) * CELL}
            x2={OFFSET + i * CELL}
            stroke={LINE}
            strokeWidth={0.9}
          />
        </g>
      ))}

      {stars.flatMap((sx) =>
        stars.map((sy) => (
          <circle key={`s-${sx}-${sy}`} cx={OFFSET + sx * CELL} cy={OFFSET + sy * CELL} r={3.2} fill={LINE} />
        ))
      )}

      {Array.from({ length: size }, (_, i) => (
        <g key={`lab-${i}`}>
          <text x={OFFSET + i * CELL} y={12} textAnchor="middle" fontSize={10} fontWeight={600} fill={LABEL}>
            {COLS[i]}
          </text>
          <text x={OFFSET + i * CELL} y={SIZE_PX - 4} textAnchor="middle" fontSize={10} fontWeight={600} fill={LABEL}>
            {COLS[i]}
          </text>
          <text x={9} y={OFFSET + i * CELL + 3} textAnchor="start" fontSize={10} fontWeight={600} fill={LABEL}>
            {size - i}
          </text>
          <text x={SIZE_PX - 18} y={OFFSET + i * CELL + 3} textAnchor="start" fontSize={10} fontWeight={600} fill={LABEL}>
            {size - i}
          </text>
        </g>
      ))}

      {cells.map((c, i) => {
        const x = i % size;
        const y = Math.floor(i / size);
        if (c === "B" || c === "W") {
          return (
            <g key={`st-${i}`}>
              <circle cx={OFFSET + x * CELL + 0.8} cy={OFFSET + y * CELL + 1.2} r={STONE_R} fill="rgba(0,0,0,0.22)" />
              <circle
                cx={OFFSET + x * CELL}
                cy={OFFSET + y * CELL}
                r={STONE_R}
                fill={c === "B" ? "url(#black-stone)" : "url(#white-stone)"}
                stroke={c === "W" ? "#8a8579" : "none"}
                strokeWidth={c === "W" ? 0.5 : 0}
              />
            </g>
          );
        }
        return null;
      })}

      {lastMove && (() => {
        const idx = lastMove.y * size + lastMove.x;
        const c = cells[idx];
        const dotFill = c === "B" ? "#ffffff" : "#d0342c";
        return (
          <circle cx={OFFSET + lastMove.x * CELL} cy={OFFSET + lastMove.y * CELL} r={4} fill={dotFill} />
        );
      })()}

      {overlay?.map((o, i) => (
        <g key={`o-${i}`}>
          <circle cx={OFFSET + o.x * CELL} cy={OFFSET + o.y * CELL} r={CELL / 2 - 3} fill={o.color} opacity={0.4} />
          {o.label && (
            <text x={OFFSET + o.x * CELL} y={OFFSET + o.y * CELL + 3} textAnchor="middle" fontSize={9} fontWeight={700} fill="#ffffff">
              {o.label}
            </text>
          )}
        </g>
      ))}

      <rect
        x={OFFSET - CELL / 2}
        y={OFFSET - CELL / 2}
        width={CELL * size}
        height={CELL * size}
        fill="transparent"
        onClick={(e) => {
          if (disabled || !onClick) return;
          const svg = e.currentTarget.ownerSVGElement!;
          const rect = svg.getBoundingClientRect();
          const scale = SIZE_PX / rect.width;
          const px = (e.clientX - rect.left) * scale - OFFSET;
          const py = (e.clientY - rect.top) * scale - OFFSET;
          const x = Math.round(px / CELL);
          const y = Math.round(py / CELL);
          if (x >= 0 && x < size && y >= 0 && y < size) onClick(x, y);
        }}
      />
    </svg>
  );
}
```

- [ ] **Step 2: Run type check**

```bash
npm run type-check
```

Expected: fails at the two pages that render `<Board ... />` without `size` (we fix them in Task 17).

- [ ] **Step 3: Commit**

```bash
git add web/components/Board.tsx
git commit -m "feat(web): Board takes size prop"
```

---

## Task 15: Add `BoardSizePicker` component

**Files:**
- Create: `web/components/BoardSizePicker.tsx`

- [ ] **Step 1: Write the component**

Create `web/components/BoardSizePicker.tsx`:

```tsx
"use client";
import { useT } from "@/lib/i18n";
import { SUPPORTED_SIZES, type BoardSize } from "@/lib/board";

interface Props {
  value: BoardSize;
  onChange: (size: BoardSize) => void;
}

export default function BoardSizePicker({ value, onChange }: Props) {
  const t = useT();
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm">{t("game.boardSize")}</span>
      <div role="radiogroup" aria-label={t("game.boardSize")} className="flex gap-2">
        {SUPPORTED_SIZES.map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            onClick={() => onChange(n)}
            className={
              "px-3 py-1 rounded border text-sm " +
              (value === n
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700")
            }
          >
            {n}×{n}
          </button>
        ))}
      </div>
    </label>
  );
}
```

- [ ] **Step 2: Add the i18n keys**

In `web/lib/i18n/ko.json`, inside the `"game"` object, add the `boardSize` key (before `rank`):

Find:
```
"game": { "rank": "급수", ...
```

Change to:
```
"game": { "boardSize": "바둑판 크기", "rank": "급수", ...
```

Also add `"INVALID_BOARD_SIZE": "바둑판 크기가 올바르지 않습니다"` into the `"errors"` object (place it next to `INVALID_HANDICAP`).

In `web/lib/i18n/en.json`, do the same:
- `"boardSize": "Board size"` at the start of the `"game"` object.
- `"INVALID_BOARD_SIZE": "Invalid board size"` in `"errors"`.

- [ ] **Step 3: Commit**

```bash
git add web/components/BoardSizePicker.tsx web/lib/i18n/
git commit -m "feat(web): BoardSizePicker component"
```

---

## Task 16: `HandicapPicker` becomes size-aware

**Files:**
- Modify: `web/components/HandicapPicker.tsx`

- [ ] **Step 1: Edit the component**

Replace `web/components/HandicapPicker.tsx` with:

```tsx
"use client";
import { useT } from "@/lib/i18n";

const HANDICAPS_BY_SIZE: Record<number, number[]> = {
  9: [2, 3, 4, 5],
  13: [2, 3, 4, 5, 6, 7, 8, 9],
  19: [2, 3, 4, 5, 6, 7, 8, 9],
};

interface Props {
  boardSize: number;
  value: number;
  onChange: (n: number) => void;
}

export default function HandicapPicker({ boardSize, value, onChange }: Props) {
  const t = useT();
  const options = HANDICAPS_BY_SIZE[boardSize] ?? [];
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm">{t("game.handicap")}</span>
      <select
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="border rounded px-2 py-1 dark:bg-gray-900 dark:border-gray-700"
      >
        <option value={0}>{t("game.handicapNone")}</option>
        {options.map((n) => (
          <option key={n} value={n}>{t("game.handicapStones", { n })}</option>
        ))}
      </select>
    </label>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add web/components/HandicapPicker.tsx
git commit -m "feat(web): HandicapPicker takes boardSize and filters options"
```

---

## Task 17: Wire up new-game page + gameStore + play/review pages

**Files:**
- Modify: `web/store/gameStore.ts`
- Modify: `web/app/game/new/page.tsx`
- Modify: `web/app/game/play/[id]/page.tsx`
- Modify: `web/app/game/review/[id]/page.tsx`
- Modify: `web/components/AnalysisOverlay.tsx` (if it renders `<Board/>` or computes per-cell indices)

- [ ] **Step 1: Update `web/store/gameStore.ts`**

Replace with:

```ts
"use client";
import { create } from "zustand";
import { totalCells } from "@/lib/board";

interface GameStoreState {
  boardSize: number;
  board: string;
  toMove: string;
  moveCount: number;
  captures: Record<string, number>;
  lastAiMove: string | null;
  aiThinking: boolean;
  gameOver: boolean;
  result: string | null;
  error: string | null;
  set(partial: Partial<GameStoreState>): void;
  reset(size?: number): void;
}

function initial(size: number) {
  return {
    boardSize: size,
    board: ".".repeat(totalCells(size)),
    toMove: "B",
    moveCount: 0,
    captures: { B: 0, W: 0 },
    lastAiMove: null as string | null,
    aiThinking: false,
    gameOver: false,
    result: null as string | null,
    error: null as string | null,
  };
}

export const useGameStore = create<GameStoreState>((set) => ({
  ...initial(19),
  set: (p) => set(p),
  reset: (size = 19) => set(initial(size)),
}));
```

- [ ] **Step 2: Update `web/app/game/new/page.tsx`**

Replace the file with:

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import RankPicker, { type Rank } from "@/components/RankPicker";
import HandicapPicker from "@/components/HandicapPicker";
import BoardSizePicker from "@/components/BoardSizePicker";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import type { BoardSize } from "@/lib/board";

const VALID_HANDICAPS_BY_SIZE: Record<number, number[]> = {
  9: [0, 2, 3, 4, 5],
  13: [0, 2, 3, 4, 5, 6, 7, 8, 9],
  19: [0, 2, 3, 4, 5, 6, 7, 8, 9],
};

export default function NewGamePage() {
  const t = useT();
  const router = useRouter();
  const [boardSize, setBoardSize] = useState<BoardSize>(19);
  const [rank, setRank] = useState<Rank>("5k");
  const [handicap, setHandicap] = useState<number>(0);
  const [userColor, setUserColor] = useState<"black" | "white">("black");
  const [err, setErr] = useState<string | null>(null);
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    api("/api/auth/me")
      .then(() => setAuthed(true))
      .catch(() => {
        setAuthed(false);
        router.replace("/login?next=/game/new");
      });
  }, [router]);

  function pickSize(s: BoardSize) {
    setBoardSize(s);
    if (!VALID_HANDICAPS_BY_SIZE[s].includes(handicap)) {
      setHandicap(0);
    }
  }

  async function create() {
    setErr(null);
    try {
      const body = JSON.stringify({
        ai_rank: rank,
        handicap,
        user_color: handicap > 0 ? "black" : userColor,
        board_size: boardSize,
      });
      const game = await api<{ id: number }>("/api/games", { method: "POST", body });
      router.push(`/game/play/${game.id}`);
    } catch (e: unknown) {
      const code = (e as ApiError).code || "validation";
      if ((e as ApiError).status === 401) {
        router.replace("/login?next=/game/new");
        return;
      }
      setErr(t(`errors.${code}`));
    }
  }

  if (authed === null) {
    return <div className="mt-6 text-sm text-gray-500">...</div>;
  }

  return (
    <div className="space-y-4 max-w-md mt-6">
      <h1 className="text-2xl font-bold">{t("nav.newGame")}</h1>
      <BoardSizePicker value={boardSize} onChange={pickSize} />
      <RankPicker value={rank} onChange={setRank} />
      <HandicapPicker boardSize={boardSize} value={handicap} onChange={setHandicap} />
      {handicap === 0 && (
        <label className="flex flex-col gap-1">
          <span className="text-sm">{t("game.color")}</span>
          <select value={userColor} onChange={(e) => setUserColor(e.target.value as "black" | "white")} className="border rounded px-2 py-1 dark:bg-gray-900">
            <option value="black">{t("game.colorBlack")}</option>
            <option value="white">{t("game.colorWhite")}</option>
          </select>
        </label>
      )}
      {err && <div className="text-red-600 text-sm">{err}</div>}
      <button onClick={create} className="px-4 py-2 bg-blue-600 text-white rounded">{t("game.create")}</button>
    </div>
  );
}
```

- [ ] **Step 3: Replace `web/app/game/play/[id]/page.tsx`**

The current file imports a removed `BOARD` constant and calls the old arity of `gtpToXy` / `xyToGtp`. Replace with:

```tsx
"use client";
import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Board from "@/components/Board";
import GameControls from "@/components/GameControls";
import ScorePanel from "@/components/ScorePanel";
import { openGameWS, type WSMessage, type GameWS } from "@/lib/ws";
import { useGameStore } from "@/store/gameStore";
import { api } from "@/lib/api";
import { gtpToXy, xyToGtp } from "@/lib/board";
import { useT } from "@/lib/i18n";

export default function PlayPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const gameId = parseInt(params.id, 10);
  const g = useGameStore();
  const wsRef = useRef<GameWS | null>(null);
  const preOptimisticBoard = useRef<string | null>(null);
  const optimisticUserMove = useRef<{ x: number; y: number } | null>(null);
  const [hint, setHint] = useState<{ move: string; winrate: number; visits: number }[]>([]);

  useEffect(() => {
    // Fetch the game summary first so we know the size before the WS opens.
    api<{ board_size: number }>(`/api/games/${gameId}`).then((detail) => {
      g.reset(detail.board_size);
    });

    const ws = openGameWS(gameId, (msg: WSMessage) => {
      if (msg.type === "state") {
        preOptimisticBoard.current = null;
        g.set({
          boardSize: msg.board_size,
          board: msg.board,
          toMove: msg.to_move,
          moveCount: msg.move_count,
          captures: msg.captures,
          error: null,
        });
      } else if (msg.type === "ai_move") {
        g.set({ lastAiMove: msg.coord, aiThinking: false });
      } else if (msg.type === "game_over") {
        g.set({ gameOver: true, result: msg.result, aiThinking: false });
      } else if (msg.type === "error") {
        if (preOptimisticBoard.current !== null) {
          g.set({ board: preOptimisticBoard.current });
          preOptimisticBoard.current = null;
        }
        optimisticUserMove.current = null;
        g.set({ error: msg.code, aiThinking: false });
      }
    });
    wsRef.current = ws;
    return () => { ws.close(); g.reset(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId]);

  const sendMove = (x: number, y: number) => {
    if (g.gameOver || g.aiThinking) return;
    const coord = xyToGtp(x, y, g.boardSize);
    const idx = y * g.boardSize + x;
    if (g.board[idx] !== ".") {
      g.set({ error: "OCCUPIED" });
      return;
    }
    preOptimisticBoard.current = g.board;
    const userColor = g.toMove;
    const newBoard = g.board.substring(0, idx) + userColor + g.board.substring(idx + 1);
    optimisticUserMove.current = { x, y };
    g.set({
      board: newBoard,
      aiThinking: true,
      error: null,
      lastAiMove: null,
    });
    wsRef.current?.send({ type: "move", coord });
  };

  const pass = () => {
    g.set({ aiThinking: true, error: null });
    wsRef.current?.send({ type: "pass" });
  };
  const undo = () => {
    g.set({ error: null });
    wsRef.current?.send({ type: "undo", steps: 2 });
  };
  const resign = async () => {
    await api(`/api/games/${gameId}/resign`, { method: "POST" });
    g.set({ gameOver: true });
  };
  const hintMe = async () => {
    const r = await api<{ hints: typeof hint }>(`/api/games/${gameId}/hint`, { method: "POST" });
    setHint(r.hints);
  };

  const lastMoveXy = g.lastAiMove
    ? gtpToXy(g.lastAiMove, g.boardSize)
    : optimisticUserMove.current
      ? [optimisticUserMove.current.x, optimisticUserMove.current.y] as [number, number]
      : null;

  return (
    <div className="mt-4 space-y-4">
      <Board
        size={g.boardSize}
        board={g.board}
        lastMove={lastMoveXy ? { x: lastMoveXy[0], y: lastMoveXy[1] } : null}
        onClick={sendMove}
        disabled={g.aiThinking || g.gameOver}
        overlay={hint.map((h) => {
          const xy = gtpToXy(h.move, g.boardSize);
          return xy ? { x: xy[0], y: xy[1], color: "rgba(0,200,0,0.6)", label: `${Math.round(h.winrate * 100)}` } : null;
        }).filter((x): x is { x: number; y: number; color: string; label: string } => x !== null)}
      />
      <ScorePanel captures={g.captures} />
      <GameControls onPass={pass} onResign={resign} onUndo={undo} onHint={hintMe} disabled={g.gameOver || g.aiThinking} />
      {g.aiThinking && <div className="text-sm text-gray-500">{t("game.aiThinking")}</div>}
      {g.error && <div className="text-sm text-red-600">{t(`errors.${g.error}`)}</div>}
      {g.gameOver && (
        <div className="text-sm font-medium">
          {t("game.resultLabel")}: {g.result || ""}{" "}
          <a className="underline ml-2" href={`/api/games/${gameId}/sgf`} target="_blank" rel="noreferrer">{t("game.downloadSgf")}</a>
        </div>
      )}
    </div>
  );
}
```

Also update `web/lib/ws.ts`'s `WSMessage` type: the `state` variant must now include `board_size: number`. Open the file and add the field to the `state` shape (leave other variants unchanged).

- [ ] **Step 4: Replace `web/app/game/review/[id]/page.tsx`**

Replace with:

```tsx
"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Board from "@/components/Board";
import AnalysisOverlay from "@/components/AnalysisOverlay";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { gtpToXy, totalCells } from "@/lib/board";

interface MoveEntry { move_number: number; color: string; coord: string | null; is_undone: boolean; }
interface GameDetail { id: number; board_size: number; moves: MoveEntry[]; result: string | null; }
interface AnalysisResp { winrate: number; top_moves: { move: string; winrate: number; visits: number }[]; ownership: number[] }

function replay(size: number, moves: MoveEntry[], upto: number): string {
  const cells = Array.from({ length: totalCells(size) }, () => ".");
  for (let i = 0; i < Math.min(upto, moves.length); i++) {
    const m = moves[i];
    if (m.is_undone || !m.coord || m.coord === "pass") continue;
    const xy = gtpToXy(m.coord, size);
    if (!xy) continue;
    const [x, y] = xy;
    cells[y * size + x] = m.color;
  }
  return cells.join("");
}

export default function ReviewPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const gameId = parseInt(params.id, 10);
  const [game, setGame] = useState<GameDetail | null>(null);
  const [idx, setIdx] = useState(0);
  const [analysis, setAnalysis] = useState<AnalysisResp | null>(null);

  useEffect(() => {
    api<GameDetail>(`/api/games/${gameId}`).then(setGame);
  }, [gameId]);

  if (!game) return <div className="mt-6">Loading...</div>;
  const board = replay(game.board_size, game.moves, idx);

  const analyze = async () => {
    const r = await api<AnalysisResp>(`/api/games/${gameId}/analyze?moveNum=${idx}`, { method: "POST" });
    setAnalysis(r);
  };

  return (
    <div className="mt-4 space-y-4">
      <Board size={game.board_size} board={board} />
      <div className="flex gap-2 text-sm">
        <button className="border rounded px-2 py-1" onClick={() => setIdx(0)}>{t("review.first")}</button>
        <button className="border rounded px-2 py-1" onClick={() => setIdx(Math.max(0, idx - 1))}>{t("review.prev")}</button>
        <button className="border rounded px-2 py-1" onClick={() => setIdx(Math.min(game.moves.length, idx + 1))}>{t("review.next")}</button>
        <button className="border rounded px-2 py-1" onClick={() => setIdx(game.moves.length)}>{t("review.last")}</button>
        <button className="border rounded px-2 py-1" onClick={analyze}>{t("review.analyze")}</button>
        <span className="ml-2">Move {idx}/{game.moves.length}</span>
      </div>
      {analysis && <AnalysisOverlay winrate={analysis.winrate} topMoves={analysis.top_moves} />}
    </div>
  );
}
```

`AnalysisOverlay` itself renders no board; it needs no change.

- [ ] **Step 5: Run type check and frontend tests**

```bash
npm run type-check
npm test -- --run
```

Expected: both pass.

- [ ] **Step 6: Manual smoke test**

Start backend + frontend (easiest via Docker from repo root):

```bash
# repo root
docker-compose up --build -d
```

Open `http://localhost:3000`, sign up, create three games — one each on 9×9, 13×13, 19×19 — and play a single move on each. Verify:
- Each board renders at its correct size.
- Coord labels on the 9×9 run A–J across and 9–1 down.
- Handicap dropdown on 9×9 only offers 2–5 stones.

If it all works, shut down the stack:

```bash
docker-compose down
```

- [ ] **Step 7: Commit**

```bash
git add web/
git commit -m "feat(web): wire BoardSizePicker through new-game, gameStore, play, review"
```

---

## Task 18: E2E test for 9×9 new game

**Files:**
- Modify: `e2e/tests/` (whichever file covers new-game flow; add a new spec if none)

- [ ] **Step 1: Find the existing new-game e2e**

```bash
grep -rln "ai_rank\|new game\|handicap" e2e/tests/
```

Pick the file that creates a game. If none exists, create `e2e/tests/board-size.spec.ts`.

- [ ] **Step 2: Add a "create 9x9 game" test**

Append (or in a new file, scaffold after the existing 19x19 new-game test — reuse the same signup/login helpers):

```ts
import { test, expect } from "@playwright/test";

test("create a 9x9 game and play a move", async ({ page }) => {
  // Follow the same signup/login flow as the existing new-game spec in this file.
  // ...

  await page.goto("/game/new");
  await page.getByRole("radio", { name: "9×9" }).click();
  await page.getByRole("button", { name: /create|새 게임 시작/i }).click();

  await expect(page).toHaveURL(/\/game\/play\/\d+$/);
  // 9x9 board renders with label "A" present and "T" absent
  const svg = page.locator("svg[aria-label*='9x9']");
  await expect(svg).toBeVisible();
});
```

- [ ] **Step 3: Run e2e**

From repo root, make sure the stack is up (`docker-compose up --build -d`), then from `e2e/`:

```bash
npm test
```

Expected: new test passes; existing tests still pass.

- [ ] **Step 4: Commit and tear down**

```bash
git add e2e/
git commit -m "test(e2e): 9x9 new-game flow"
docker-compose down
```

---

## Task 19: Update CHANGELOG and CLAUDE.md

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `CLAUDE.md` (and `baduk/CLAUDE.md` if it duplicates)

- [ ] **Step 1: Update CHANGELOG.md**

Open `CHANGELOG.md` and add a new section at the top:

```markdown
## [0.2.0] - 2026-04-18

### Added
- 9×9 and 13×13 board sizes selectable at new-game time (default 19×19).
- Handicap tables extended to 9×9 (2–5 stones) and 13×13 (2–9 stones).

### Changed
- `Board` now carries its `size` as an instance attribute; `BOARD_SIZE` constant removed.
- `games.board_size` column added; `sgf_coord.gtp_to_xy` / `xy_to_gtp` take an explicit `size` argument.

### Removed
- Legacy 19×19-only DB schema. The 0002 migration drops and recreates `games`, `moves`, `analyses`.
```

Also remove "19x19 only" from the Known Limitations section.

- [ ] **Step 2: Update CLAUDE.md**

In `CLAUDE.md`, find the line:

```
- Web-based Go board (19x19 SVG)
```

— no wait, that's in the README/CHANGELOG. In `CLAUDE.md`, the phrase to update is under the "Rules Engine" section: "Korean rules: komi 6.5 even, 0.5 with handicap." This is still correct; no change needed.

However, replace the final bullet in the Reference section that currently implies 19×19-only still applies:

```
- `CHANGELOG.md` — what shipped in 0.1.0 and what was explicitly deferred (9x9/13x13, time controls, user-vs-user, OAuth).
```

with:

```
- `CHANGELOG.md` — versioned history. 0.2.0 added 9×9/13×13 board sizes; time controls, user-vs-user, OAuth still deferred.
```

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md CLAUDE.md
git commit -m "docs: 0.2.0 changelog for flexible board size"
```

---

## Task 20: Final full-stack verification

- [ ] **Step 1: Backend full suite with coverage gate**

```bash
# from backend/ (venv)
pytest --cov=app --cov-fail-under=80
ruff check .
mypy app
```

Expected: all green; rules engine at 100% line coverage.

- [ ] **Step 2: Frontend full suite**

```bash
# from web/
npm run type-check
npm run lint
npm test -- --run
```

Expected: all green.

- [ ] **Step 3: Docker + E2E**

```bash
# repo root
cp -n .env.example .env
docker-compose up --build -d
cd e2e && npm test && cd ..
docker-compose down
```

Expected: all e2e specs pass.

- [ ] **Step 4: Final commit (only if there were last-minute fixes)**

```bash
git status
# if dirty:
git add -A
git commit -m "chore: final cleanup"
```

---

## Spec Coverage Check

Every requirement from `docs/superpowers/specs/2026-04-18-flexible-board-size-design.md` maps to a task:

| Spec item | Task |
|---|---|
| `SUPPORTED_SIZES = (9, 13, 19)` | 1 |
| `Board.size` instance attribute | 1 |
| Size-aware `sgf_coord` | 2 |
| Handicap tables for 9/13 | 3 |
| `scoring` iterates `board.size` | 4 |
| `engine.build_sgf` reads size from state | 5 |
| KataGo mock tracks size correctly | 6 |
| Real adapter replay already supports size | 7 (verified, no change) |
| `games.board_size` column + migration | 8 |
| `game_service.create_game(board_size=...)` | 9 |
| Pydantic `board_size: Literal[9,13,19]` | 10 |
| WS payload includes `board_size` | 11 |
| Lint/type pass | 12, 20 |
| Frontend `lib/board.ts` size helpers | 13 |
| Frontend `Board` takes `size` prop | 14 |
| `BoardSizePicker` | 15 |
| `HandicapPicker` filters by size | 16 |
| Page wiring + gameStore | 17 |
| E2E 9×9 flow | 18 |
| Docs / CHANGELOG | 19 |
| Final verification | 20 |
