"""Dependency injection helpers."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db as _db_module
from app import last_seen_cache
from app.models import Session

COOKIE_SESSION = "baduk_session"


def bearer_token(authorization: str | None) -> str | None:
    """Authorization 헤더에서 Bearer 토큰을 추출한다. 형식이 다르면 None.

    RFC 7235에 따라 스킴 이름은 대소문자 무관("bearer"/"BEARER" 허용).
    """
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip() or None
    return None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _db_module.AsyncSessionLocal() as s:
        yield s


# Type alias used by every endpoint that needs a DB session — keeps signatures
# short and satisfies ruff B008 (no Depends() in default-argument position).
DbSession = Annotated[AsyncSession, Depends(get_db)]


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
