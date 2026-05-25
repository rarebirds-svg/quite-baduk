# `last_seen_at` 디바운스 캐시 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sessions.last_seen_at` 매 요청 UPDATE를 60s 메모리 디바운스 캐시로 대체해 hot row DB 쓰기 압박을 95%+ 감소.

**Architecture:** 단일 모듈 `app/last_seen_cache.py`에 모듈 전역 dict + asyncio 백그라운드 flusher. `deps.py`·`ws.py`는 인라인 UPDATE를 `stamp()` 한 줄로 교체. lifespan이 flusher 시작·종료를 관리하고 `session_purge`가 cutoff SELECT 전에 `flush_all`을 호출해 정확성 보장.

**Tech Stack:** Python 3.11, SQLAlchemy 2 async + aiosqlite, FastAPI lifespan, pytest-asyncio, structlog.

**Spec:** `docs/superpowers/specs/2026-05-25-last-seen-at-debounce-design.md`

---

## 파일 구조

**신규.**
- `backend/app/last_seen_cache.py` — 단일 책임 모듈 (stamp / flush_due / lifecycle).
- `backend/tests/test_last_seen_cache.py` — 단위 + 통합 테스트 8건.

**수정.**
- `backend/app/deps.py` (L46–L65 부근) — 인라인 UPDATE 제거, `stamp(sess.id)` 호출.
- `backend/app/api/ws.py` (L108–L126 부근) — 동일.
- `backend/app/main.py` (lifespan) — flusher 시작·종료 통합.
- `backend/app/session_purge.py` (L23–L43 부근) — 진입 시 `flush_all` 호출.

---

## Task 0: 브랜치·워크트리

**Files:** (변경 없음 — setup만)

- [ ] **Step 1: 워크트리 + 브랜치**

```bash
cd /Users/daegong/projects/baduk
git worktree add .claude/worktrees/last-seen-debounce -b feat/last-seen-at-debounce
cd .claude/worktrees/last-seen-debounce
```

Expected. `Preparing worktree (new branch 'feat/last-seen-at-debounce')`. 이후 모든 작업은 이 디렉터리에서.

---

## Task 1: `last_seen_cache.py` — 모듈 골격과 `stamp()`

**Files:**
- Create: `backend/app/last_seen_cache.py`
- Create: `backend/tests/test_last_seen_cache.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_last_seen_cache.py` 생성:

```python
# last_seen_cache 모듈 단위 테스트 — stamp / flush_due / lifecycle.
from __future__ import annotations

import datetime as dt

import pytest

from app import last_seen_cache as lsc


@pytest.fixture(autouse=True)
def _reset_cache():
    lsc._reset_for_tests()
    yield
    lsc._reset_for_tests()


def test_stamp_sets_cache_entry():
    now = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    lsc.stamp(42, when=now)
    assert 42 in lsc._cache
    seen, flushed = lsc._cache[42]
    assert seen == now
    assert flushed == lsc._EPOCH


def test_stamp_overwrites_seen_keeps_flushed():
    t1 = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t2 = dt.datetime(2026, 5, 25, 12, 0, 5, tzinfo=dt.UTC)
    lsc.stamp(7, when=t1)
    # 가짜 flushed_at 주입
    lsc._cache[7] = (t1, t1)
    lsc.stamp(7, when=t2)
    seen, flushed = lsc._cache[7]
    assert seen == t2
    assert flushed == t1
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/last-seen-debounce/backend
source .venv311/bin/activate || (python3.11 -m venv .venv311 && source .venv311/bin/activate && pip install -q -e ".[dev]")
pytest tests/test_last_seen_cache.py -v
```

Expected. `ModuleNotFoundError: No module named 'app.last_seen_cache'` (또는 `_reset_for_tests` 미존재 에러).

- [ ] **Step 3: 최소 구현 작성**

`backend/app/last_seen_cache.py` 생성:

```python
# sessions.last_seen_at 쓰기 디바운스 — 매 요청 UPDATE 대신 메모리 캐시 후 60s 단위 flush.
from __future__ import annotations

import asyncio
import datetime as dt
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import update as _sa_update

from app.models import Session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

_FLUSH_INTERVAL_SEC = 60.0
_LOOP_TICK_SEC = 30.0
_EPOCH = dt.datetime.min.replace(tzinfo=dt.UTC)
_cache: dict[int, tuple[dt.datetime, dt.datetime]] = {}
_lock = asyncio.Lock()
_task: asyncio.Task[None] | None = None
log = structlog.get_logger()


def stamp(session_id: int, when: dt.datetime | None = None) -> None:
    """매 요청에서 호출. 메모리 dict만 갱신. DB 무접촉."""
    now = when or dt.datetime.now(dt.UTC)
    flushed = _cache.get(session_id, (None, _EPOCH))[1]
    _cache[session_id] = (now, flushed)


def _reset_for_tests() -> None:
    _cache.clear()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_last_seen_cache.py -v
```

Expected. `2 passed`.

- [ ] **Step 5: 커밋**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/last-seen-debounce
git add backend/app/last_seen_cache.py backend/tests/test_last_seen_cache.py
git commit -m "$(cat <<'EOF'
feat(db): last_seen_cache 모듈 골격과 stamp() 도입 (TDD)

매 요청 sessions.last_seen_at UPDATE를 메모리 디바운스로 대체할
모듈의 핵심 자료구조와 stamp() API. flush·lifecycle은 후속 커밋.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `flush_due()` — DB 쓰기 로직

**Files:**
- Modify: `backend/app/last_seen_cache.py`
- Modify: `backend/tests/test_last_seen_cache.py`

- [ ] **Step 1: 실패 테스트 4건 추가**

`backend/tests/test_last_seen_cache.py` 뒤에 추가:

```python
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.models import Session


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def seeded_session(session_factory):
    """DB에 세션 행 1개 미리 삽입. id=1 반환."""
    base_seen = dt.datetime(2026, 5, 25, 11, 0, 0, tzinfo=dt.UTC)
    async with session_factory() as s:
        row = Session(
            token="qa-token-1",
            nickname="qa",
            nickname_key="qa",
            created_at=base_seen,
            last_seen_at=base_seen,
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
        return row.id


async def _db_last_seen(factory, sid: int) -> dt.datetime | None:
    async with factory() as s:
        res = await s.execute(select(Session.last_seen_at).where(Session.id == sid))
        return res.scalar_one_or_none()


@pytest.mark.asyncio
async def test_flush_due_writes_when_aged(session_factory, seeded_session):
    sid = seeded_session
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush = dt.datetime(2026, 5, 25, 12, 1, 0, tzinfo=dt.UTC)  # +60s

    lsc.stamp(sid, when=t_stamp)
    written = await lsc.flush_due(session_factory, now=t_flush)

    assert written == 1
    assert await _db_last_seen(session_factory, sid) == t_stamp
    seen, flushed = lsc._cache[sid]
    assert flushed == t_flush


@pytest.mark.asyncio
async def test_flush_due_skips_recent(session_factory, seeded_session):
    sid = seeded_session
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush = dt.datetime(2026, 5, 25, 12, 0, 30, tzinfo=dt.UTC)  # +30s only

    lsc.stamp(sid, when=t_stamp)
    written = await lsc.flush_due(session_factory, now=t_flush)

    assert written == 0
    # DB의 last_seen_at은 seeded 시점 그대로
    db_seen = await _db_last_seen(session_factory, sid)
    assert db_seen != t_stamp


@pytest.mark.asyncio
async def test_flush_force_writes_all(session_factory, seeded_session):
    sid = seeded_session
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush = dt.datetime(2026, 5, 25, 12, 0, 5, tzinfo=dt.UTC)  # +5s only

    lsc.stamp(sid, when=t_stamp)
    written = await lsc.flush_due(session_factory, force=True, now=t_flush)

    assert written == 1
    assert await _db_last_seen(session_factory, sid) == t_stamp


@pytest.mark.asyncio
async def test_flush_removes_orphan_entry(session_factory):
    # cache에는 있지만 DB엔 없는 sid (idle purge 같은 시나리오)
    orphan_sid = 9999
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush = dt.datetime(2026, 5, 25, 12, 1, 0, tzinfo=dt.UTC)

    lsc.stamp(orphan_sid, when=t_stamp)
    written = await lsc.flush_due(session_factory, now=t_flush)

    assert written == 0
    assert orphan_sid not in lsc._cache


@pytest.mark.asyncio
async def test_flush_repeated_is_noop(session_factory, seeded_session):
    sid = seeded_session
    t_stamp = dt.datetime(2026, 5, 25, 12, 0, 0, tzinfo=dt.UTC)
    t_flush1 = dt.datetime(2026, 5, 25, 12, 1, 0, tzinfo=dt.UTC)
    t_flush2 = dt.datetime(2026, 5, 25, 12, 2, 0, tzinfo=dt.UTC)

    lsc.stamp(sid, when=t_stamp)
    written1 = await lsc.flush_due(session_factory, now=t_flush1)
    written2 = await lsc.flush_due(session_factory, now=t_flush2)

    assert written1 == 1
    assert written2 == 0  # seen <= flushed
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
pytest tests/test_last_seen_cache.py -v
```

