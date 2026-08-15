"""Nickname-only session endpoints.

Replaces the former /api/auth/* namespace. No signup, no password, no
OAuth — a browser session is a row in ``sessions`` identified by an
HttpOnly session cookie with a 90-day Max-Age. The cookie is re-issued
on every ``GET /api/session`` and the server bumps ``last_seen_at`` on
every request, so the 90 days slide forward as long as the visitor keeps
coming back.

Nicknames are not unique: any number of sessions may share one, except
for the reserved admin keys (see ``app.deps.ADMIN_NICKNAME_KEYS``).
"""
from __future__ import annotations

import datetime as _dt
import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Header, HTTPException, Request, Response, status
from sqlalchemy import delete as _sa_delete
from sqlalchemy import select
from sqlalchemy import update as _sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_ip import client_country as _client_country
from app.client_ip import client_ip as _client_key
from app.config import settings
from app.core.nickname import InvalidNickname, normalize, to_key, validate
from app.deps import (
    ADMIN_NICKNAME_KEYS,
    COOKIE_SESSION,
    CurrentSession,
    DbSession,
    bearer_token,
)
from app.models import Session
from app.rate_limit import rate_limiter
from app.schemas.session import NicknameAvailability, SessionCreateRequest, SessionPublic

router = APIRouter(prefix="/api/session", tags=["session"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_SESSION,
        token,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        path="/",
        max_age=settings.session_ttl_sec,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE_SESSION,
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


def _parse_nickname(raw: str) -> tuple[str, str]:
    """Return (display, key) or raise :class:`InvalidNickname`."""
    display = normalize(raw)
    validate(display)
    return display, to_key(display)


async def _reserved_key_taken(db: AsyncSession, key: str) -> bool:
    """어드민 예약 닉네임 키를 쓰는 라이브 세션이 있는지 DB로 확인한다.

    어드민 게이트(``app.deps.is_admin``)가 닉네임 키 하나에 걸려 있으므로
    선점 상태는 프로세스 재시작을 견뎌야 한다. 따라서 in-memory 구조가
    아니라 ``sessions`` 테이블을 직접 조회한다. 동시 2요청 레이스는 수용
    범위다 — 실질 위협은 재시작 후 사칭 선점이다.
    """
    if key not in ADMIN_NICKNAME_KEYS:
        return False
    res = await db.execute(select(Session.id).where(Session.nickname_key == key))
    return res.first() is not None


@router.post("", response_model=SessionPublic, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreateRequest,
    request: Request,
    response: Response,
    db: DbSession,
) -> SessionPublic:
    if not await rate_limiter.check(
        f"session_create:{_client_key(request)}", max_hits=5, window_sec=60
    ):
        raise HTTPException(status_code=429, detail="rate_limited")
    try:
        display, key = _parse_nickname(body.nickname)
    except InvalidNickname as e:
        raise HTTPException(status_code=422, detail="invalid_nickname") from e

    # 일반 닉네임은 중복 허용 — 같은 이름으로 여러 세션이 공존한다.
    # 어드민 예약 키만 선점을 막는다.
    if await _reserved_key_taken(db, key):
        raise HTTPException(status_code=409, detail="nickname_taken")

    token = secrets.token_urlsafe(32)
    sess = Session(
        token=token,
        nickname=display,
        nickname_key=key,
        country=_client_country(request),
    )
    db.add(sess)
    await db.commit()
    await db.refresh(sess)

    # Append an audit log row so the admin console can see historical
    # logins even after the session itself is deleted.
    from app.models import SessionHistory
    db.add(SessionHistory(
        session_id=sess.id, nickname=display, nickname_key=key,
    ))
    await db.commit()

    _set_session_cookie(response, token)
    return SessionPublic(id=sess.id, nickname=sess.nickname, token=token)


@router.get("", response_model=SessionPublic)
async def read_session(sess: CurrentSession, response: Response) -> SessionPublic:
    # 방문할 때마다 쿠키를 재발급해 Max-Age 90일을 앞으로 민다 (슬라이딩 만료).
    # 서버 측 슬라이딩은 last_seen_at 갱신이 담당한다.
    _set_session_cookie(response, sess.token)
    return SessionPublic(id=sess.id, nickname=sess.nickname)


@router.post("/end", status_code=204)
async def end_session(
    response: Response,
    db: DbSession,
    baduk_session: Annotated[str | None, Cookie(alias=COOKIE_SESSION)] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """Idempotent logout. Browsers fire this twice (explicit logout +
    pagehide beacon, React StrictMode dev double-effect, mobile Safari's
    duplicate unload), so missing/already-deleted sessions must succeed
    rather than 500 on a stale-row race or 401 on the second attempt."""
    response.status_code = 204
    token_value = baduk_session or bearer_token(authorization)
    if not token_value:
        _clear_session_cookie(response)
        return response
    res = await db.execute(select(Session).where(Session.token == token_value))
    sess = res.scalar_one_or_none()
    if sess is None:
        _clear_session_cookie(response)
        return response
    # Mark the audit row as ended before deleting the session so we don't
    # lose the link via session_id.
    from app.models import SessionHistory
    await db.execute(
        _sa_update(SessionHistory)
        .where(
            SessionHistory.session_id == sess.id,
            SessionHistory.ended_at.is_(None),
        )
        .values(ended_at=_dt.datetime.utcnow(), end_reason="logout")
    )
    await db.execute(_sa_delete(Session).where(Session.id == sess.id))
    await db.commit()
    _clear_session_cookie(response)
    return response


@router.get("/nickname/check", response_model=NicknameAvailability)
async def check_nickname(
    name: str,
    request: Request,
    db: DbSession,
) -> NicknameAvailability:
    if not await rate_limiter.check(
        f"nickname_check:{_client_key(request)}", max_hits=30, window_sec=60
    ):
        raise HTTPException(status_code=429, detail="rate_limited")
    try:
        _display, key = _parse_nickname(name)
    except InvalidNickname:
        return NicknameAvailability(available=False, reason="invalid")

    # 일반 닉네임은 중복 가능하므로 형식만 통과하면 항상 사용 가능하다.
    # 어드민 예약 키만 라이브 세션 점유 여부를 본다.
    if await _reserved_key_taken(db, key):
        return NicknameAvailability(available=False, reason="taken")
    return NicknameAvailability(available=True)
