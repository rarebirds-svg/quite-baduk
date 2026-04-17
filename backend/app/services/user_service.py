from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.security import hash_password, verify_password


class AuthError(Exception):
    pass


async def create_user(
    db: AsyncSession, *, email: str, password: str, display_name: str
) -> User:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise AuthError("email_already_registered")
    user = User(email=email, password_hash=hash_password(password), display_name=display_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError("invalid_credentials")
    user.last_login_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
    return user
