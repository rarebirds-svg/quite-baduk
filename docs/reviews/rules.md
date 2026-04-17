# Rules Engine Review

**Reviewer:** Rules-Reviewer
**Date:** 2026-04-17
**Files reviewed:**
- `backend/app/core/rules/__init__.py`
- `backend/app/core/rules/board.py`
- `backend/app/core/rules/captures.py`
- `backend/app/core/rules/ko.py`
- `backend/app/core/rules/scoring.py`
- `backend/app/core/rules/handicap.py`
- `backend/app/core/rules/sgf_coord.py`
- `backend/app/core/rules/engine.py`
- `backend/tests/rules/test_board.py`
- `backend/tests/rules/test_captures.py`
- `backend/tests/rules/test_ko.py`
- `backend/tests/rules/test_scoring.py`
- `backend/tests/rules/test_handicap.py`
- `backend/tests/rules/test_sgf_coord.py`
- `backend/tests/rules/test_engine.py`

## Test Execution

**Unable to execute pytest** — the sandbox denied every Bash invocation of the form
`pytest ... --cov=app.core.rules --cov-report=term-missing --cov-fail-under=100 -v`,
including direct invocation via `.venv311/bin/pytest`.
The review therefore relies on static inspection of source and test files.

Based on static inspection:

- Test files total: 7 (`test_board`, `test_captures`, `test_ko`, `test_scoring`,
  `test_handicap`, `test_sgf_coord`, `test_engine`).
- Approximate test functions counted by hand: ~80.
- Every non-`pragma: no cover` branch in `app/core/rules/*` appears to have at
  least one exercising test. The `# pragma: no cover` annotations cover
  unreachable defensive branches:
  - `board.py:82` — BFS re-push guard (pre-filtered by caller)
  - `board.py:114` — `__repr__` debug helper
  - `engine.py:81`, `engine.py:85`, `engine.py:142` — unreachable branches
    after `gtp_to_xy` already validates (see "Minor" section)
- **Status:** Coverage NOT independently verified — test execution blocked.
  Agent/reviewer must re-run the pytest command to confirm 100%.

## Findings

### Critical (must-fix)

- [ ] None identified.

### Important (should-fix)

1. **Resign move leaves game in an "active" state.**
   `engine.play` accepts `Move(color, coord=None)` as resign. It records the
   move and flips `to_move`, but `is_game_over(state)` still returns `False`
   (it only checks `consecutive_passes >= 2`). Consequence: the engine allows
   the opponent (or the resigning player, on their next turn) to keep playing
   moves after a resign. Spec §7.1 / §5.4 assume resign terminates the game.
   Suggested fix: add an explicit `resigned: Color | None = None` field on
   `GameState`, set it inside the resign branch of `play`, and make
   `is_game_over` return `True` when it is populated. Also consider rejecting
   further `play()` calls once set (raise `IllegalMoveError("GAME_OVER")`).
   Relevant code: `backend/app/core/rules/engine.py:54-64`, `:117-118`.

2. **Handicap stones don't set `to_move = WHITE` or `komi = 0.5`.**
   `apply_handicap(board, stones)` returns a new `Board` only. Spec §7.2
   states "첫 수는 백(AI)부터" (first move is white) and "덤 0.5" for
   handicap games. Today the caller must remember to flip `to_move` and set
   `komi` separately; a Game Service mistake here silently corrupts the game
   rules. Suggested fix: provide a higher-level `setup_handicap_game(stones)
   -> GameState` helper that returns a ready-to-play `GameState` with correct
   board, `to_move=WHITE`, `komi=0.5`. Alternatively document this contract
   loudly in the module docstring and add an assertion test.
   Relevant code: `backend/app/core/rules/handicap.py:31-46`.

3. **`GameState` is mutable — ko-state can be overwritten after the fact.**
   `GameState`/`Move` use `@dataclass` (no `frozen=True`), so callers can mutate
   `state.ko_state`, `state.captures`, `state.move_history` directly. The test
   `test_play_ko_violation` relies on this (line 102: `state.ko_state = ...`).
   While intentional for that test, it enables accidental corruption in the
   Game Service. Suggested fix: `@dataclass(frozen=True)` with `replace()`
   usage, or at least a note in the module docstring that all returned states
   are to be treated as immutable.
   Relevant code: `backend/app/core/rules/engine.py:30-38`.

