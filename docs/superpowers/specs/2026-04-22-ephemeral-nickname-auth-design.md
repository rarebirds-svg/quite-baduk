# Ephemeral Nickname Auth — Design

**Date:** 2026-04-22
**Status:** Approved for planning
**Supersedes:** `2026-04-21-social-auth-design.md` (pivoted for privacy reasons — no signup, no PII, no cross-session persistence)
**Scope:** Replace all account/signup machinery with a single nickname-set step; keep all user activity strictly scoped to the current browser session; wipe everything on browser close or one-hour idle.

## 1. Problem & Goals

The service must not persist user identity across browser sessions. Any per-user data — nickname, game history, analysis cache — must disappear when the browser session ends. A brand-new visitor should enter play through one screen: "set your nickname and start."

**Success criteria**

- No signup, login, email, password, OAuth, or long-lived account tables.
- A session is a browser session. It's identified by an HttpOnly cookie with no `Expires`/`Max-Age`, so the cookie self-destructs on browser close.
- Server-side session rows are deleted on explicit end (`sendBeacon`) or after 1 hour of idle.
- When a session is deleted, all owned games / moves / analyses are CASCADE-deleted with it.
- Nicknames are unique **only among currently-connected sessions**. A disconnected nickname is immediately reusable (after purge).
- Concurrent nickname collisions are detected server-side and rejected.

**Non-goals (YAGNI)**

- Restoring a session from a different device or after browser close.
- Persistent user profiles, avatars, friend lists, or SGF archives.
- Nickname reservation beyond the active session.
- Multiple independent sessions per browser (tabs share the same cookie; same session).
- Redis-backed nickname registry for multi-process deployment (current single-uvicorn deployment assumed).
- Session-expiry pre-warning toasts or grace-period countdowns.

## 2. Key Design Decisions

| Decision | Choice |
|----------|--------|
| Data retention | Session-scoped DB rows; cascade-delete on session end |
| Nickname uniqueness | In-memory `NicknameRegistry` keyed on `casefold(NFKC(name))`, DB UNIQUE as secondary defense |
| Session transport | HttpOnly session cookie (no `Expires`), idle-TTL 1 hour + `beforeunload` beacon |
| Device-level settings | `localStorage` kept (theme, locale, preferred_rank, board bg) — functional, not PII |
| Superseded work | Prior social-auth spec + plan retained with `SUPERSEDED` notice |
| Table naming | New `sessions` table (not reused `users`); `games.session_id` FK |

## 3. Data Model

Migration `0005_ephemeral_sessions.py` recreates every user-owned table. Pre-launch, so all current rows are dropped.

### `sessions` (new)

```
id             INTEGER PK
token          VARCHAR(64)   UNIQUE NOT NULL   -- secrets.token_urlsafe(32)
nickname       VARCHAR(32)   NOT NULL          -- NFKC-normalized display form
nickname_key   VARCHAR(32)   UNIQUE NOT NULL   -- nickname.casefold() for uniqueness
created_at     DATETIME      NOT NULL DEFAULT now()
last_seen_at   DATETIME      NOT NULL DEFAULT now()
```

- No `email`, `password`, `country_code`, `locale`, `theme`, `avatar_url`. Device-level preferences live in `localStorage` only.
- `token` is the cookie value; compared with `hmac.compare_digest`-equivalent.

### `games` (recreated)

```
id           INTEGER PK
session_id   INTEGER NOT NULL   REFERENCES sessions(id) ON DELETE CASCADE
ai_rank      VARCHAR(8)   NOT NULL
ai_style     VARCHAR(16)  NOT NULL DEFAULT 'balanced'
ai_player    VARCHAR(32)  NULL
board_size   INTEGER  NOT NULL
handicap     INTEGER  NOT NULL DEFAULT 0
komi         FLOAT    NOT NULL DEFAULT 6.5
user_color   VARCHAR(8)   NOT NULL
status       VARCHAR(16)  NOT NULL DEFAULT 'active'
result       VARCHAR(16)  NULL
winner       VARCHAR(8)   NULL
move_count   INTEGER  NOT NULL DEFAULT 0
started_at   DATETIME NOT NULL DEFAULT now()
finished_at  DATETIME NULL
sgf_cache    TEXT     NULL
INDEX (session_id, status)
```

