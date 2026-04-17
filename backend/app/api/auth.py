from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_current_user, get_db
from app.models import User
from app.rate_limit import rate_limiter
from app.schemas.auth import LoginRequest, SignupRequest, UserPublic
from app.security import create_access_token, create_refresh_token
from app.services.user_service import AuthError, authenticate, create_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_ACCESS = "access_token"
COOKIE_REFRESH = "refresh_token"
ACCESS_COOKIE_MAX_AGE = 60 * 60 * 24  # 24h


def _set_auth_cookies(response: Response, user_id: int) -> None:
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    response.set_cookie(
        COOKIE_ACCESS, access, httponly=True, samesite="lax",
        secure=False, max_age=ACCESS_COOKIE_MAX_AGE, path="/",
    )
    response.set_cookie(
        COOKIE_REFRESH, refresh, httponly=True, samesite="lax",
        secure=False, max_age=60 * 60 * 24 * settings.jwt_refresh_ttl_days, path="/",
    )


def _client_key(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=UserPublic)
async def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    if not await rate_limiter.check(f"signup:{_client_key(request)}", max_hits=5, window_sec=60):
        raise HTTPException(status_code=429, detail="rate_limited")
    try:
        user = await create_user(
            db, email=body.email, password=body.password, display_name=body.display_name
        )
    except AuthError as e:
        raise HTTPException(status_code=409, detail=str(e))
    _set_auth_cookies(response, user.id)
    return UserPublic.model_validate(user, from_attributes=True)


@router.post("/login", response_model=UserPublic)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    if not await rate_limiter.check(f"login:{_client_key(request)}", max_hits=5, window_sec=60):
        raise HTTPException(status_code=429, detail="rate_limited")
    try:
        user = await authenticate(db, email=body.email, password=body.password)
    except AuthError:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    _set_auth_cookies(response, user.id)
    return UserPublic.model_validate(user, from_attributes=True)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> Response:
    response.delete_cookie(COOKIE_ACCESS, path="/")
    response.delete_cookie(COOKIE_REFRESH, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(user, from_attributes=True)
