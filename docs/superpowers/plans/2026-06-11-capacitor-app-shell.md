# Capacitor 앱 셸 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** inkbaduk 웹앱을 Capacitor 정적 export 번들로 감싸 Google Play(우선)·App Store(후속)에 배포 가능한 Android 앱 셸을 만든다.

**Architecture:** 백엔드에 Bearer 토큰 인증을 쿠키와 병행 추가(Phase 0) → 프론트를 `BUILD_TARGET=app`으로 정적 export 가능하게 분기하고 동적 세그먼트를 쿼리 라우트로 이중화(Phase 1) → `web/` 안에 Capacitor Android 프로젝트를 추가하고 네이티브 브리지를 연결(Phase 2). 웹 prod(standalone + rewrite) 경로는 불변.

**Tech Stack:** FastAPI + SQLAlchemy(기존), Next.js 14 App Router(기존), Capacitor 6 (@capacitor/core·android·app·haptics·preferences·splash-screen·status-bar).

**스펙:** `docs/superpowers/specs/2026-06-11-capacitor-app-shell-design.md`

**스펙 보정 2건** (구현 조사 결과 반영, 스펙 파일에도 동일 수정 커밋):
1. Capacitor 프로젝트 루트는 `mobile/` 형제 디렉토리가 아니라 **`web/` 내부** (`web/capacitor.config.ts`, `web/android/`). Capacitor는 자기 루트의 `package.json`에서 플러그인을 감지하므로 분리하면 플러그인 등록이 깨진다.
2. 오프라인 감지는 `@capacitor/network` 플러그인 대신 **브라우저 `online`/`offline` 이벤트** 사용 (WebView에서 동일하게 동작, 플러그인 1개 절감).

**실행 규칙**
- 각 Task는 독립 커밋. 백엔드 Task 후에는 `backend/`에서 `pytest`·`ruff check .`·`mypy app`, 프론트 Task 후에는 `web/`에서 `npm run type-check`·`npm run lint` 실행이 기본 검증.
- 백엔드 명령은 전부 `backend/`에서 `source .venv311/bin/activate` 후 실행.
- 신규 파일은 CLAUDE.md 규칙 6에 따라 첫 줄(디렉티브 직후)에 한국어 역할 주석 필수.

---

## Phase 0 — 백엔드 토큰 인증 (웹 무해, 독립 배포 가능)

### Task 1: 세션 생성 응답에 토큰 포함

**Files:**
- Modify: `backend/app/schemas/session.py`
- Modify: `backend/app/api/session.py:110` (create_session 반환)
- Test: `backend/tests/api/test_session.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `backend/tests/api/test_session.py` 끝에 추가

```python
@pytest.mark.asyncio
async def test_create_session_returns_token_in_body(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "tokuser"})
    assert r.status_code == 201
    body = r.json()
    assert isinstance(body.get("token"), str)
    assert len(body["token"]) >= 32
    # GET /api/session은 토큰을 재노출하지 않는다 (생성 시 1회만).
    r2 = await client.get("/api/session")
    assert r2.status_code == 200
    assert r2.json().get("token") is None
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/api/test_session.py::test_create_session_returns_token_in_body -v`
Expected: FAIL (`body.get("token")`이 None — KeyError 아님, assert 실패)

- [ ] **Step 3: 구현** — `backend/app/schemas/session.py`의 `SessionPublic`에 필드 추가

```python
class SessionPublic(BaseModel):
    id: int
    nickname: str
    # 앱 셸(Capacitor)용 Bearer 토큰. 세션 생성 응답에만 채워진다.
    token: str | None = None
```

`backend/app/api/session.py` `create_session`의 반환(현재 110행)을 수정.

```python
        return SessionPublic(id=sess.id, nickname=sess.nickname, token=token)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/api/test_session.py -v`
Expected: 전부 PASS (기존 테스트 회귀 포함)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/schemas/session.py backend/app/api/session.py backend/tests/api/test_session.py
git commit -m "feat(api): 세션 생성 응답에 Bearer 토큰 포함 (앱 셸용)"
```

### Task 2: REST Bearer 헤더 인증 (쿠키 폴백 유지)

**Files:**
- Modify: `backend/app/deps.py:28-51` (get_current_session)
- Modify: `backend/app/api/session.py:124-159` (end_session)
- Test: `backend/tests/api/test_session.py`

- [ ] **Step 1: 실패하는 테스트 작성** — `backend/tests/api/test_session.py`에 추가

```python
@pytest.mark.asyncio
async def test_bearer_header_authenticates_without_cookie(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "appuser"})
    token = r.json()["token"]
    client.cookies.clear()
    r2 = await client.get("/api/session", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["nickname"] == "appuser"


@pytest.mark.asyncio
async def test_bad_bearer_token_is_401(client: AsyncClient) -> None:
    client.cookies.clear()
    r = await client.get("/api/session", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_end_session_via_bearer_header(client: AsyncClient) -> None:
    r = await client.post("/api/session", json={"nickname": "enduser"})
    token = r.json()["token"]
    client.cookies.clear()
    r2 = await client.post(
        "/api/session/end", headers={"Authorization": f"Bearer {token}"}
    )
    assert r2.status_code == 204
    r3 = await client.get("/api/session", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 401
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/api/test_session.py -v -k bearer`
Expected: 3개 모두 FAIL (헤더 미지원 — 401 또는 nickname 불일치)

- [ ] **Step 3: 구현** — `backend/app/deps.py`

import에 `Header` 추가.

```python
from fastapi import Cookie, Depends, Header, HTTPException, status
```