Expected. 5개 신규 테스트 FAIL — `module 'app.last_seen_cache' has no attribute 'flush_due'`.

- [ ] **Step 3: `flush_due` / `flush_all` 구현**

`backend/app/last_seen_cache.py` 끝에 추가:

```python
async def flush_due(
    factory: "async_sessionmaker",
    *,
    force: bool = False,
    now: dt.datetime | None = None,
) -> int:
    """조건 부합 항목 일괄 UPDATE. force=True면 시간 무관 모두.

    조건 (force=False). seen > flushed 이고 flushed가 60s+ 전.
    UPDATE rowcount==0 이면 cache에서 해당 entry 제거(orphan 정리).
    반환. 실제 UPDATE 성공 건수.
    """
    n = now or dt.datetime.now(dt.UTC)
    threshold = n - dt.timedelta(seconds=_FLUSH_INTERVAL_SEC)
    async with _lock:
        snapshot = list(_cache.items())
    due: list[tuple[int, dt.datetime]] = []
    for sid, (seen, flushed) in snapshot:
        if seen <= flushed:
            continue
        if force or flushed < threshold:
            due.append((sid, seen))
    if not due:
        return 0
    written = 0
    async with factory() as db:
        for sid, seen in due:
            res = await db.execute(
                _sa_update(Session).where(Session.id == sid).values(last_seen_at=seen)
            )
            rc = getattr(res, "rowcount", 0)
            if rc == 0:
                _cache.pop(sid, None)
            else:
                _cache[sid] = (seen, n)
                written += 1
        await db.commit()
    return written


async def flush_all(factory: "async_sessionmaker") -> int:
    """force=True alias. session_purge·shutdown 진입에서 사용."""
    return await flush_due(factory, force=True)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_last_seen_cache.py -v
```

Expected. `7 passed`.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/last_seen_cache.py backend/tests/test_last_seen_cache.py
git commit -m "feat(db): last_seen_cache.flush_due + flush_all 구현

조건 부합(seen > flushed AND flushed 60s+ 경과) entry만 UPDATE.
orphan은 cache에서 제거. force=True alias로 flush_all 제공.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: lifecycle — `start_flusher` / `stop_flusher`

**Files:**
- Modify: `backend/app/last_seen_cache.py`
- Modify: `backend/tests/test_last_seen_cache.py`

- [ ] **Step 1: 실패 테스트 추가**

`backend/tests/test_last_seen_cache.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_start_and_stop_flusher_idempotent(session_factory):
    # 시작·재시작·정지 시퀀스가 task 누수 없이 안전한지.
    lsc.start_flusher(session_factory)
    assert lsc._task is not None
    first = lsc._task

    lsc.start_flusher(session_factory)  # 이미 살아 있으면 noop
    assert lsc._task is first

    await lsc.stop_flusher()
    assert lsc._task is None

    # 정지 후 재시작 가능
    lsc.start_flusher(session_factory)
    assert lsc._task is not None
    await lsc.stop_flusher()
```

- [ ] **Step 2: 실패 확인**

```bash
pytest tests/test_last_seen_cache.py::test_start_and_stop_flusher_idempotent -v
```