Other than the FK rename, identical columns to the current `games` schema.

### `moves`, `analyses` (recreated unchanged)

Each FKs to `games(id) ON DELETE CASCADE`. Session deletion cascades through `sessions → games → moves/analyses`.

## 4. Nickname Registry (in-memory)

```python
class NicknameRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_key: dict[str, int] = {}   # nickname_key -> session_id

    async def claim(self, nickname_key: str, session_id: int) -> bool:
        async with self._lock:
            if nickname_key in self._by_key:
                return False
            self._by_key[nickname_key] = session_id
            return True

    async def release(self, nickname_key: str) -> None:
        async with self._lock:
            self._by_key.pop(nickname_key, None)

    async def is_taken(self, nickname_key: str) -> bool:
        async with self._lock:
            return nickname_key in self._by_key
```

Module-level singleton `registry: NicknameRegistry` in `backend/app/session_registry.py`. The DB `UNIQUE(nickname_key)` constraint is the secondary defense against races the in-memory registry might miss (e.g., mid-purge). Both layers are kept.

### Validation + normalization

- Input `nickname` is trimmed, NFKC-normalized, length-checked (2..32 code points).
- Rejected categories: control chars, whitespace-only, emoji (`So`, `Sk`, combinations in `Extended_Pictographic`).
- `nickname_key = normalized.casefold()` — the registry/DB-unique key.
- Display form stored in `sessions.nickname` is the NFKC-normalized original casing.

Rule module: `backend/app/core/nickname.py` with `normalize()`, `validate()`, `is_emoji()` helpers + unit tests.

## 5. Session Lifecycle

### Create

```
POST /api/session
body: { "nickname": "홍길동" }

1. Validate + normalize. Reject -> 422 "invalid_nickname".
2. registry.claim(key, pending=-1). Reject -> 409 "nickname_taken".
3. INSERT sessions(token, nickname, nickname_key). DB UNIQUE miss -> 409 (and release the registry claim).
4. registry swaps pending entry to the real session_id.
5. Set-Cookie baduk_session=<token> (HttpOnly, SameSite=Lax, Secure=prod, Path=/, no Expires).
6. Response 201 { id, nickname }.
```

### Access

`baduk_session` cookie → `get_current_session` dependency → looks up, updates `last_seen_at`, returns `Session`. Missing or unknown cookie → 401 `no_session` / `invalid_session`.

### End

```
POST /api/session/end  (authenticated via cookie, also used by sendBeacon)
  - DELETE sessions WHERE id = current  (CASCADE games/moves/analyses)
  - registry.release(key)
  - Set-Cookie: baduk_session=""; Max-Age=0
  - 204 No Content
```

`sendBeacon` does not wait for a response; the browser fires-and-forgets. Server behavior is identical whether beacon-triggered or explicit.

### Idle purge

`backend/app/session_purge.py` runs on app startup:

```python
async def purge_expired_sessions_once(ttl_sec: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl_sec)
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Session).where(Session.last_seen_at < cutoff)
        )
        expired = res.scalars().all()
        for s in expired:
            await db.delete(s)
            await registry.release(s.nickname_key)
        await db.commit()
        return len(expired)


async def _run_purge_loop(interval_sec: int, ttl_sec: int) -> None:
    while True:
        await asyncio.sleep(interval_sec)
        try:
            await purge_expired_sessions_once(ttl_sec)
        except Exception:
            structlog.get_logger().exception("session_purge_failed")
```

`app/main.py` lifespan `asyncio.create_task(_run_purge_loop(60, 3600))`, cancelled on shutdown.

