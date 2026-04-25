# Quality Polish Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the three pieces of mobile-beta polish from `2026-04-26-quality-polish-pack-design.md` — replace synthetic stone-click sound with real samples, expose territory coordinates from the scoring engine and overlay them on the board during scoring, and fill in the existing Kaya `BOARD_THEMES` slot with SVG wood-grain background and lithic 3D stones.

**Architecture:** Three loosely coupled vertical slices on a shared trunk:

1. **Backend rules engine + service layer** propagates flood-fill territory coordinates (and the existing `dead_stones` set) all the way out to the WS `score_result` payload. No KataGo or DB changes — `_flood_territory` already computes regions, we stop discarding the coordinates.
2. **Frontend Board renderer** gains a `territoryMarkers` prop (plus theme metadata: `surface`, `stoneStyle`, `shadow`) so we can drive the scoring overlay and the per-theme rendering branch from data, without duplicating the SVG block.
3. **Sound** swaps the AudioContext synthesizer for an `<audio>` element pool fed by three real samples in `public/sounds/`.

The Editorial paper theme stays the default and visually unchanged. Kaya/wood/slate gain a fractal-noise wood filter, radial-gradient stones, and a faint drop-shadow.

**Tech Stack:** FastAPI + SQLAlchemy 2 async (backend), Next.js 14 App Router + TypeScript + Tailwind + Zustand + shadcn (frontend), Vitest + Playwright (frontend tests), pytest (backend tests). All-SVG board rendering — no `<canvas>`, no external image assets.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `backend/app/core/rules/scoring.py` | Modify | `_flood_territory` returns point sets; `ScoreResult` carries them |
| `backend/tests/rules/test_scoring.py` | Modify | New tests asserting point-set contents |
| `backend/app/services/game_service.py` | Modify | `ScoringDetail` carries point sets + dead_stones; constructors thread them through |
| `backend/app/api/ws.py` | Modify | `score_result` payload (two emit sites) include the new fields |
| `backend/tests/api/test_games.py` | Modify | One end-to-end check via `score_request` WS message |
| `web/lib/ws.ts` | Modify | `ScoreResultMsg` type extended |
| `web/store/boardThemeStore.ts` | Modify | `BoardThemeMeta` adds `surface`/`stoneStyle`/`shadow`; values per theme |
| `web/components/Board.tsx` | Modify | New `territoryMarkers` prop + theme-driven rendering branch (`<defs>` for filter + lithic gradients + shadow ellipse) |
| `web/components/ui/sheet.tsx` | Existing | Used by scoring panel (no edit) |
| `web/app/game/play/[id]/page.tsx` | Modify | Replace scoring `Dialog` with `Sheet`, pipe `territoryMarkers` to `<Board>` |
| `web/tests/board.test.ts` | Modify | Theme metadata branch + territoryMarkers rendering tests |
| `web/lib/soundfx.ts` | Rewrite | `<audio>` pool + random sample picker |
| `web/public/sounds/stone-1.mp3` | Create | First stone sample |
| `web/public/sounds/stone-2.mp3` | Create | Second stone sample |
| `web/public/sounds/stone-3.mp3` | Create | Third stone sample |
| `web/public/sounds/CREDITS.md` | Create | Sound source + license |
| `web/tests/lib/soundfx.test.ts` | Create | Pool selection + enabled toggle |
| `CLAUDE.md` | Modify | Note the board-only shadow exception in §Radius/Shadow |

---

## Task 1: Extend `_flood_territory` to return point coordinates

**Files:**
- Modify: `backend/app/core/rules/scoring.py`
- Test: `backend/tests/rules/test_scoring.py`

- [ ] **Step 1: Write the failing test** — append to `backend/tests/rules/test_scoring.py`

```python
def test_flood_territory_returns_point_sets():
    # 5x5 board with a 1x1 black eye at (1,1) and a 1x1 white eye at (3,3)
    b = Board(5)
    for x, y in [(0, 1), (1, 0), (2, 1), (1, 2)]:
        b = b.place(x, y, BLACK)
    for x, y in [(2, 3), (3, 2), (4, 3), (3, 4)]:
        b = b.place(x, y, WHITE)
    result = score_game(b, 0, 0, 0.0)
    assert (1, 1) in result.black_points
    assert (3, 3) in result.white_points
    # The shared border between the two formations must be neutral (dame)
    assert (0, 0) not in result.black_points
    assert (0, 0) not in result.white_points
    # Sizes must agree with counts
    assert len(result.black_points) == result.black_territory
    assert len(result.white_points) == result.white_territory
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && source .venv311/bin/activate
pytest tests/rules/test_scoring.py::test_flood_territory_returns_point_sets -v
```

Expected: FAIL — `AttributeError: 'ScoreResult' object has no attribute 'black_points'`

- [ ] **Step 3: Add point fields to `ScoreResult` and have `_flood_territory` return them**

Replace the existing `ScoreResult` dataclass (lines 10–20 of `backend/app/core/rules/scoring.py`):

```python
@dataclass(frozen=True)
class ScoreResult:
    black_territory: int
    white_territory: int
    black_captures: int
    white_captures: int
    komi: float
    black_score: float
    white_score: float
    winner: str  # 'B' or 'W'
    margin: float  # absolute difference
    black_points: frozenset[tuple[int, int]] = frozenset()
    white_points: frozenset[tuple[int, int]] = frozenset()
    dame_points: frozenset[tuple[int, int]] = frozenset()
```

Replace `_flood_territory` (currently at lines 23–71) with the version below — same algorithm, but it now returns the per-color point sets too:

```python
def _flood_territory(
    board: Board, dead_stones: set[tuple[int, int]]
) -> tuple[
    int,
    int,
    frozenset[tuple[int, int]],
    frozenset[tuple[int, int]],
    frozenset[tuple[int, int]],
]:
    """Flood-fill empty regions to determine territory ownership.

    Returns (black_count, white_count, black_points, white_points, dame_points).
    Dead stones are treated as empty during counting.
    """
    visited: set[tuple[int, int]] = set()
    black_pts: set[tuple[int, int]] = set()
    white_pts: set[tuple[int, int]] = set()
    dame_pts: set[tuple[int, int]] = set()

    effective = board
    for pos in dead_stones:
        effective = effective.remove(*pos)

    def flood(sx: int, sy: int) -> tuple[set[tuple[int, int]], set[str]]:
        region: set[tuple[int, int]] = set()
        border_colors: set[str] = set()
        stack = [(sx, sy)]
        while stack:
            x, y = stack.pop()
            if (x, y) in region:
                continue
            cell = effective.get(x, y)
            if cell == EMPTY:
                region.add((x, y))
                for nx, ny in effective.neighbors(x, y):
                    if (nx, ny) not in region:
                        stack.append((nx, ny))
            else:
                border_colors.add(cell)
        return region, border_colors

    for y in range(board.size):
        for x in range(board.size):
            if (x, y) not in visited and effective.get(x, y) == EMPTY:
                region, colors = flood(x, y)
                visited |= region
                if colors == {BLACK}:
                    black_pts |= region
                elif colors == {WHITE}:
                    white_pts |= region
                else:
                    dame_pts |= region

    return (
        len(black_pts),
        len(white_pts),
        frozenset(black_pts),
        frozenset(white_pts),
        frozenset(dame_pts),
    )
```

