# `sessions.last_seen_at` 디바운스 캐시 설계 (2026-05-25)

## 배경

PR #25(`d469164`)에서 SQLite `PRAGMA busy_timeout=5000`을 추가해 `database is locked` 발생 시 5초 대기로 흡수했다. 이는 **증상**을 막지만 **근본 원인**(`sessions.last_seen_at` UPDATE의 hot row 압박)은 그대로다.

`last_seen_at`은 인증된 매 REST 요청과 매 WS 연결마다 bump된다(`app/deps.py:46-58`, `app/api/ws.py:118-123`). 한 사용자가 폴링·다중 탭으로 동시 요청 burst를 일으키면 동일 `sessions.id` 행에 동시 UPDATE 다수가 발사되고, busy_timeout으로 직렬화되지만 그 자체로 latency·CPU 낭비다.

본 spec은 매 요청 UPDATE를 메모리 캐시로 디바운스해 DB 쓰기를 **이론적 95%+ 감소** 시킨다.

## 목표

- 동일 세션에 대한 `last_seen_at` DB UPDATE 빈도를 **60초당 최대 1회**로 제한.
- 매 요청·매 WS 연결의 hot path에서 DB 무접촉(메모리 쓰기만).
- session_purge·shutdown과 정합 — cache가 stale write를 막지 않음.
- prod 동작 변경 없음 — 사용자에게 보이는 거동(401 invalid_session, 1h idle 자동 로그아웃)은 동등.

## 비목표 (YAGNI)

- 다중 uvicorn worker 지원(prod는 `--workers 1`). 워커당 별도 cache로 부분 일관성은 수용.
- Redis·메모리 외부 store. 단일 노드에 작은 dict면 충분.
- `last_seen_at` 외 다른 필드 디바운스. 다른 hot row 없음.
- batched UPDATE 1회로 묶기(`CASE WHEN ... END`). SQLite 단일 writer 모델에서 미미한 이득.

## 결정된 파라미터

- **flush 윈도우**: 60초 (활성 세션이 DB에 반영되는 최대 간격, 프로세스 크래시 손실 한계).
- **flusher loop tick**: 30초 (60초의 절반 — 노이즈 마진).
- **session_purge 협조**: purge SELECT 직전 `flush_all` 강제 호출(정확한 cutoff 판정).
- **`rowcount==0` 분기 제거**: SELECT 직후 race window는 무시. 다음 요청의 SELECT가 401 처리.

## 아키텍처

### 작업 단위

**신규.**
- `backend/app/last_seen_cache.py` — 단일 책임 모듈 (stamp / flush / lifecycle).
- `backend/tests/test_last_seen_cache.py` — 단위 + 통합 테스트.

**수정.**
- `backend/app/deps.py:46-58` — 인라인 UPDATE → `last_seen_cache.stamp(sess.id)` 한 줄. `rowcount==0` 분기 제거.
- `backend/app/api/ws.py:118-123` — 동일.
- `backend/app/main.py:25-` — lifespan에 `start_flusher(AsyncSessionLocal)` 추가, shutdown handler에서 `flush_all` + `stop_flusher`.
- `backend/app/session_purge.py:24-` — `purge_expired_sessions_once` 진입에 `await flush_all(_db_module.AsyncSessionLocal)` 추가.

### 모듈 API