**TTL: 3600 seconds (1 hour)**. Purge interval: 60 seconds. Both from `settings`.

### Reconnect + reload

- **F5 / reload**: session cookie persists → same session id → state preserved.
- **Tab close / browser close**: session cookie destroyed. Next visit starts fresh at `/`. Server side row lingers ≤ 1 hour until idle purge or until the new browser session explicitly ends an orphan via `beforeunload`.
- **Same nickname, new tab while old still active**: new POST `/api/session` → 409 taken (correct; uniqueness among concurrent sessions).
- **Same nickname shortly after browser close, before purge**: 409 taken. User must pick another or wait up to TTL. Error message makes this explicit.

## 6. API Surface

```
POST   /api/session                       create (unauthenticated)
GET    /api/session                       read current (authenticated)
POST   /api/session/end                   end (authenticated; beacon-safe)
GET    /api/session/nickname/check?name=… live availability (unauthenticated)
```

`/api/auth/*` namespace is **removed entirely**: `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` all deleted.

All other authenticated endpoints (`/api/games`, `/api/games/{id}/hint`, `/api/analysis`, WS `/api/ws/games/{id}`) switch `Depends(get_current_user)` → `Depends(get_current_session)` and use `session.id` in place of `user.id`.

### Schemas

**`POST /api/session`** request: `{ nickname: str }`. Response 201: `{ id, nickname }`. 409 `nickname_taken`. 422 `invalid_nickname`. 429 `rate_limited`.

**`GET /api/session`** response: `{ id, nickname }`. 401 `no_session` | `invalid_session`.

**`POST /api/session/end`** response: 204. Sets the clearing cookie.

**`GET /api/session/nickname/check?name=…`** response 200: `{ available: true }` or `{ available: false, reason: "taken" | "invalid" }`. 429 `rate_limited`.

### Rate limits

- `POST /api/session`: 5 / min / IP.
- `GET /api/session/nickname/check`: 30 / min / IP (debounced typing-level feedback).

### Error codes (i18n keys under `errors.`)

```
no_session         -> "먼저 닉네임을 설정해주세요"
invalid_session    -> "세션이 만료되었습니다"
nickname_taken     -> "이미 사용 중인 닉네임입니다"
invalid_nickname   -> "2–32자의 문자만 사용할 수 있습니다"
rate_limited       -> "요청이 너무 많습니다. 잠시 후 다시 시도해주세요"
```

## 7. WebSocket Integration

`backend/app/api/ws.py`:

- `_authenticate_ws` takes `baduk_session` cookie, looks up `Session`.
- Reject (1008) if missing or unknown.
- Validate `game.session_id == sess.id`; reject (1008) otherwise.
- Inside the loop, a 60-second heartbeat task updates `sess.last_seen_at` so long-lived WS connections don't get idle-purged.
- If the session row is deleted mid-stream (another tab ended the session), subsequent `place_move` / `undo_move` calls will see the game gone (cascade) and the service layer returns `game_not_found`; the WS then closes gracefully.
- Existing single-connection-per-game policy (`SESSION_REPLACED`) is preserved.

Message types, payloads, and client-side WS reconnection behavior (1.5-second retry) are unchanged. Only the auth adapter swaps.

## 8. Client-side Storage Policy

- **`localStorage`** — kept for device-level preferences only: `preferred_rank`, `theme` (next-themes), `locale`, `board_bg`. No nickname, no PII, no token.
- **`sessionStorage`** — not used (nothing needs to persist across reloads yet survive closes).
- **Cookies** — exactly one: `baduk_session`. HttpOnly, so JS cannot read it.
- **No nickname caching.** Every fresh browser session lands on `/` and retypes the nickname. This is deliberate and matches user instruction.

`/settings` page gets a "Reset device settings" button that clears the `localStorage` keys listed above.

## 9. Frontend

### `/` — Nickname Setup (the only public route)