Expected. FAIL — `start_flusher` 미정의.

- [ ] **Step 3: lifecycle 구현 추가**

`backend/app/last_seen_cache.py` 끝에 추가:

```python
async def _flusher_loop(factory: "async_sessionmaker") -> None:
    """30s마다 flush_due(force=False) 호출. 예외는 로깅 후 계속."""
    while True:
        try:
            await flush_due(factory, force=False)
        except Exception as e:  # noqa: BLE001
            log.warning("last_seen_cache.flush_failed", error=str(e))
        await asyncio.sleep(_LOOP_TICK_SEC)


def start_flusher(factory: "async_sessionmaker") -> None:
    """lifespan startup에서 호출. 기존 task가 살아있으면 noop."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_flusher_loop(factory))


async def stop_flusher() -> None:
    """lifespan shutdown에서 호출. task 종료까지 대기."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None
```

`_reset_for_tests` 갱신 (task도 cleanup):

```python
def _reset_for_tests() -> None:
    global _task
    _cache.clear()
    if _task and not _task.done():
        _task.cancel()
    _task = None
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_last_seen_cache.py -v
```

Expected. `8 passed`.

- [ ] **Step 5: lint·type 통과 확인**

```bash
ruff check app/last_seen_cache.py
mypy app/last_seen_cache.py
```

Expected. 무에러.

- [ ] **Step 6: 커밋**

```bash
git add backend/app/last_seen_cache.py backend/tests/test_last_seen_cache.py
git commit -m "feat(db): last_seen_cache lifecycle — start/stop flusher

asyncio Task로 30s 주기 flush_due 실행. idempotent start, cancel
+ 종료 대기로 안전한 shutdown.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `deps.py` — REST 인증 경로를 stamp로 교체

**Files:**
- Modify: `backend/app/deps.py` (L46–L65 부근)

- [ ] **Step 1: 현재 상태 확인**

```bash
sed -n '40,75p' backend/app/deps.py
```

목표 — `get_current_session` 안의 인라인 UPDATE + `rowcount==0 → 401` 분기를 `stamp(sess.id)` 한 줄로 교체.

- [ ] **Step 2: 신규 흐름 적용**

`backend/app/deps.py`에서 `# Use a direct UPDATE rather than ORM ...`로 시작하는 블록을 (다음 `return sess`까지) 다음으로 교체. 핵심 차이는 인라인 UPDATE 제거 + import.

기존:
```python
    # Use a direct UPDATE rather than ORM attribute mutation + commit so a
    # concurrent DELETE (logout beacon double-fire, idle purge) doesn't trip
    # the optimistic-lock check and bubble up as a 500.
    upd = await db.execute(
        _sa_update(Session)
        .where(Session.id == sess.id)
        .values(last_seen_at=dt.datetime.now(dt.UTC))
    )
    await db.commit()
    # `Result[Any].rowcount` is exposed at runtime by CursorResult (returned for
    # UPDATE/DELETE) but not declared in the parent generic — see SQLAlchemy
    # typing stubs. Read via getattr to satisfy strict mypy.
    if getattr(upd, "rowcount", 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session"
        )
    return sess
```

교체:
```python
    # last_seen_at은 디바운스 캐시(app.last_seen_cache)에 메모리 stamp만 한다.
    # 60s 단위로 백그라운드 flusher가 DB UPDATE. SELECT 직후 다른 코루틴이
    # 세션을 삭제했을 race는 다음 요청의 SELECT가 401로 처리한다.
    last_seen_cache.stamp(sess.id)
    return sess
```

상단 import 추가 (`from sqlalchemy import update as _sa_update` 라인 근처):

```python
from app import last_seen_cache
```

미사용이 된 import 정리:
- `import datetime as dt` — 함수 본문에서 dt 사용처 없으면 제거.
- `from sqlalchemy import update as _sa_update` — 다른 함수에서 안 쓰면 제거.

```bash
grep -n "dt\.\|_sa_update" backend/app/deps.py
```

미사용 import 제거.

- [ ] **Step 3: ruff·mypy**

```bash
cd backend
ruff check app/deps.py
mypy app/deps.py
```

Expected. 무에러.