```python
# backend/app/last_seen_cache.py
# sessions.last_seen_at 쓰기 디바운스 — 매 요청 UPDATE 대신 메모리 캐시 후 60s 단위 flush.

import asyncio
import datetime as dt
import structlog
from sqlalchemy import update as _sa_update
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.models import Session

_FLUSH_INTERVAL_SEC = 60.0
_LOOP_TICK_SEC = 30.0
_EPOCH = dt.datetime.min.replace(tzinfo=dt.UTC)
_cache: dict[int, tuple[dt.datetime, dt.datetime]] = {}
_lock = asyncio.Lock()
_task: asyncio.Task | None = None
log = structlog.get_logger()

def stamp(session_id: int, when: dt.datetime | None = None) -> None:
    """매 요청에서 호출. 메모리 dict만 갱신. DB 무접촉."""
    now = when or dt.datetime.now(dt.UTC)
    flushed = _cache.get(session_id, (None, _EPOCH))[1]
    _cache[session_id] = (now, flushed)

async def flush_due(factory: async_sessionmaker, *, force: bool = False,
                    now: dt.datetime | None = None) -> int:
    """조건 부합 항목 일괄 UPDATE. force=True면 시간 무관 모두."""
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
                _cache.pop(sid, None)  # orphan 정리
            else:
                _cache[sid] = (seen, n)
                written += 1
        await db.commit()
    return written

async def flush_all(factory: async_sessionmaker) -> int:
    return await flush_due(factory, force=True)

async def _flusher_loop(factory: async_sessionmaker) -> None:
    while True:
        try:
            await flush_due(factory, force=False)
        except Exception as e:
            log.warning("last_seen_cache.flush_failed", error=str(e))
        await asyncio.sleep(_LOOP_TICK_SEC)

def start_flusher(factory: async_sessionmaker) -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_flusher_loop(factory))

async def stop_flusher() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    _task = None

def _reset_for_tests() -> None:
    _cache.clear()
```

### 데이터 흐름

**Hot path** (매 요청).
```
SELECT (cookie token) → sess  [기존 그대로]
stamp(sess.id)                [메모리만; ~µs]
요청 핸들러
```

**Background** (30초 tick).
```
flush_due(force=False) → 60s+ 묵은 항목 UPDATE → flushed_at 갱신
```

**Session purge** (현 5분 tick).
```
flush_all() → cache 비움
SELECT WHERE last_seen_at < cutoff
DELETE 영향받은 sessions
```

**Shutdown** (lifespan exit).
```
flush_all() → 모든 cache → DB
stop_flusher() → task 종료 대기
```

## 에러 처리

- `stamp()` 예외 무. 메모리 쓰기뿐.
- `flush_due()` DB 오류 — structlog warning. cache 미갱신 → 다음 tick 재시도.
- flusher task 크래시 — structlog error. lifespan 재기동 시 `start_flusher` 재호출.
- session 행 부재(`rowcount==0`) — cache pop. 정상 흐름.
- 옛 코드의 `rowcount==0 → 401` 분기 — 본 변경으로 사라짐. SELECT 직후 race window는 무시 (다음 요청에서 401 처리).

## 테스트

`backend/tests/test_last_seen_cache.py`. monkeypatch로 `dt.datetime.now(dt.UTC)` 또는 `when=` 인자 주입해 시계 제어.

1. `test_stamp_sets_cache` — 호출 후 cache에 entry.
2. `test_flush_due_writes_when_aged` — 60s+ entry는 UPDATE + flushed_at 갱신.
3. `test_flush_due_skips_recent` — 60s 미만은 skip.
4. `test_flush_force_writes_all` — force=True면 시간 무관 모두 flush.
5. `test_flush_removes_orphan_entries` — DB 없는 sid는 cache에서 pop.
6. `test_flush_repeated_is_no_op` — `seen <= flushed`이면 skip.
7. **통합** `test_get_current_session_no_per_request_write` — 동일 세션 100회 요청 후 DB UPDATE ≤ 2건.
8. **통합** `test_session_purge_sees_fresh_value` — stamp 후 purge가 즉시 호출되면 stamp 값을 본다.

`autouse` fixture로 매 테스트 후 `_reset_for_tests()` 호출.

## 검증 기준

1. 단위 테스트 8건 모두 PASS, mypy strict 통과.
2. `pytest --cov=app/last_seen_cache --cov-fail-under=95` 통과.
3. 머지 후 prod 재배포, 24h 후 `baduk-api.err`에 신규 `database is locked` 0건.
4. session_purge가 1h idle 세션을 정상 제거 (cache 잔존이 막지 않음).
5. shutdown 후 `last_seen_at`이 cache의 최신 값을 반영.

## 위험·미해결

- **메모리**: 활성 세션 수 × 32 bytes. 1000 세션 ≈ 32KB. 무시.
- **다중 worker**: 본 작업은 `--workers 1` 가정. multi-worker 전환 시 별도 PR(외부 store).
- **테스트 격리**: 모듈 전역 dict leak 가능 → `_reset_for_tests()` fixture로 cleanup.

## 추정

helpers 모듈 30m + 테스트 8건 30m + 3개 호출자 수정 + lifespan 통합 20m + 검증 10m = **약 90분**.
