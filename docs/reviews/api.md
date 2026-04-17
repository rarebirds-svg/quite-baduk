# API Review
**Reviewer:** API-Reviewer
**Date:** 2026-04-17

## Scope
- `backend/app/api/` (auth, games, analysis, stats, health, ws)
- `backend/app/services/` (game_service, user_service)
- `backend/app/schemas/` (auth, game, ws)
- `backend/app/deps.py`, `errors.py`, `rate_limit.py`, `security.py`, `engine_pool.py`
- `backend/tests/api/`

## Test Execution

Live execution of `pytest tests/api/ --cov=app.api --cov=app.services --cov-report=term-missing -v` was NOT possible in this review session (sandbox denied Bash execution of `pytest`/venv binaries). Coverage numbers therefore cannot be reported.

Static inspection of the test suite shows the following tests are present:

- `tests/api/test_auth.py` (6 tests): signup, duplicate email, login bad password, `/me` auth guard, signup -> me, logout clears cookie.
- `tests/api/test_games.py` (7 tests): create game, handicap game, list games, cross-user 403 on GET `/games/{id}`, resign, SGF download, hint.
- `tests/api/test_health_and_stats.py` (3 tests): health, stats auth guard, empty stats.

Total: ~16 API tests. Conftest (`backend/tests/conftest.py`) wires a fresh SQLite file DB, forces the mock KataGo adapter, clears state and rate-limiter buckets between tests — fixtures are well-isolated.

Action requested: please re-run the full suite and append the results block to this review. A reviewer needs to see an all-green run + ≥80% coverage on `app.api`/`app.services` before marking APPROVED.

## Findings

### Critical
None. The surface area is small, correct in broad strokes, and the most dangerous class of issues (IDOR on game-scoped endpoints) is guarded consistently.

### Important

**I-1. Rate limit on moves is not implemented (spec §9 violation).**
Spec requires `moves 30/min/user`. `rate_limiter` is used only for `signup` and `login` in `backend/app/api/auth.py:48` and `:67`. The WebSocket handler (`backend/app/api/ws.py`) processes `move`/`pass`/`undo` messages with no rate limiting per user. A malicious or buggy client can flood moves at engine/DB speed.
Recommendation: in `ws.py` before `place_move`/`undo_move`, call `rate_limiter.check(f"move:{user.id}", 30, 60)` and send `{type:"error", code:"RATE_LIMITED"}` on rejection instead of crashing the socket.

**I-2. Error envelope is inconsistent — validation errors only.**
`app/errors.py:11` wraps `HTTPException` as `{error:{code, message_key}}` but omits `detail`, and the validation handler at `:17` emits `detail`. Spec §10 describes `{error:{code,message_key,detail}}`. All `HTTPException(detail="game_not_found")` calls now lose any extra context. Game-service `GameError` has a `detail` string that is thrown away at `games.py:53, 118` (only `e.code` is propagated) and never reaches the client.
Recommendation: change `http_handler` to always emit `detail` (null when absent); change `games.py`/`analysis.py` to raise `HTTPException(status_code=..., detail={"code": e.code, "detail": e.detail})` (or similar) and teach the exception handler to render structured details. Today a client cannot distinguish `INVALID_HANDICAP` from `INVALID_COLOR` without the detail.

**I-3. WebSocket single-session policy has a race.**
`ws.py:74-83` looks up `_connections.get(game_id)`, closes the old socket, then stores the new one. Two sockets arriving nearly simultaneously can both read `None`, both `accept()`, and whichever writes second wins — but the first is never closed. Additionally `_connections` is a plain dict with no lock, and the WS never checks `user_id` match on the evicted session (fine since game_id already maps to one user, but worth a comment).
Recommendation: use `asyncio.Lock()` keyed per `game_id` around the replace-and-insert sequence, or a `dict.setdefault` + swap pattern.

**I-4. WS auth does not re-check game ownership inside the loop.**
`ws.py:69` checks `game.user_id != user.id` on connect, but the long-lived loop never refreshes the `game` ORM object or re-verifies. If `game.status` changes out-of-band (e.g., the owner deletes or resigns via REST in another tab), the WS keeps accepting `move` messages and `place_move`/`undo_move` will throw `GameError("GAME_NOT_ACTIVE")` — which is handled, so not catastrophic, but the game is stale-cached in memory. Low risk, but worth adding `await db.refresh(game)` before each action or re-selecting.

**I-5. Analysis endpoint `moveNum` semantics diverge from spec.**
`analysis.py:30-56` accepts `moveNum` but the comment at `:53` acknowledges it analyzes the current state instead. The cache is keyed by `(game_id, moveNum)` however (`:39`, `:68`), so the first call with `moveNum=5` caches a "current state" result under move 5, and a later call with `moveNum=10` (after a few moves) returns a stale cache for move 5 but the board has changed. This is an incorrect-cache bug, not just a TODO.
Recommendation: until per-move seek is implemented, (a) key the cache only by current `game.move_count`, or (b) reject `moveNum != game.move_count` with `400 NOT_IMPLEMENTED`, or (c) replay to the target move before analysis.

**I-6. SGF endpoint missing Content-Disposition.**
`games.py:122` returns `PlainTextResponse`, but spec §9 implies a downloadable SGF. Add `Content-Disposition: attachment; filename="game-{id}.sgf"` so browsers offer a save dialog instead of rendering text.

**I-7. Auth cookies have `secure=False` hardcoded.**
`auth.py:26, 30`. Acceptable for local dev, but there is no config toggle. When the app is deployed behind HTTPS, the cookies will still be set without `Secure`, allowing interception over a downgrade. Add a `settings.cookie_secure` (default `False` for dev, `True` in prod) and plumb it into `_set_auth_cookies`.