- [ ] **Step 4: 기존 deps 관련 테스트 통과 확인**

```bash
pytest tests/api/ -v -k "session or auth" 2>&1 | tail -20
```

Expected. 기존 테스트들이 그대로 통과. 일부 `rowcount==0` 기반 401 단언이 있으면 그것만 갱신 필요(다음 Step에서).

- [ ] **Step 5: rowcount 기반 단언이 있으면 spec 변경에 맞게 갱신**

`rowcount==0`이 새 흐름에서 더 이상 401을 일으키지 않으므로 — 만약 테스트가 "삭제된 세션 토큰으로 요청 → 401"을 가정하고 그게 한 요청 안의 race를 의도한 것이라면 그대로 통과 (SELECT가 not found라 invalid_session). 따로 갱신 필요 없을 가능성 높음.

만약 실패 테스트가 나오면 해당 케이스를 다음과 같이 갱신:

```python
# (예시 — 실제 실패 테스트가 있을 경우 그 위치에 맞춰)
# 옛: race에서 401 기대 → 새 흐름은 SELECT가 먼저 실패하므로 그대로 401
# 따로 수정 없음. 만약 race window 정밀 테스트가 있다면 그 단언 제거.
```

- [ ] **Step 6: 커밋**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/last-seen-debounce
git add backend/app/deps.py
git commit -m "$(cat <<'EOF'
feat(db): deps.get_current_session에서 last_seen_at을 cache로 디바운스

매 요청 인라인 UPDATE 제거. last_seen_cache.stamp(sess.id) 한 줄.
rowcount==0 기반 401 분기는 제거 (race window는 다음 요청의 SELECT가 처리).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `ws.py` — WS 인증 경로를 stamp로 교체

**Files:**
- Modify: `backend/app/api/ws.py` (L108–L126 부근)

- [ ] **Step 1: 현재 상태 확인**

```bash
sed -n '105,130p' backend/app/api/ws.py
```

- [ ] **Step 2: `_authenticate_ws` 교체**

기존:
```python
async def _authenticate_ws(token: str | None, db: AsyncSession) -> Session | None:
    if not token:
        return None
    res = await db.execute(select(Session).where(Session.token == token))
    sess = res.scalar_one_or_none()
    if sess is None:
        return None
    # Direct UPDATE so a concurrent DELETE (logout, idle purge) doesn't
    # trigger SQLAlchemy's optimistic-lock StaleDataError.
    upd = await db.execute(
        _sa_update(Session)
        .where(Session.id == sess.id)
        .values(last_seen_at=dt.datetime.now(dt.UTC))
    )
    await db.commit()
    if getattr(upd, "rowcount", 0) == 0:
        return None
    return sess
```

교체:
```python
async def _authenticate_ws(token: str | None, db: AsyncSession) -> Session | None:
    if not token:
        return None
    res = await db.execute(select(Session).where(Session.token == token))
    sess = res.scalar_one_or_none()
    if sess is None:
        return None
    # last_seen_at은 디바운스 캐시(app.last_seen_cache)에 stamp만. DB 무접촉.
    last_seen_cache.stamp(sess.id)
    return sess
```

상단 import 추가:
```python
from app import last_seen_cache
```

미사용 import 정리 — 본 파일에서 `_sa_update`·`dt`가 다른 곳에서 안 쓰면 제거. 확인:

```bash
grep -n "_sa_update\|dt\." backend/app/api/ws.py
```

- [ ] **Step 3: ruff·mypy**

```bash
ruff check app/api/ws.py
mypy app/api/ws.py
```

Expected. 무에러.

- [ ] **Step 4: WS 관련 테스트**

```bash
pytest tests/api/test_ws.py -v 2>&1 | tail -10
```

Expected. 통과.

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/ws.py
git commit -m "feat(db): _authenticate_ws에서 last_seen_at을 cache로 디바운스

deps.py와 동일 패턴. WS 연결마다 UPDATE 대신 stamp().

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: lifespan — flusher 시작·종료 통합

**Files:**
- Modify: `backend/app/main.py` (lifespan 함수)

- [ ] **Step 1: 현재 lifespan 확인**

```bash
sed -n '20,55p' backend/app/main.py
```