```
┌─────────────────────────────────────┐
│  AI 바둑                              │  BrandMark
│  닉네임을 정해주세요                  │  Heading
│  ────────────                         │  RuleDivider
│  [ 홍길동 ___________ ]  [시작하기]   │  Input + submit
│  2–32자, 이모지 금지                   │  Helper text
│  사용 가능                             │  Live availability
│                                       │
│  브라우저를 닫으면 모든 기록이         │
│  자동으로 삭제됩니다.                  │  Privacy note
└─────────────────────────────────────┘
```

- Debounced 400 ms `GET /api/session/nickname/check` while typing. Result rendered in a text span with `aria-live="polite"` — no emoji indicator.
- Submit → `POST /api/session`. 201 → `router.replace("/game/new")`. 409/422 → inline field error with the matching i18n string.
- If `GET /api/session` already returns 200 on mount (cookie still valid), the component bypasses the form and immediately redirects to `/game/new`.

### `AuthGate` (existing component, rewritten)

Public route list: `["/"]`. For anything else:

- `GET /api/session` → 200 → render children.
- 401 → `router.replace("/")`.

### `SessionBeacon` (new)

Global `beforeunload` handler that calls `navigator.sendBeacon("/api/session/end")`. Mounted in `web/app/layout.tsx` alongside `AuthGate`.

### Pages to delete

- `web/app/login/page.tsx` — removed.
- `web/app/signup/page.tsx` — removed.
- Navigation entries pointing at them — removed.
- The prior-spec `/onboarding` route — not created.

### Pages to update

- `web/components/TopNav.tsx` — signup/login links out; current nickname + "세션 종료" button in.
- `web/app/history/page.tsx` — heading changed to "세션 대국", added ephemeral-note text.
- `web/app/settings/page.tsx` — remove any server-writing controls; add "이 장치의 설정 초기화" and "세션 종료" rows.

### i18n (`ko.json`, `en.json`)

**Remove**: `auth.email`, `auth.password`, `auth.displayName`, `auth.signup`, `auth.mustBeLongerPassword`, `nav.signup`, `nav.login`, `home.guestSignup`, `errors.invalid_credentials`, `errors.email_already_registered`, `errors.not_authenticated` (replaced).

**Add** (ko shown; mirror in en):

```json
"session": {
  "nicknameHeading": "닉네임을 정해주세요",
  "nicknamePlaceholder": "2–32자, 이모지 금지",
  "nicknameSubmit": "시작하기",
  "nicknameAvailable": "사용 가능",
  "nicknameTaken": "이미 사용 중인 닉네임입니다",
  "nicknameInvalid": "2–32자의 문자만 사용할 수 있습니다",
  "privacyNote": "브라우저를 닫으면 모든 기록이 자동으로 삭제됩니다.",
  "ephemeralNote": "이 목록은 현재 세션의 대국만 표시합니다. 브라우저를 닫으면 함께 삭제됩니다.",
  "endSession": "세션 종료",
  "expiredTitle": "세션이 만료되었습니다",
  "expiredDesc": "닉네임을 다시 설정해주세요"
},
"errors": {
  "no_session": "먼저 닉네임을 설정해주세요",
  "invalid_session": "세션이 만료되었습니다",
  "nickname_taken": "이미 사용 중인 닉네임입니다",
  "invalid_nickname": "2–32자의 문자만 사용할 수 있습니다",
  "rate_limited": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요"
}
```

## 10. Security Checklist

- Session cookie: HttpOnly, SameSite=Lax, Secure-in-prod, no Expires.
- Token: 256-bit entropy (`secrets.token_urlsafe(32)`).
- Nickname input: server-side NFKC + length + category validation.
- No nickname plaintext in structured logs; log only `session_id` and `len(nickname)`.
- Rate limits on both session create and nickname availability check.
- `POST /api/session/end` verifies cookie — no arbitrary session termination by other users.
- All DB deletions go through `session_id` FK with `ON DELETE CASCADE` — no orphan rows.
- `NicknameRegistry.claim` and DB `UNIQUE(nickname_key)` together close the race window.
- Bandit / ruff `S1xx` suites remain green.

