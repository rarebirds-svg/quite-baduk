"""Dependency injection helpers."""
from __future__ import annotations

import datetime as dt
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy import update as _sa_update
from sqlalchemy.ext.asyncio import AsyncSession

import app.db as _db_module
from app.models import Session

COOKIE_SESSION = "baduk_session"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _db_module.AsyncSessionLocal() as s:
        yield s


# Type alias used by every endpoint that needs a DB session — keeps signatures
# short and satisfies ruff B008 (no Depends() in default-argument position).
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_session(
    db: DbSession,
    baduk_session: Annotated[str | None, Cookie()] = None,
) -> Session:
    """Resolve the current session from the cookie, bumping ``last_seen_at``.

    Raises 401 if the cookie is missing or refers to a session that has been
    deleted (e.g. idle-purged or logged out concurrently).
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


# Admin gate: the app has no proper admin auth layer — for the single-operator
# dev use case we gate on a well-known nickname key. The `대공` key is
# case-folded NFKC, matching what `session.nickname_key` stores. Registering
# that nickname first is effectively how you claim admin access.
ADMIN_NICKNAME_KEYS: frozenset[str] = frozenset({"대공", "레어버드"})


def is_admin(sess: Session) -> bool:
    return sess.nickname_key in ADMIN_NICKNAME_KEYS


CurrentSession = Annotated[Session, Depends(get_current_session)]


async def require_admin(sess: CurrentSession) -> Session:
    if not is_admin(sess):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="admin_only"
        )
    return sess


AdminSession = Annotated[Session, Depends(require_admin)]
