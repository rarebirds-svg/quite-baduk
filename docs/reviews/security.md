# Security Review
**Reviewer:** Security-Reviewer
**Date:** 2026-04-17
**Target:** AI 바둑 web application (backend + web + e2e)

## Tooling Results

Automated tooling (`bandit`, `pip-audit`, `npm audit`) could not be executed in
this sandboxed review session: every `Bash` invocation, including
`bandit --version`, was blocked by the sandbox permission layer. The results
below are therefore from a thorough manual audit of the relevant code paths.
The tools are declared in `backend/pyproject.toml` (bandit, pip-audit), and
should be re-run in CI as follows:

```bash
cd backend && source .venv311/bin/activate
bandit -r app -ll -f txt
pip-audit --strict
cd ../web && npm audit --omit=dev --audit-level=high
cd ../e2e && npm audit --audit-level=high
```

- bandit: not executed (sandbox)
- pip-audit: not executed (sandbox)
- npm audit (web): not executed (sandbox)
- npm audit (e2e): not executed (sandbox)

Observation from the dependency lists:
- `backend/pyproject.toml` is mostly well-known libraries (`fastapi>=0.110`,
  `pydantic>=2.6`, `sqlalchemy>=2.0`, `bcrypt>=4.1`, `pyjwt>=2.8`,
  `aiosqlite>=0.19`, `httpx>=0.27`, `websockets>=12.0`, `greenlet>=3.0`). All
  are recent enough to be past known advisories as of 2026-04-17, but this
  needs `pip-audit` confirmation.
- `web/package.json`: `next 14.2.5`, `react 18.3.1`, `react-dom 18.3.1`,
  `zustand 4.5.2`. `next 14.2.5` (released 2024-07) has several security
  advisories patched in subsequent 14.2.x releases (e.g. CVE-2024-51479 path
  confusion; CVE-2025-29927 middleware authorization bypass). This MUST be
  confirmed and bumped — see Finding H1.
- `e2e/package.json`: only `@playwright/test` and `typescript`. Low blast
  radius (dev-only tooling).

---

## Findings

### Critical
None.

### High

**H1 — Next.js 14.2.5 likely vulnerable (middleware auth-bypass / path confusion).**
`web/package.json` pins `next: 14.2.5`. Multiple public advisories against the
14.2.x line (including the middleware-authorization-bypass CVE-2025-29927)
were addressed in later patch releases. This application does not use
middleware for authorization today, but Next.js is still in the request path
(rewrites to the backend in `web/next.config.js`), so any path-confusion /
cache-poisoning issue in the framework is directly reachable. `npm audit
--omit=dev --audit-level=high` should be run; the expected remediation is a
bump to the latest 14.2.x (or 14.x) patch release.