## 11. Testing

### Unit

- `backend/tests/test_nickname.py` — NFKC, trim, length, emoji category rejection, whitespace-only rejection, casefold behavior, edge cases (single grapheme that expands under NFKC, mixed-script).
- `backend/tests/test_nickname_registry.py` — `claim`/`release`/`is_taken`, concurrency via `asyncio.gather`.

### Integration

- `backend/tests/api/test_session.py` — all four endpoints, happy + rejection paths, cookie semantics (no `Max-Age`, cleared on end).
- `backend/tests/api/test_ws.py` — WS auth, game ownership, graceful close when session deleted mid-stream.
- `backend/tests/api/test_games.py` — existing game tests retrofitted to use session cookie helper.
- `backend/tests/test_session_purge.py` — `purge_expired_sessions_once` single-shot call + cascade assertions.

### Frontend

- `web/tests/nickname-gate.test.tsx` — debounce, live availability, submit success + error paths.
- `web/tests/auth-gate.test.tsx` (updated) — 200/401 branches.
- `web/tests/session-beacon.test.tsx` — sendBeacon invocation on `beforeunload`.

### E2E

- `e2e/tests/session.spec.ts` — first visit → nickname → game → reload keeps session → end session → `/`.
- Two-browser scenario is flagged as manual QA (playwright can simulate with two contexts but adds complexity; deferred for v1).

## 12. Migration + Rollout

- Delete `backend/data/baduk.db` before running `alembic upgrade head`. Pre-launch, so data loss is acceptable.
- Remove `bcrypt` from `backend/pyproject.toml` dependencies (carried over from the prior password-auth era).
- `authlib` is not added (prior spec added it; current spec doesn't need it and it won't be introduced).
- Config additions in `.env.example`:
  ```
  SESSION_IDLE_TTL_SEC=3600
  SESSION_PURGE_INTERVAL_SEC=60
  NICKNAME_MIN_LEN=2
  NICKNAME_MAX_LEN=32
  COOKIE_SECURE=false
  ```

## 13. Agent-based Quality Review (post-implementation, mandatory)

Parallel dispatch; PR description summarizes verdicts and remediation commits.

| Agent | Surface | Pass criterion |
|-------|---------|----------------|
| `design-token-guardian` | `/`, `/history`, `/settings`, `SessionBeacon`, `TopNav` updates — hex/emoji/framer-motion/inline font | Zero violations |
| `visual-qa` | Light + dark screenshots of the three affected screens, Editorial spec conformance | No regressions |
| `korean-copy-qa` | `session.*` and `errors.no_session|invalid_session|nickname_*` — naturalness, term consistency ("닉네임" vs "별명"), privacy note tone | Suggestions applied |
| `a11y-auditor` | Nickname input `aria-describedby`, live region feedback, focus ring on "세션 종료", dialog focus trap on any confirmations | No critical issues |
| `superpowers:code-reviewer` | `sessions` table + CASCADE, purge task, `NicknameRegistry` concurrency, WS auth swap, security checklist | Approved |

## 14. Superseded Prior Work

Both prior documents get a `SUPERSEDED 2026-04-22` banner at the top; their content is preserved for historical reference (design decisions still illuminate trade-offs).

- `docs/superpowers/specs/2026-04-21-social-auth-design.md`
- `docs/superpowers/plans/2026-04-21-social-auth.md`

## 15. Glossary

- **Session** — a row in `sessions`; one-to-one with a browser session holding the `baduk_session` cookie.
- **Nickname key** — `casefold(NFKC(trim(nickname)))`; the canonical form used for uniqueness checks.
- **Idle purge** — background task that deletes sessions older than `SESSION_IDLE_TTL_SEC` since their last request/WS activity.
- **Beacon end** — client-fired `navigator.sendBeacon("/api/session/end")` on `beforeunload`, best-effort immediate cleanup.