`COOKIE_SESSION` 정의 아래 헬퍼 추가, `get_current_session` 수정.

```python
def bearer_token(authorization: str | None) -> str | None:
    """Authorization 헤더에서 Bearer 토큰을 추출한다. 형식이 다르면 None."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip() or None
    return None


async def get_current_session(
    db: DbSession,
    baduk_session: Annotated[str | None, Cookie()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Session:
    """Resolve the current session from the cookie (web) or the
    ``Authorization: Bearer`` header (Capacitor app shell), bumping
    ``last_seen_at``. Cookie wins when both are present.

    Raises 401 if neither credential resolves to a live session row.
    """
    token = baduk_session or bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="no_session"
        )
    result = await db.execute(select(Session).where(Session.token == token))
    sess = result.scalar_one_or_none()
    if sess is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session"
        )
    # last_seen_at은 디바운스 캐시(app.last_seen_cache)에 메모리 stamp만 한다.
    # 60s 단위로 백그라운드 flusher가 DB UPDATE. SELECT 직후 다른 코루틴이
    # 세션을 삭제하는 race는 다음 요청의 SELECT가 401로 처리한다.
    last_seen_cache.stamp(sess.id)
    return sess
```

`backend/app/api/session.py` `end_session` — 시그니처에 헤더 폴백 추가 (import에 `Header` 추가, `from app.deps import bearer_token` 추가).

```python
@router.post("/end", status_code=204)
async def end_session(
    response: Response,
    db: DbSession,
    baduk_session: Annotated[str | None, Cookie(alias=COOKIE_SESSION)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
```

본문 첫 부분의 토큰 결정만 교체 (이후 로직의 `baduk_session` 사용처는 지역 변수 `token_value`로 치환).

```python
    response.status_code = 204
    token_value = baduk_session or bearer_token(authorization)
    if not token_value:
        _clear_session_cookie(response)
        return response
    res = await db.execute(select(Session).where(Session.token == token_value))
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/api/ -v` 후 `ruff check . && mypy app`
Expected: 전부 PASS, lint/타입 클린

- [ ] **Step 5: 커밋**

```bash
git add backend/app/deps.py backend/app/api/session.py backend/tests/api/test_session.py
git commit -m "feat(api): Authorization Bearer 헤더 인증 추가 (쿠키 폴백 유지)"
```

### Task 3: WebSocket 토큰 쿼리 파라미터 인증

**Files:**
- Modify: `backend/app/api/ws.py:120-130` (ws_game 시그니처)
- Test: `backend/tests/api/test_ws_token_auth.py` (신규)

- [ ] **Step 1: 실패하는 테스트 작성** — `backend/tests/api/test_ws_token_auth.py` 신규 생성

```python
"""WS 쿼리 파라미터(token=) 인증 테스트 — 앱 셸은 쿠키 없이 WS를 연다."""
from __future__ import annotations

import pytest

from tests.api.test_ws_flow import _wire_test_app

_GAME_PAYLOAD = {
    "board_size": 9,
    "handicap": 0,
    "ai_rank": "5k",
    "user_color": "black",
}


def test_ws_accepts_query_token_without_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "wstoken"})
            token = r.json()["token"]
            tc.cookies.clear()  # 쿠키 경로 차단 — 헤더/쿼리만으로 통과해야 함
            auth = {"Authorization": f"Bearer {token}"}
            g = tc.post("/api/games", json=_GAME_PAYLOAD, headers=auth)
            assert g.status_code == 201, g.text
            game_id = g.json()["id"]
            with tc.websocket_connect(
                f"/api/ws/games/{game_id}?token={token}"
            ) as ws:
                ws.send_json({"type": "move", "coord": "C3"})
                msg = ws.receive_json()
                assert msg["type"] in ("state", "ai_move", "winrate")
    finally:
        import os

        os.unlink(db_path)


def test_ws_rejects_bad_query_token(monkeypatch: pytest.MonkeyPatch) -> None:
    tc, db_path = _wire_test_app(monkeypatch)
    try:
        with tc:
            r = tc.post("/api/session", json={"nickname": "wstoken2"})
            token = r.json()["token"]
            auth = {"Authorization": f"Bearer {token}"}
            g = tc.post("/api/games", json=_GAME_PAYLOAD, headers=auth)
            game_id = g.json()["id"]
            tc.cookies.clear()
            with pytest.raises(Exception):  # noqa: B017 (1008 close → handshake 예외)
                with tc.websocket_connect(f"/api/ws/games/{game_id}?token=bogus"):
                    pass
    finally:
        import os

        os.unlink(db_path)
```

주의: `/api/games` 생성 응답 키가 `id`가 아니면 `tests/api/test_ws_flow.py`의 기존 사용례를 따른다 (그쪽이 진실).

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/api/test_ws_token_auth.py -v`
Expected: 첫 테스트 FAIL — 쿠키 없이 연결되어 1008로 끊김 (handshake 예외)

- [ ] **Step 3: 구현** — `backend/app/api/ws.py` `ws_game` 시그니처에 쿼리 파라미터 추가

```python
@router.websocket("/api/ws/games/{game_id}")
async def ws_game(
    websocket: WebSocket,
    game_id: int,
    db: DbSession,
    baduk_session: Annotated[str | None, Cookie(alias=COOKIE_SESSION)] = None,
    token: str | None = None,
) -> None:
    # 쿠키(웹) 우선, 쿼리 파라미터(앱 셸 WebView)는 폴백. 토큰이 URL에 남는
    # 노출면은 자체 서버 wss 한정이라 수용한다.
    sess = await _authenticate_ws(baduk_session or token, db)
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/api/test_ws_token_auth.py tests/api/test_ws_flow.py tests/api/test_ws_lifecycle.py -v` 후 `ruff check . && mypy app`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/ws.py backend/tests/api/test_ws_token_auth.py
git commit -m "feat(ws): WS 인증에 token 쿼리 파라미터 폴백 추가"
```