Update `score_game` to consume the new tuple — replace lines 97 onwards in the same file with:

```python
    black_terr, white_terr, black_pts, white_pts, dame_pts = _flood_territory(
        board, dead_stones
    )

    b_score = float(black_terr + black_captures + extra_black_captures)
    w_score = white_terr + white_captures + extra_white_captures + komi

    if b_score > w_score:
        winner = BLACK
        margin = b_score - w_score
    else:
        winner = WHITE
        margin = w_score - b_score

    return ScoreResult(
        black_territory=black_terr,
        white_territory=white_terr,
        black_captures=black_captures + extra_black_captures,
        white_captures=white_captures + extra_white_captures,
        komi=komi,
        black_score=b_score,
        white_score=w_score,
        winner=winner,
        margin=margin,
        black_points=black_pts,
        white_points=white_pts,
        dame_points=dame_pts,
    )
```

- [ ] **Step 4: Run the targeted test to verify it passes**

```bash
pytest tests/rules/test_scoring.py::test_flood_territory_returns_point_sets -v
```

Expected: PASS.

- [ ] **Step 5: Run the full rules suite to confirm no regression**

```bash
pytest tests/rules/ -q
```

Expected: all tests pass (the new behaviour is purely additive — existing assertions on `black_territory` etc. still hold). `frozen=True` on the dataclass is also new — if any test mutates a `ScoreResult` field it will fail here; the existing rules tests don't.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/rules/scoring.py backend/tests/rules/test_scoring.py
git commit -m "feat(rules): return territory coordinates from flood-fill scoring"
```

---

## Task 2: Thread points + dead_stones through `ScoringDetail`

**Files:**
- Modify: `backend/app/services/game_service.py`

The service layer has a parallel `ScoringDetail` dataclass (lines 60–73) that mirrors `ScoreResult` for the WS API. Both `score_by_request` (around line 502) and the auto-`ai_passed_scored` path (around line 380) construct it. Both now need the new fields.

- [ ] **Step 1: Write a failing test** — append to `backend/tests/api/test_games.py` (or create a new helper test if the existing one is too crowded). Use the existing test client fixtures.

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_score_request_includes_territory_points(
    test_client: AsyncClient, authed_session_cookie: str
):
    """When the user requests scoring on a finished position, the WS
    score_result payload includes per-side territory coordinates and the
    dead-stones set inferred by the engine."""
    # Create a 9x9 game so the position fills quickly.
    r = await test_client.post(
        "/api/games",
        json={"board_size": 9, "handicap": 0, "ai_rank": "5k", "user_color": "black"},
        cookies={"baduk_session": authed_session_cookie},
    )
    assert r.status_code == 201
    game_id = r.json()["id"]

    # Use the WS test helper to play a settled game and request scoring.
    # If a helper exists in tests/api/conftest.py use it; otherwise inline:
    from app.services.game_service import score_by_request
    from app.db import AsyncSessionLocal
    from sqlalchemy import select
    from app.models import Game, Session

    async with AsyncSessionLocal() as db:
        sess = (
            await db.execute(
                select(Session).where(Session.token == authed_session_cookie)
            )
        ).scalar_one()
        game = (
            await db.execute(select(Game).where(Game.id == game_id))
        ).scalar_one()
        # Force the game into a finished-board state for scoring. For this
        # test it's sufficient to have an empty board — score_by_request
        # will return all-dame coordinates.
        detail = await score_by_request(db, game=game, session=sess)

    # New assertions: detail must expose point sets and dead_stones.
    assert isinstance(detail.black_points, frozenset)
    assert isinstance(detail.white_points, frozenset)
    assert isinstance(detail.dame_points, frozenset)
    assert isinstance(detail.dead_stones, frozenset)
    # Counts agree with set sizes.
    assert len(detail.black_points) == detail.black_territory
    assert len(detail.white_points) == detail.white_territory
```

If `tests/api/test_games.py` lacks the `authed_session_cookie` fixture, look at any existing test in that file for the pattern (the file already exercises `/api/games`) and reuse it. Do not invent a new fixture name.

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/api/test_games.py::test_score_request_includes_territory_points -v
```

Expected: FAIL — `AttributeError: 'ScoringDetail' object has no attribute 'black_points'`.

- [ ] **Step 3: Extend `ScoringDetail` and its constructors**

Edit `backend/app/services/game_service.py`. Replace the `ScoringDetail` dataclass (currently lines 60–73) with:

```python
@dataclass
class ScoringDetail:
    """Per-side breakdown returned by the "계가 신청" (request scoring) flow."""
    black_territory: int
    white_territory: int
    black_captures: int
    white_captures: int
    komi: float
    black_score: float
    white_score: float
    winner: str  # 'B' or 'W'
    margin: float
    result_str: str  # "B+3.5"
    black_points: frozenset[tuple[int, int]] = frozenset()
    white_points: frozenset[tuple[int, int]] = frozenset()
    dame_points: frozenset[tuple[int, int]] = frozenset()
    dead_stones: frozenset[tuple[int, int]] = frozenset()
```

Now find the two `ScoringDetail(...)` constructors and add the new fields. The first is in the `ai_passed_scored` path around line 380:

```python
                ai_passed_scored = ScoringDetail(
                    black_territory=result_obj.black_territory,
                    white_territory=result_obj.white_territory,
                    black_captures=result_obj.black_captures,
                    white_captures=result_obj.white_captures,
                    komi=result_obj.komi,
                    black_score=result_obj.black_score,
                    white_score=result_obj.white_score,
                    winner=result_obj.winner,
                    margin=result_obj.margin,
                    result_str=ai_result_str,
                    black_points=result_obj.black_points,
                    white_points=result_obj.white_points,
                    dame_points=result_obj.dame_points,
                    dead_stones=frozenset(dead_stones),
                )