`enable_wal`, engine pool start, `run_purge_loop` task 등이 이미 있는 패턴.

- [ ] **Step 2: lifespan에 flusher 통합**

`async def lifespan` 본문에서 `await enable_wal()` 다음과 `yield` 사이에 추가:

```python
    # last_seen_at 디바운스 캐시의 백그라운드 flusher 시작.
    from app.db import AsyncSessionLocal
    from app import last_seen_cache
    last_seen_cache.start_flusher(AsyncSessionLocal)
```

그리고 `yield` 다음 (즉 shutdown handler 영역)에 추가:

```python
    # 셧다운. cache 잔여를 모두 DB로 flush한 뒤 task 정지.
    try:
        await last_seen_cache.flush_all(AsyncSessionLocal)
    finally:
        await last_seen_cache.stop_flusher()
```

> shutdown handler 구조가 try/finally 또는 다른 정리 순서면 그 패턴에 맞춰 끼워 넣는다. 기존 `purge_task.cancel()` 직후가 자연스러움.

- [ ] **Step 3: 부팅 통합 확인**

backend 가동:

```bash
cd backend
source .venv311/bin/activate
KATAGO_MOCK=true uvicorn app.main:app --port 18000 &
sleep 5
curl -s http://localhost:18000/api/health
```

Expected. `{"status":"ok",...}`. structlog에 flusher 시작 로그가 있으면 더 좋음(없어도 OK).

```bash
kill %1
```

- [ ] **Step 4: 커밋**

```bash
git add backend/app/main.py
git commit -m "feat(db): lifespan에 last_seen_cache flusher 시작·종료 통합

startup. start_flusher(AsyncSessionLocal).
shutdown. flush_all + stop_flusher.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `session_purge` — cutoff SELECT 전 강제 flush

**Files:**
- Modify: `backend/app/session_purge.py`

- [ ] **Step 1: 현재 함수 확인**

```bash
sed -n '20,50p' backend/app/session_purge.py
```

`purge_expired_sessions_once(ttl_sec)`의 첫 라인에 추가.

- [ ] **Step 2: flush_all 호출 추가**

```python
async def purge_expired_sessions_once(ttl_sec: int) -> int:
    # cache 잔여를 DB로 먼저 흘려 보낸다 — 그래야 cutoff 판정이 정확하다.
    from app import last_seen_cache
    await last_seen_cache.flush_all(_db_module.AsyncSessionLocal)

    cutoff = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=ttl_sec)
    async with _db_module.AsyncSessionLocal() as db:
        ...  # 이하 기존 그대로
```

- [ ] **Step 3: 통합 테스트 추가**

`backend/tests/test_last_seen_cache.py` 끝에 추가:

```python
@pytest.mark.asyncio
async def test_session_purge_sees_fresh_value(db_engine, monkeypatch):
    # purge가 cache의 최신 stamp 후 DB를 보고 정확하게 살릴 세션을 살리는지.
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    from app import db as db_module
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    db_module.AsyncSessionLocal = factory  # type: ignore[assignment]

    base = dt.datetime(2026, 5, 25, 10, 0, 0, tzinfo=dt.UTC)
    async with factory() as s:
        row = Session(
            token="qa-fresh",
            nickname="qa-fresh",
            nickname_key="qa-fresh",
            created_at=base,
            last_seen_at=base,  # 1h 묵음 — purge 후보
        )
        s.add(row)
        await s.commit()
        await s.refresh(row)
        sid = row.id

    # 활발히 활동 중인 척: cache에 최신 stamp.
    fresh = dt.datetime(2026, 5, 25, 11, 0, 30, tzinfo=dt.UTC)
    lsc.stamp(sid, when=fresh)

    # 시계는 fresh 직후. ttl=3600s → cutoff = fresh - 3600 = 10:00:30.
    # DB의 last_seen_at(=base=10:00:00)은 cutoff보다 작아 purge 대상이지만,
    # flush_all 후엔 last_seen_at=fresh로 갱신되어 cutoff보다 커서 살아남아야 한다.

    from app.session_purge import purge_expired_sessions_once
    # 시계 주입을 위해 dt.datetime.now를 monkeypatch
    import app.session_purge as sp
    monkeypatch.setattr(
        sp.dt, "datetime",
        type("DT", (), {"now": staticmethod(lambda tz=None: fresh)})
    )

    n_purged = await purge_expired_sessions_once(ttl_sec=3600)
    assert n_purged == 0  # cache 덕분에 살아남음

    async with factory() as s:
        from sqlalchemy import select
        res = await s.execute(select(Session.last_seen_at).where(Session.id == sid))
        db_val = res.scalar_one_or_none()
    assert db_val == fresh