### Task 4: CORS 오리진 문서화 (.env.example)

**Files:**
- Modify: `backend/.env.example` (CORS_ORIGINS 항목)

- [ ] **Step 1: 수정** — `backend/.env.example`의 `CORS_ORIGINS` 줄에 앱 셸 오리진 주석 추가

```bash
# 웹 + 앱 셸 오리진. Android Capacitor WebView는 https://localhost,
# iOS(후속)는 capacitor://localhost 를 추가해야 한다.
CORS_ORIGINS=http://localhost:3000,https://inkbaduk.com,https://localhost
```

코드 변경 없음 — `cors_origins_list`가 이미 쉼표 분리 파싱. 프로덕션 `~/.baduk.env`에도 배포 시 동일 값 반영 필요 (Phase 3 체크리스트에 포함).

- [ ] **Step 2: 커밋**

```bash
git add backend/.env.example
git commit -m "docs(env): CORS_ORIGINS에 Capacitor 앱 셸 오리진 안내 추가"
```

---

## Phase 1 — 프론트 앱 셸 모드

### Task 5: next.config.js BUILD_TARGET 분기

**Files:**
- Modify: `web/next.config.js`

- [ ] **Step 1: 구현** — 전체 교체

```javascript
/** @type {import('next').NextConfig} */
// BUILD_TARGET=app → Capacitor 정적 export. 그 외(웹)는 기존 standalone + rewrite 불변.
const isAppShell = process.env.BUILD_TARGET === "app";

const nextConfig = isAppShell
  ? { output: "export" }
  : {
      output: "standalone",
      async rewrites() {
        return [
          { source: "/api/:path*", destination: (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api/:path*" }
        ];
      }
    };
module.exports = nextConfig;
```

- [ ] **Step 2: 웹 모드 회귀 확인**

Run: `cd web && npm run build`
Expected: 기존과 동일하게 성공 (standalone 산출물)

- [ ] **Step 3: 커밋**

```bash
git add web/next.config.js
git commit -m "build(web): BUILD_TARGET=app 정적 export 분기 추가"
```

### Task 6: 앱 셸 플래그·토큰 저장·라우트 헬퍼 모듈

**Files:**
- Create: `web/lib/appShell.ts`
- Create: `web/lib/sessionToken.ts`
- Create: `web/lib/routes.ts`
- Test: `web/tests/routes.test.ts`
- Modify: `web/package.json` (@capacitor/preferences 의존성)

- [ ] **Step 1: 의존성 설치** (sessionToken의 dynamic import 대상 — 미리 설치해야 웹 빌드도 통과)

```bash
cd web && npm i @capacitor/core @capacitor/preferences
```

- [ ] **Step 2: 실패하는 테스트 작성** — `web/tests/routes.test.ts` 신규

```typescript
// 라우트 헬퍼 단위 테스트 — 웹 모드(기본)에서 path 형태 URL을 반환하는지 검증.
import { describe, expect, it } from "vitest";
import { gamePlayHref, gameReviewHref, proGameHref, spectateWatchHref } from "../lib/routes";

describe("routes (web mode)", () => {
  it("path 세그먼트 형태를 반환한다", () => {
    expect(gamePlayHref(7)).toBe("/game/play/7");
    expect(gameReviewHref(7)).toBe("/game/review/7");
    expect(spectateWatchHref(7)).toBe("/spectate/7");
    expect(proGameHref(12)).toBe("/spectate/pro/12");
  });
});
```

Run: `cd web && npm test -- --run tests/routes.test.ts`
Expected: FAIL (모듈 없음)

- [ ] **Step 3: 구현** — 3개 신규 파일

`web/lib/appShell.ts`

```typescript
// 앱 셸(Capacitor) 빌드 여부 플래그 — NEXT_PUBLIC_APP_SHELL=1 일 때만 true.
export const IS_APP_SHELL = process.env.NEXT_PUBLIC_APP_SHELL === "1";
```

`web/lib/sessionToken.ts`

```typescript
// 앱 셸용 세션 토큰 보관소 — 메모리 캐시 + Capacitor Preferences 영속화 담당.
import { IS_APP_SHELL } from "./appShell";

const KEY = "baduk_session_token";
let token: string | null = null;
let hydration: Promise<void> | null = null;

export function getSessionToken(): string | null {
  return token;
}

/** 앱 부팅 후 첫 API 호출 전에 Preferences → 메모리로 1회 복원한다. */
export function ensureSessionToken(): Promise<void> {
  if (!IS_APP_SHELL) return Promise.resolve();
  if (!hydration) {
    hydration = import("@capacitor/preferences")
      .then(async ({ Preferences }) => {
        const { value } = await Preferences.get({ key: KEY });
        if (token === null) token = value;
      })
      .catch(() => {});
  }
  return hydration;
}

export async function setSessionToken(next: string | null): Promise<void> {
  token = next;
  if (!IS_APP_SHELL) return;
  try {
    const { Preferences } = await import("@capacitor/preferences");
    if (next) await Preferences.set({ key: KEY, value: next });
    else await Preferences.remove({ key: KEY });
  } catch {}
}
```

`web/lib/routes.ts`