```

(The exact variable names — `result_obj`, `dead_stones`, `ai_result_str` — already exist in that block; keep them. Only add the four new keyword arguments.)

The second is at the bottom of `score_by_request`, around line 502:

```python
    return ScoringDetail(
        black_territory=result.black_territory,
        white_territory=result.white_territory,
        black_captures=result.black_captures,
        white_captures=result.white_captures,
        komi=result.komi,
        black_score=result.black_score,
        white_score=result.white_score,
        winner=result.winner,
        margin=result.margin,
        result_str=result_str,
        black_points=result.black_points,
        white_points=result.white_points,
        dame_points=result.dame_points,
        dead_stones=frozenset(dead_stones),
    )
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
pytest tests/api/test_games.py::test_score_request_includes_territory_points -v
```

Expected: PASS.

- [ ] **Step 5: Run the full backend suite**

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/game_service.py backend/tests/api/test_games.py
git commit -m "feat(score): include territory points + dead stones in ScoringDetail"
```

---

## Task 3: Add point + dead-stone fields to WS `score_result` payload

**Files:**
- Modify: `backend/app/api/ws.py`

There are two emit sites in `ws.py`: the `ai_passed_scored` branch around line 183 and the explicit `score_request` handler around line 217. Both currently send the same nine numeric/string fields. We add four list fields.

- [ ] **Step 1: Write the failing test** — append to `backend/tests/api/test_games.py`

```python
@pytest.mark.asyncio
async def test_ws_score_result_payload_includes_points(
    test_client: AsyncClient, authed_session_cookie: str
):
    """End-to-end: open the WS, send a score_request, expect the payload
    fields the frontend renders the territory map from."""
    r = await test_client.post(
        "/api/games",
        json={"board_size": 9, "handicap": 0, "ai_rank": "5k", "user_color": "black"},
        cookies={"baduk_session": authed_session_cookie},
    )
    game_id = r.json()["id"]

    with test_client.websocket_connect(  # type: ignore[attr-defined]
        f"/api/ws/games/{game_id}",
        cookies={"baduk_session": authed_session_cookie},
    ) as ws:
        # Discard the initial state message
        ws.receive_json()
        ws.send_json({"type": "score_request"})
        msg = ws.receive_json()
        assert msg["type"] == "score_result"
        # New required fields
        assert isinstance(msg["black_points"], list)
        assert isinstance(msg["white_points"], list)
        assert isinstance(msg["dame_points"], list)
        assert isinstance(msg["dead_stones"], list)
        # Each entry must be a [x, y] pair
        for pt in msg["black_points"]:
            assert isinstance(pt, list) and len(pt) == 2
```

If the existing test file uses Starlette's TestClient via FastAPI directly (not httpx AsyncClient), copy that pattern instead — open `backend/tests/api/test_games.py` and look at how an existing WS or HTTP test is structured. The assertions above are the contract that matters; the harness boilerplate must follow what's already working in the file.

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/api/test_games.py::test_ws_score_result_payload_includes_points -v
```

Expected: FAIL — `KeyError: 'black_points'`.

- [ ] **Step 3: Add a serialization helper and update both emit sites**

At the top of `backend/app/api/ws.py` (right after the existing imports), add:

```python
def _serialize_points(pts: frozenset[tuple[int, int]]) -> list[list[int]]:
    """Convert a frozenset of (x, y) coords to JSON-friendly [[x, y], ...]."""
    return [[x, y] for (x, y) in sorted(pts)]
```

In the `ai_passed_scored` branch (around lines 183–195), replace the dict literal with:

```python
                        await websocket.send_json({
                            "type": "score_result",
                            "black_territory": d.black_territory,
                            "white_territory": d.white_territory,
                            "black_captures": d.black_captures,
                            "white_captures": d.white_captures,
                            "komi": d.komi,
                            "black_score": d.black_score,
                            "white_score": d.white_score,
                            "winner": d.winner,
                            "margin": d.margin,
                            "result": d.result_str,
                            "reason": "ai_passed",
                            "black_points": _serialize_points(d.black_points),
                            "white_points": _serialize_points(d.white_points),
                            "dame_points": _serialize_points(d.dame_points),
                            "dead_stones": _serialize_points(d.dead_stones),
                        })
```

Same shape applied to the `score_request` branch around line 217:

```python
                    await websocket.send_json({
                        "type": "score_result",
                        "black_territory": detail.black_territory,
                        "white_territory": detail.white_territory,
                        "black_captures": detail.black_captures,
                        "white_captures": detail.white_captures,
                        "komi": detail.komi,
                        "black_score": detail.black_score,
                        "white_score": detail.white_score,
                        "winner": detail.winner,
                        "margin": detail.margin,
                        "result": detail.result_str,
                        "black_points": _serialize_points(detail.black_points),
                        "white_points": _serialize_points(detail.white_points),
                        "dame_points": _serialize_points(detail.dame_points),
                        "dead_stones": _serialize_points(detail.dead_stones),
                    })
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
pytest tests/api/test_games.py::test_ws_score_result_payload_includes_points -v
```

Expected: PASS.

- [ ] **Step 5: Full backend suite + ruff + mypy**

```bash
pytest -q
ruff check app
mypy app
```

Expected: tests pass; ruff clean; mypy may surface errors only in unrelated files (the count from the prior baseline must not increase).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/ws.py backend/tests/api/test_games.py
git commit -m "feat(ws): emit territory points + dead stones in score_result"
```

---

## Task 4: Extend `ScoreResultMsg` on the frontend

**Files:**
- Modify: `web/lib/ws.ts`

- [ ] **Step 1: Update the TypeScript message shape**

Edit `web/lib/ws.ts` lines 1–14 (the `ScoreResultMsg` interface):

```ts
export interface ScoreResultMsg {
  type: "score_result";
  black_territory: number;
  white_territory: number;
  black_captures: number;
  white_captures: number;
  komi: number;
  black_score: number;
  white_score: number;
  winner: string; // "B" | "W"
  margin: number;
  result: string;
  reason?: "ai_passed";
  black_points: [number, number][];
  white_points: [number, number][];
  dame_points: [number, number][];
  dead_stones: [number, number][];
}
```

- [ ] **Step 2: Verify type-check**

```bash
cd web && npm run type-check
```