4. **`_flood_territory` rebuilds the board once per dead stone.**
   `scoring.py:38-40` iterates dead stones and calls `effective.remove(*pos)`
   inside a loop; each call reallocates a 361-cell tuple. At 30 dead stones
   this is 30 × 361 = ~11k allocations per scoring call. For A-scale usage
   this is still sub-millisecond but it is avoidable. Suggested fix: use
   `Board.remove_group(dead_stones)` once (the API already exists).
   Relevant code: `backend/app/core/rules/scoring.py:37-40`.

### Minor / Observations

1. **Unreachable error branches kept behind `pragma: no cover`.**
   `engine.py:81-85` and `engine.py:142` are unreachable because `gtp_to_xy`
   already validates both the coordinate format and the row/column range. The
   branches are defensive but harmless; consider removing to simplify or
   converting to `assert` with a clear message.

2. **Test `test_play_ko_violation` hand-crafts a ko state.**
   It works but does not exercise a real capture-recapture sequence; a
   physical-shape ko test would give more confidence.
   Relevant code: `backend/tests/rules/test_engine.py:84-105`.

3. **`test_play_out_of_bounds` accepts two error codes.**
   The "INVALID_COORD" branch is unreachable (see point 1); the assertion
   `exc_info.value.code in ("OUT_OF_BOUNDS", "INVALID_COORD")` is a loose
   check. Tighten to `== "OUT_OF_BOUNDS"`.
   Relevant code: `backend/tests/rules/test_engine.py:46-50`.

4. **`test_play_ko` is mislabeled.**
   It only verifies that `ko_state.previous_board` is updated after a
   non-pass move; it does not prove ko detection end-to-end.
   Relevant code: `backend/tests/rules/test_engine.py:67-82`.

5. **Pass move updates `ko_state` to current (unchanged) board.**
   `engine.py:71` does `ko_state=state.ko_state.update(state.board)`. Since a
   pass does not change the board, this means `previous_board == board`. Any
   legal subsequent non-pass move adds a stone, so the new board differs →
   ko check trivially passes. Functionally correct, but worth a comment
   noting the intent (the ko window is effectively cleared by any pass).
   Relevant code: `backend/app/core/rules/engine.py:66-75`.

6. **`score_game` silently ignores dead-stone positions that are empty.**
   `scoring.py:90-95` — if a caller passes a dead-stone coord that is already
   `EMPTY` on the board, no extras are credited. Consider `assert
   board.get(*pos) != EMPTY` or raise `ValueError` to catch upstream bugs.

7. **`IllegalMoveError` does not distinguish `INVALID_COORD`.**
   The string `"INVALID_COORD"` appears in `engine.py:82` but is unreachable,
   never documented, and not in the spec list (spec §10.2 lists five codes).
   Remove the dead branch to keep the code set canonical.

8. **Docstring drift.**
   `captures.place_with_captures` docstring says "Caller is responsible" for
   checking ko/occupied/suicide. That is accurate, but the header could name
   the engine module that actually does it so future maintainers find it fast.

9. **No explicit 19x19 constant import check in scoring.**
   `scoring.py` imports `BOARD_SIZE` but the function could easily be
   generalised later; `_flood_territory` hard-codes `range(BOARD_SIZE)`. Fine
   for now, but note V2 might add 9x9/13x13 (spec §1.3).

10. **SGF build does not escape properties or include handicap.**
    `build_sgf` emits `GM[1]FF[4]SZ[{n}]KM[{komi}]` but omits `HA[{n}]` and
    `AB[...]` for handicap games. Golden-test goal (§11.2) of matching 20
    professional SGFs may fail for handicap games. Out of scope for the
    rules engine purely, but worth flagging now.
    Relevant code: `backend/app/core/rules/engine.py:131-150`.

## Edge Cases Not Covered

The current test suite does **not** exercise the following scenarios that
the review brief explicitly calls out, plus several additional gaps:

1. **Ko is lifted after an intervening move.** No test plays M1 creating a
   ko, W plays an unrelated move M2, then B legally recaptures. (Static
   analysis shows the code is correct because an extra W stone on the board
   means `new_board != previous_board`, but the test suite does not lock
   this invariant in.)

2. **Capture that would otherwise be suicide (corner / edge shapes).**
   `test_capture_before_suicide_check` and `test_is_suicide_capture_prevents`
   both test "my stone survives because I captured", but neither tests the
   engine path end-to-end via `play(state, move)` with a corner / edge ko
   shape where the placed stone has zero own liberties pre-capture.