```typescript
// 동적 화면 이동 URL 헬퍼 — 웹은 path 세그먼트, 앱 셸은 쿼리 파라미터 형태.
import { IS_APP_SHELL } from "./appShell";

export function gamePlayHref(id: number): string {
  return IS_APP_SHELL ? `/game/play?id=${id}` : `/game/play/${id}`;
}

export function gameReviewHref(id: number): string {
  return IS_APP_SHELL ? `/game/review?id=${id}` : `/game/review/${id}`;
}

export function spectateWatchHref(id: number): string {
  return IS_APP_SHELL ? `/spectate/watch?id=${id}` : `/spectate/${id}`;
}

export function proGameHref(id: number): string {
  return IS_APP_SHELL ? `/spectate/pro/view?id=${id}` : `/spectate/pro/${id}`;
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd web && npm test -- --run tests/routes.test.ts && npm run type-check`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add web/lib/appShell.ts web/lib/sessionToken.ts web/lib/routes.ts web/tests/routes.test.ts web/package.json web/package-lock.json
git commit -m "feat(web): 앱 셸 플래그·세션 토큰 보관소·라우트 헬퍼 추가"
```

### Task 7: api.ts — 절대 URL + Authorization 헤더

**Files:**
- Modify: `web/lib/api.ts`

- [ ] **Step 1: 구현** — `web/lib/api.ts` 상단과 `api()` 수정

```typescript
import { IS_APP_SHELL } from "./appShell";
import { ensureSessionToken, getSessionToken } from "./sessionToken";

// 웹: 동일 출처 상대경로(next rewrite). 앱 셸: 백엔드 절대 URL 직접 호출.
export const API_BASE = IS_APP_SHELL
  ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : "";

/** 앱 셸에서만 Bearer 헤더를 만든다. 웹은 쿠키가 처리하므로 빈 객체. */
export function authHeaders(): Record<string, string> {
  const t = IS_APP_SHELL ? getSessionToken() : null;
  return t ? { Authorization: `Bearer ${t}` } : {};
}
```

`api()` 함수 — fetch 직전에 토큰 복원을 보장하고 헤더에 합류 (기존 구조 유지, 두 줄만 변경).

```typescript
export async function api<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  if (IS_APP_SHELL) await ensureSessionToken();
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init.headers || {}) },
    ...init
  });
```

- [ ] **Step 2: 토큰 라이프사이클 연결** — 발급·폐기 지점 2곳

`web/app/page.tsx` — `POST /api/session` 성공 직후 (현재 69행 부근, `const sess = await api<Session>(...)` 다음 줄).

```typescript
      await setSessionToken((sess as { token?: string | null }).token ?? null);
```

상단 import 추가: `import { setSessionToken } from "../lib/sessionToken";`
Session 타입 정의에 `token?: string | null` 필드 추가 — 정의 위치는 `grep -rn "interface Session" web/lib web/app` 으로 확인 후 수정.

`web/app/settings/page.tsx` — `/api/session/end` 호출 성공 직후에 `await setSessionToken(null);` 추가 (import 동일). 위치는 `grep -n "session/end" web/app/settings/page.tsx`.

- [ ] **Step 3: 검증**

Run: `cd web && npm run type-check && npm test -- --run && npm run build`
Expected: 전부 PASS (웹 모드 동작 불변 — API_BASE는 빈 문자열 유지)

- [ ] **Step 4: 커밋**

```bash
git add web/lib/api.ts web/app/page.tsx web/app/settings/page.tsx
git commit -m "feat(web): 앱 셸 API 절대 URL + Bearer 헤더 + 토큰 라이프사이클"
```

### Task 8: ws.ts — 토큰 쿼리 파라미터 + 절대 경로 프로브

**Files:**
- Modify: `web/lib/ws.ts:86-87` (url/probeUrl), `web/lib/ws.ts:121` (probe fetch)

- [ ] **Step 1: 구현**

상단 import 추가.

```typescript
import { API_BASE, authHeaders } from "./api";
import { IS_APP_SHELL } from "./appShell";
import { getSessionToken } from "./sessionToken";
```

`openGameWS` 내 url/probeUrl 구성 교체 (현재 86~87행).

```typescript
  const wsToken = IS_APP_SHELL ? getSessionToken() : null;
  const url =
    `${base}/api/ws/games/${gameId}` +
    (wsToken ? `?token=${encodeURIComponent(wsToken)}` : "");
  const probeUrl = `${API_BASE}/api/games/${gameId}`;
```

probe fetch 교체 (현재 121행).

```typescript
          const r = await fetch(probeUrl, {
            credentials: IS_APP_SHELL ? "include" : "same-origin",
            headers: authHeaders(),
          });
