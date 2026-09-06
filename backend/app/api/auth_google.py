"""구글 간편 계정 연동(옵트인).

닉네임 세션은 그대로 로그인의 단위다. 구글은 "이 세션(과 그 대국들)을 내
계정에 묶어 두고, 다른 기기·만료 뒤에도 이어 보기" 위한 열쇠일 뿐이다.

흐름
  GET  /api/auth/google/start?next=/settings  → state 쿠키 심고 구글로 302
  GET  /api/auth/google/callback?code&state    → 코드 교환 → userinfo(sub,email)
      · 세션 쿠키가 있으면: 그 세션과 세션의 대국들을 계정에 연동
      · 없으면: 계정 이름으로 새 세션을 만들어 쿠키 발급 (새 기기에서 이어하기)
  POST /api/auth/google/unlink                 → 이 세션의 연동만 해제
  GET  /api/auth/providers                     → {"google": bool} (기능 on/off)

id_token 서명 검증 대신 토큰 엔드포인트에서 받은 access_token으로 구글
userinfo를 서버 간 TLS로 조회한다 — 검증할 JWT 라이브러리 없이도 안전하다.
"""
from __future__ import annotations

import base64
import datetime as _dt
import secrets
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
import structlog
from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy import update as _sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session import _parse_nickname, _set_session_cookie
from app.client_ip import client_country as _client_country
from app.client_ip import client_ip as _client_key
from app.config import settings
from app.core.nickname import InvalidNickname
from app.deps import COOKIE_SESSION, CurrentSession, DbSession
from app.models import Account, Game, Session, SessionHistory
from app.rate_limit import rate_limiter

log = structlog.get_logger()
router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105 (URL, not a secret)
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
COOKIE_STATE = "baduk_oauth_state"
STATE_TTL_SEC = 600


def _safe_next(raw: str | None) -> str:
    """오픈 리다이렉트 방지 — 사이트 내부 경로만 허용한다."""
    if raw and raw.startswith("/") and not raw.startswith("//") and "\\" not in raw:
        return raw
    return "/settings"


def _encode_next(path: str) -> str:
    """쿠키 값에 못 들어가는 '/'를 피하려고 base64url로 감싼다."""
    return base64.urlsafe_b64encode(path.encode()).decode().rstrip("=")


def _decode_next(raw: str) -> str:
    try:
        padded = raw + "=" * (-len(raw) % 4)
        return _safe_next(base64.urlsafe_b64decode(padded).decode())
    except (ValueError, UnicodeDecodeError):
        return "/settings"


def _finish_url(next_path: str, **params: str) -> str:
    base = settings.public_base_url.rstrip("/")
    sep = "&" if "?" in next_path else "?"
    return f"{base}{next_path}{sep}{urlencode(params)}"


async def exchange_code(code: str) -> dict[str, Any]:
    """authorization code → 토큰 응답(JSON). 테스트에서 monkeypatch 한다."""
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


async def fetch_userinfo(access_token: str) -> dict[str, Any]:
    """access_token → {sub, email, name, ...}. 테스트에서 monkeypatch 한다."""
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


def _require_enabled() -> None:
    if not settings.google_enabled:
        raise HTTPException(status_code=404, detail="google_login_disabled")


@router.get("/providers")
async def providers() -> dict[str, bool]:
    return {"google": settings.google_enabled}


@router.get("/google/start")
async def google_start(request: Request, next: str | None = None) -> RedirectResponse:  # noqa: A002
    _require_enabled()
    if not await rate_limiter.check(
        f"google_start:{_client_key(request)}", max_hits=10, window_sec=60
    ):
        raise HTTPException(status_code=429, detail="rate_limited")
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    resp = RedirectResponse(
        f"{GOOGLE_AUTH_URL}?{urlencode(params)}", status_code=status.HTTP_302_FOUND
    )
    # state와 돌아갈 경로를 짧은 수명의 HttpOnly 쿠키에 둔다. Lax라 구글에서
    # 돌아오는 최상위 GET 내비게이션에도 실려 온다.
    resp.set_cookie(
        COOKIE_STATE,
        f"{state}|{_encode_next(_safe_next(next))}",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/api/auth/google",
        max_age=STATE_TTL_SEC,
    )
    return resp


