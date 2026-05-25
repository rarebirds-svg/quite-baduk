# sessions.last_seen_at 쓰기 디바운스 — 매 요청 UPDATE 대신 메모리 캐시 후 60s 단위 flush.
from __future__ import annotations

import asyncio
import datetime as dt
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import update as _sa_update

from app.models import Session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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


async def flush_due(
    factory: async_sessionmaker[AsyncSession],
    *,
    force: bool = False,
    now: dt.datetime | None = None,
) -> int:
    """조건 부합 항목 일괄 UPDATE.

    조건(force=False). seen > flushed AND flushed가 60s+ 전.
    초기 stamp는 flushed=_EPOCH라 다음 flush 사이클에서 즉시 DB로 쓰여진다.
    그 후엔 60s마다 한 번씩만 flush. UPDATE rowcount==0이면 orphan으로
    간주해 cache에서 제거.
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
            entry = _cache.get(sid)
            if rc == 0:
                # Orphan — DB row gone. Only pop if our snapshot is still
                # the current entry; otherwise a concurrent stamp(sid) added
                # a fresh entry (e.g., session re-created with same id) and
                # we must not drop it.
                if entry is not None and entry[0] == seen:
                    _cache.pop(sid, None)
            else:
                # Bump flushed_at only. seen may have advanced during await
                # — leave it as-is so the next stamp/flush cycle picks it up.
                if entry is not None:
                    _cache[sid] = (entry[0], n)
                written += 1
        await db.commit()
    return written


async def flush_all(factory: async_sessionmaker[AsyncSession]) -> int:
    """force=True alias. session_purge·shutdown 진입에서 사용."""
    return await flush_due(factory, force=True)


async def _flusher_loop(factory: async_sessionmaker[AsyncSession]) -> None:
    """30s마다 flush_due(force=False) 호출. 예외는 로깅 후 계속."""
    while True:
        try:
            await flush_due(factory, force=False)
        except Exception as e:  # noqa: BLE001
            log.warning("last_seen_cache.flush_failed", error=str(e), exc_info=True)
        await asyncio.sleep(_LOOP_TICK_SEC)


def start_flusher(factory: async_sessionmaker[AsyncSession]) -> None:
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


def _reset_for_tests() -> None:
    """pytest fixture에서 호출. cache·task 초기화."""
    global _task
    _cache.clear()
    if _task and not _task.done():
        _task.cancel()
    _task = None