```

- [ ] **Step 2: 검증**

Run: `cd web && npm run type-check && npm test -- --run`
Expected: PASS (웹 모드에선 wsToken=null·API_BASE="" → 기존 동작 동일)

- [ ] **Step 3: 커밋**

```bash
git add web/lib/ws.ts
git commit -m "feat(web): WS 연결에 앱 셸 토큰 파라미터·절대 프로브 적용"
```

### Task 9: game/play 쿼리 라우트 이중화

**Files:**
- Create: `web/components/screens/GamePlayScreen.tsx` (기존 page 본체 이동)
- Modify: `web/app/game/play/[id]/page.tsx` (얇은 셸로 축소)
- Create: `web/app/game/play/page.tsx` (쿼리 진입점)
- Modify: `web/app/game/new/page.tsx:116` (이동 링크)

- [ ] **Step 1: 본체 추출**

```bash
mkdir -p web/components/screens
git mv "web/app/game/play/[id]/page.tsx" web/components/screens/GamePlayScreen.tsx
```

`GamePlayScreen.tsx` 편집.
- 첫 줄 `"use client"` 직후에 헤더 주석 추가. `// 대국 진행 화면 본체 — path/query 두 진입점이 공유한다.`
- 컴포넌트 시그니처를 `({ params }: { params: { id: string } })`에서 `({ gameId }: { gameId: number })`로 변경, 함수명을 `GamePlayScreen`으로 변경.
- 본문에서 `params.id`(또는 `Number(params.id)`) 사용처를 전부 `gameId`로 치환. 확인: `grep -n "params" web/components/screens/GamePlayScreen.tsx` 결과 0건.
- 상대 import 깊이 변경 주의: `../../../../`(app/game/play/[id] 기준) → `../../`(components/screens 기준) 형태로 type-check가 잡아주는 대로 수정.

- [ ] **Step 2: 두 진입점 작성**

`web/app/game/play/[id]/page.tsx` (재생성 — 웹 전용 path 셸)

```tsx
"use client";
// 웹 전용 path 진입점 — /game/play/[id] 기존 링크 호환. 본체는 GamePlayScreen.
import GamePlayScreen from "../../../../components/screens/GamePlayScreen";

export default function GamePlayByPath({ params }: { params: { id: string } }) {
  return <GamePlayScreen gameId={Number(params.id)} />;
}
```

`web/app/game/play/page.tsx` (신규 — 쿼리 진입점, 앱 셸 포함 빌드용)

```tsx
"use client";
// 쿼리 진입점 — /game/play?id= 형태. 앱 셸(정적 export)에서 사용한다.
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import GamePlayScreen from "../../../components/screens/GamePlayScreen";

function PlayFromQuery() {
  const id = Number(useSearchParams().get("id"));
  if (!Number.isInteger(id) || id <= 0) return null;
  return <GamePlayScreen gameId={id} />;
}

export default function GamePlayPage() {
  return (
    <Suspense fallback={null}>
      <PlayFromQuery />
    </Suspense>
  );
}
```

- [ ] **Step 3: 내부 이동을 헬퍼로 전환** — `web/app/game/new/page.tsx:116`

```typescript
      router.push(gamePlayHref(res.id));
```

import 추가: `import { gamePlayHref } from "../../../lib/routes";`

- [ ] **Step 4: 검증**

Run: `cd web && npm run type-check && npm run lint && npm test -- --run && npm run build`
Expected: PASS. 브라우저 수동 확인(선택): `/game/play/7`과 `/game/play?id=7` 모두 동일 화면.

- [ ] **Step 5: 커밋**

```bash
git add -A web/app/game web/components/screens
git commit -m "refactor(web): game/play 본체 추출 + 쿼리 진입점 이중화"
```

### Task 10: game/review 쿼리 라우트 이중화

**Files:**
- Create: `web/components/screens/GameReviewScreen.tsx`
- Modify: `web/app/game/review/[id]/page.tsx`
- Create: `web/app/game/review/page.tsx`
- Modify: `web/app/history/page.tsx:202` (review 링크)

- [ ] **Step 1: Task 9와 동일 패턴으로 추출·작성**

```bash
git mv "web/app/game/review/[id]/page.tsx" web/components/screens/GameReviewScreen.tsx
```

`GameReviewScreen.tsx` — 헤더 주석 `// 복기 화면 본체 — path/query 두 진입점이 공유한다.`, 시그니처 `({ gameId }: { gameId: number })`, 함수명 `GameReviewScreen`, `params` 사용처 치환.

`web/app/game/review/[id]/page.tsx`

```tsx
"use client";
// 웹 전용 path 진입점 — /game/review/[id] 기존 링크 호환. 본체는 GameReviewScreen.
import GameReviewScreen from "../../../../components/screens/GameReviewScreen";

export default function GameReviewByPath({ params }: { params: { id: string } }) {
  return <GameReviewScreen gameId={Number(params.id)} />;
}
```

`web/app/game/review/page.tsx`

```tsx
"use client";
// 쿼리 진입점 — /game/review?id= 형태. 앱 셸(정적 export)에서 사용한다.
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import GameReviewScreen from "../../../components/screens/GameReviewScreen";

function ReviewFromQuery() {
  const id = Number(useSearchParams().get("id"));
  if (!Number.isInteger(id) || id <= 0) return null;
  return <GameReviewScreen gameId={id} />;
}

export default function GameReviewPage() {
  return (
    <Suspense fallback={null}>
      <ReviewFromQuery />
    </Suspense>
  );
}
```

`web/app/history/page.tsx:202` — `href={gameReviewHref(g.id)}` 로 교체, import 추가.

- [ ] **Step 2: 검증 후 커밋**

Run: `cd web && npm run type-check && npm run lint && npm run build`

```bash
git add -A web/app/game/review web/app/history/page.tsx web/components/screens/GameReviewScreen.tsx
git commit -m "refactor(web): game/review 본체 추출 + 쿼리 진입점 이중화"
```

### Task 11: spectate 상세·프로 상세 쿼리 라우트 이중화

**Files:**
- Create: `web/components/screens/SpectateWatchScreen.tsx` ← `web/app/spectate/[id]/page.tsx`
- Create: `web/app/spectate/watch/page.tsx`
- Create: `web/components/screens/ProGameScreen.tsx` ← `web/app/spectate/pro/[id]/page.tsx`
- Create: `web/app/spectate/pro/view/page.tsx`
- Modify: `web/app/spectate/page.tsx` (목록 → 상세 링크), `web/components/ProGameList.tsx:156`

