# Flexible Board Size — Design Spec

**Date:** 2026-04-18
**Status:** Draft, pending implementation plan
**Scope:** Allow users to play 9x9, 13x13, and 19x19 games (previously 19x19 only).

## Goals

- Support standard Go board sizes 9, 13, and 19.
- Keep all existing rules, handicap, KataGo integration, and scoring working for every supported size.
- Avoid one-off code paths per size — size flows as data through a single code path.

## Non-Goals

- Arbitrary board sizes (e.g. 5, 7, 11, 21+). Fixed set `{9, 13, 19}` only.
- Chinese / Japanese scoring variants (Korean scoring retained).
- Changing board size mid-game.
- Backward compatibility with existing 19x19 game records (DB is wiped — dev-only decision).

## Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Supported sizes | 9, 13, 19 only (Q1=A) |
| Default size | 19 (Q2=A) |
| Handicap support | All sizes (Q3=A) |
| Existing game data | Delete (Q4=B) |
| UI placement | New `BoardSizePicker` component (Q5=A) |

## Architecture Overview

Replace the module-level `BOARD_SIZE = 19` constant with a `Board.size` instance attribute. Size information travels with the `Board` → `GameState` → `Game` row → WebSocket payload → frontend store. Any module that previously read the constant reads `board.size` (or accepts a `size: int` parameter).

A single constant `SUPPORTED_SIZES = (9, 13, 19)` defines the allowed set in one place, used by Pydantic validation and the frontend picker.

### End-to-end data flow

```
UI BoardSizePicker  ──► POST /games {board_size, rank, handicap, ...}
                        │
                        ▼
                 game_service.create_game(board_size, ...)
                        │
                        ▼
                 rules.engine: Board(size=N) → apply_handicap(board, stones)
                        │                              │
                        ▼                              ▼
                 DB: games.board_size = N    HANDICAP_TABLES[N][stones]
                        │
                        ▼
                 KataGo adapter: boardsize N → clear_board → replay
                        │
                        ▼
                 WS state payload includes board_size
                        │
                        ▼
                 Frontend gameStore.boardSize → <Board size={N} />
```

## Component Changes

### Backend — `core/rules/`

- **`board.py`**
  - Remove `BOARD_SIZE` and `_TOTAL` module constants.
  - `Board.__init__(size: int, cells: tuple[str, ...] | None = None)`.
  - `__slots__ = ("size", "_cells")`.
  - `_idx`, `in_bounds`, `__repr__`, `neighbors` use `self.size`.
  - `place`, `remove`, `remove_group` return `Board(self.size, new_cells)`.
  - `__eq__`/`__hash__` include size in their identity so boards of different sizes never compare equal.

- **`sgf_coord.py`**
  - Remove `BOARD_SIZE`.
  - `gtp_to_xy(coord: str, size: int) -> tuple[int, int] | None`.
  - `xy_to_gtp(x: int, y: int, size: int) -> str`.
  - `COLS` stays (sliced to `size` letters).

- **`handicap.py`** — replace single `HANDICAP_COORDS` with:
  ```python
  HANDICAP_TABLES: dict[int, dict[int, list[str]]] = {
      9:  {2: [...], 3: [...], 4: [...], 5: [...]},
      13: {2: [...], ..., 9: [...]},
      19: {2: [...], ..., 9: [...]},  # unchanged
  }
  ```
  Exact positions (Korean convention, GTP coords):
  - **9×9** (2–5 stones): 2=C3,G7 · 3=+G3 · 4=+C7 · 5=+E5
  - **13×13** (2–9 stones):
    - 2: D4, K10
    - 3: +K4
    - 4: +D10
    - 5: +G7 (tengen)
    - 6: D4, K10, K4, D10, D7, K7  *(tengen removed; 4 corners + 2 sides)*
    - 7: +G7  *(tengen back)*
    - 8: D4, K10, K4, D10, D7, K7, G4, G10  *(4 corners + all 4 sides, no tengen)*
    - 9: +G7  *(all 9 star points)*
  - **19×19**: unchanged (D16, Q4, Q16, D4, K10, D10, Q10, K4, K16)
  - `apply_handicap(board, stones)` selects the inner table by `board.size`. Invalid `(size, stones)` pair raises `ValueError`.

- **`scoring.py`, `captures.py`, `ko.py`** — replace `range(BOARD_SIZE)` with `range(board.size)`; otherwise logic is size-independent.

- **`engine.py`**
  - `build_sgf(state)` writes `SZ[state.board.size]` (remove the `board_size` default parameter).
  - `GameState` continues to hold `board: Board`; size is read via `state.board.size`.

### Backend — other layers

- **`models/game.py`**: add `board_size: Mapped[int] = mapped_column(Integer, nullable=False)`. No default value — creator must pass one.

- **`api/games.py`**:
  - Request schema: `board_size: Literal[9, 13, 19] = 19`.
  - Response DTO: include `board_size`.
  - Per-move endpoint: validate `0 <= x, y < game.board_size`.