```

> 주의 — `monkeypatch.setattr(sp.dt, "datetime", ...)`이 다른 dt 사용을 깰 수 있다. 더 안전한 방법은 `purge_expired_sessions_once`가 `now` 인자를 옵셔널로 받게 시그니처를 살짝 확장하는 것. 본 plan에서는 그 path를 함께 적용:
>
> ```python
> async def purge_expired_sessions_once(ttl_sec: int, *, now: dt.datetime | None = None) -> int:
>     ...
>     await last_seen_cache.flush_all(_db_module.AsyncSessionLocal)
>     n = now or dt.datetime.now(dt.UTC)
>     cutoff = n - dt.timedelta(seconds=ttl_sec)
>     ...
> ```
>
> 테스트는 `now=fresh` 인자로 호출. monkeypatch 불필요.

위 메모대로 적용. 테스트 내 monkeypatch 줄을 빼고 `await purge_expired_sessions_once(ttl_sec=3600, now=fresh)`로.

- [ ] **Step 4: 테스트 실행**

```bash
pytest tests/test_last_seen_cache.py::test_session_purge_sees_fresh_value -v
```

Expected. `1 passed`.

- [ ] **Step 5: ruff·mypy + 전체 단위 테스트**

```bash
ruff check app/session_purge.py
mypy app/session_purge.py
pytest tests/test_last_seen_cache.py -v
```

Expected. 모두 통과 (총 9 tests).

- [ ] **Step 6: 커밋**

```bash
git add backend/app/session_purge.py backend/tests/test_last_seen_cache.py
git commit -m "$(cat <<'EOF'
feat(db): session_purge가 cutoff SELECT 전 last_seen_cache.flush_all 호출

활성 세션이 cache 덕분에 잘못 purge되지 않도록. purge 함수에
선택적 now 인자도 추가해 테스트가 시계를 주입할 수 있게 한다.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 전수 검증 (백엔드 단위·통합·lint·type)

**Files:** (변경 없음 — 검증만)

- [ ] **Step 1: 백엔드 전체 테스트 + coverage**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/last-seen-debounce/backend
source .venv311/bin/activate
pytest --cov=app --cov-fail-under=80 -q 2>&1 | tail -15
```

Expected. 모든 기존 + 신규 테스트 통과. coverage ≥ 80%.

- [ ] **Step 2: last_seen_cache 단독 coverage**

```bash
pytest tests/test_last_seen_cache.py --cov=app.last_seen_cache --cov-report=term-missing 2>&1 | tail -10
```

Expected. `app/last_seen_cache.py` 커버 ≥ 95%.

- [ ] **Step 3: ruff·mypy 전체**

```bash
ruff check .
mypy app
```

Expected. 무에러.

- [ ] **Step 4: 로컬 부팅·smoke**

```bash
KATAGO_MOCK=true uvicorn app.main:app --port 18000 &
sleep 5
# 같은 토큰으로 빠른 연속 요청 100회
for i in $(seq 1 100); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:18000/api/health; done | sort | uniq -c
kill %1
```

Expected. `100 200`. (실제 sessions UPDATE 빈도는 별도 sqlite3 확인 가능 — 본 검증은 안정성 위주).

> 더 정밀한 검증을 원하면 별도 fixture 세션을 만들고 인증된 요청을 100회 보낸 뒤 `select count(*) from sessions where ...` 또는 structlog 로그로 flush 빈도 측정.

---

## Task 9: PR 생성

**Files:** (변경 없음)

- [ ] **Step 1: 브랜치 푸시**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/last-seen-debounce
git push -u origin feat/last-seen-at-debounce
```

