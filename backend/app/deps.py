"""Dependency injection helpers."""
from __future__ import annotations

import datetime as dt
from typing import AsyncGenerator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db as _db_module
from app.models import Session

COOKIE_SESSION = "baduk_session"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _db_module.AsyncSessionLocal() as s:
        yield s


async def get_current_session(
    baduk_session: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Session:
    """Resolve the current session from the cookie, bumping ``last_seen_at``.

    Raises 401 if the cookie is missing or refers to a session that has been
    deleted (e.g. idle-purged).
    """
    if not baduk_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="no_session"
        )
    result = await db.execute(select(Session).where(Session.token == baduk_session))
    sess = result.scalar_one_or_none()
    if sess is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session"
        )
    sess.last_seen_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
    return sess