**I-8. Logout cookie-deletion must match the original `SameSite`/`path` or the browser may not remove it.**
`auth.py:79-82` calls `response.delete_cookie(name, path="/")` — good on `path`, but FastAPI's `delete_cookie` does not pass `samesite` by default. Most browsers still match by `(name, path, domain)` so this usually works, but the test `test_logout_clears_cookie` at `tests/api/test_auth.py:57` only asserts `Set-Cookie` is emitted — it does *not* prove `/me` fails after logout. The comment in that test even concedes the bug. Recommend: explicitly set `samesite="lax"` on delete, and strengthen the test by asserting `me.status_code == 401` (manually clear `client.cookies` beforehand if httpx auto-persists).

### Minor / Suggestions

**M-1. Stats endpoint response is untyped.**
`stats.py:13` returns `dict` — no Pydantic response model, so `/docs` shows a bare JSON object. Define `StatsResponse` in `schemas/game.py` (or a new `schemas/stats.py`) and add `response_model=StatsResponse`.

**M-2. `CreateGameRequest.handicap: int = Field(ge=0, le=9)` allows `1`.**
`game_service.create_game` then calls `apply_handicap` with `HANDICAP_COORDS` keys; if that dict excludes `1` (typical Korean 2..9), the request 400s with `INVALID_HANDICAP`. Schema-side `Literal[0,2,3,4,5,6,7,8,9]` would surface the constraint in OpenAPI.

**M-3. `_client_key` trusts `X-Forwarded-For` unconditionally.**
`auth.py:34-38` will let any caller claim an arbitrary IP to evade rate limiting by spoofing the header. Fine if deployed strictly behind a known reverse proxy, but document the assumption or gate on a `trust_forwarded_for` setting.

**M-4. `rate_limiter` is in-process only.**
`rate_limit.py`. In multi-worker deployments each worker has its own bucket; real limit becomes `5 * workers`. Spec is MVP-friendly, so acceptable, but note for scale-out.

**M-5. Logout is stateless — JWT still valid until `exp`.**
Acknowledged in prompt as "Fine for MVP but note." Adding a token-revocation (jti blacklist) later will tighten this.

**M-6. Access token max_age vs. JWT exp mismatch risk.**
`auth.py:18` hardcodes `ACCESS_COOKIE_MAX_AGE = 60 * 60 * 24` while the JWT TTL uses `settings.jwt_access_ttl_hours`. If someone changes the setting to 48, the cookie still expires at 24h. Compute from the setting: `max_age=settings.jwt_access_ttl_hours * 3600`.

**M-7. `games.py` imports `datetime` and `func` that are unused.**
`games.py:3` and `:7` — minor lint; remove.

**M-8. No WebSocket tests at all.**
`tests/api/` has no `test_ws.py`. The WS handler is the single biggest piece of novel logic in this layer (single-session eviction, move/pass/undo routing, GameError translation). At minimum add: (a) auth rejection with no cookie, (b) reject foreign game_id, (c) happy-path move, (d) single-session replacement sends `SESSION_REPLACED` to the old socket. FastAPI's `TestClient.websocket_connect` supports this; httpx does not, so a separate sync test module is needed.

**M-9. No raw SQL except `SELECT 1` in health (spec compliant).**
Grep for `text(` finds only `health.py:18`. SQL-injection surface is ORM-only — good.

**M-10. Authorization coverage is consistent.**
Every game-scoped endpoint routes through `_fetch_owned_game` (`games.py:32`) or `_fetch_owned` (`analysis.py:17`), both of which check `game.user_id != user.id` before returning. `list_games` filters by `user_id`. `stats` filters by `user_id`. `hint` calls `_fetch_owned_game`. `sgf` calls `_fetch_owned_game`. No IDOR gap found.

**M-11. `deps.get_current_user` catches bare `Exception`.**
`deps.py:31` — prefer catching `jwt.PyJWTError` plus `KeyError`/`ValueError` so unrelated bugs surface as 500s, not silent 401s.

**M-12. OpenAPI `/docs` rendering.**
All routers declare `tags` and `response_model` except `stats` and `health`. `analysis.py` uses tag `"analysis"` under `/api/games` prefix — OK. `ws.py` uses tag `"ws"` but WS routes do not appear in OpenAPI by design. Expect `/docs` to render cleanly; adding response models for stats/health is a cosmetic improvement (M-1).

## Summary of What Was Done Well
- Clean separation of routers, services, schemas, deps.
- ORM-only data access (no string-interpolated SQL in business paths).
- Bcrypt cost=12 configurable; JWT HS256; HttpOnly + SameSite=Lax cookies (spec §9).
- Consistent ownership checks on all game-scoped endpoints.
- Per-game `asyncio.Lock` (`engine_pool.game_lock`) serializes concurrent moves — race between REST `resign` and WS `move` cannot double-mutate.
- Centralized exception handler returns structured `error` envelope.
- WS single-session policy is implemented (even if racy, see I-3).
- Test fixtures properly isolate DB, adapter, engine cache, and rate-limit state.

## Verdict: CHANGES_REQUIRED

Blocking items: I-1 (move rate limit missing — hard spec requirement), I-5 (analysis cache is incorrect, not merely incomplete), I-2 (error envelope drops `detail` that the service layer is producing).

Should-fix before merge: I-3, I-4, I-6, I-7, I-8, M-8 (WS tests).

Once the blocking trio is fixed and the test suite is re-run and shown green with coverage ≥80% on `app.api`/`app.services`, this can be re-reviewed and upgraded to APPROVED_WITH_CONCERNS or APPROVED.