- **`services/game_service.py`**:
  - `create_game(..., board_size: int)` builds `Board(size=board_size)`.
  - Persists `board_size` on the row.

- **`engine_pool.py`**: no structural change — `GameState` already carries the `Board`, so size travels with it.

- **`core/katago/adapter.py`**:
  - `_ReplayState` gains `board_size: int`.
  - `replay()` sends `boardsize N` first, then `komi`, then `kata-set-param`, then replays moves. `boardsize` resets the KataGo-side board, which is the desired behavior.
  - Before handling commands for a given game, the handler already re-seeds via `clear_board + replay`; swap `clear_board` → `boardsize N` at the head (since `boardsize` also clears). For the same game in flight, KataGo stays on its current size.

- **`core/katago/mock.py`**: accept `boardsize N` and update its internal size so genmove returns legal coords.

- **Migration**: one Alembic revision — drop `games`, `moves`, `analysis_cache` and recreate them with `board_size` in `games`. Destructive on purpose (Q4=B).

### Frontend — `web/`

- **`lib/board.ts`**
  - Remove `BOARD` constant.
  - `starPoints(size: number): number[]` — `9 → [2,4,6]`, `13 → [3,6,9]`, `19 → [3,9,15]`.
  - `xyToGtp(x, y, size)` and `gtpToXy(coord, size)`.

- **`components/Board.tsx`**
  - Add `size: number` prop.
  - Compute `SIZE_PX = OFFSET*2 + CELL*(size-1)` inside. `CELL` stays 30.
  - Grid, star-point, label, and hit-test loops use `size`.
  - SVG's `viewBox` and existing Tailwind `max-w-[640px]` cause the board to scale down in the same visual box for small sizes.

- **`components/BoardSizePicker.tsx`** (new)
  - Three radio buttons (9 / 13 / 19), controlled.
  - Default 19.
  - i18n labels: `새 게임 바둑판 크기` / `Board size`.

- **`components/HandicapPicker.tsx`**
  - Add `boardSize` prop.
  - Valid handicap values computed from `SUPPORTED_HANDICAPS[boardSize]`.
  - When `boardSize` changes to a value where current handicap is out of range, caller resets handicap to 0.

- **`store/gameStore.ts`**: add `boardSize: number`, populated from the server `state` payload. Used by `Board` and any coord-aware UI.

- **New-game screen**: add `BoardSizePicker` above `RankPicker`.

### Tests

- **Rules unit tests** — parametrize common scenarios over `size ∈ {9, 13, 19}`:
  - `tests/rules/test_board.py`: placement, liberties, group BFS.
  - `tests/rules/test_ko.py`: simple ko still works on 9×9 (smaller → easier setup).
  - `tests/rules/test_captures.py`: corner, edge, center captures on each size.
  - `tests/rules/test_scoring.py`: territory count on each size with known positions.
- **Handicap** — `tests/rules/test_handicap.py`:
  - Each size's supported stone counts land on the documented coords.
  - Invalid `(size, stones)` pairs raise `ValueError`.
- **API** — `tests/api/test_games.py`:
  - Create 9 / 13 / 19 games, send a move on each, verify persisted `board_size`.
  - Reject `board_size=7` (422).
- **KataGo mock** — `tests/katago/test_adapter.py`:
  - After a 9x9 game, starting a 19x19 game issues `boardsize 19` before replay.
- **Frontend** — `tests/board.test.ts`:
  - `starPoints` returns correct values for each size.
  - `xyToGtp`/`gtpToXy` round-trip on each size.
- **E2E** — `e2e/tests/new-game.spec.ts`:
  - Add "create 9×9 game, play a move, resign" path alongside the existing 19×19 flow.
- **Coverage gates**: rules engine 100% line coverage maintained; overall backend ≥ 80%.

## Error Handling & Edge Cases

- Invalid `board_size` at API boundary: Pydantic 422.
- Invalid handicap for a given size: `ValueError` in `apply_handicap` → 422 at API layer.
- Move outside `[0, board_size)`: rejected by rules engine (`in_bounds`), also pre-checked in API.
- KataGo process death mid-game: existing replay restores size via `_ReplayState.board_size`.
- Two games of different sizes in flight: per-game `asyncio.Lock` + `boardsize N` at re-seed time prevents interleaving.
- Overlay / last-move marker: coord math uses the `size` prop → correct for every size.

## Out of Scope

- Sizes outside {9, 13, 19}.
- Mid-game size change.
- Scoring variants.
- Migrating or preserving existing 19×19 games (DB is dropped).
- Rank tuning per size (same rank ladder used for all sizes — good enough for MVP).

## Risks

- **Handicap tables for 9/13 are convention-dependent**: we pick one mainstream Korean convention and document it; users expecting a different convention may be surprised. Mitigation: document the chosen positions in `handicap.py` docstring.
- **KataGo mock**: needs to track size state correctly, otherwise tests pass locally but production behavior diverges. Mitigation: dedicated `test_adapter.py` size-switch test.
- **Scope creep**: the refactor touches many files; staying disciplined to "size as data, no behavior change otherwise" keeps the diff reviewable.