3. **Scoring with both dead stones AND live stones of the same color.**
   No test places a live white wall AND dead white stones inside black
   territory simultaneously and verifies that only the dead ones are counted
   as captures while the live wall still acts as territory border.

4. **Seki.** Spec §7.1 and §11.2 list seki, but no test covers a seki shape
   (two alive groups sharing a single set of dame, neither wins territory).

5. **Handicap 9 exact-coordinate assertion vs spec.** `test_handicap_9_stones`
   only counts 9 stones; it does not assert that the exact set is
   `{D4, D16, Q4, Q16, D10, Q10, K4, K10, K16}`. A future edit that changed
   the coord list (e.g., to K4→J4) would still pass this test.

6. **Resign in the middle of a game.** `test_resign_move` only verifies state
   after a single resign from the initial board. No test verifies that (a)
   the game is treated as over (per current code it is *not* — see Important
   finding #1), (b) no further moves can be played, (c) SGF result reflects
   resignation.

7. **Real capture-recapture ko.** See Minor #2. A true three-turn cycle
   (play, opponent recaptures, you attempt immediate recapture → ILLEGAL_KO)
   is not reproduced from actual board positions.

8. **Snapback.** A classic tesuji where a stone is offered to be captured so
   the opponent's capturing stone itself has one liberty. Not strictly a ko,
   but should be legal and is good coverage for the capture engine.

9. **Passing when ko was just set.** Does pass correctly "clear" the ko? The
   code stores `previous_board=current_board` on pass; no test verifies the
   next move after the pass is accepted when it would have violated ko.

10. **`apply_handicap(0)` is a no-op but **other invalid values** (e.g., 1,
    10, -1, 100) — `test_handicap_invalid_raises` covers 1 and 10 only.

11. **`score_game` with negative captures.** No input validation. A caller
    bug (passing -5 captures) silently corrupts the score.

## Recommendations

1. **Fix resign semantics** (Important #1) — this is the single item most
   likely to cause visible bugs in the Game Service. Either make resign
   terminal in the engine, or document that the engine intentionally does
   not handle it and the Game Service owns that state.

2. **Add a `setup_handicap_game(stones)` helper** (Important #2) so the
   Game Service cannot accidentally start a handicap game with
   `komi=6.5` / `to_move=BLACK`.

3. **Add the explicitly-missing tests** called out in the Edge Cases section,
   in priority order:
   - Ko lifted after intervening move
   - Handicap-9 exact coordinate set
   - Real capture-recapture ko
   - Resign semantics (after fix)
   - Seki territory region
   - Dead + live stones of the same colour in the same territory

4. **Freeze `GameState` and `Move`** with `@dataclass(frozen=True)` and
   update the one test that mutates `ko_state` to use `dataclasses.replace`.

5. **Replace the loop-based `remove` in `_flood_territory`** with a single
   `Board.remove_group(dead_stones)` call.

6. **Delete the unreachable `INVALID_COORD` branch** and the two
   `pragma: no cover` bounds checks in `engine.py` or convert them to
   `assert` statements with descriptive messages.

7. **Confirm 100% coverage by actually running pytest** — the sandbox
   blocked me from doing so. Either re-run in this environment with Bash
   permission, or have the Rules-Agent report the exact `pytest --cov`
   output.

8. **Add `HA[n]` and `AB[...]` SGF properties** for handicap games (or route
   that responsibility to the SGF module explicitly).

## Verdict

**APPROVED_WITH_CONCERNS**

The rules engine is well-structured, the code is clean, and the core
algorithms (captures, simple ko, territory flood-fill, GTP/SGF coord
conversion) look correct under static review. The existing test suite is
broad and appears to cover the vast majority of branches.

However, three issues should be addressed before declaring the engine
"done":

1. Resign does not terminate the game (Important #1).
2. Handicap setup is incomplete (komi + to_move are the caller's problem;
   easy to get wrong) (Important #2).
3. Several edge cases explicitly called out in the review brief and in
   spec §11.2 (ko after intervening move, seki, exact handicap-9
   coordinates, resign semantics) are not covered by tests — and one of
   them (resign) currently masks a real semantic bug.

Additionally, **coverage was not independently verified** because the
sandbox denied pytest execution. The agent must confirm `--cov-fail-under=100`
actually passes before the engine is handed to downstream consumers.