async def _upsert_account(db: AsyncSession, info: dict[str, Any]) -> Account:
    sub = str(info.get("sub") or "")
    if not sub:
        raise HTTPException(status_code=502, detail="google_no_sub")
    acc = (
        await db.execute(
            select(Account).where(Account.provider == "google", Account.provider_sub == sub)
        )
    ).scalar_one_or_none()
    email = info.get("email") if info.get("email_verified", True) else None
    name = info.get("name") or info.get("given_name")
    if acc is None:
        acc = Account(
            provider="google",
            provider_sub=sub,
            email=email,
            display_name=str(name)[:64] if name else None,
        )
        db.add(acc)
    else:
        if email:
            acc.email = email
        if name:
            acc.display_name = str(name)[:64]
        acc.last_login_at = _dt.datetime.utcnow()
    await db.flush()
    return acc


def _nickname_for(acc: Account) -> tuple[str, str]:
    """계정 정보로 새 세션 닉네임을 만든다. 규칙에 안 맞으면 폴백."""
    candidates = [acc.display_name, (acc.email or "").split("@")[0], "Player"]
    for cand in candidates:
        if not cand:
            continue
        try:
            return _parse_nickname(cand[: settings.nickname_max_len])
        except InvalidNickname:
            continue
    return _parse_nickname("Player")


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    baduk_oauth_state: Annotated[str | None, Cookie(alias=COOKIE_STATE)] = None,
    baduk_session: Annotated[str | None, Cookie(alias=COOKIE_SESSION)] = None,
) -> Response:
    _require_enabled()
    expected, _, next_raw = (baduk_oauth_state or "").partition("|")
    next_path = _decode_next(next_raw)

    def fail(reason: str) -> Response:
        log.warning("google_login.failed", reason=reason)
        resp = RedirectResponse(_finish_url(next_path, link_error=reason), status_code=302)
        resp.delete_cookie(COOKIE_STATE, path="/api/auth/google")
        return resp

    if error:
        return fail("denied")
    if not code or not state or not expected or not secrets.compare_digest(state, expected):
        return fail("state")
    try:
        token = await exchange_code(code)
        access_token = str(token.get("access_token") or "")
        if not access_token:
            return fail("token")
        info = await fetch_userinfo(access_token)
    except (httpx.HTTPError, ValueError):
        return fail("exchange")

    acc = await _upsert_account(db, info)

    sess: Session | None = None
    if baduk_session:
        sess = (
            await db.execute(select(Session).where(Session.token == baduk_session))
        ).scalar_one_or_none()

    resp = RedirectResponse(_finish_url(next_path, linked="1"), status_code=302)
    if sess is not None:
        # 기존 세션 연동 + 이 세션이 만든 대국들을 계정에 귀속.
        sess.account_id = acc.id
        await db.execute(
            _sa_update(Game)
            .where(Game.session_id == sess.id, Game.account_id.is_(None))
            .values(account_id=acc.id)
        )
    else:
        # 새 기기에서 이어하기 — 계정 이름으로 세션을 새로 만든다.
        display, key = _nickname_for(acc)
        sess = Session(
            token=secrets.token_urlsafe(32),
            nickname=display,
            nickname_key=key,
            country=_client_country(request),
            account_id=acc.id,
        )
        db.add(sess)
        await db.flush()
        db.add(SessionHistory(session_id=sess.id, nickname=display, nickname_key=key))
        _set_session_cookie(resp, sess.token)
    await db.commit()
    resp.delete_cookie(COOKIE_STATE, path="/api/auth/google")
    log.info("google_login.linked", session_id=sess.id, account_id=acc.id)
    return resp


@router.post("/google/unlink", status_code=204)
async def google_unlink(sess: CurrentSession, db: DbSession) -> Response:
    """이 세션의 연동만 푼다. 이미 계정에 귀속된 대국은 그대로 남아,
    나중에 같은 계정으로 다시 연동하면 다시 보인다."""
    sess.account_id = None
    await db.commit()
    return Response(status_code=204)