- [ ] **Step 1: 두 화면 모두 Task 9와 동일 패턴 적용**

헤더 주석은 각각 `// 라이브 관전 화면 본체 — path/query 두 진입점이 공유한다.`, `// 프로 기보 감상 화면 본체 — path/query 두 진입점이 공유한다.` 쿼리 진입점 경로는 `/spectate/watch?id=`, `/spectate/pro/view?id=`.

주의 — `web/app/spectate/pro/[id]/layout.tsx`(generateMetadata)는 **그대로 둔다**. 웹 SEO용 path 라우트의 메타는 보존되어야 한다. path page 셸만 본체를 import하도록 축소한다.

- [ ] **Step 2: 목록 링크를 헬퍼로 전환**

- `web/components/ProGameList.tsx:156` — `href={proGameHref(r.id)}` (import 추가).
- `web/app/spectate/page.tsx` — 상세로 가는 `href={\`/spectate/${...}\`}` 패턴을 `spectateWatchHref(...)`로 교체. 위치 확인: `grep -n "spectate/\${" web/app/spectate/page.tsx` 및 `grep -n 'href={`/spectate' web/app/spectate/page.tsx`.

- [ ] **Step 3: 검증 후 커밋**

Run: `cd web && npm run type-check && npm run lint && npm test -- --run && npm run build`

```bash
git add -A web/app/spectate web/components
git commit -m "refactor(web): 관전·프로 상세 본체 추출 + 쿼리 진입점 이중화"
```

### Task 12: 앱 셸 export 빌드 스크립트

**Files:**
- Create: `web/scripts/build-app.sh`

- [ ] **Step 1: 스크립트 작성**

```bash
#!/usr/bin/env bash
# 앱 셸(Capacitor) 정적 export 빌드 — 웹 전용 라우트를 임시 제외하고 next build를 돌린다.
set -euo pipefail

WEB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WEB_DIR"

# 웹 전용(앱 제외) 라우트·파일. export를 깨뜨리는 force-dynamic/동적 세그먼트 포함.
EXCLUDES=(
  "app/admin" "app/dev" "app/support" "app/supporters"
  "app/faq" "app/glossary"
  "app/spectate/picks" "app/spectate/themes"
  "app/spectate/[id]" "app/spectate/pro/[id]"
  "app/game/play/[id]" "app/game/review/[id]"
  "app/sitemap.ts" "app/robots.ts"
)

STASH="$WEB_DIR/.app-shell-excluded"
rm -rf "$STASH"

restore() {
  cd "$WEB_DIR"
  for p in "${EXCLUDES[@]}"; do
    if [ -e "$STASH/$p" ]; then
      mkdir -p "$(dirname "$p")"
      rm -rf "$p"
      mv "$STASH/$p" "$p"
    fi
  done
  rm -rf "$STASH"
}
trap restore EXIT

for p in "${EXCLUDES[@]}"; do
  if [ -e "$p" ]; then
    mkdir -p "$STASH/$(dirname "$p")"
    mv "$p" "$STASH/$p"
  fi
done

BUILD_TARGET=app \
NEXT_PUBLIC_APP_SHELL=1 \
NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-https://inkbaduk.com}" \
NEXT_PUBLIC_WS_URL="${NEXT_PUBLIC_WS_URL:-wss://inkbaduk.com}" \
npx next build

echo "✔ app shell export → $WEB_DIR/out"
```

```bash
chmod +x web/scripts/build-app.sh
```

- [ ] **Step 2: export 빌드 성공 확인 (이 Phase의 게이트)**

Run: `bash web/scripts/build-app.sh`
Expected: 성공, `web/out/index.html` 존재, 제외 라우트가 원위치 복원됨 (`git status`에 잔여 이동 없음).
실패 시 에러에 찍힌 라우트를 읽고 원인(잔여 동적 세그먼트·force-dynamic·서버 전용 API)을 제거한다 — 추측 금지, 에러의 라우트명이 진실.

- [ ] **Step 3: 웹 빌드 회귀 확인**

Run: `cd web && npm run build`
Expected: 성공 (standalone — 제외 없이 전체 라우트)

- [ ] **Step 4: 커밋**

```bash
git add web/scripts/build-app.sh
git commit -m "build(web): 앱 셸 정적 export 빌드 스크립트 추가"
```

### Task 13: 후원 링크 숨김 + 오프라인 배너

**Files:**
- Modify: `web/components/Footer.tsx` (support 링크 분기)
- Create: `web/components/OfflineBanner.tsx`
- Modify: `web/app/layout.tsx` (배너 장착)
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json` (offline 키 동시 추가)

- [ ] **Step 1: Footer 분기** — `web/components/Footer.tsx`의 링크 배열에서 support 항목을 조건 제외

```typescript
import { IS_APP_SHELL } from "../lib/appShell";
// 기존 링크 배열 정의를 따라가서 support 항목만 필터
const links = ALL_LINKS.filter((l) => !(IS_APP_SHELL && l.href === "/support"));
```

실제 배열 이름·구조는 파일을 열어 맞춘다 (`grep -n "support" web/components/Footer.tsx`). supporters 링크가 있으면 함께 제외.

- [ ] **Step 2: i18n 키 추가** — `ko.json` / `en.json` **동시에**

```json
"offline": { "banner": "오프라인 상태입니다. 연결을 확인해 주세요." }
```

```json
"offline": { "banner": "You're offline. Check your connection." }
```

- [ ] **Step 3: 배너 컴포넌트** — `web/components/OfflineBanner.tsx`

```tsx
"use client";
// 네트워크 단절 안내 배너 — offline 이벤트 시 상단 고정 표시 (앱 심사 필수 UX).
import { useEffect, useState } from "react";