- [ ] **Step 2: PR 생성**

```bash
gh pr create --base main --head feat/last-seen-at-debounce \
  --title "feat(db): last_seen_at 매 요청 UPDATE를 60s 디바운스 캐시로 대체" \
  --body "$(cat <<'EOF'
## Summary
PR #25(busy_timeout) 후속. \`sessions.last_seen_at\` UPDATE를 메모리 디바운스 캐시로 대체해 hot row 압박 자체를 완화한다.

## 핵심
- \`backend/app/last_seen_cache.py\` 신규 — \`stamp\` / \`flush_due\` / \`flush_all\` / \`start_flusher\` / \`stop_flusher\`.
- \`backend/app/deps.py\`·\`backend/app/api/ws.py\` — 인라인 UPDATE → \`stamp(sess.id)\` 한 줄. \`rowcount==0 → 401\` 분기 제거 (race window는 다음 요청 SELECT가 처리).
- \`backend/app/main.py\` lifespan — startup에 \`start_flusher\`, shutdown에 \`flush_all + stop_flusher\`.
- \`backend/app/session_purge.py\` — cutoff SELECT 전 \`flush_all\` 호출. 옵셔널 \`now\` 인자로 테스트 시계 주입.

## 파라미터
- flush interval. 60s (활성 세션의 DB 반영 최대 간격)
- loop tick. 30s (인터벌의 절반)
- 크래시 시 소실 최대 60s — 1h idle TTL 대비 1.7%

## 검증
- 신규 \`backend/tests/test_last_seen_cache.py\` 9개 테스트 통과
- backend pytest 전체 통과, coverage ≥ 80%
- last_seen_cache 자체 coverage ≥ 95%
- ruff·mypy 무에러

## 후속 (별도)
머지 후 prod 재배포 — \`launchctl kickstart -k gui/\$(id -u)/com.baduk.api\`. 24h 후 \`baduk-api.err\`에 신규 \`database is locked\` 0건 + sessions UPDATE 빈도 측정 권장.

설계 spec. \`docs/superpowers/specs/2026-05-25-last-seen-at-debounce-design.md\`
구현 계획. \`docs/superpowers/plans/2026-05-25-last-seen-at-debounce.md\`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

PR URL 출력 후 종료. 본 plan은 여기까지.

- [ ] **Step 3: 워크트리 정리 안내**

PR 머지 후:

```bash
cd /Users/daegong/projects/baduk
git worktree remove .claude/worktrees/last-seen-debounce
git branch -d feat/last-seen-at-debounce
```

---

## 자체 점검 (Self-Review)

**Spec coverage.**
- spec § 1 아키텍처 → Task 1–7
- spec § 2 모듈 API (stamp/flush_due/flush_all/start/stop/_reset_for_tests) → Task 1, 2, 3 ✓
- spec § 3 데이터 흐름 (hot path/background/purge/shutdown) → Task 4, 6, 7 ✓
- spec § 4 에러 처리 → Task 3 step 3 (`_flusher_loop`의 try/except) + Task 2 step 3 (orphan rowcount=0) ✓
- spec § 5 테스트 8건 → Task 1·2·3·7에서 9건 작성 (overlap 살짝, 더 많이 커버) ✓
- spec § 6 검증 기준 → Task 8 ✓
- spec § 7 위험 — 메모리·다중 worker는 본 plan에서 코드 변경 없음 (수용). 테스트 격리는 `_reset_for_tests` + autouse fixture ✓

**Placeholder scan.**
- TBD/TODO 없음. ✓
- Task 4 step 5 "rowcount 기반 단언이 있으면 갱신" 조건부 안내 — `grep`으로 발견 시만 적용. 충분히 구체.
- Task 6 step 2 "기존 try/finally 패턴이 있으면 그 패턴에 맞춰 끼워 넣는다" — 패턴 미상이라 그렇게 안내. 구현자가 보고 결정.

**Type 일관성.** `stamp` / `flush_due` / `flush_all` / `start_flusher` / `stop_flusher` 시그니처가 모든 Task에서 일관. `_cache: dict[int, tuple[datetime, datetime]]` 동일. ✓

자체 점검 통과 — plan 실행 준비.
