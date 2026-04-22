"""Ephemeral nickname-only session endpoints.

Replaces the former /api/auth/* namespace. No signup, no password, no
OAuth — a browser session is a row in ``sessions`` identified by an
HttpOnly session cookie with no Max-Age (deleted on browser close).
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete as _sa_delete
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.nickname import InvalidNickname, normalize, to_key, validate
from app.deps import COOKIE_SESSION, get_current_session, get_db
from app.models import Session
from app.rate_limit import rate_limiter
from app.schemas.session import NicknameAvailability, SessionCreateRequest, SessionPublic
from app.session_registry import registry

router = APIRouter(prefix="/api/session", tags=["session"])


def _client_key(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_SESSION,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
        # deliberately no max_age / expires — deleted on browser close
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_SESSION, path="/")


def _parse_nickname(raw: str) -> tuple[str, str]:
    """Return (display, key) or raise :class:`InvalidNickname`."""
    display = normalize(raw)
    validate(display)
    return display, to_key(display)


@router.post("", response_model=SessionPublic, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreateRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> SessionPublic:
    if not await rate_limiter.check(f"session_create:{_client_key(request)}", max_hits=5, window_sec=60):
        raise HTTPException(status_code=429, detail="rate_limited")
    try:
        display, key = _parse_nickname(body.nickname)
    except InvalidNickname:
        raise HTTPException(status_code=422, detail="invalid_nickname")

    # Primary defense — in-memory claim. Use a sentinel session_id, then swap
    # to the real id once the row is inserted.
    SENTINEL = -1
    if not await registry.claim(key, SENTINEL):
        raise HTTPException(status_code=409, detail="nickname_taken")

    try:
        token = secrets.token_urlsafe(32)
        sess = Session(token=token, nickname=display, nickname_key=key)
        db.add(sess)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=409, detail="nickname_taken")
        await db.refresh(sess)
        # Swap sentinel → real session_id
        async with registry._lock:  # noqa: SLF001 (intentional — atomic swap)
            registry._by_key[key] = sess.id  # noqa: SLF001

        _set_session_cookie(response, token)
        return SessionPublic(id=sess.id, nickname=sess.nickname)
    except HTTPException:
        await registry.release(key)
        raise
    except Exception:
        await registry.release(key)
        raise


@router.get("", response_model=SessionPublic)
async def read_session(sess: Session = Depends(get_current_session)) -> SessionPublic:
    return SessionPublic(id=sess.id, nickname=sess.nickname)


@router.post("/end", status_code=204)
async def end_session(
    response: Response,
    sess: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> Response:
    key = sess.nickname_key
    await db.execute(_sa_delete(Session).where(Session.id == sess.id))
    await db.commit()
    await registry.release(key)
    _clear_session_cookie(response)
    response.status_code = 204
    return response


@router.get("/nickname/check", response_model=NicknameAvailability)
async def check_nickname(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> NicknameAvailability:
    if not await rate_limiter.check(f"nickname_check:{_client_key(request)}", max_hits=30, window_sec=60):
        raise HTTPException(status_code=429, detail="rate_limited")
    try:
        _display, key = _parse_nickname(name)
    except InvalidNickname:
        return NicknameAvailability(available=False, reason="invalid")

    if await registry.is_taken(key):
        return NicknameAvailability(available=False, reason="taken")
    # Secondary check against the DB in case an orphan row exists.
    res = await db.execute(select(Session).where(Session.nickname_key == key))
    if res.scalar_one_or_none() is not None:
        return NicknameAvailability(available=False, reason="taken")
    return NicknameAvailability(available=True)