export default function OfflineBanner({ label }: { label: string }) {
  const [offline, setOffline] = useState(false);
  useEffect(() => {
    setOffline(!navigator.onLine);
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  if (!offline) return null;
  return (
    <div role="status" className="fixed inset-x-0 top-0 z-50 bg-oxblood px-4 py-2 text-center text-sm text-paper">
      {label}
    </div>
  );
}
```

`label`은 layout에서 i18n으로 주입 — layout의 기존 i18n 사용 방식을 따른다 (`grep -n "i18n\|t(" web/app/layout.tsx`로 확인). 클래스는 디자인 토큰만 사용 (hex 금지).

- [ ] **Step 4: 검증 후 커밋**

Run: `cd web && npm run type-check && npm run lint && npm test -- --run && bash scripts/build-app.sh`

```bash
git add web/components/Footer.tsx web/components/OfflineBanner.tsx web/app/layout.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): 앱 셸 후원 링크 숨김 + 오프라인 배너"
```

---

## Phase 2 — Capacitor Android

### Task 14: Capacitor 초기화 (web/ 루트)

**Files:**
- Create: `web/capacitor.config.ts`
- Modify: `web/package.json`, `web/.gitignore`

- [ ] **Step 1: 의존성 설치 + init**

```bash
cd web
npm i @capacitor/app @capacitor/haptics @capacitor/splash-screen @capacitor/status-bar
npm i -D @capacitor/cli
```

- [ ] **Step 2: 설정 작성** — `web/capacitor.config.ts` (config 파일 — 헤더 주석 예외)

먼저 paper 토큰 원값 확인: `grep -n "\-\-paper" web/app/globals.css | head -3` → 라이트 모드 hex를 아래 `backgroundColor`에 사용.

```typescript
import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.inkbaduk.app",
  appName: "Inkbaduk",
  webDir: "out",
  plugins: {
    SplashScreen: {
      launchShowDuration: 600,
      backgroundColor: "<globals.css --paper 라이트 값>",
      showSpinner: false,
    },
  },
};

export default config;
```

`web/.gitignore`에 추가: `android/app/build/`, `android/.gradle/` (android/ 자체는 커밋 대상).

- [ ] **Step 3: 커밋**

```bash
git add web/capacitor.config.ts web/package.json web/package-lock.json web/.gitignore
git commit -m "feat(app): Capacitor 설정 추가 (com.inkbaduk.app)"
```

### Task 15: 네이티브 브리지 (뒤로가기·복귀 이벤트)

**Files:**
- Create: `web/components/AppShellBridge.tsx`
- Modify: `web/app/layout.tsx` (장착)
- Modify: `web/components/screens/GamePlayScreen.tsx` (복귀 시 재동기화)

- [ ] **Step 1: 브리지 컴포넌트**

```tsx
"use client";
// 앱 셸 네이티브 브리지 — Android 뒤로가기와 포그라운드 복귀를 웹 쪽에 연결한다.
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { IS_APP_SHELL } from "../lib/appShell";

export const APP_RESUMED_EVENT = "inkbaduk:app-resumed";

