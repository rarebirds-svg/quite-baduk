# Frontend Review
**Reviewer:** Frontend-Reviewer
**Date:** 2026-04-17

## Checks
- Type check: PASS (`tsc --noEmit` clean)
- Lint: PASS (`next lint` — no warnings/errors)
- Vitest: 8/8 passed (3 files: board.test.ts, i18n.test.ts, sgf.test.ts)

## Scope audited
- `web/app/*` (layout, pages: /, /login, /signup, /game/new, /game/play/[id], /game/review/[id], /history, /settings)
- `web/components/*` (Board, TopNav, RankPicker, HandicapPicker, GameControls, ScorePanel, AnalysisOverlay, ThemeBootstrapper)
- `web/lib/*` (api, ws, board, sgf, theme, i18n)
- `web/store/*` (authStore, gameStore)
- `web/tests/*`
- Cross-checked error-code surface in `backend/app/api/{auth,games,ws,analysis}.py`, `backend/app/services/{game_service,user_service}.py`, `backend/app/core/rules/engine.py`, and `backend/app/errors.py`.

## Findings

### Critical
None. App builds, lints, type-checks, and all unit tests pass. No client-side secrets leaked (only `NEXT_PUBLIC_API_URL` env var is referenced). Auth cookies are `httponly` on the backend side; frontend only uses `credentials: "include"`. `gameStore.reset()` is invoked on unmount in `web/app/game/play/[id]/page.tsx`.

### Important

1. **Missing i18n keys for backend error codes** (`web/lib/i18n/{ko,en}.json`). The unit test `tests/i18n.test.ts` only verifies that ko/en keys match each other, not that every backend code has a key. The backend can emit these codes that have no entry in `errors.*`, so the UI will fall back to showing the raw key as the error message:
   - `INVALID_HANDICAP` — raised from `game_service.create_game` (HTTP 400 via `/api/games` POST). Shown in `/game/new` toast.
   - `INVALID_COLOR` — same path.
   - `INVALID_COORD` — raised from `core/rules/engine.py` for malformed coord, surfaced via WS `{type:"error", code:"INVALID_COORD"}`.
   - `INVALID_UNDO_STEPS` — raised from `game_service.undo_move`, surfaced via WS.
   - `AI_ILLEGAL_MOVE` — raised when KataGo returns an illegal move; surfaced via WS.
   - `validation_error` — note that `backend/app/errors.py` sets the response body's `error.code` to the literal string `"validation_error"` (even though `message_key` is `errors.validation`). Frontend `api.ts` uses `body.error.code` for the thrown `ApiError.code`, so `t("errors.validation_error")` currently falls back to the literal key. The i18n dict only has a `validation` key.

