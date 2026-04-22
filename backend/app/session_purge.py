"""Background purge loop for idle sessions.

Deletes ``sessions`` rows whose ``last_seen_at`` is older than
``ttl_sec``. CASCADE removes all owned games / moves / analyses.
Also releases the nickname from the in-memory registry so it is
immediately reusable.
"""
from __future__ import annotations

import asyncio
import datetime as dt

import structlog
from sqlalchemy import select

import app.db as _db_module
from app.models import Session
from app.session_registry import registry

log = structlog.get_logger()


async def purge_expired_sessions_once(ttl_sec: int) -> int:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=ttl_sec)
    async with _db_module.AsyncSessionLocal() as db:
        res = await db.execute(select(Session).where(Session.last_seen_at < cutoff))
        expired = res.scalars().all()
        for s in expired:
            await db.delete(s)
            await registry.release(s.nickname_key)
        await db.commit()
    return len(expired)


async def run_purge_loop(*, interval_sec: int, ttl_sec: int) -> None:
    while True:
        try:
            await asyncio.sleep(interval_sec)
            n = await purge_expired_sessions_once(ttl_sec)
            if n:
                log.info("session_purge", removed=n, ttl_sec=ttl_sec)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            log.exception("session_purge_failed")