**H2 — Production cookies hard-coded to `secure=False`.**
`backend/app/api/auth.py:24-31` sets both `access_token` and `refresh_token`
cookies with `secure=False` unconditionally. In production this means the
session cookie can be transmitted over plain HTTP (if HTTPS is ever
terminated improperly or a user visits via http://), enabling session
hijacking. Mitigation: read `secure` from configuration (e.g.
`settings.cookie_secure`, defaulting `True` in prod) and set it in
`_set_auth_cookies`. Also recommend `domain` pinning and consider
`samesite="strict"` for the refresh cookie.

### Medium

**M1 — X-Forwarded-For trusted without a verified proxy (rate-limit bypass).**
`backend/app/api/auth.py:34-38` (`_client_key`) reads the first value of the
`X-Forwarded-For` header with no check that the request actually came through
a trusted proxy. Any attacker can submit arbitrary/rotating XFF values to
trivially bypass the 5/min login and signup rate-limits (`auth.py:48, 67`),
turning these endpoints into credential-stuffing vectors. Mitigation: either
(a) only honor XFF when `settings.trust_proxy=True` and the actual client
comes from a known reverse-proxy subnet, or (b) always key on
`request.client.host` and document the deployment assumption.

**M2 — No rate limiting outside `/auth/signup` and `/auth/login`.**
All other endpoints (`POST /api/games`, `POST /api/games/{id}/hint`,
`POST /api/games/{id}/analyze`, WebSocket moves/undo) are authenticated but
not rate-limited. A single authenticated user can spam `/analyze` (each call
runs `adapter.analyze(max_visits=100)` which is expensive), or open many
concurrent WS sessions per game (the "single session policy" in `ws.py:74`
is per game, not per user), producing a DoS against KataGo. Recommend a
per-user-plus-endpoint bucket for `analyze` and `hint`, and a global concurrency
cap in `engine_pool.py`.

**M3 — User-enumeration / timing oracle on `/auth/login`.**
`backend/app/services/user_service.py:29-33`: when the e-mail is unknown, the
function returns immediately without running bcrypt; when the e-mail is
known, it runs bcrypt (~hundreds of ms at cost=12). The timing delta reveals
whether an address is registered, and also amplifies the value of the M1 rate-
limit bypass. Fix: always run a dummy `bcrypt.checkpw` against a constant hash
if the user is absent.

**M4 — In-memory rate-limiter is not safe against horizontal scaling.**
`backend/app/rate_limit.py` keeps buckets in process memory. The moment the
backend is run with >1 worker (uvicorn `--workers N`, or multiple replicas
behind a load balancer), a client simply gets N×5 attempts per minute. The
single-instance SQLite deployment documented in `docker-compose.yml` keeps
this at "medium" for now, but this assumption must be made explicit or moved
to a shared store (e.g. Redis) before scale-out.

**M5 — WebSocket has no idle timeout, no per-connection message quota, and
no auth re-check on token expiry.**
`backend/app/api/ws.py` authenticates once at `accept()` time (line 62-65)
and then loops forever on `receive_json()`. Consequences:
  - If the access token expires mid-session, the socket stays open
    indefinitely with the now-invalid identity (the server happily executes
    moves for an expired session).
  - No idle/read timeout means a connected but silent client consumes server
    resources (one WS + one row in `_connections`) until the TCP peer dies.
  - `receive_json()` has no size limit (websockets default is ~1 MiB, but that
    is still large for single-move payloads).
Mitigation: decode token TTL, schedule a task to close the connection at
`exp`, cap `receive_json` with `asyncio.wait_for(..., idle_timeout)` and
reject oversized frames.

**M6 — Missing security response headers (CSP, HSTS, X-Frame-Options,
X-Content-Type-Options, Referrer-Policy).**
Neither the FastAPI backend nor the Next.js config adds any of these headers.
For an authenticated app served from Next.js, at minimum `Strict-Transport-
Security`, `X-Content-Type-Options: nosniff`, and a clickjacking header are
expected. CSP is optional for an internal tool but advisable for a public
deployment. Add a `custom_headers` middleware in FastAPI and/or `headers()`
in `next.config.js`.

### Low

**L1 — `page` query parameter in `GET /api/games` is not validated.**
`backend/app/api/games.py:59-67` accepts `page: int = 1` from the query
string, then computes `offset((page - 1) * 50)`. A negative `page` produces
a negative offset, which SQLAlchemy will pass to SQLite as a large 2's-
complement unsigned value; SQLite tolerates this, but user-controllable
negative offsets are a code smell and can waste query plans on future
backends. Validate with `Field(ge=1)` (Pydantic `Query(..., ge=1)`).

**L2 — `moveNum` query parameter in `POST /api/games/{id}/analyze` is
unbounded and untrusted.**
`backend/app/api/analysis.py:30-39` takes `moveNum: int` from the query
string and uses it only as a cache key. A user can spam arbitrary moveNums
to flood `analysis_cache` with junk rows keyed by a single game. Validate
`moveNum` against the game's actual `move_count` before caching.

**L3 — `games.user_id` has no FK constraint at the DB level.**
`backend/app/models/game.py:13` declares `user_id` as an index but not a
`ForeignKey("users.id")`. Likewise `move.game_id`, `analysis_cache.game_id`.
Application code enforces ownership, but a single wrong migration could
leave orphaned games that are still reachable by whoever happens to have
matching IDs. Add FKs (with `ondelete="CASCADE"`). `PRAGMA foreign_keys=ON`
is already enabled in `db.py:22`.

**L4 — `cors_origins.split(",")` does not strip whitespace.**
`backend/app/main.py:32`. A configuration of `"a.com, b.com"` will register
`" b.com"` as an origin and silently fail to match actual Origin headers.
Trivial to fix with `[o.strip() for o in settings.cors_origins.split(",") if o.strip()]`.

**L5 — `display_name` accepts arbitrary Unicode including control chars.**
`backend/app/schemas/auth.py:6` only bounds length (1..64). Bidi override
characters (U+202E), zero-width joiners, or control chars can be stored and
later rendered in the UI. React auto-escapes HTML but not Unicode presentation
tricks. Recommend a `\p{C}`-stripping validator.

**L6 — JWT secret default is `"dev-secret-change-me"`.**
`backend/app/config.py:8`. `docker-compose.yml:17` passes `JWT_SECRET` from
env with a fallback of `"changeme-in-production"`. Add an explicit startup
assertion that `jwt_secret` is not one of the known defaults when running in
production mode, so a misconfigured deploy fails loudly instead of shipping
with a predictable key.

### Observations (not actionable issues, just confirmations)

- **JWT algorithm pinning is correct.** `backend/app/security.py:32, 43, 47`
  encodes and decodes with `algorithms=["HS256"]` only. No `none` fallback,
  no `algorithm` reflection from the token header. PyJWT is immune to the
  classic "alg=none" bug when `algorithms` is a closed list.
- **Password hashing is bcrypt cost 12.** `security.py:14`, configurable via
  `settings.bcrypt_cost`. Acceptable for 2026 on general-purpose hardware.
  `verify_password` (lines 17-21) catches the expected exceptions from
  malformed hashes, so a corrupted row returns `False` instead of 500.
- **Token-type claim is enforced.** Both `deps.get_current_user` (`deps.py:28`)
  and `_authenticate_ws` (`ws.py:46`) explicitly check `payload.get("type") ==
  "access"` before accepting the token. Refresh tokens cannot be used as
  access tokens.
- **Cookies are `HttpOnly=True, SameSite="lax"`.** `auth.py:25-31`. Lax +
  JSON-bodied POSTs is a valid CSRF defence for this stack: the browser will
  not attach the cookie to cross-site top-level POSTs with `Content-Type:
  application/json` (and pre-flight will fail anyway because `allow_origins`
  is an explicit list, not `*`). No separate CSRF token needed here.
- **Ownership is enforced on every game-scoped endpoint.**
  `games.py:_fetch_owned_game` (line 32), `analysis.py:_fetch_owned` (line
  17), and `ws.py` (line 69) all reject `game.user_id != user.id` with 403
  / 1008. The SGF download, hint, analyze, delete, resign, get-detail, and
  WS channels are all gated.
- **No raw SQL anywhere in the application surface.** `health.py:19` uses
  `text("SELECT 1")` with no interpolation; every other query is built via
  SQLAlchemy Core `select(...).where(...)` with bound parameters. No SQL
  injection reachable.
- **No `dangerouslySetInnerHTML`, `eval`, `Function`, or `document.write`
  anywhere in `web/`.** (`grep` across `web/**/*.{ts,tsx,js,jsx}`.) React's
  default escaping is intact. `localStorage` is used only for non-sensitive
  UI preferences (`locale`, `theme`, `preferred_rank`); no tokens are ever
  stored there.
- **KataGo subprocess uses `create_subprocess_exec(*args, ...)` (not
  `shell=True`)**; `core/katago/adapter.py:109`. User-controlled `coord`
  values reach `adapter.play(color, coord)`, but only after
  `engine.play(...)` has validated them through `gtp_to_xy`, which restricts
  input to `[A-HJ-T][1-19]` or `"pass"`. No GTP command injection reachable.
- **Structured logging (structlog JSON)** is configured in `main.py:12-19`;
  no `print(...)`, and no grep hits for logging calls that include tokens,
  passwords, or the JWT secret.

---

## Recommendations

Prioritized in execution order:

1. **H1:** Run `npm audit --omit=dev` under `web/` and bump `next` to the
   latest 14.2.x/14.x patch release covering CVE-2024-51479 and
   CVE-2025-29927. Re-run audit until clean at `--audit-level=high`.
2. **H2:** Add `cookie_secure: bool` to `Settings` (default `True`; override
   to `False` in the dev compose file) and thread it through
   `_set_auth_cookies`.
3. **M1 + M3:** Harden `/auth/login`. Add (a) optional trusted-proxy check
   before honoring `X-Forwarded-For`, (b) constant-time dummy bcrypt on
   missing users, (c) keep the 5/min rate limit but also add a slower
   per-account limit (e.g. 10/hr) keyed by email to blunt slow enumeration.
4. **M2 + M5:** Add a lightweight per-user rate-limit decorator and apply it
   to `analyze`, `hint`, and the WS move loop. For the WS: compute token
   `exp`, schedule `websocket.close(code=1008)` at that time, and wrap
   `receive_json` in `asyncio.wait_for(..., idle_timeout)`.
5. **M4:** Either document "single-worker / single-replica only" as a
   supported deployment invariant, or move `RateLimiter` to a shared backend
   before turning on multi-worker uvicorn.
6. **M6:** Add a middleware that sets `Strict-Transport-Security`,
   `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or a `frame-
   ancestors` CSP), and `Referrer-Policy: same-origin` on every response.
7. **L1, L2, L5:** Tighten Pydantic validators (`Query(..., ge=1)` for page;
   validate `moveNum` against `game.move_count`; strip/ reject
   `\p{C}` in `display_name`).
8. **L3:** In the next migration, add FK constraints to `games.user_id`,
   `moves.game_id`, and `analysis_cache.game_id` with `ON DELETE CASCADE`.
9. **L4, L6:** 1-line fix to strip CORS origins; add a startup check that
   rejects the known default `jwt_secret` values when `ENV=production`.
10. **Tooling:** wire `bandit -r app -ll` and `pip-audit --strict` into CI
    (backend), and `npm audit --omit=dev --audit-level=high` into CI for
    both `web/` and `e2e/`. These were blocked from running in this review
    session and need to be confirmed green outside the sandbox.

---

## Verdict

**APPROVED_WITH_CONCERNS**

- Status: review complete, tooling pending external CI run.
- Critical findings: 0
- High findings: 2 (H1 Next.js version; H2 cookie `secure=False`)
- Medium findings: 6 (M1–M6)
- Low findings: 6 (L1–L6)

The core security primitives (JWT HS256 pinning, bcrypt hashing, token-type
enforcement, HttpOnly + SameSite=Lax cookies, explicit CORS origin list,
ownership checks on every game-scoped endpoint, ORM-only SQL, React
auto-escape, `create_subprocess_exec` without shell) are sound. No critical
or immediately exploitable issue was found.

The two High items are straightforward fixes (dependency bump + config
plumbing). The cluster of Medium items all stem from two root causes —
"trusted proxy is assumed without verification" and "rate-limit only covers
credentials" — and can be closed with a small amount of middleware work.
Resolve H1/H2 and the M-tier items before a public production deploy.