2. **`forbidden` casing mismatch between HTTP and WS paths**. `backend/app/api/games.py::_fetch_owned_game` raises `HTTPException(403, detail="forbidden")` (lowercase), but i18n has only uppercase `FORBIDDEN`. All WS / service errors use uppercase `FORBIDDEN`. So an HTTP 403 from `/api/games/{id}` (e.g., viewing another user's game, resign, SGF, hint) renders as the literal `errors.forbidden` string. Fix at backend (easier) by changing `detail="forbidden"` to `detail="FORBIDDEN"`, or add lowercase alias in both i18n dicts.

3. **Duplicate-send risk in `/game/play` controls**. `web/app/game/play/[id]/page.tsx:71` passes `disabled={g.gameOver}` to `<GameControls>` — it does **not** include `g.aiThinking`. That means while the AI is thinking, the user can still click Pass, Undo, Hint repeatedly; each click sends another WS message (`pass` sets aiThinking true, but Undo/Hint don't). The Board itself is correctly gated with `disabled={g.aiThinking || g.gameOver}` at line 64. Recommendation: pass `disabled={g.gameOver || g.aiThinking}` to `GameControls`, and in `undo()`/`hintMe()` set `aiThinking: true` for the duration of the request.

4. **Resign via REST does not update game state in the UI** (`web/app/game/play/[id]/page.tsx:47-50`). `resign()` calls the REST endpoint and manually sets `gameOver: true`, but doesn't populate `result`, `winner`, or close the WS. The backend's resign handler does not push a `game_over` message over the existing WS, so the user sees "결과:" with an empty value. Either (a) route resign through the WS (add a `{type: "resign"}` WS message handled by `ws.py`), or (b) after the REST response, update `gameStore` with the returned `GameSummary` (`result`, `winner`).

5. **WS reconnect drops in-flight user messages silently** (`web/lib/ws.ts:41-43`). `send()` is a no-op when `readyState !== OPEN` — during the 1.5s backoff or after close, the caller has no way to know the message was dropped. This doesn't *duplicate*, but could feel like "click did nothing." Also there is no cap on retries (infinite reconnect). Recommend buffering pending sends on reconnect or emitting a synthetic `error` to the UI.

6. **`ScorePanel` hard-codes Korean** (`web/components/ScorePanel.tsx`): "흑 잡은 수"/"백 잡은 수" are not in the i18n dict. The spec requires ko/en parity. Add `game.capturedByBlack` / `game.capturedByWhite` keys (or similar) and route through `useT()`.

### Minor

1. **Board click math is correct** (`web/components/Board.tsx:73-90`). `SIZE = 588` (=`2*24 + 30*18`); click rect spans x,y ∈ `[9, 579]` which fully covers the intersection grid `[24, 564]` and gives a half-cell tolerance at edges. `scale = SIZE / rect.width` assumes uniform aspect-preserving scaling, which is correct because (a) viewBox is square (588×588), (b) default `preserveAspectRatio="xMidYMid meet"` forces uniform scale, (c) `w-full max-w-[640px]` with an SVG preserves aspect automatically — `rect.height` ≈ `rect.width`. No bug here, but consider computing `scale` from both dimensions defensively in case future CSS breaks it, or use the SVG CTM (`svg.getScreenCTM().inverse()`) for mathematical correctness.

2. **`parseInt(params.id, 10)` in dynamic routes** (`/game/play/[id]`, `/game/review/[id]`). `useParams<{id: string}>()` can theoretically return `string | string[] | undefined` — TypeScript is only permissive because the return type is coerced via the generic. No runtime guard against `NaN`. Minor hardening: `if (!Number.isFinite(gameId)) return notFound();`.

3. **Dark mode lang attribute**. `app/layout.tsx` hardcodes `<html lang="ko">`. `initLocale()` overrides `document.documentElement.lang` at runtime, which is fine for a11y but produces a brief flash for English users. Acceptable for v1.

4. **`useEffect([gameId])` on play page disables exhaustive-deps warning**. It references `g.set`/`g.reset`, which are stable zustand setters — safe, but pulling `const setG = useGameStore(s => s.set)` etc. would satisfy the linter without the escape hatch.

5. **`resign` on play page doesn't wrap in `try/catch`** (`web/app/game/play/[id]/page.tsx:47-50`). A 403/404/429 would bubble up and unmount nothing; error toast is never shown for resign/hint failures (hint also unguarded at line 51-54).

6. **`SgfMove.coord` is `string | null` in `lib/sgf.ts`** but the SGF pass representation `B[]` is correctly round-tripped. No issue — test covers it.

7. **Dark mode applied consistently**: `darkMode: "class"` in `tailwind.config.ts`; `document.documentElement.classList.toggle("dark", ...)` in `lib/theme.ts`; `dark:` variants used throughout nav, inputs, table, Board (via `dark:bg-board-dark`). Verified.

8. **i18n key parity test exists** but is a tautology of ko/en files against each other. Add a test that asserts every *code* we know the backend emits has a key in `errors.*` (see Important #1).

## Verdict

**PASS with conditions.** Zero critical defects; build, type-check, lint, and unit tests all green. The spec's core requirements (App Router, TS strict, Tailwind dark mode, ko/en i18n, REST+WS, SVG board, local-storage persistence, no client secrets) are satisfied. However, six important issues should be addressed before claiming feature completeness — particularly the missing i18n error keys (#1), the `forbidden` casing mismatch (#2), the duplicate-send gating on `GameControls` (#3), and the resign-via-REST state update (#4). Hard-coded Korean in `ScorePanel` (#6) breaks the ko/en promise for that component.

**Critical count: 0**
**Important count: 6**
**Minor count: 8**