Expected: clean. (No consumer reads the new fields yet — that's Task 9.)

- [ ] **Step 3: Commit**

```bash
git add web/lib/ws.ts
git commit -m "types(ws): add territory points + dead stones to ScoreResultMsg"
```

---

## Task 5: Add `BoardThemeMeta` rendering hints

**Files:**
- Modify: `web/store/boardThemeStore.ts`
- Test: `web/tests/board.test.ts`

- [ ] **Step 1: Write the failing test** — append to `web/tests/board.test.ts`

```ts
import { BOARD_THEMES } from "@/store/boardThemeStore";

describe("BOARD_THEMES metadata", () => {
  it("paper is flat with no shadow", () => {
    expect(BOARD_THEMES.paper.surface).toBe("flat");
    expect(BOARD_THEMES.paper.stoneStyle).toBe("flat");
    expect(BOARD_THEMES.paper.shadow).toBe(false);
  });

  it("kaya uses wood surface and lithic stones", () => {
    expect(BOARD_THEMES.kaya.surface).toBe("wood");
    expect(BOARD_THEMES.kaya.stoneStyle).toBe("lithic");
    expect(BOARD_THEMES.kaya.shadow).toBe(true);
  });

  it("slate is flat surface but lithic stones", () => {
    expect(BOARD_THEMES.slate.surface).toBe("flat");
    expect(BOARD_THEMES.slate.stoneStyle).toBe("lithic");
    expect(BOARD_THEMES.slate.shadow).toBe(true);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd web && npm test -- --run tests/board.test.ts
```

Expected: FAIL — `expect(BOARD_THEMES.paper.surface).toBe("flat")` fails because the field doesn't exist yet.

- [ ] **Step 3: Add the metadata fields**

Replace the `BOARD_THEMES` block in `web/store/boardThemeStore.ts`:

```ts
export type BoardSurface = "flat" | "wood";
export type BoardStoneStyle = "flat" | "lithic";

export interface BoardThemeMeta {
  bg: string;
  lineInk: string;
  starInk: string;
  labelInk: string;
  surface: BoardSurface;
  stoneStyle: BoardStoneStyle;
  shadow: boolean;
}

export const BOARD_THEMES: Record<BoardTheme, BoardThemeMeta> = {
  paper: {
    bg: "rgb(233 223 201)",
    lineInk: "rgb(26 23 21)",
    starInk: "rgb(26 23 21)",
    labelInk: "rgb(107 99 90)",
    surface: "flat",
    stoneStyle: "flat",
    shadow: false,
  },
  wood: {
    bg: "rgb(216 180 120)",
    lineInk: "rgb(40 28 18)",
    starInk: "rgb(40 28 18)",
    labelInk: "rgb(82 62 40)",
    surface: "wood",
    stoneStyle: "lithic",
    shadow: true,
  },
  kaya: {
    bg: "rgb(224 174 105)",
    lineInk: "rgb(44 28 14)",
    starInk: "rgb(44 28 14)",
    labelInk: "rgb(92 62 32)",
    surface: "wood",
    stoneStyle: "lithic",
    shadow: true,
  },
  slate: {
    bg: "rgb(72 82 92)",
    lineInk: "rgb(222 228 235)",
    starInk: "rgb(222 228 235)",
    labelInk: "rgb(176 186 196)",
    surface: "flat",
    stoneStyle: "lithic",
    shadow: true,
  },
};
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
npm test -- --run tests/board.test.ts
```

Expected: PASS — all three new specs green; the existing board tests still pass.

- [ ] **Step 5: Commit**

```bash
git add web/store/boardThemeStore.ts web/tests/board.test.ts
git commit -m "feat(board): add surface/stoneStyle/shadow metadata to themes"
```

---

## Task 6: Add the `territoryMarkers` prop to `Board.tsx` (data plumbing only)

**Files:**
- Modify: `web/components/Board.tsx`
- Test: `web/tests/board.test.ts`

This task adds the prop and renders nothing yet — Task 7 covers the SVG. We do this in two steps so the prop signature is reviewed independently.

- [ ] **Step 1: Write the failing test** — append to `web/tests/board.test.ts`

```ts
import { render } from "@testing-library/react";
import Board from "@/components/Board";

describe("Board territoryMarkers prop", () => {
  it("renders a black territory marker at the given coordinate", () => {
    const board = ".".repeat(9 * 9);
    const { container } = render(
      <Board
        size={9}
        board={board}
        territoryMarkers={{
          black: [[2, 2]],
          white: [],
          dame: [],
          deadStones: [],
        }}
      />
    );
    const markers = container.querySelectorAll('[data-territory="black"]');
    expect(markers.length).toBe(1);
  });

  it("renders nothing when territoryMarkers is omitted", () => {
    const board = ".".repeat(9 * 9);
    const { container } = render(<Board size={9} board={board} />);
    expect(container.querySelectorAll('[data-territory]').length).toBe(0);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
npm test -- --run tests/board.test.ts
```

Expected: FAIL — Board does not accept `territoryMarkers`.

- [ ] **Step 3: Add the prop and render markers**

Edit `web/components/Board.tsx`. Extend the props type:

```ts
type Pt = [number, number];

export default function Board({
  size,
  board,
  lastMove = null,
  onClick,
  disabled,
  overlay,
  territoryMarkers,
}: {
  size: number;
  board: string;
  lastMove?: { x: number; y: number } | null;
  onClick?: (x: number, y: number) => void;
  disabled?: boolean;
  overlay?: OverlayItem[];
  territoryMarkers?: {
    black: Pt[];
    white: Pt[];
    dame?: Pt[];
    deadStones?: Pt[];
  };
}) {
```

At the very end of the SVG (just before the closing `</svg>` — find the last `</svg>` in the file and insert above it), add:

```tsx
      {territoryMarkers && (
        <g aria-hidden>
          {territoryMarkers.black.map(([x, y]) => (
            <rect
              key={`tb-${x}-${y}`}
              data-territory="black"
              x={pad + x * CELL - CELL * 0.09}
              y={pad + y * CELL - CELL * 0.09}
              width={CELL * 0.18}
              height={CELL * 0.18}
              fill="rgb(26 23 21)"
            />
          ))}
          {territoryMarkers.white.map(([x, y]) => (
            <rect
              key={`tw-${x}-${y}`}
              data-territory="white"
              x={pad + x * CELL - CELL * 0.09}
              y={pad + y * CELL - CELL * 0.09}
              width={CELL * 0.18}
              height={CELL * 0.18}
              fill="rgb(248 246 240)"
              stroke={palette.lineInk}
              strokeWidth={0.5}
            />
          ))}
          {(territoryMarkers.dame ?? []).map(([x, y]) => (
            <circle
              key={`td-${x}-${y}`}
              data-territory="dame"
              cx={pad + x * CELL}
              cy={pad + y * CELL}
              r={1.5}
              fill={palette.labelInk}
              opacity={0.6}
            />
          ))}
          {(territoryMarkers.deadStones ?? []).map(([x, y]) => (
            <g key={`tx-${x}-${y}`} data-territory="dead">
              <line
                x1={pad + x * CELL - CELL * 0.25}
                y1={pad + y * CELL - CELL * 0.25}
                x2={pad + x * CELL + CELL * 0.25}
                y2={pad + y * CELL + CELL * 0.25}
                stroke="rgb(var(--oxblood))"
                strokeWidth={1.25}
              />
              <line
                x1={pad + x * CELL + CELL * 0.25}
                y1={pad + y * CELL - CELL * 0.25}
                x2={pad + x * CELL - CELL * 0.25}
                y2={pad + y * CELL + CELL * 0.25}
                stroke="rgb(var(--oxblood))"
                strokeWidth={1.25}
              />
            </g>
          ))}
        </g>
      )}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
npm test -- --run tests/board.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/components/Board.tsx web/tests/board.test.ts
git commit -m "feat(board): add territoryMarkers prop with SVG overlay"
```

---

## Task 7: Wire the scoring overlay + replace `Dialog` with `Sheet`

**Files:**
- Modify: `web/app/game/play/[id]/page.tsx`

The play page already stores `scoringDetail` in state and renders a modal `Dialog` showing the breakdown (lines ~462–513). We pipe the new fields into `<Board territoryMarkers={...}>` and swap the Dialog for a non-modal `Sheet`.

- [ ] **Step 1: Locate the existing dialog**

Open `web/app/game/play/[id]/page.tsx` and confirm the scoring `Dialog` block is still at the location reviewed in the spec (search for `scoringDetail !== null`). If line numbers differ, work from the search hit.

- [ ] **Step 2: Update the imports**

Find the line that imports `Dialog` (e.g. `import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"`) and add:

```ts
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
```

(Leave the `Dialog` import in place — other dialogs on this page may still use it. Only remove it after confirming no other usage in the file via `grep -n "Dialog" web/app/game/play/\\[id\\]/page.tsx`.)

- [ ] **Step 3: Compute markers from `scoringDetail`**

Just above the `return (...)` of the page, add:

```ts
  const territoryMarkers = scoringDetail
    ? {
        black: scoringDetail.black_points,
        white: scoringDetail.white_points,
        dame: scoringDetail.dame_points,
        deadStones: scoringDetail.dead_stones,
      }
    : undefined;
```

Find the `<Board ... />` element on this page and add the prop:

```tsx
        <Board
          size={g.boardSize}
          board={g.board}
          /* …existing props… */
          territoryMarkers={territoryMarkers}
        />
```

- [ ] **Step 4: Replace the scoring `Dialog` with `Sheet`**

Replace the entire `<Dialog open={scoringDetail !== null} …>…</Dialog>` block (the second of the two dialogs on the page — the one whose `DialogTitle` uses `t("game.scoringBreakdown")`) with:

```tsx
      <Sheet
        open={scoringDetail !== null}
        onOpenChange={(open) => {
          if (!open) setScoringDetail(null);
        }}
      >
        <SheetContent
          side="right"
          className="w-full sm:max-w-sm"
          // Non-modal: backdrop click does NOT dismiss; the user closes via
          // the explicit button so the territory map stays visible while
          // they read the breakdown.
        >
          <SheetHeader>
            <SheetTitle>
              {scoringDetail?.reason === "ai_passed"
                ? t("game.aiPassedScoredTitle")
                : t("game.scoringBreakdown")}
            </SheetTitle>
            <SheetDescription className="font-serif text-2xl text-ink">
              {scoringDetail?.result ?? ""}
            </SheetDescription>
          </SheetHeader>
          {scoringDetail && (
            <div className="flex flex-col gap-3 font-mono tabular-nums text-sm mt-4">
              <div className="grid grid-cols-3 gap-2 border-b border-ink-faint pb-2">
                <span className="text-ink-mute">{t("game.blackTerritory")}</span>
                <span className="text-right">{scoringDetail.black_territory}</span>
                <span className="text-right text-ink-mute">
                  +{scoringDetail.black_captures} {t("game.blackCaptures")}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 border-b border-ink-faint pb-2">
                <span className="text-ink-mute">{t("game.whiteTerritory")}</span>
                <span className="text-right">{scoringDetail.white_territory}</span>
                <span className="text-right text-ink-mute">
                  +{scoringDetail.white_captures} {t("game.whiteCaptures")}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 border-b border-ink-faint pb-2">
                <span className="text-ink-mute">{t("game.komiLabel")}</span>
                <span />
                <span className="text-right">+{scoringDetail.komi}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 font-semibold">
                <span>{t("game.totalLabel")}</span>
                <span className="text-right">● {scoringDetail.black_score}</span>
                <span className="text-right">○ {scoringDetail.white_score}</span>
              </div>
            </div>
          )}
          <div className="flex justify-end mt-6">
            <Button onClick={() => setScoringDetail(null)}>
              {t("game.close") /* fallback to game.cancel below if not yet added */}
            </Button>
          </div>
        </SheetContent>
      </Sheet>
```

If `t("game.close")` returns the key string (i.e. no translation), fall back to `t("game.cancel")` — same key the dialog used. Search both `web/lib/i18n/ko.json` and `en.json` first; if `game.close` is missing, use `game.cancel`.

- [ ] **Step 5: Type-check + lint + tests**

```bash
cd web && npm run type-check && npm run lint && npm test -- --run
```

Expected: clean.

- [ ] **Step 6: Manual smoke** (skip if this is a subagent without a browser)

Start the dev stack (`backend/` uvicorn + `web/` next dev) and play through to a passing/score-request finish on a 9×9 game. Confirm: territory squares appear on the board, the Sheet slides in from the right (or bottom on mobile width), and dismissing it leaves the markers in place.

- [ ] **Step 7: Commit**

```bash
git add web/app/game/play/[id]/page.tsx
git commit -m "feat(play): scoring breakdown as Sheet + territory map on board"
```

---

## Task 8: Render the wood-grain filter on Kaya/wood themes

**Files:**
- Modify: `web/components/Board.tsx`

- [ ] **Step 1: Write the failing test** — append to `web/tests/board.test.ts`

```ts
describe("Board surface=wood themes", () => {
  it("renders the wood grain filter when theme has surface='wood'", () => {
    // Force theme via the Zustand store before render
    const { useBoardTheme } = require("@/store/boardThemeStore");
    useBoardTheme.setState({ theme: "kaya" });
    const board = ".".repeat(9 * 9);
    const { container } = render(<Board size={9} board={board} />);
    expect(container.querySelector("filter#kayaGrain")).not.toBeNull();
    expect(container.querySelector('rect[filter="url(#kayaGrain)"]')).not.toBeNull();
  });

  it("does NOT render the wood grain filter on paper theme", () => {
    const { useBoardTheme } = require("@/store/boardThemeStore");
    useBoardTheme.setState({ theme: "paper" });
    const board = ".".repeat(9 * 9);
    const { container } = render(<Board size={9} board={board} />);
    expect(container.querySelector("filter#kayaGrain")).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
npm test -- --run tests/board.test.ts
```

Expected: FAIL — `filter#kayaGrain` not present.

- [ ] **Step 3: Add the `<defs>` block + conditional surface**

Inside `Board.tsx`, just inside the opening `<svg ...>` (right after the `<rect>` border line of the board, around the existing `viewBox` block), insert:

```tsx
      <defs>
        {palette.surface === "wood" && (
          <filter id="kayaGrain" x="0" y="0" width="100%" height="100%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.012 0.6"
              numOctaves={2}
              seed={7}
              result="noise"
            />
            <feColorMatrix
              in="noise"
              values="0 0 0 0 0.55  0 0 0 0 0.38  0 0 0 0 0.20  0 0 0 0.10 0"
              result="grain"
            />
            <feComposite in="grain" in2="SourceGraphic" operator="in" />
          </filter>
        )}
      </defs>
      {palette.surface === "wood" && (
        <rect
          x={0}
          y={0}
          width={W}
          height={W}
          fill={palette.bg}
          filter="url(#kayaGrain)"
        />
      )}
```

The base `<svg style={{ backgroundColor: palette.bg }}>` is already setting the flat background — the filtered `<rect>` overlays grain on top. Paper/slate skip the filter and the flat bg shows through unchanged.

- [ ] **Step 4: Run the test to verify it passes**

```bash
npm test -- --run tests/board.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/components/Board.tsx web/tests/board.test.ts
git commit -m "feat(board): SVG fractal-noise wood grain on kaya/wood themes"
```

---

## Task 9: Render lithic stones (radial gradient) when `stoneStyle === 'lithic'`

**Files:**
- Modify: `web/components/Board.tsx`

- [ ] **Step 1: Write the failing test** — append to `web/tests/board.test.ts`

```ts
describe("Board lithic stones", () => {
  it("uses radial gradient fill when theme.stoneStyle is lithic", () => {
    const { useBoardTheme } = require("@/store/boardThemeStore");
    useBoardTheme.setState({ theme: "kaya" });
    const board = "B" + ".".repeat(9 * 9 - 1); // single black stone at (0,0)
    const { container } = render(<Board size={9} board={board} />);
    const stone = container.querySelector('circle[data-stone="B"]');
    expect(stone).not.toBeNull();
    expect(stone?.getAttribute("fill")).toContain("url(#stoneBlackLithic)");
  });

  it("uses flat token fill on paper theme", () => {
    const { useBoardTheme } = require("@/store/boardThemeStore");
    useBoardTheme.setState({ theme: "paper" });
    const board = "B" + ".".repeat(9 * 9 - 1);
    const { container } = render(<Board size={9} board={board} />);
    const stone = container.querySelector('circle[data-stone="B"]');
    expect(stone?.getAttribute("fill")).not.toContain("url(");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
npm test -- --run tests/board.test.ts
```

Expected: FAIL — stones currently have no `data-stone` attribute and use flat fill.

- [ ] **Step 3: Add the gradient defs + branch the stone fill**

Inside the existing `<defs>` block (added in Task 8), append the two gradients (always defined; cheap):

```tsx
        <radialGradient id="stoneBlackLithic" cx="35%" cy="32%" r="65%">
          <stop offset="0%" stopColor="rgb(74 66 60)" />
          <stop offset="55%" stopColor="rgb(28 24 21)" />
          <stop offset="100%" stopColor="rgb(8 6 6)" />
        </radialGradient>
        <radialGradient id="stoneWhiteLithic" cx="35%" cy="32%" r="70%">
          <stop offset="0%" stopColor="rgb(253 252 248)" />
          <stop offset="65%" stopColor="rgb(229 224 213)" />
          <stop offset="100%" stopColor="rgb(187 181 168)" />
        </radialGradient>
```

Now find the existing stone-rendering block (the `Array.from(board).map((c, idx) => …)` returning the `<circle>`). Replace the `fill` and `stroke` lines — and add `data-stone` — so the new branch is:

```tsx
        const isLithic = palette.stoneStyle === "lithic";
        const fill =
          c === "B"
            ? isLithic
              ? "url(#stoneBlackLithic)"
              : tokens.light["stone-black"]
            : isLithic
              ? "url(#stoneWhiteLithic)"
              : tokens.light["stone-white"];
        const stroke =
          c === "W" && !isLithic ? palette.lineInk : "transparent";
        return (
          <circle
            key={`st-${idx}`}
            data-stone={c}
            cx={cx}
            cy={cy}
            r={CELL * 0.45}
            fill={fill}
            stroke={stroke}
            strokeWidth={c === "W" && !isLithic ? 0.5 : 0}
          />
        );
```

(If the existing return-block has a `strokeWidth` attribute, keep it but make it 0 in the lithic branch — the radial gradient already provides the white stone's edge.)

- [ ] **Step 4: Run the test to verify it passes**

```bash
npm test -- --run tests/board.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/components/Board.tsx web/tests/board.test.ts
git commit -m "feat(board): lithic 3D stones via radial gradient on kaya/wood/slate"
```

---

## Task 10: Render a faint drop-shadow under stones when `theme.shadow === true`

**Files:**
- Modify: `web/components/Board.tsx`

- [ ] **Step 1: Write the failing test** — append to `web/tests/board.test.ts`

```ts
describe("Board stone shadow", () => {
  it("renders a shadow ellipse per stone on kaya theme", () => {
    const { useBoardTheme } = require("@/store/boardThemeStore");
    useBoardTheme.setState({ theme: "kaya" });
    const board = "B" + ".".repeat(9 * 9 - 1);
    const { container } = render(<Board size={9} board={board} />);
    expect(container.querySelector('ellipse[data-stone-shadow]')).not.toBeNull();
  });

  it("renders no shadow on paper theme", () => {
    const { useBoardTheme } = require("@/store/boardThemeStore");
    useBoardTheme.setState({ theme: "paper" });
    const board = "B" + ".".repeat(9 * 9 - 1);
    const { container } = render(<Board size={9} board={board} />);
    expect(container.querySelector('ellipse[data-stone-shadow]')).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
npm test -- --run tests/board.test.ts
```

Expected: FAIL.

- [ ] **Step 3: Render the shadow before each stone circle**

In the same map block from Task 9, return a fragment with the shadow ellipse first, then the stone:

```tsx
        return (
          <g key={`st-${idx}`}>
            {palette.shadow && (
              <ellipse
                data-stone-shadow
                cx={cx}
                cy={cy + CELL * 0.05}
                rx={CELL * 0.42}
                ry={CELL * 0.12}
                fill="rgba(0,0,0,0.18)"
              />
            )}
            <circle
              data-stone={c}
              cx={cx}
              cy={cy}
              r={CELL * 0.45}
              fill={fill}
              stroke={stroke}
              strokeWidth={c === "W" && !isLithic ? 0.5 : 0}
            />
          </g>
        );
```

(The outer `<g>` replaces the top-level `<circle>` key — move the React `key` to the wrapper.)

- [ ] **Step 4: Run the test to verify it passes**

```bash
npm test -- --run tests/board.test.ts
```

Expected: PASS — both new specs and all prior ones still green.

- [ ] **Step 5: Commit**

```bash
git add web/components/Board.tsx web/tests/board.test.ts
git commit -m "feat(board): faint drop-shadow under stones on kaya/wood/slate"
```

---

## Task 11: Update CLAUDE.md — note the board-only shadow exception

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Read the current §Radius/Shadow section**

Open `CLAUDE.md` and find the line:

```
**Radius / Shadow** — `rounded-none` (카드·보드), `rounded-sm` (2px 기본), `rounded-full` (토글·배지·돌)만. 그림자는 사용하지 않음 — 위계는 규칙선과 배경 대비로.
```

- [ ] **Step 2: Append the exception**

Replace that line with:

```
**Radius / Shadow** — `rounded-none` (카드·보드), `rounded-sm` (2px 기본), `rounded-full` (토글·배지·돌)만. 그림자는 사용하지 않음 — 위계는 규칙선과 배경 대비로. **예외**: `Board.tsx`의 `lithic` 돌 스타일은 사실감 표현을 위해 미세 drop-shadow 사용 (Kaya/wood/slate 테마 한정, paper는 평면 유지).
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: allow board lithic stone shadow as the only shadow exception"
```

---

## Task 12: Acquire and add real stone-clack sample files + credits

**Files:**
- Create: `web/public/sounds/stone-1.mp3`
- Create: `web/public/sounds/stone-2.mp3`
- Create: `web/public/sounds/stone-3.mp3`
- Create: `web/public/sounds/CREDITS.md`

This task does not have a unit test — the asset is the deliverable. The next task (the soundfx rewrite) covers the integration test.

- [ ] **Step 1: Make the sounds directory**

```bash
mkdir -p web/public/sounds
```

- [ ] **Step 2: Source the samples (in priority order)**

  1. **Sabaki repo** — clone or browse <https://github.com/SabakiHQ/Sabaki>, look in `resources/sounds/` (file names like `0.wav`, `1.wav`, etc.). Inspect `LICENSES/` or the top-level README for the audio licence. If MIT or CC0, take three files, transcode to mp3 at 96kbps mono with `ffmpeg`:

     ```bash
     ffmpeg -i 0.wav -ac 1 -ar 22050 -b:a 96k web/public/sounds/stone-1.mp3
     ```

  2. **freesound.org fallback** — search `go stone`, `baduk stone`, `shogi`. Filter by license `Creative Commons 0`. Download three short (50–150ms) clacks, transcode as above.

  3. **Synth fallback** — if no acceptable licensed sample is available within ~30 minutes, generate three approximate clacks with `ffmpeg` from a short noise burst run through a low-pass filter; document this in CREDITS.md as `synthetic placeholder`. This is acceptable — the next task only requires that `playStoneClick()` can pick from the pool.

- [ ] **Step 3: Verify file sizes (sanity)**

```bash
ls -lh web/public/sounds/
```

Each file should be 5–30KB. If any is over 80KB, re-encode at lower bitrate.

- [ ] **Step 4: Write CREDITS.md**

Create `web/public/sounds/CREDITS.md` with the actual source/license used. Template:

```markdown
# Sound credits

| File | Source | License | Original author |
|---|---|---|---|
| stone-1.mp3 | <URL or repo path> | <CC0 / MIT / CC-BY-4.0> | <name or "anonymous"> |
| stone-2.mp3 | … | … | … |
| stone-3.mp3 | … | … | … |
```

If the chosen source is CC-BY, attribution above is mandatory and we additionally must show it in the running app's About/Settings page (out of scope for this task — open a follow-up).

- [ ] **Step 5: Commit**

```bash
git add web/public/sounds/
git commit -m "assets: add stone-clack sound samples + credits"
```

---

## Task 13: Rewrite `soundfx.ts` to use an `<audio>` pool

**Files:**
- Modify: `web/lib/soundfx.ts`
- Create: `web/tests/lib/soundfx.test.ts`

- [ ] **Step 1: Write the failing test** — create `web/tests/lib/soundfx.test.ts`

```ts
import { describe, it, expect, vi, beforeEach } from "vitest";

class FakeAudio {
  src: string;
  volume = 1;
  paused = true;
  static instances: FakeAudio[] = [];
  constructor(src: string) {
    this.src = src;
    FakeAudio.instances.push(this);
  }
  play() {
    this.paused = false;
    return Promise.resolve();
  }
  pause() {
    this.paused = true;
  }
  set currentTime(_v: number) {
    // no-op
  }
}

describe("soundfx", () => {
  beforeEach(() => {
    vi.stubGlobal("Audio", FakeAudio);
    FakeAudio.instances = [];
    localStorage.clear();
  });

  it("plays one sample from the pool when enabled", async () => {
    const { playStoneClick } = await import("@/lib/soundfx");
    playStoneClick();
    const playing = FakeAudio.instances.filter((a) => !a.paused);
    expect(playing.length).toBe(1);
    expect(playing[0].src).toMatch(/\/sounds\/stone-\d\.mp3$/);
  });

  it("does not play when disabled", async () => {
    const mod = await import("@/lib/soundfx");
    mod.setStoneSoundEnabled(false);
    mod.playStoneClick();
    const playing = FakeAudio.instances.filter((a) => !a.paused);
    expect(playing.length).toBe(0);
  });

  it("persists enabled flag in localStorage", async () => {
    const mod = await import("@/lib/soundfx");
    mod.setStoneSoundEnabled(false);
    expect(localStorage.getItem("sfx:stone")).toBe("0");
    mod.setStoneSoundEnabled(true);
    expect(localStorage.getItem("sfx:stone")).toBe("1");
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd web && npm test -- --run tests/lib/soundfx.test.ts
```

Expected: FAIL — current `playStoneClick` uses AudioContext, no `<audio>` instance is created, so the pool assertion fails.

- [ ] **Step 3: Rewrite `web/lib/soundfx.ts`**

```ts
const STORAGE_KEY = "sfx:stone";
const SAMPLES = [
  "/sounds/stone-1.mp3",
  "/sounds/stone-2.mp3",
  "/sounds/stone-3.mp3",
];
const POOL_SIZE = 3;

let enabled = true;
let pool: HTMLAudioElement[] | null = null;
let cursor = 0;

if (typeof window !== "undefined") {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "0") enabled = false;
}

function getPool(): HTMLAudioElement[] | null {
  if (typeof window === "undefined") return null;
  if (pool) return pool;
  pool = [];
  for (let i = 0; i < POOL_SIZE; i++) {
    const a = new Audio(SAMPLES[i % SAMPLES.length]);
    a.volume = 0.7;
    a.preload = "auto";
    pool.push(a);
  }
  return pool;
}

export function setStoneSoundEnabled(on: boolean): void {
  enabled = on;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, on ? "1" : "0");
  }
}

export function isStoneSoundEnabled(): boolean {
  return enabled;
}

export function playStoneClick(): void {
  if (!enabled) return;
  const p = getPool();
  if (!p) return;
  const sample = SAMPLES[Math.floor(Math.random() * SAMPLES.length)];
  // Round-robin across audio elements so rapid clicks don't cut each other off.
  const slot = p[cursor];
  cursor = (cursor + 1) % p.length;
  slot.pause();
  slot.currentTime = 0;
  if (slot.src !== window.location.origin + sample) {
    slot.src = sample;
  }
  void slot.play().catch(() => {
    // Browser refused autoplay (no user gesture yet) — silently ignore.
  });
}
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
npm test -- --run tests/lib/soundfx.test.ts
```

Expected: PASS.

- [ ] **Step 5: Run the full Vitest suite to confirm nothing broke**

```bash
npm test -- --run
```

Expected: every test passes.

- [ ] **Step 6: Commit**

```bash
git add web/lib/soundfx.ts web/tests/lib/soundfx.test.ts
git commit -m "feat(soundfx): real stone-clack samples via audio element pool"
```

---

## Task 14: Final integration — full test sweep + commit lockstep

**Files:**
- (no files modified — verification step)

- [ ] **Step 1: Backend full sweep**

```bash
cd backend && source .venv311/bin/activate
pytest -q
ruff check app
mypy app
```

Expected: all tests pass; ruff clean; mypy error count not greater than the baseline before this work began (the baseline error count is logged in the prior session — record it before starting Task 1 and ensure it's the same or lower at the end).

- [ ] **Step 2: Frontend full sweep**

```bash
cd web
npm run type-check
npm run lint
npm test -- --run
```

Expected: all green.

- [ ] **Step 3: Manual smoke (only if running interactively)**

Start the dev stack and verify:

  1. Settings or top nav board-theme picker switches between paper / wood / kaya / slate; Kaya now shows wood grain + 3D stones; paper looks identical to before.
  2. Place a stone — the clack sound is audibly more substantial than before; rapid clicks don't choke each other.
  3. Play to two passes (or hit "계가 신청") — the territory map appears as small black/white squares on empty intersections, neutral points have a faint grey dot, and dead stones (if any) carry an oxblood X. The Sheet slides in from the right with the breakdown; closing it leaves the markers in place.

- [ ] **Step 4: Commit a marker tag (optional but recommended)**

```bash
git tag -a polish-pack-2026-04-26 -m "ship: stone sound + territory map + Kaya board"
```

---

## Self-Review

**Spec coverage check** (each spec section maps to a task):

- §2 Sound → Task 12 + Task 13
- §3 Scoring backend (`_flood_territory` + `ScoreResult`) → Task 1
- §3 Scoring service layer (`ScoringDetail` + dead_stones) → Task 2
- §3 Scoring WS payload → Task 3
- §3 Scoring frontend type → Task 4
- §3 Scoring frontend overlay + Sheet → Task 6 + Task 7
- §4.2 BoardThemeMeta → Task 5
- §4.3 Wood grain filter → Task 8
- §4.4 Lithic stones → Task 9
- §4.5 Drop-shadow → Task 10
- §4.6 CLAUDE.md design system exception → Task 11
- §5 Test additions → covered inside each task's TDD step
- §6 Decisions / open items → noted in plan; deferred to implementation as the spec already contracts

**Type consistency check:**
- Backend `frozenset[tuple[int, int]]` → frontend `[number, number][]` via `_serialize_points` (Task 3) which sorts and converts. Sorted output is deterministic — the frontend doesn't depend on order, but tests can still inspect the array.
- `ScoringDetail` (service) and `ScoreResult` (rules) both gain matching field names — `black_points` / `white_points` / `dame_points` / `dead_stones` (the last only on `ScoringDetail` since it's a service-level concept derived from KataGo).
- Frontend `ScoreResultMsg` mirrors the wire fields exactly.
- `BoardThemeMeta` field names (`surface`, `stoneStyle`, `shadow`) used identically in Tasks 5, 8, 9, 10.
- Stone gradient ids (`stoneBlackLithic`, `stoneWhiteLithic`) defined in Task 9 and not referenced elsewhere.

**Placeholder scan:** every step shows the actual code or command. The only deferred items are the sound source (with explicit fallback in Task 12 step 2) and the i18n key fallback in Task 7 step 4 (with the exact lookup the engineer should perform).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-26-quality-polish-pack.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