export default function AppShellBridge() {
  const router = useRouter();
  useEffect(() => {
    if (!IS_APP_SHELL) return;
    let cleanup: (() => void) | undefined;
    import("@capacitor/app").then(({ App }) => {
      const backSub = App.addListener("backButton", () => {
        if (window.location.pathname === "/") App.minimizeApp();
        else router.back();
      });
      const stateSub = App.addListener("appStateChange", ({ isActive }) => {
        if (isActive) window.dispatchEvent(new Event(APP_RESUMED_EVENT));
      });
      cleanup = () => {
        backSub.then((s) => s.remove());
        stateSub.then((s) => s.remove());
      };
    });
    // 상태바를 paper 배경에 어두운 아이콘으로 맞춘다 (Editorial 톤).
    import("@capacitor/status-bar")
      .then(({ StatusBar, Style }) => StatusBar.setStyle({ style: Style.Light }))
      .catch(() => {});
    return () => cleanup?.();
  }, [router]);
  return null;
}
```

`web/app/layout.tsx` body 안(기존 Provider 트리 안쪽 아무 위치)에 `<AppShellBridge />` 추가.

- [ ] **Step 2: 대국 화면 복귀 재동기화** — `web/components/screens/GamePlayScreen.tsx`

게임 메타/상태를 최초 로드하는 기존 함수(useEffect의 fetch)를 재사용해 복귀 시 재호출한다. WS는 onclose → 재연결 루프가 이미 있으므로 상태 재취득만 보강.

```tsx
import { APP_RESUMED_EVENT } from "../AppShellBridge";
// 기존 로드 함수가 useCallback이 아니면 ref로 감싸 최신 참조를 유지한다.
useEffect(() => {
  const onResume = () => {
    void reloadGame(); // ← 기존 초기 로드 함수명으로 교체
  };
  window.addEventListener(APP_RESUMED_EVENT, onResume);
  return () => window.removeEventListener(APP_RESUMED_EVENT, onResume);
}, []);
```

- [ ] **Step 3: 검증 후 커밋**

Run: `cd web && npm run type-check && npm run lint && npm run build && bash scripts/build-app.sh`

```bash
git add web/components/AppShellBridge.tsx web/app/layout.tsx web/components/screens/GamePlayScreen.tsx
git commit -m "feat(app): 네이티브 브리지 — 뒤로가기·포그라운드 복귀 연결"
```

### Task 16: 착수 햅틱

**Files:**
- Modify: `web/components/screens/GamePlayScreen.tsx` (사용자 착수 전송 지점)

- [ ] **Step 1: 구현** — 사용자가 돌을 놓아 move를 전송하는 핸들러(보드 클릭 확정 지점)에 추가. 위치 확인: `grep -n '"move"' web/components/screens/GamePlayScreen.tsx`.

```typescript
if (IS_APP_SHELL) {
  import("@capacitor/haptics")
    .then(({ Haptics, ImpactStyle }) => Haptics.impact({ style: ImpactStyle.Light }))
    .catch(() => {});
}
```

- [ ] **Step 2: 검증 후 커밋**

Run: `cd web && npm run type-check && bash scripts/build-app.sh`

```bash
git add web/components/screens/GamePlayScreen.tsx
git commit -m "feat(app): 착수 시 햅틱 피드백 (앱 셸 한정)"
```

### Task 17: Android 플랫폼 추가 + 디버그 APK

**Files:**
- Create: `web/android/` (cap add 생성물 일체)

- [ ] **Step 1: 플랫폼 추가 + 동기화**

```bash
cd web
npm i @capacitor/android
bash scripts/build-app.sh
npx cap add android
npx cap sync android
```

- [ ] **Step 2: 디버그 APK 빌드**

Run: `cd web/android && ./gradlew assembleDebug`
Expected: `web/android/app/build/outputs/apk/debug/app-debug.apk` 생성.
JDK 21 필요 — 없으면 `brew install --cask temurin@21` 후 `JAVA_HOME` 지정.

- [ ] **Step 3: 커밋**

```bash
git add web/android web/package.json web/package-lock.json
git commit -m "feat(app): Android 플랫폼 추가 (Capacitor)"
```

---

## Phase 3 — 검증·문서

### Task 18: 에뮬레이터 스모크 + 회귀

- [ ] **Step 1: 에뮬레이터 스모크** (수동 — Android Studio 에뮬레이터 또는 실기기, 로컬 백엔드 대상이면 `NEXT_PUBLIC_API_URL=http://10.0.2.2:8000 NEXT_PUBLIC_WS_URL=ws://10.0.2.2:8000 bash scripts/build-app.sh && npx cap sync android` 후 실행)

체크리스트.
1. 닉네임 입력 → 입장 (토큰 발급·저장).
2. 새 대국 생성 → 착수 → AI 응수 (WS 토큰 인증 + 햅틱).
3. 홈 버튼으로 백그라운드 → 복귀 → 보드 상태 일치 (재동기화).
4. 비행기 모드 → 오프라인 배너 표시 → 해제 → 배너 소멸 + WS 자동 복구.
5. Android 뒤로가기 — 화면 스택 후퇴, 홈에선 앱 최소화.
6. 앱 완전 종료 → 재실행 → 닉네임 재입력 없이 세션 유지 (Preferences 토큰, 1시간 TTL 내).
7. Footer에 후원 링크 없음, faq/글로서리/픽스 링크 미노출 확인 (TopNav·Footer에 해당 링크가 있으면 IS_APP_SHELL 분기 추가).

- [ ] **Step 2: 웹 전체 회귀**

```bash
cd backend && source .venv311/bin/activate && pytest && ruff check . && mypy app
cd ../web && npm run lint && npm run type-check && npm test -- --run && npm run build
```

Expected: 전부 PASS.

- [ ] **Step 3: 프로덕션 배포 메모** — `~/.baduk.env`의 `CORS_ORIGINS`에 `https://localhost` 추가 후 launchd 재시작 (`launchctl kickstart -k gui/$(id -u)/com.baduk.api`). 앱이 prod API를 치려면 이 값이 선행 조건.

### Task 19: CI·문서 갱신

**Files:**
- Modify: `.github/workflows/ci.yml` (app export 빌드 잡 추가)
- Modify: `CLAUDE.md` (Commands 섹션), `CHANGELOG.md`

- [ ] **Step 1: CI 잡 추가** — frontend 잡과 동급으로

```yaml
  app-shell-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: web/package-lock.json
      - run: npm ci
        working-directory: web
      - run: bash scripts/build-app.sh
        working-directory: web
```

- [ ] **Step 2: CLAUDE.md Commands에 추가**

```bash
bash scripts/build-app.sh                # 앱 셸 정적 export (web/out)
npx cap sync android && cd android && ./gradlew assembleDebug  # 디버그 APK
```

- [ ] **Step 3: CHANGELOG에 Unreleased 항목 추가 후 커밋**

```bash
git add .github/workflows/ci.yml CLAUDE.md CHANGELOG.md
git commit -m "ci(app): 앱 셸 export 빌드 잡 + 문서 갱신"
```

---

## 전체 검증 (Definition of Done)

1. `backend` — `pytest`(기존 170 + 신규 6) · `ruff` · `mypy` 클린.
2. `web` — `npm run build`(웹 standalone) · `bash scripts/build-app.sh`(export) 둘 다 성공.
3. `app-debug.apk` 에뮬레이터에서 Task 18 스모크 7항목 통과.
4. 웹 prod 영향 0 — 쿠키 인증·rewrite·기존 URL(`/game/play/[id]` 등) 전부 기존 동작 유지.
5. 스토어 자산·서명·Play Console 등록은 본 계획 범위 밖 (스펙 '범위 밖' 절).
