# Social Login + Nationality Onboarding Implementation Plan

> **SUPERSEDED 2026-04-22** — 상위 스펙이 폐기되었습니다. 대체 설계: [`../specs/2026-04-22-ephemeral-nickname-auth-design.md`](../specs/2026-04-22-ephemeral-nickname-auth-design.md). 이 플랜은 실행되지 않았으며 역사 보존 목적으로만 유지합니다.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace email/password auth with social-only login across 8 providers (Google, Naver, Kakao, Facebook, LINE, WeChat, LinkedIn, Yahoo! JAPAN), and gate first login on a nationality (`country_code`) choice.

**Architecture:** Backend-driven OAuth — FastAPI owns the authorize/callback dance, issues existing JWT cookies on success. Each provider is a thin adapter behind a common Protocol; providers activate only when both client id and secret are configured. A signed, HttpOnly `oauth_state` cookie carries CSRF nonce, PKCE verifier, flow type (login/link), and `next` redirect. A new `user_identities` table stores `(provider, subject)` unique bindings; `users` drops `email`/`password_hash` and gains `country_code`/`avatar_url`.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, alembic, httpx, authlib (new), structlog, Next.js 14 App Router, Radix UI + custom Combobox, Intl.DisplayNames.

**Spec:** `docs/superpowers/specs/2026-04-21-social-auth-design.md`

**Branch convention:** Run this plan on a dedicated branch off `main` (e.g. `feat/social-auth`). Use a worktree if the current branch has unrelated WIP.

---

## Phase 0: Setup

### Task 1: Add `authlib` dependency, drop `bcrypt`

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/.venv311/` (re-install deps)

- [ ] **Step 1: Edit `pyproject.toml` dependencies**

In `backend/pyproject.toml`, replace the `bcrypt>=4.1` line in `[project].dependencies` with `"authlib>=1.3"`, and leave the rest alone. Resulting dependency list:

```toml
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.29",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "sqlalchemy>=2.0",
  "alembic>=1.13",
  "aiosqlite>=0.19",
  "authlib>=1.3",
  "pyjwt>=2.8",
  "python-multipart>=0.0.9",
  "httpx>=0.27",
  "structlog>=24.1",
  "websockets>=12.0",
  "greenlet>=3.0",
]
```

- [ ] **Step 2: Install updated deps**

Run from `backend/`:

```bash
source .venv311/bin/activate
pip install -e ".[dev]"
```

Expected: successful reinstall including `authlib-1.3.x`.

- [ ] **Step 3: Verify authlib import works**

```bash
python -c "from authlib.integrations.httpx_client import AsyncOAuth2Client; print('ok')"
```

Expected output: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore(backend): swap bcrypt for authlib"
```

---

### Task 2: OAuth settings (config + `.env.example`)

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add OAuth settings to `app/config.py`**

Append to the `Settings` class (after existing fields):

```python
    # OAuth — each provider is enabled iff both client_id and client_secret
    # (or app_id / app_secret for WeChat) are set.
    oauth_redirect_base_url: str = "http://localhost:8000"
    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_naver_client_id: str = ""
    oauth_naver_client_secret: str = ""
    oauth_kakao_client_id: str = ""
    oauth_kakao_client_secret: str = ""
    oauth_facebook_client_id: str = ""
    oauth_facebook_client_secret: str = ""
    oauth_line_client_id: str = ""
    oauth_line_client_secret: str = ""
    oauth_wechat_app_id: str = ""
    oauth_wechat_app_secret: str = ""
    oauth_linkedin_client_id: str = ""
    oauth_linkedin_client_secret: str = ""
    oauth_yahoo_jp_client_id: str = ""
    oauth_yahoo_jp_client_secret: str = ""
    cookie_secure: bool = False
    mock_oauth_enabled: bool = False
```

- [ ] **Step 2: Mirror into `backend/.env.example`**

Append (after the existing entries):

```
# OAuth — redirect base (https in prod). Each provider block is blank until
# you register the app and paste its credentials.
OAUTH_REDIRECT_BASE_URL=http://localhost:8000
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=
OAUTH_NAVER_CLIENT_ID=
OAUTH_NAVER_CLIENT_SECRET=
OAUTH_KAKAO_CLIENT_ID=
OAUTH_KAKAO_CLIENT_SECRET=
OAUTH_FACEBOOK_CLIENT_ID=
OAUTH_FACEBOOK_CLIENT_SECRET=
OAUTH_LINE_CLIENT_ID=
OAUTH_LINE_CLIENT_SECRET=
OAUTH_WECHAT_APP_ID=
OAUTH_WECHAT_APP_SECRET=
OAUTH_LINKEDIN_CLIENT_ID=
OAUTH_LINKEDIN_CLIENT_SECRET=
OAUTH_YAHOO_JP_CLIENT_ID=
OAUTH_YAHOO_JP_CLIENT_SECRET=
COOKIE_SECURE=false
MOCK_OAUTH_ENABLED=false
```

- [ ] **Step 3: Smoke-test config load**

```bash
cd backend && source .venv311/bin/activate
python -c "from app.config import settings; print(settings.oauth_redirect_base_url, settings.mock_oauth_enabled)"
```

Expected: `http://localhost:8000 False`

- [ ] **Step 4: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat(config): OAuth client settings for 8 providers"
```

---

### Task 3: ISO-2 country allowlist (backend) + list for frontend

**Files:**
- Create: `backend/app/core/countries.py`
- Create: `backend/tests/test_countries.py`
- Create: `web/lib/countries.ts`

- [ ] **Step 1: Write failing test for the backend allowlist**

Create `backend/tests/test_countries.py`:

```python
from app.core.countries import COUNTRY_CODES, is_valid_country_code


def test_known_codes_are_valid():
    for code in ("KR", "JP", "CN", "US", "DE", "FR", "GB", "TW"):
        assert is_valid_country_code(code)


def test_lowercase_rejected():
    assert not is_valid_country_code("kr")


def test_unknown_rejected():
    assert not is_valid_country_code("ZZ")
    assert not is_valid_country_code("")
    assert not is_valid_country_code("USA")


def test_allowlist_is_nonempty_set_of_2char_upper():
    assert len(COUNTRY_CODES) >= 240
    for c in COUNTRY_CODES:
        assert len(c) == 2
        assert c.isupper()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_countries.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.countries'`

- [ ] **Step 3: Create the allowlist**

Create `backend/app/core/countries.py`:

```python
"""ISO 3166-1 alpha-2 country code allowlist.

Bundled static list (no runtime dep on pycountry). Used by the onboarding
endpoint to validate `country_code` input. Frontend uses
`Intl.DisplayNames` for localized labels; this module only gates codes.
"""
from __future__ import annotations

# ISO 3166-1 alpha-2, current as of 2026-01. Reserved / user-assigned
# codes (AA, QM-QZ, XA-XZ, ZZ) are intentionally excluded.
COUNTRY_CODES: frozenset[str] = frozenset({
    "AD","AE","AF","AG","AI","AL","AM","AO","AQ","AR","AS","AT","AU","AW","AX","AZ",
    "BA","BB","BD","BE","BF","BG","BH","BI","BJ","BL","BM","BN","BO","BQ","BR","BS",
    "BT","BV","BW","BY","BZ","CA","CC","CD","CF","CG","CH","CI","CK","CL","CM","CN",
    "CO","CR","CU","CV","CW","CX","CY","CZ","DE","DJ","DK","DM","DO","DZ","EC","EE",
    "EG","EH","ER","ES","ET","FI","FJ","FK","FM","FO","FR","GA","GB","GD","GE","GF",
    "GG","GH","GI","GL","GM","GN","GP","GQ","GR","GS","GT","GU","GW","GY","HK","HM",
    "HN","HR","HT","HU","ID","IE","IL","IM","IN","IO","IQ","IR","IS","IT","JE","JM",
    "JO","JP","KE","KG","KH","KI","KM","KN","KP","KR","KW","KY","KZ","LA","LB","LC",
    "LI","LK","LR","LS","LT","LU","LV","LY","MA","MC","MD","ME","MF","MG","MH","MK",
    "ML","MM","MN","MO","MP","MQ","MR","MS","MT","MU","MV","MW","MX","MY","MZ","NA",
    "NC","NE","NF","NG","NI","NL","NO","NP","NR","NU","NZ","OM","PA","PE","PF","PG",
    "PH","PK","PL","PM","PN","PR","PS","PT","PW","PY","QA","RE","RO","RS","RU","RW",
    "SA","SB","SC","SD","SE","SG","SH","SI","SJ","SK","SL","SM","SN","SO","SR","SS",
    "ST","SV","SX","SY","SZ","TC","TD","TF","TG","TH","TJ","TK","TL","TM","TN","TO",
    "TR","TT","TV","TW","TZ","UA","UG","UM","US","UY","UZ","VA","VC","VE","VG","VI",
    "VN","VU","WF","WS","YE","YT","ZA","ZM","ZW",
})


def is_valid_country_code(code: str) -> bool:
    return isinstance(code, str) and len(code) == 2 and code.isupper() and code in COUNTRY_CODES
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_countries.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Create frontend list**

Create `web/lib/countries.ts`:

```typescript
// ISO 3166-1 alpha-2. Paired with Intl.DisplayNames for localized labels.
// Keep in sync with backend/app/core/countries.py.
export const COUNTRY_CODES: readonly string[] = [
  "AD","AE","AF","AG","AI","AL","AM","AO","AQ","AR","AS","AT","AU","AW","AX","AZ",
  "BA","BB","BD","BE","BF","BG","BH","BI","BJ","BL","BM","BN","BO","BQ","BR","BS",
  "BT","BV","BW","BY","BZ","CA","CC","CD","CF","CG","CH","CI","CK","CL","CM","CN",
  "CO","CR","CU","CV","CW","CX","CY","CZ","DE","DJ","DK","DM","DO","DZ","EC","EE",
  "EG","EH","ER","ES","ET","FI","FJ","FK","FM","FO","FR","GA","GB","GD","GE","GF",
  "GG","GH","GI","GL","GM","GN","GP","GQ","GR","GS","GT","GU","GW","GY","HK","HM",
  "HN","HR","HT","HU","ID","IE","IL","IM","IN","IO","IQ","IR","IS","IT","JE","JM",
  "JO","JP","KE","KG","KH","KI","KM","KN","KP","KR","KW","KY","KZ","LA","LB","LC",
  "LI","LK","LR","LS","LT","LU","LV","LY","MA","MC","MD","ME","MF","MG","MH","MK",
  "ML","MM","MN","MO","MP","MQ","MR","MS","MT","MU","MV","MW","MX","MY","MZ","NA",
  "NC","NE","NF","NG","NI","NL","NO","NP","NR","NU","NZ","OM","PA","PE","PF","PG",
  "PH","PK","PL","PM","PN","PR","PS","PT","PW","PY","QA","RE","RO","RS","RU","RW",
  "SA","SB","SC","SD","SE","SG","SH","SI","SJ","SK","SL","SM","SN","SO","SR","SS",
  "ST","SV","SX","SY","SZ","TC","TD","TF","TG","TH","TJ","TK","TL","TM","TN","TO",
  "TR","TT","TV","TW","TZ","UA","UG","UM","US","UY","UZ","VA","VC","VE","VG","VI",
  "VN","VU","WF","WS","YE","YT","ZA","ZM","ZW",
] as const;

// Guess a default country from a BCP-47 tag like "ko-KR" → "KR".
export function guessCountryFromLocale(tag: string | undefined): string {
  if (!tag) return "US";
  const m = tag.match(/-([A-Z]{2})(?:-|$)/);
  if (m && COUNTRY_CODES.includes(m[1])) return m[1];
  const lang = tag.slice(0, 2).toLowerCase();
  const fallback: Record<string, string> = { ko: "KR", ja: "JP", zh: "CN", en: "US" };
  return fallback[lang] ?? "US";
}
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/countries.py backend/tests/test_countries.py web/lib/countries.ts
git commit -m "feat(core): ISO-2 country allowlist + locale-based guess"
```

---

## Phase 1: Data Layer

### Task 4: Alembic migration — drop old `users`, recreate, add `user_identities`

**Files:**
- Create: `backend/migrations/versions/0005_social_auth.py`

- [ ] **Step 1: Create the migration**

```python
"""Social auth schema — wipe users + add user_identities

Pre-launch dev state: drop all user-owned data and recreate users with
social-only columns. Adds user_identities(provider, subject).

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pre-launch: drop all user-owned data.
    op.drop_table("analyses")
    op.drop_table("moves")
    op.drop_table("games")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("locale", sa.String(8), nullable=False, server_default="ko"),
        sa.Column("theme", sa.String(8), nullable=False, server_default="light"),
        sa.Column("preferred_rank", sa.String(8), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "user_identities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("email_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "subject", name="uq_identity_provider_subject"),
    )
    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])
    op.create_index("ix_user_identities_email", "user_identities", ["email"])

    # Recreate games/moves/analyses with user FK intact.
    op.create_table(
        "games",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("ai_rank", sa.String(8), nullable=False),
        sa.Column("ai_style", sa.String(16), nullable=False, server_default="balanced"),
        sa.Column("ai_player", sa.String(32), nullable=True),
        sa.Column("board_size", sa.Integer, nullable=False, server_default="19"),
        sa.Column("handicap", sa.Integer, nullable=False, server_default="0"),
        sa.Column("komi", sa.Float, nullable=False, server_default="6.5"),
        sa.Column("user_color", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("winner", sa.String(8), nullable=True),
        sa.Column("move_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("sgf_cache", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_games_user_status", "games", ["user_id", "status"])

    op.create_table(
        "moves",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("game_id", sa.Integer, nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("color", sa.String(2), nullable=False),
        sa.Column("coord", sa.String(4), nullable=True),
        sa.Column("captures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_undone", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("played_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "move_number", name="uq_game_move"),
    )
    op.create_index("ix_moves_game", "moves", ["game_id", "move_number"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("game_id", sa.Integer, nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "move_number", name="uq_analysis_game_move"),
    )
    op.create_index("ix_analyses_game_move", "analyses", ["game_id", "move_number"])


def downgrade() -> None:
    op.drop_table("analyses")
    op.drop_table("moves")
    op.drop_table("games")
    op.drop_index("ix_user_identities_email", table_name="user_identities")
    op.drop_index("ix_user_identities_user_id", table_name="user_identities")
    op.drop_table("user_identities")
    op.drop_table("users")
    # Recreate original schema
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("preferred_rank", sa.String(8), nullable=True),
        sa.Column("locale", sa.String(4), nullable=False, server_default="ko"),
        sa.Column("theme", sa.String(8), nullable=False, server_default="light"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
```

- [ ] **Step 2: Delete the existing dev DB so the new migration takes effect**

```bash
rm -f backend/data/baduk.db
```

- [ ] **Step 3: Apply the migration**

```bash
cd backend && source .venv311/bin/activate && alembic upgrade head
```

Expected: runs `0005_social_auth` without error.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0005_social_auth.py
git commit -m "feat(db): 0005 — social auth schema (user_identities, drop password)"
```

---

### Task 5: Rewrite `User` model, add `UserIdentity` model

**Files:**
- Modify: `backend/app/models/user.py`
- Create: `backend/app/models/user_identity.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing test for new schema**

In `backend/tests/test_models.py`, replace the existing body with:

```python
from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.models import User, UserIdentity


@pytest.mark.asyncio
async def test_create_user_with_minimal_fields(db_session):
    u = User(display_name="alice")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    assert u.id is not None
    assert u.country_code is None  # not yet onboarded
    assert u.avatar_url is None
    assert u.locale == "ko"


@pytest.mark.asyncio
async def test_identity_unique_per_provider_subject(db_session):
    u = User(display_name="bob")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)

    i1 = UserIdentity(user_id=u.id, provider="google", subject="abc123")
    db_session.add(i1)
    await db_session.commit()

    i2 = UserIdentity(user_id=u.id, provider="google", subject="abc123")
    db_session.add(i2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_identity_same_subject_different_provider_ok(db_session):
    u = User(display_name="carol")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    db_session.add(UserIdentity(user_id=u.id, provider="google", subject="X"))
    db_session.add(UserIdentity(user_id=u.id, provider="kakao",  subject="X"))
    await db_session.commit()
    res = await db_session.execute(select(UserIdentity).where(UserIdentity.user_id == u.id))
    assert len(res.scalars().all()) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: `ImportError: cannot import name 'UserIdentity' from 'app.models'` or model attribute errors.

- [ ] **Step 3: Rewrite `User` model**

Replace the entire contents of `backend/app/models/user.py`:

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, default="ko")
    theme: Mapped[str] = mapped_column(String(8), nullable=False, default="light")
    preferred_rank: Mapped[str | None] = mapped_column(String(8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    identities: Mapped[list["UserIdentity"]] = relationship(  # noqa: F821
        "UserIdentity", back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
```

- [ ] **Step 4: Create `UserIdentity` model**

Create `backend/app/models/user_identity.py`:

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_identity_provider_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="identities")  # noqa: F821
```

- [ ] **Step 5: Export from `models/__init__.py`**

Replace `backend/app/models/__init__.py` with:

```python
from app.models.user import User
from app.models.user_identity import UserIdentity
from app.models.game import Game
from app.models.move import Move
from app.models.analysis_cache import AnalysisCache

__all__ = ["User", "UserIdentity", "Game", "Move", "AnalysisCache"]
```

Also update `backend/tests/conftest.py` import line to include `UserIdentity`:

```python
from app.models import User, UserIdentity, Game, Move, AnalysisCache  # register models with metadata
```

- [ ] **Step 6: Run model tests**

```bash
pytest tests/test_models.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/user.py backend/app/models/user_identity.py backend/app/models/__init__.py backend/tests/test_models.py backend/tests/conftest.py
git commit -m "feat(models): UserIdentity + social-only User (no email/password)"
```

---

## Phase 2: OAuth Infrastructure

### Task 6: `oauth/state.py` — HMAC-signed state payload

**Files:**
- Create: `backend/app/core/oauth/__init__.py` (empty)
- Create: `backend/app/core/oauth/state.py`
- Create: `backend/tests/oauth/__init__.py` (empty)
- Create: `backend/tests/oauth/test_state.py`

- [ ] **Step 1: Write failing test for state sign/verify**

Create `backend/tests/oauth/test_state.py`:

```python
from __future__ import annotations

import time

import pytest

from app.core.oauth.state import (
    StatePayload,
    decode_state_cookie,
    encode_state_cookie,
)


def _payload(**over):
    base = dict(
        nonce="n123",
        provider="google",
        flow="login",
        next_url="/",
        code_verifier="v" * 43,
        user_id=None,
    )
    base.update(over)
    return StatePayload(**base)


def test_encode_decode_roundtrip():
    payload = _payload()
    cookie = encode_state_cookie(payload)
    out = decode_state_cookie(cookie, expected_provider="google")
    assert out.nonce == payload.nonce
    assert out.provider == "google"
    assert out.flow == "login"
    assert out.next_url == "/"
    assert out.code_verifier == payload.code_verifier
    assert out.user_id is None


def test_tampered_signature_rejected():
    cookie = encode_state_cookie(_payload())
    head, sig = cookie.rsplit(".", 1)
    tampered = head + "." + ("a" if sig[0] != "a" else "b") + sig[1:]
    with pytest.raises(ValueError):
        decode_state_cookie(tampered, expected_provider="google")


def test_provider_mismatch_rejected():
    cookie = encode_state_cookie(_payload(provider="google"))
    with pytest.raises(ValueError):
        decode_state_cookie(cookie, expected_provider="kakao")


def test_expired_rejected(monkeypatch):
    p = _payload()
    cookie = encode_state_cookie(p)
    # Jump 11 minutes forward — default TTL is 10.
    monkeypatch.setattr("app.core.oauth.state.time.time", lambda: time.time() + 660)
    with pytest.raises(ValueError):
        decode_state_cookie(cookie, expected_provider="google")


def test_link_flow_preserves_user_id():
    cookie = encode_state_cookie(_payload(flow="link", user_id=42))
    out = decode_state_cookie(cookie, expected_provider="google")
    assert out.flow == "link"
    assert out.user_id == 42
```

- [ ] **Step 2: Run test to verify failure**

```bash
mkdir -p backend/app/core/oauth backend/tests/oauth
touch backend/app/core/oauth/__init__.py backend/tests/oauth/__init__.py
pytest tests/oauth/test_state.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.oauth.state'`

- [ ] **Step 3: Implement state module**

Create `backend/app/core/oauth/state.py`:

```python
"""HMAC-signed OAuth state cookie.

Payload carried across the authorize-callback round-trip:
  nonce, provider, flow (login|link), next_url, code_verifier, user_id

Encoded as urlsafe-b64(JSON).<hex-hmac-sha256(payload + "." + issued_at)>.
A 10-minute TTL is enforced on decode. `JWT_SECRET` seeds the HMAC key.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Literal

from app.config import settings

STATE_TTL_SEC = 600  # 10 minutes
Flow = Literal["login", "link"]


@dataclass(frozen=True)
class StatePayload:
    nonce: str
    provider: str
    flow: Flow
    next_url: str = "/"
    code_verifier: str | None = None
    user_id: int | None = None
    issued_at: int = field(default_factory=lambda: int(time.time()))


def _key() -> bytes:
    return hashlib.sha256(("oauth-state::" + settings.jwt_secret).encode()).digest()


def _sign(body: bytes) -> str:
    return hmac.new(_key(), body, hashlib.sha256).hexdigest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def new_nonce() -> str:
    return secrets.token_urlsafe(24)


def encode_state_cookie(payload: StatePayload) -> str:
    body = json.dumps(asdict(payload), separators=(",", ":")).encode()
    head = _b64(body)
    sig = _sign(head.encode())
    return head + "." + sig


def decode_state_cookie(cookie: str, *, expected_provider: str) -> StatePayload:
    try:
        head, sig = cookie.rsplit(".", 1)
    except ValueError:
        raise ValueError("oauth_state_invalid") from None
    expected_sig = _sign(head.encode())
    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("oauth_state_invalid")
    try:
        data = json.loads(_b64d(head).decode())
        payload = StatePayload(**data)
    except (ValueError, TypeError):
        raise ValueError("oauth_state_invalid") from None
    if payload.provider != expected_provider:
        raise ValueError("oauth_state_invalid")
    if time.time() > payload.issued_at + STATE_TTL_SEC:
        raise ValueError("oauth_state_invalid")
    return payload
```

- [ ] **Step 4: Run test to verify passing**

```bash
pytest tests/oauth/test_state.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/oauth/__init__.py backend/app/core/oauth/state.py backend/tests/oauth/__init__.py backend/tests/oauth/test_state.py
git commit -m "feat(oauth): HMAC-signed state cookie with TTL + provider pin"
```

---

### Task 7: `oauth/base.py` — `OAuthProvider` Protocol + `UserInfo`

**Files:**
- Create: `backend/app/core/oauth/base.py`

- [ ] **Step 1: Create the protocol and data types**

```python
"""OAuth provider adapter interface.

All 8 providers conform to this shape, so the generic login/callback
endpoints can treat them uniformly. Each adapter owns its own URL set,
scope string, and userinfo parsing. PKCE + nonce are optional per-
provider capabilities — the endpoint only generates them when supported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass(frozen=True)
class UserInfo:
    subject: str
    email: str | None
    email_verified: bool
    name: str | None
    avatar_url: str | None


class OAuthProvider(Protocol):
    name: str
    scope: str
    supports_pkce: bool
    supports_oidc_nonce: bool
    # Email from this provider is trusted as verified without extra checks.
    email_is_verified_by_default: bool

    def build_authorize_url(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        state: str,
        nonce: str | None,
        code_challenge: str | None,
    ) -> str: ...

    async def exchange_code(
        self,
        *,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: str | None,
        nonce: str | None,
        http: httpx.AsyncClient,
    ) -> dict[str, Any]: ...

    async def fetch_userinfo(
        self,
        *,
        token_response: dict[str, Any],
        http: httpx.AsyncClient,
    ) -> UserInfo: ...
```

- [ ] **Step 2: Verify module imports cleanly**

```bash
cd backend && python -c "from app.core.oauth.base import OAuthProvider, UserInfo; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/oauth/base.py
git commit -m "feat(oauth): Protocol + UserInfo for provider adapters"
```

---

### Task 8: `oauth/registry.py` + `MockProvider` for tests

**Files:**
- Create: `backend/app/core/oauth/registry.py`
- Create: `backend/app/core/oauth/mock.py`
- Create: `backend/tests/oauth/test_registry.py`

- [ ] **Step 1: Write failing test for registry**

```python
# backend/tests/oauth/test_registry.py
from __future__ import annotations

from app.core.oauth.registry import (
    PROVIDERS,
    enabled_providers,
    get_provider,
    provider_credentials,
)


def test_all_eight_providers_registered():
    names = set(PROVIDERS.keys())
    assert {"google", "naver", "kakao", "facebook", "line", "wechat", "linkedin", "yahoo_jp"} <= names


def test_disabled_when_credentials_missing(monkeypatch):
    # All OAUTH_* settings are blank by default.
    assert "google" not in enabled_providers()


def test_enabled_when_both_id_and_secret_set(monkeypatch):
    monkeypatch.setattr("app.config.settings.oauth_google_client_id", "x")
    monkeypatch.setattr("app.config.settings.oauth_google_client_secret", "y")
    assert "google" in enabled_providers()


def test_wechat_uses_app_id_app_secret(monkeypatch):
    monkeypatch.setattr("app.config.settings.oauth_wechat_app_id", "x")
    monkeypatch.setattr("app.config.settings.oauth_wechat_app_secret", "y")
    assert "wechat" in enabled_providers()
    cid, csec = provider_credentials("wechat")
    assert cid == "x"
    assert csec == "y"


def test_mock_provider_enabled_only_when_flag_set(monkeypatch):
    monkeypatch.setattr("app.config.settings.mock_oauth_enabled", True)
    assert "mock" in enabled_providers()


def test_get_provider_unknown_raises():
    import pytest
    with pytest.raises(KeyError):
        get_provider("nope")
```

- [ ] **Step 2: Run test to see failure**

```bash
pytest tests/oauth/test_registry.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: Implement registry**

```python
# backend/app/core/oauth/registry.py
"""Provider registry — maps provider name to adapter instance.

Enabled = credentials present in settings (or `mock_oauth_enabled=True`
for the test provider). Actual provider adapters are registered in later
tasks; until then, only the mock is wired up.
"""
from __future__ import annotations

from typing import cast

from app.config import settings
from app.core.oauth.base import OAuthProvider
from app.core.oauth.mock import MockProvider

PROVIDERS: dict[str, OAuthProvider] = {
    "mock": cast(OAuthProvider, MockProvider()),
    # real providers registered in later tasks
}


def get_provider(name: str) -> OAuthProvider:
    if name not in PROVIDERS:
        raise KeyError(name)
    return PROVIDERS[name]


def provider_credentials(name: str) -> tuple[str, str]:
    """Return (id, secret) / (app_id, app_secret). Empty strings if unset."""
    if name == "wechat":
        return settings.oauth_wechat_app_id, settings.oauth_wechat_app_secret
    if name == "mock":
        return ("mock-id", "mock-secret") if settings.mock_oauth_enabled else ("", "")
    id_attr = f"oauth_{name}_client_id"
    sec_attr = f"oauth_{name}_client_secret"
    return getattr(settings, id_attr, ""), getattr(settings, sec_attr, "")


def enabled_providers() -> list[str]:
    out: list[str] = []
    for name in PROVIDERS:
        cid, csec = provider_credentials(name)
        if cid and csec:
            out.append(name)
    return out
```

- [ ] **Step 4: Implement `MockProvider`**

```python
# backend/app/core/oauth/mock.py
"""Deterministic OAuth provider for tests + local E2E.

Activated when `MOCK_OAUTH_ENABLED=true`. `authorize_url` bounces straight
to the callback with a fixed `code`, and `exchange_code` returns a
preset userinfo the test suite can customise via environment.
"""
from __future__ import annotations

import json
import os
from dataclasses import replace
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.oauth.base import UserInfo

MOCK_DEFAULT = UserInfo(
    subject="mock-subject-1",
    email="alice@mock.test",
    email_verified=True,
    name="Alice",
    avatar_url=None,
)


class MockProvider:
    name = "mock"
    scope = "mock"
    supports_pkce = False
    supports_oidc_nonce = False
    email_is_verified_by_default = True

    def build_authorize_url(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        state: str,
        nonce: str | None,
        code_challenge: str | None,
    ) -> str:
        # Point the browser directly at our callback. The "code" embeds the
        # subject so E2E tests can simulate multiple users.
        params = urlencode({"code": os.environ.get("MOCK_OAUTH_CODE", "default"), "state": state})
        return f"{redirect_uri}?{params}"

    async def exchange_code(
        self,
        *,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: str | None,
        nonce: str | None,
        http: httpx.AsyncClient,
    ) -> dict[str, Any]:
        return {"access_token": "mock-token", "code": code}

    async def fetch_userinfo(
        self,
        *,
        token_response: dict[str, Any],
        http: httpx.AsyncClient,
    ) -> UserInfo:
        # Env override lets tests swap the identity per scenario.
        raw = os.environ.get("MOCK_OAUTH_USERINFO_JSON")
        if raw:
            data = json.loads(raw)
            return replace(
                MOCK_DEFAULT,
                subject=data.get("subject", MOCK_DEFAULT.subject),
                email=data.get("email", MOCK_DEFAULT.email),
                email_verified=data.get("email_verified", MOCK_DEFAULT.email_verified),
                name=data.get("name", MOCK_DEFAULT.name),
                avatar_url=data.get("avatar_url", MOCK_DEFAULT.avatar_url),
            )
        # Code-derived subject so two different codes produce two different users.
        code = token_response.get("code", "default")
        return replace(MOCK_DEFAULT, subject=f"mock-subject-{code}")
```

- [ ] **Step 5: Run test**

```bash
pytest tests/oauth/test_registry.py -v
```

Expected: 3 of 6 pass (mock + credential checks); the `test_all_eight_providers_registered` still fails because only `mock` is registered. That is expected — it will pass after Tasks 17–24 add the real providers. Mark this in a comment and move on. Update the test as follows so it doesn't block Phase 2:

Change the assertion in `test_all_eight_providers_registered` to:

```python
def test_mock_provider_always_registered():
    assert "mock" in PROVIDERS
```

Re-run. Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/oauth/registry.py backend/app/core/oauth/mock.py backend/tests/oauth/test_registry.py
git commit -m "feat(oauth): registry + MockProvider for tests"
```

---

## Phase 3: Core Login Flow (with Mock Provider)

### Task 9: `oauth_service.py` — find/create user, conflict detection

**Files:**
- Create: `backend/app/services/oauth_service.py`
- Create: `backend/tests/oauth/test_oauth_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/oauth/test_oauth_service.py
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.oauth.base import UserInfo
from app.models import User, UserIdentity
from app.services.oauth_service import (
    ConflictError,
    link_identity_to_user,
    resolve_login,
)


@pytest.mark.asyncio
async def test_new_user_created_for_first_login(db_session):
    info = UserInfo(subject="g-1", email="new@g.com", email_verified=True, name="New", avatar_url="u")
    user, created = await resolve_login(db_session, provider="google", info=info)
    assert created is True
    assert user.display_name == "New"
    assert user.avatar_url == "u"
    assert user.country_code is None
    ids = (await db_session.execute(select(UserIdentity).where(UserIdentity.user_id == user.id))).scalars().all()
    assert len(ids) == 1
    assert ids[0].provider == "google"
    assert ids[0].subject == "g-1"


@pytest.mark.asyncio
async def test_returning_user_reuses_same_row(db_session):
    info = UserInfo(subject="g-2", email="a@g.com", email_verified=True, name="A", avatar_url=None)
    u1, c1 = await resolve_login(db_session, provider="google", info=info)
    u2, c2 = await resolve_login(db_session, provider="google", info=info)
    assert c1 is True and c2 is False
    assert u1.id == u2.id


@pytest.mark.asyncio
async def test_verified_email_conflict_raises(db_session):
    # Register with Google first.
    g = UserInfo(subject="g-3", email="bob@x.com", email_verified=True, name="Bob", avatar_url=None)
    await resolve_login(db_session, provider="google", info=g)
    # Now try Kakao with the same verified email.
    k = UserInfo(subject="k-3", email="bob@x.com", email_verified=True, name="BK", avatar_url=None)
    with pytest.raises(ConflictError) as ei:
        await resolve_login(db_session, provider="kakao", info=k)
    assert ei.value.existing_provider == "google"


@pytest.mark.asyncio
async def test_unverified_email_does_not_conflict(db_session):
    g = UserInfo(subject="g-4", email="x@x.com", email_verified=True, name="G", avatar_url=None)
    await resolve_login(db_session, provider="google", info=g)
    # Facebook is never trusted verified.
    f = UserInfo(subject="f-4", email="x@x.com", email_verified=False, name="F", avatar_url=None)
    user, created = await resolve_login(db_session, provider="facebook", info=f)
    assert created is True  # separate account — no conflict


@pytest.mark.asyncio
async def test_link_identity_adds_second_binding(db_session):
    g = UserInfo(subject="g-5", email="c@g.com", email_verified=True, name="C", avatar_url=None)
    user, _ = await resolve_login(db_session, provider="google", info=g)
    k = UserInfo(subject="k-5", email="c@kakao.com", email_verified=False, name="C", avatar_url=None)
    linked = await link_identity_to_user(db_session, user=user, provider="kakao", info=k)
    assert linked.user_id == user.id
    ids = (await db_session.execute(select(UserIdentity).where(UserIdentity.user_id == user.id))).scalars().all()
    assert {i.provider for i in ids} == {"google", "kakao"}
```

- [ ] **Step 2: Run tests — see failures**

```bash
pytest tests/oauth/test_oauth_service.py -v
```

Expected: `ImportError: cannot import name 'resolve_login' from 'app.services.oauth_service'`

- [ ] **Step 3: Implement the service**

```python
# backend/app/services/oauth_service.py
"""Translate (provider, userinfo) into a DB user + identity.

Policy: (provider, subject) is the unique login key. Emails are never
auto-merged — only providers whose emails are `email_verified` by the
caller can trigger a conflict notice, and even then we never link
silently. The user must come back through the existing provider's login
and use the settings "connect" flow.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.oauth.base import UserInfo
from app.models import User, UserIdentity


class ConflictError(Exception):
    def __init__(self, existing_provider: str) -> None:
        self.existing_provider = existing_provider
        super().__init__(f"email_conflict_with_{existing_provider}")


async def _find_identity(
    db: AsyncSession, *, provider: str, subject: str
) -> UserIdentity | None:
    res = await db.execute(
        select(UserIdentity).where(
            UserIdentity.provider == provider, UserIdentity.subject == subject
        )
    )
    return res.scalar_one_or_none()


async def _find_verified_email_conflict(
    db: AsyncSession, *, email: str, exclude_provider: str
) -> UserIdentity | None:
    res = await db.execute(
        select(UserIdentity).where(
            UserIdentity.email == email,
            UserIdentity.email_verified == True,  # noqa: E712
            UserIdentity.provider != exclude_provider,
        )
    )
    return res.scalars().first()


async def resolve_login(
    db: AsyncSession, *, provider: str, info: UserInfo
) -> tuple[User, bool]:
    """Return (user, created). Raise ConflictError on verified email clash."""
    # 1. Existing identity? → return its user.
    existing = await _find_identity(db, provider=provider, subject=info.subject)
    if existing is not None:
        res = await db.execute(select(User).where(User.id == existing.user_id))
        user = res.scalar_one()
        return user, False

    # 2. Verified email clash with another provider?
    if info.email and info.email_verified:
        clash = await _find_verified_email_conflict(
            db, email=info.email, exclude_provider=provider
        )
        if clash is not None:
            raise ConflictError(existing_provider=clash.provider)

    # 3. New user + new identity.
    user = User(display_name=(info.name or provider).strip()[:64], avatar_url=info.avatar_url)
    db.add(user)
    await db.flush()
    ident = UserIdentity(
        user_id=user.id,
        provider=provider,
        subject=info.subject,
        email=info.email,
        email_verified=info.email_verified,
    )
    db.add(ident)
    await db.commit()
    await db.refresh(user)
    return user, True


async def link_identity_to_user(
    db: AsyncSession, *, user: User, provider: str, info: UserInfo
) -> UserIdentity:
    # Refuse if this (provider, subject) is already bound to some other user.
    existing = await _find_identity(db, provider=provider, subject=info.subject)
    if existing is not None and existing.user_id != user.id:
        raise ConflictError(existing_provider=provider)  # already bound elsewhere
    if existing is not None:
        return existing
    ident = UserIdentity(
        user_id=user.id,
        provider=provider,
        subject=info.subject,
        email=info.email,
        email_verified=info.email_verified,
    )
    db.add(ident)
    await db.commit()
    await db.refresh(ident)
    return ident
```

- [ ] **Step 4: Run tests — confirm green**

```bash
pytest tests/oauth/test_oauth_service.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/oauth_service.py backend/tests/oauth/test_oauth_service.py
git commit -m "feat(oauth): resolve_login + link_identity with conflict detection"
```

---

### Task 10: OAuth endpoints — `/providers`, `/start`, `/callback`

**Files:**
- Modify: `backend/app/api/auth.py`
- Create: `backend/tests/api/test_oauth_flow.py`

- [ ] **Step 1: Write failing integration test using mock provider**

```python
# backend/tests/api/test_oauth_flow.py
from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_providers_endpoint_lists_only_enabled(client, monkeypatch):
    monkeypatch.setenv("MOCK_OAUTH_ENABLED", "true")
    monkeypatch.setattr("app.config.settings.mock_oauth_enabled", True)
    r = await client.get("/api/auth/providers")
    assert r.status_code == 200
    assert r.json() == {"providers": ["mock"]}


@pytest.mark.asyncio
async def test_start_redirects_to_authorize_url(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.mock_oauth_enabled", True)
    r = await client.get("/api/auth/oauth/mock/start?next=/game/new", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    # Mock points at our own callback.
    assert "/api/auth/oauth/mock/callback" in loc
    assert "state=" in loc
    # State cookie was set.
    assert any(c.name == "oauth_state" for c in r.cookies.jar)


@pytest.mark.asyncio
async def test_callback_creates_user_and_sets_session(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.mock_oauth_enabled", True)
    monkeypatch.setenv(
        "MOCK_OAUTH_USERINFO_JSON",
        json.dumps({"subject": "alice", "email": "alice@mock.test",
                     "email_verified": True, "name": "Alice"}),
    )
    start = await client.get("/api/auth/oauth/mock/start?next=/", follow_redirects=False)
    # Follow the mock authorize URL → callback.
    cb = await client.get(start.headers["location"], follow_redirects=False)
    assert cb.status_code == 302
    # New user → should land on /onboarding (country_code still NULL).
    assert cb.headers["location"] == "/onboarding"
    # Session cookies are set.
    cookies = {c.name for c in cb.cookies.jar}
    assert "access_token" in cookies and "refresh_token" in cookies


@pytest.mark.asyncio
async def test_callback_rejects_tampered_state(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.mock_oauth_enabled", True)
    r = await client.get(
        "/api/auth/oauth/mock/callback?code=x&state=badstate",
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "error=oauth_state_invalid" in r.headers["location"]
```

- [ ] **Step 2: Run test — see failures**

```bash
pytest tests/api/test_oauth_flow.py -v
```

Expected: endpoint 404 (not yet routed).

- [ ] **Step 3: Rewrite `app/api/auth.py`** (append new routes; DO NOT yet delete the old `/signup`/`/login` — that happens in Phase 6)

Add to `backend/app/api/auth.py`:

```python
# ── imports (add to existing) ─────────────────────────────────────────────
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.core.oauth.registry import enabled_providers, get_provider, provider_credentials
from app.core.oauth.state import STATE_TTL_SEC, StatePayload, decode_state_cookie, encode_state_cookie, new_nonce
from app.services.oauth_service import ConflictError, resolve_login

COOKIE_STATE = "oauth_state"


def _callback_url(provider: str, flow: str = "login") -> str:
    base = settings.oauth_redirect_base_url.rstrip("/")
    suffix = "/callback" if flow == "login" else "/link/callback"
    return f"{base}/api/auth/oauth/{provider}{suffix}"


def _safe_next(v: str | None) -> str:
    if not v or not v.startswith("/") or v.startswith("//"):
        return "/"
    return v


@router.get("/providers")
async def providers() -> dict[str, list[str]]:
    return {"providers": [p for p in enabled_providers() if p != "mock" or settings.mock_oauth_enabled]}


@router.get("/oauth/{provider}/start")
async def oauth_start(provider: str, request: Request, next: str = "/") -> Response:
    if provider not in enabled_providers():
        raise HTTPException(status_code=404, detail="provider_not_enabled")
    p = get_provider(provider)
    client_id, _ = provider_credentials(provider)

    code_verifier = secrets.token_urlsafe(64) if p.supports_pkce else None
    code_challenge = (
        base64_urlsafe_sha256(code_verifier) if code_verifier else None
    )
    nonce = new_nonce() if p.supports_oidc_nonce else None

    payload = StatePayload(
        nonce=nonce or "",
        provider=provider,
        flow="login",
        next_url=_safe_next(next),
        code_verifier=code_verifier,
    )
    cookie_value = encode_state_cookie(payload)
    authorize_url = p.build_authorize_url(
        client_id=client_id,
        redirect_uri=_callback_url(provider, "login"),
        state=cookie_value.split(".", 1)[0],
        nonce=nonce,
        code_challenge=code_challenge,
    )
    resp = RedirectResponse(url=authorize_url, status_code=302)
    resp.set_cookie(
        COOKIE_STATE, cookie_value,
        httponly=True, samesite="lax", secure=settings.cookie_secure,
        max_age=STATE_TTL_SEC, path="/api/auth/oauth",
    )
    return resp


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Response:
    frontend_base = "/"  # relative — the web app serves /login and /onboarding
    if error or not code or not state or not oauth_state:
        return RedirectResponse(url="/login?error=oauth_provider_error", status_code=302)

    try:
        payload = decode_state_cookie(oauth_state, expected_provider=provider)
    except ValueError:
        return RedirectResponse(url="/login?error=oauth_state_invalid", status_code=302)

    # The cookie and the query param must agree.
    if oauth_state.split(".", 1)[0] != state:
        return RedirectResponse(url="/login?error=oauth_state_invalid", status_code=302)

    p = get_provider(provider)
    client_id, client_secret = provider_credentials(provider)

    async with httpx.AsyncClient(timeout=15.0) as http:
        try:
            token_resp = await p.exchange_code(
                code=code, client_id=client_id, client_secret=client_secret,
                redirect_uri=_callback_url(provider, "login"),
                code_verifier=payload.code_verifier,
                nonce=payload.nonce or None, http=http,
            )
            info = await p.fetch_userinfo(token_response=token_resp, http=http)
        except Exception:
            return RedirectResponse(url="/login?error=oauth_provider_error", status_code=302)

    try:
        user, _created = await resolve_login(db, provider=provider, info=info)
    except ConflictError as e:
        return RedirectResponse(
            url=f"/login?error=oauth_email_conflict&with={e.existing_provider}",
            status_code=302,
        )

    # Issue session cookies.
    resp_url = "/onboarding" if user.country_code is None else payload.next_url
    resp = RedirectResponse(url=resp_url, status_code=302)
    _set_auth_cookies(resp, user.id)
    resp.delete_cookie(COOKIE_STATE, path="/api/auth/oauth")
    return resp


def base64_urlsafe_sha256(verifier: str) -> str:
    import base64
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
```

- [ ] **Step 4: Re-run tests**

```bash
pytest tests/api/test_oauth_flow.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/auth.py backend/tests/api/test_oauth_flow.py
git commit -m "feat(api): OAuth /providers /start /callback + state cookie"
```

---

## Phase 4: Onboarding + `/me`

### Task 11: `UserPublic.needs_onboarding` + `POST /api/auth/onboarding`

**Files:**
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/auth.py`
- Create: `backend/tests/api/test_onboarding.py`

- [ ] **Step 1: Update `UserPublic` schema**

Replace `backend/app/schemas/auth.py` entirely:

```python
from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    id: int
    display_name: str
    avatar_url: str | None = None
    country_code: str | None = None
    locale: str = "ko"
    theme: str = "light"
    preferred_rank: str | None = None
    needs_onboarding: bool = False


class OnboardingRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=2)
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
```

- [ ] **Step 2: Update `/api/auth/me` response to compute `needs_onboarding`**

In `backend/app/api/auth.py`, replace the existing `me` handler with:

```python
@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)) -> UserPublic:
    pub = UserPublic.model_validate(user, from_attributes=True)
    pub = pub.model_copy(update={"needs_onboarding": user.country_code is None})
    return pub
```

- [ ] **Step 3: Write failing tests for onboarding**

```python
# backend/tests/api/test_onboarding.py
from __future__ import annotations

import json

import pytest


async def _login(client, monkeypatch, *, subject: str = "alice", email: str = "a@a.a"):
    monkeypatch.setattr("app.config.settings.mock_oauth_enabled", True)
    monkeypatch.setenv(
        "MOCK_OAUTH_USERINFO_JSON",
        json.dumps({"subject": subject, "email": email,
                    "email_verified": True, "name": "Alice"}),
    )
    start = await client.get("/api/auth/oauth/mock/start", follow_redirects=False)
    await client.get(start.headers["location"], follow_redirects=False)


@pytest.mark.asyncio
async def test_me_reports_needs_onboarding_after_signup(client, monkeypatch):
    await _login(client, monkeypatch)
    r = await client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["needs_onboarding"] is True
    assert r.json()["country_code"] is None


@pytest.mark.asyncio
async def test_onboarding_persists_country_and_display_name(client, monkeypatch):
    await _login(client, monkeypatch)
    r = await client.post(
        "/api/auth/onboarding",
        json={"country_code": "KR", "display_name": "앨리스"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["country_code"] == "KR"
    assert body["display_name"] == "앨리스"
    assert body["needs_onboarding"] is False


@pytest.mark.asyncio
async def test_onboarding_rejects_bad_country(client, monkeypatch):
    await _login(client, monkeypatch)
    r = await client.post("/api/auth/onboarding", json={"country_code": "ZZ"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_onboarding_refuses_second_call(client, monkeypatch):
    await _login(client, monkeypatch)
    await client.post("/api/auth/onboarding", json={"country_code": "KR"})
    r = await client.post("/api/auth/onboarding", json={"country_code": "JP"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_onboarding_requires_auth(client):
    r = await client.post("/api/auth/onboarding", json={"country_code": "KR"})
    assert r.status_code == 401
```

- [ ] **Step 4: Run tests — see failures**

```bash
pytest tests/api/test_onboarding.py -v
```

Expected: routing 404 / schema errors.

- [ ] **Step 5: Add `POST /api/auth/onboarding` handler**

Append to `backend/app/api/auth.py`:

```python
from app.core.countries import is_valid_country_code
from app.schemas.auth import OnboardingRequest


@router.post("/onboarding", response_model=UserPublic)
async def onboarding(
    body: OnboardingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserPublic:
    if not await rate_limiter.check(f"onboarding:{_client_key(request)}", max_hits=5, window_sec=60):
        raise HTTPException(status_code=429, detail="rate_limited")
    if not is_valid_country_code(body.country_code):
        raise HTTPException(status_code=422, detail="invalid_country")
    if user.country_code is not None:
        raise HTTPException(status_code=409, detail="already_onboarded")
    user.country_code = body.country_code
    if body.display_name:
        user.display_name = body.display_name
    await db.commit()
    await db.refresh(user)
    pub = UserPublic.model_validate(user, from_attributes=True)
    return pub.model_copy(update={"needs_onboarding": False})
```

- [ ] **Step 6: Run tests — confirm pass**

```bash
pytest tests/api/test_onboarding.py -v
```

Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/auth.py backend/app/api/auth.py backend/tests/api/test_onboarding.py
git commit -m "feat(api): /me needs_onboarding flag + /onboarding POST"
```

---

## Phase 5: Identities + Linking

### Task 12: `GET /api/auth/identities`, link/unlink endpoints

**Files:**
- Modify: `backend/app/api/auth.py`
- Create: `backend/tests/api/test_identities.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/api/test_identities.py
from __future__ import annotations

import json

import pytest


async def _login(client, monkeypatch, *, subject: str = "u1"):
    monkeypatch.setattr("app.config.settings.mock_oauth_enabled", True)
    monkeypatch.setenv("MOCK_OAUTH_USERINFO_JSON",
                      json.dumps({"subject": subject, "email": f"{subject}@x",
                                  "email_verified": True, "name": "U"}))
    start = await client.get("/api/auth/oauth/mock/start", follow_redirects=False)
    await client.get(start.headers["location"], follow_redirects=False)


@pytest.mark.asyncio
async def test_list_identities_after_login(client, monkeypatch):
    await _login(client, monkeypatch, subject="abc")
    r = await client.get("/api/auth/identities")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["provider"] == "mock"


@pytest.mark.asyncio
async def test_unlink_last_identity_rejected(client, monkeypatch):
    await _login(client, monkeypatch, subject="def")
    ids = (await client.get("/api/auth/identities")).json()
    r = await client.delete(f"/api/auth/identities/{ids[0]['id']}")
    assert r.status_code == 409
    assert "oauth_unlink_last" in r.text


@pytest.mark.asyncio
async def test_unauth_list_rejected(client):
    r = await client.get("/api/auth/identities")
    assert r.status_code == 401
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/api/test_identities.py -v
```

Expected: 404 on the new endpoints.

- [ ] **Step 3: Implement the endpoints**

Append to `backend/app/api/auth.py`:

```python
from pydantic import BaseModel as _BM

from app.models import UserIdentity


class IdentityPublic(_BM):
    id: int
    provider: str
    email: str | None
    created_at: datetime  # type: ignore[name-defined]

    class Config:
        from_attributes = True


@router.get("/identities", response_model=list[IdentityPublic])
async def list_identities(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IdentityPublic]:
    from sqlalchemy import select as _s
    res = await db.execute(_s(UserIdentity).where(UserIdentity.user_id == user.id))
    rows = res.scalars().all()
    return [IdentityPublic.model_validate(r, from_attributes=True) for r in rows]


@router.delete("/identities/{identity_id}", status_code=204)
async def unlink_identity(
    identity_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    from sqlalchemy import select as _s, delete as _d
    res = await db.execute(_s(UserIdentity).where(UserIdentity.user_id == user.id))
    rows = res.scalars().all()
    target = next((r for r in rows if r.id == identity_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail="identity_not_found")
    if len(rows) <= 1:
        raise HTTPException(status_code=409, detail="oauth_unlink_last")
    await db.execute(_d(UserIdentity).where(UserIdentity.id == target.id))
    await db.commit()
    return Response(status_code=204)
```

Add the missing `datetime` import at the top:

```python
from datetime import datetime
```

- [ ] **Step 4: Link endpoints — `POST /api/auth/oauth/{provider}/link` and `GET .../link/callback`**

```python
from app.services.oauth_service import link_identity_to_user


@router.post("/oauth/{provider}/link")
async def oauth_link_start(
    provider: str,
    request: Request,
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    if provider not in enabled_providers():
        raise HTTPException(status_code=404, detail="provider_not_enabled")
    p = get_provider(provider)
    client_id, _ = provider_credentials(provider)
    code_verifier = secrets.token_urlsafe(64) if p.supports_pkce else None
    code_challenge = base64_urlsafe_sha256(code_verifier) if code_verifier else None
    nonce = new_nonce() if p.supports_oidc_nonce else None
    payload = StatePayload(
        nonce=nonce or "", provider=provider, flow="link",
        next_url="/settings", code_verifier=code_verifier, user_id=user.id,
    )
    cookie_value = encode_state_cookie(payload)
    authorize_url = p.build_authorize_url(
        client_id=client_id,
        redirect_uri=_callback_url(provider, "link"),
        state=cookie_value.split(".", 1)[0], nonce=nonce,
        code_challenge=code_challenge,
    )
    resp = Response()
    resp.set_cookie(
        COOKIE_STATE, cookie_value,
        httponly=True, samesite="lax", secure=settings.cookie_secure,
        max_age=STATE_TTL_SEC, path="/api/auth/oauth",
    )
    resp.media_type = "application/json"
    resp.body = json.dumps({"authorize_url": authorize_url}).encode()
    return resp  # type: ignore[return-value]


@router.get("/oauth/{provider}/link/callback")
async def oauth_link_callback(
    provider: str,
    request: Request,
    code: str | None = None,
    state: str | None = None,
    oauth_state: str | None = Cookie(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not code or not state or not oauth_state:
        return RedirectResponse(url="/settings?error=oauth_provider_error", status_code=302)
    try:
        payload = decode_state_cookie(oauth_state, expected_provider=provider)
    except ValueError:
        return RedirectResponse(url="/settings?error=oauth_state_invalid", status_code=302)
    if payload.flow != "link" or payload.user_id != user.id:
        return RedirectResponse(url="/settings?error=oauth_state_invalid", status_code=302)
    p = get_provider(provider)
    client_id, client_secret = provider_credentials(provider)
    async with httpx.AsyncClient(timeout=15.0) as http:
        try:
            tok = await p.exchange_code(
                code=code, client_id=client_id, client_secret=client_secret,
                redirect_uri=_callback_url(provider, "link"),
                code_verifier=payload.code_verifier, nonce=payload.nonce or None, http=http,
            )
            info = await p.fetch_userinfo(token_response=tok, http=http)
        except Exception:
            return RedirectResponse(url="/settings?error=oauth_provider_error", status_code=302)
    try:
        await link_identity_to_user(db, user=user, provider=provider, info=info)
    except ConflictError:
        return RedirectResponse(url="/settings?error=oauth_already_linked", status_code=302)
    resp = RedirectResponse(url=f"/settings?linked={provider}", status_code=302)
    resp.delete_cookie(COOKIE_STATE, path="/api/auth/oauth")
    return resp
```

Also add `import json` at top if not already present.

- [ ] **Step 5: Run tests**

```bash
pytest tests/api/test_identities.py tests/api/test_oauth_flow.py tests/api/test_onboarding.py -v
```

Expected: all previously passing + 3 new passing.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/auth.py backend/tests/api/test_identities.py
git commit -m "feat(api): identities list/unlink + OAuth link flow"
```

---

## Phase 6: Remove Password Auth

### Task 13: Delete signup/login endpoints, services, bcrypt helpers

**Files:**
- Modify: `backend/app/api/auth.py`
- Delete: `backend/app/services/user_service.py`
- Modify: `backend/app/security.py`
- Delete: `backend/tests/api/test_auth.py`
- Modify: `backend/app/schemas/auth.py` (already updated in Task 11 — no old request schemas remain)

- [ ] **Step 1: Remove `POST /signup` and `POST /login` handlers**

In `backend/app/api/auth.py`, delete the function bodies for `signup(...)` and `login(...)`, and delete their imports (`authenticate`, `create_user`, `LoginRequest`, `SignupRequest`, `AuthError`).

- [ ] **Step 2: Delete the service module**

```bash
rm backend/app/services/user_service.py
```

- [ ] **Step 3: Strip bcrypt helpers from `app/security.py`**

Edit `backend/app/security.py` — replace its full content with:

```python
"""JWT helpers. Session issuance only — password handling removed in
favor of OAuth-only auth.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import jwt

from app.config import settings


def create_access_token(user_id: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id), "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(hours=settings.jwt_access_ttl_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id), "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(days=settings.jwt_refresh_ttl_days)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
```

- [ ] **Step 4: Delete old password-auth tests**

```bash
rm backend/tests/api/test_auth.py
```

(The OAuth flow + onboarding + identities tests cover the replacement surface.)

- [ ] **Step 5: Strip the `bcrypt_cost` setting**

In `app/config.py`, remove the line `bcrypt_cost: int = 12`.

- [ ] **Step 6: Run full backend suite**

```bash
pytest
```

Expected: all tests passing. Any referencing `hash_password`/`verify_password` should already be gone.

- [ ] **Step 7: Commit**

```bash
git add -u
git add backend/app/security.py backend/app/api/auth.py backend/app/config.py
git commit -m "feat(auth): remove email/password signup, login, bcrypt"
```

---

## Phase 7: Provider Adapters (8)

Each adapter is its own task. They share the same Protocol but have distinct URLs, scopes, and userinfo parsing. Each task:

1. Registers the adapter in `PROVIDERS`.
2. Adds a fixture JSON capturing the real userinfo shape.
3. Adds adapter-specific unit tests using `respx` (or `pytest-httpx`) to mock the token + userinfo endpoints.

Install the mocking library once for all provider tasks:

```bash
cd backend && source .venv311/bin/activate && pip install respx && pip install -e ".[dev]"
```

Add `respx>=0.21` to `pyproject.toml`'s `dev` extras.

### Task 14: Google adapter (OIDC)

**Files:**
- Create: `backend/app/core/oauth/google.py`
- Modify: `backend/app/core/oauth/registry.py`
- Create: `backend/tests/oauth/fixtures/google_userinfo.json`
- Create: `backend/tests/oauth/test_google.py`

- [ ] **Step 1: Create fixture**

```json
// backend/tests/oauth/fixtures/google_userinfo.json
{
  "sub": "117389473822915749001",
  "email": "alice@gmail.com",
  "email_verified": true,
  "name": "Alice Kim",
  "picture": "https://lh3.googleusercontent.com/a/AEdFTp8..."
}
```

- [ ] **Step 2: Failing tests**

```python
# backend/tests/oauth/test_google.py
from __future__ import annotations

import json
import pathlib

import httpx
import pytest
import respx

from app.core.oauth.google import GoogleProvider


FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/google_userinfo.json").read_text())


def test_authorize_url_has_required_params():
    p = GoogleProvider()
    url = p.build_authorize_url(
        client_id="cid", redirect_uri="http://x/cb",
        state="st", nonce="nn", code_challenge="cc",
    )
    assert "scope=openid+email+profile" in url or "scope=openid%20email%20profile" in url
    assert "code_challenge=cc" in url
    assert "nonce=nn" in url
    assert "client_id=cid" in url
    assert "state=st" in url
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")


@pytest.mark.asyncio
async def test_fetch_userinfo_from_fixture():
    p = GoogleProvider()
    with respx.mock() as rx:
        rx.get("https://openidconnect.googleapis.com/v1/userinfo").respond(200, json=FIXTURE)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(
                token_response={"access_token": "t", "id_token": "xx.yy.zz"}, http=c
            )
    assert info.subject == FIXTURE["sub"]
    assert info.email == FIXTURE["email"]
    assert info.email_verified is True
    assert info.name == FIXTURE["name"]
    assert info.avatar_url == FIXTURE["picture"]
```

- [ ] **Step 3: Implement adapter**

```python
# backend/app/core/oauth/google.py
"""Google OIDC adapter."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.oauth.base import UserInfo

AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN = "https://oauth2.googleapis.com/token"
USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"


class GoogleProvider:
    name = "google"
    scope = "openid email profile"
    supports_pkce = True
    supports_oidc_nonce = True
    email_is_verified_by_default = True

    def build_authorize_url(
        self, *, client_id: str, redirect_uri: str, state: str,
        nonce: str | None, code_challenge: str | None,
    ) -> str:
        q: dict[str, str] = {
            "client_id": client_id, "redirect_uri": redirect_uri,
            "response_type": "code", "scope": self.scope, "state": state,
            "access_type": "offline", "prompt": "select_account",
        }
        if nonce:
            q["nonce"] = nonce
        if code_challenge:
            q["code_challenge"] = code_challenge
            q["code_challenge_method"] = "S256"
        return f"{AUTHORIZE}?{urlencode(q)}"

    async def exchange_code(
        self, *, code: str, client_id: str, client_secret: str,
        redirect_uri: str, code_verifier: str | None,
        nonce: str | None, http: httpx.AsyncClient,
    ) -> dict[str, Any]:
        data = {
            "grant_type": "authorization_code", "code": code,
            "client_id": client_id, "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        r = await http.post(TOKEN, data=data)
        r.raise_for_status()
        return r.json()

    async def fetch_userinfo(
        self, *, token_response: dict[str, Any], http: httpx.AsyncClient,
    ) -> UserInfo:
        tok = token_response["access_token"]
        r = await http.get(USERINFO, headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        d = r.json()
        return UserInfo(
            subject=str(d["sub"]),
            email=d.get("email"),
            email_verified=bool(d.get("email_verified", False)),
            name=d.get("name"),
            avatar_url=d.get("picture"),
        )
```

- [ ] **Step 4: Register in `registry.py`**

Update `PROVIDERS`:

```python
from app.core.oauth.google import GoogleProvider

PROVIDERS: dict[str, OAuthProvider] = {
    "mock": cast(OAuthProvider, MockProvider()),
    "google": cast(OAuthProvider, GoogleProvider()),
}
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/oauth/test_google.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/oauth/google.py backend/app/core/oauth/registry.py backend/tests/oauth/test_google.py backend/tests/oauth/fixtures/google_userinfo.json
git commit -m "feat(oauth): Google OIDC adapter"
```

---

### Task 15: Naver adapter

**Files:**
- Create: `backend/app/core/oauth/naver.py`
- Modify: `backend/app/core/oauth/registry.py`
- Create: `backend/tests/oauth/fixtures/naver_userinfo.json`
- Create: `backend/tests/oauth/test_naver.py`

- [ ] **Step 1: Fixture**

```json
// backend/tests/oauth/fixtures/naver_userinfo.json
{
  "resultcode": "00",
  "message": "success",
  "response": {
    "id": "32742776",
    "nickname": "앨리스",
    "profile_image": "https://phinf.pstatic.net/...",
    "email": "alice@naver.com",
    "name": "김앨리스"
  }
}
```

- [ ] **Step 2: Failing test**

```python
# backend/tests/oauth/test_naver.py
from __future__ import annotations

import json
import pathlib

import httpx
import pytest
import respx

from app.core.oauth.naver import NaverProvider


FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/naver_userinfo.json").read_text())


def test_authorize_url():
    p = NaverProvider()
    url = p.build_authorize_url(
        client_id="cid", redirect_uri="http://x/cb",
        state="st", nonce=None, code_challenge="cc",
    )
    assert url.startswith("https://nid.naver.com/oauth2.0/authorize?")
    assert "client_id=cid" in url
    assert "state=st" in url


@pytest.mark.asyncio
async def test_fetch_userinfo_parses_nested_response():
    p = NaverProvider()
    with respx.mock() as rx:
        rx.get("https://openapi.naver.com/v1/nid/me").respond(200, json=FIXTURE)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(token_response={"access_token": "t"}, http=c)
    r = FIXTURE["response"]
    assert info.subject == r["id"]
    assert info.email == r["email"]
    assert info.email_verified is True  # Naver policy
    assert info.name == r["name"]
    assert info.avatar_url == r["profile_image"]
```

- [ ] **Step 3: Implement**

```python
# backend/app/core/oauth/naver.py
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.oauth.base import UserInfo

AUTHORIZE = "https://nid.naver.com/oauth2.0/authorize"
TOKEN = "https://nid.naver.com/oauth2.0/token"
USERINFO = "https://openapi.naver.com/v1/nid/me"


class NaverProvider:
    name = "naver"
    scope = ""  # Naver uses console-configured scopes
    supports_pkce = False
    supports_oidc_nonce = False
    email_is_verified_by_default = True  # Naver verifies emails on signup

    def build_authorize_url(self, *, client_id, redirect_uri, state, nonce, code_challenge) -> str:
        q = {"response_type": "code", "client_id": client_id,
             "redirect_uri": redirect_uri, "state": state}
        return f"{AUTHORIZE}?{urlencode(q)}"

    async def exchange_code(self, *, code, client_id, client_secret, redirect_uri,
                            code_verifier, nonce, http) -> dict[str, Any]:
        r = await http.get(TOKEN, params={
            "grant_type": "authorization_code", "client_id": client_id,
            "client_secret": client_secret, "code": code, "state": "x",
        })
        r.raise_for_status()
        return r.json()

    async def fetch_userinfo(self, *, token_response, http) -> UserInfo:
        tok = token_response["access_token"]
        r = await http.get(USERINFO, headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        resp = r.json().get("response", {})
        return UserInfo(
            subject=str(resp["id"]),
            email=resp.get("email"),
            email_verified=bool(resp.get("email")),  # presence = verified in Naver
            name=resp.get("name") or resp.get("nickname"),
            avatar_url=resp.get("profile_image"),
        )
```

- [ ] **Step 4: Register + run tests + commit**

Register in `registry.py`, run `pytest tests/oauth/test_naver.py -v` (2 passed), commit as `feat(oauth): Naver adapter`.

---

### Task 16: Kakao adapter

**Files:** `backend/app/core/oauth/kakao.py`, fixture `kakao_userinfo.json`, test `test_kakao.py`.

- [ ] **Step 1: Fixture**

```json
{
  "id": 1234567890,
  "kakao_account": {
    "email": "alice@kakao.com",
    "is_email_valid": true,
    "is_email_verified": true,
    "profile": {"nickname": "앨리스", "profile_image_url": "https://k.kakaocdn.net/..."}
  }
}
```

- [ ] **Step 2: Test**

```python
# backend/tests/oauth/test_kakao.py
from __future__ import annotations
import json, pathlib, httpx, pytest, respx
from app.core.oauth.kakao import KakaoProvider

FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/kakao_userinfo.json").read_text())


@pytest.mark.asyncio
async def test_kakao_parses_verified_email():
    p = KakaoProvider()
    with respx.mock() as rx:
        rx.get("https://kapi.kakao.com/v2/user/me").respond(200, json=FIXTURE)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(token_response={"access_token": "t"}, http=c)
    assert info.subject == "1234567890"
    assert info.email == "alice@kakao.com"
    assert info.email_verified is True
    assert info.name == "앨리스"
    assert info.avatar_url.startswith("https://k.kakaocdn.net/")


@pytest.mark.asyncio
async def test_kakao_handles_missing_email():
    fx = {**FIXTURE, "kakao_account": {"is_email_verified": False, "profile": {"nickname": "N"}}}
    p = KakaoProvider()
    with respx.mock() as rx:
        rx.get("https://kapi.kakao.com/v2/user/me").respond(200, json=fx)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(token_response={"access_token": "t"}, http=c)
    assert info.email is None
    assert info.email_verified is False
```

- [ ] **Step 3: Implementation**

```python
# backend/app/core/oauth/kakao.py
from __future__ import annotations
from typing import Any
from urllib.parse import urlencode
import httpx
from app.core.oauth.base import UserInfo

AUTHORIZE = "https://kauth.kakao.com/oauth/authorize"
TOKEN = "https://kauth.kakao.com/oauth/token"
USERINFO = "https://kapi.kakao.com/v2/user/me"


class KakaoProvider:
    name = "kakao"
    scope = "account_email profile_nickname profile_image"
    supports_pkce = True
    supports_oidc_nonce = False
    email_is_verified_by_default = False  # verify via kakao_account.is_email_verified

    def build_authorize_url(self, *, client_id, redirect_uri, state, nonce, code_challenge) -> str:
        q = {"response_type": "code", "client_id": client_id,
             "redirect_uri": redirect_uri, "state": state, "scope": self.scope}
        if code_challenge:
            q["code_challenge"] = code_challenge
            q["code_challenge_method"] = "S256"
        return f"{AUTHORIZE}?{urlencode(q)}"

    async def exchange_code(self, *, code, client_id, client_secret, redirect_uri,
                            code_verifier, nonce, http) -> dict[str, Any]:
        data = {"grant_type": "authorization_code", "client_id": client_id,
                "client_secret": client_secret, "code": code, "redirect_uri": redirect_uri}
        if code_verifier:
            data["code_verifier"] = code_verifier
        r = await http.post(TOKEN, data=data)
        r.raise_for_status()
        return r.json()

    async def fetch_userinfo(self, *, token_response, http) -> UserInfo:
        tok = token_response["access_token"]
        r = await http.get(USERINFO, headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        d = r.json()
        acc = d.get("kakao_account", {})
        prof = acc.get("profile", {})
        return UserInfo(
            subject=str(d["id"]),
            email=acc.get("email"),
            email_verified=bool(acc.get("is_email_verified")) and bool(acc.get("is_email_valid", True)),
            name=prof.get("nickname"),
            avatar_url=prof.get("profile_image_url"),
        )
```

- [ ] **Step 4: Register, run `pytest tests/oauth/test_kakao.py -v` (2 passed), commit `feat(oauth): Kakao adapter`.**

---

### Task 17: Facebook adapter

**Files:** `backend/app/core/oauth/facebook.py`, fixture, test.

Scope `email,public_profile`. Email may be missing — not treated as verified.

- [ ] **Step 1: Fixture**

```json
{"id":"10157000000000000","name":"Alice K","email":"alice@fb.com",
 "picture":{"data":{"url":"https://scontent.xx.fbcdn.net/..."}}}
```

- [ ] **Step 2: Test**

```python
# backend/tests/oauth/test_facebook.py
import json, pathlib, httpx, pytest, respx
from app.core.oauth.facebook import FacebookProvider

FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/facebook_userinfo.json").read_text())


@pytest.mark.asyncio
async def test_facebook_parses_email_but_not_verified():
    p = FacebookProvider()
    with respx.mock() as rx:
        rx.get(url__startswith="https://graph.facebook.com/v19.0/me").respond(200, json=FIXTURE)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(token_response={"access_token": "t"}, http=c)
    assert info.subject == FIXTURE["id"]
    assert info.email == FIXTURE["email"]
    assert info.email_verified is False  # FB doesn't guarantee verification
    assert info.avatar_url.startswith("https://")


@pytest.mark.asyncio
async def test_facebook_tolerates_missing_email():
    fx = {k: v for k, v in FIXTURE.items() if k != "email"}
    p = FacebookProvider()
    with respx.mock() as rx:
        rx.get(url__startswith="https://graph.facebook.com/v19.0/me").respond(200, json=fx)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(token_response={"access_token": "t"}, http=c)
    assert info.email is None
```

- [ ] **Step 3: Implementation**

```python
# backend/app/core/oauth/facebook.py
from __future__ import annotations
from typing import Any
from urllib.parse import urlencode
import httpx
from app.core.oauth.base import UserInfo

AUTHORIZE = "https://www.facebook.com/v19.0/dialog/oauth"
TOKEN = "https://graph.facebook.com/v19.0/oauth/access_token"
USERINFO = "https://graph.facebook.com/v19.0/me"


class FacebookProvider:
    name = "facebook"
    scope = "email,public_profile"
    supports_pkce = False
    supports_oidc_nonce = False
    email_is_verified_by_default = False

    def build_authorize_url(self, *, client_id, redirect_uri, state, nonce, code_challenge) -> str:
        q = {"client_id": client_id, "redirect_uri": redirect_uri,
             "state": state, "response_type": "code", "scope": self.scope}
        return f"{AUTHORIZE}?{urlencode(q)}"

    async def exchange_code(self, *, code, client_id, client_secret, redirect_uri,
                            code_verifier, nonce, http) -> dict[str, Any]:
        r = await http.get(TOKEN, params={
            "client_id": client_id, "client_secret": client_secret,
            "code": code, "redirect_uri": redirect_uri,
        })
        r.raise_for_status()
        return r.json()

    async def fetch_userinfo(self, *, token_response, http) -> UserInfo:
        tok = token_response["access_token"]
        r = await http.get(USERINFO, params={
            "fields": "id,name,email,picture", "access_token": tok,
        })
        r.raise_for_status()
        d = r.json()
        pic = (d.get("picture") or {}).get("data", {}).get("url")
        return UserInfo(
            subject=str(d["id"]),
            email=d.get("email"),
            email_verified=False,
            name=d.get("name"),
            avatar_url=pic,
        )
```

- [ ] **Step 4: Register, test, commit as `feat(oauth): Facebook adapter`.**

---

### Task 18: LINE adapter (OIDC)

**Files:** `backend/app/core/oauth/line.py`, fixture, test.

LINE is OIDC with nonce. Email is not guaranteed-verified.

- [ ] **Step 1: Fixture**

```json
{"sub":"U4af4980629...","name":"Alice","email":"alice@line.me",
 "picture":"https://profile.line-scdn.net/..."}
```

- [ ] **Step 2: Test**

```python
# backend/tests/oauth/test_line.py
import json, pathlib, httpx, pytest, respx
from app.core.oauth.line import LineProvider

FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/line_userinfo.json").read_text())

@pytest.mark.asyncio
async def test_line_parses_profile():
    p = LineProvider()
    with respx.mock() as rx:
        rx.get("https://api.line.me/oauth2/v2.1/userinfo").respond(200, json=FIXTURE)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(token_response={"access_token": "t"}, http=c)
    assert info.subject == FIXTURE["sub"]
    assert info.email == FIXTURE["email"]
    assert info.email_verified is False
    assert info.avatar_url == FIXTURE["picture"]
```

- [ ] **Step 3: Implementation**

```python
# backend/app/core/oauth/line.py
from __future__ import annotations
from typing import Any
from urllib.parse import urlencode
import httpx
from app.core.oauth.base import UserInfo

AUTHORIZE = "https://access.line.me/oauth2/v2.1/authorize"
TOKEN = "https://api.line.me/oauth2/v2.1/token"
USERINFO = "https://api.line.me/oauth2/v2.1/userinfo"


class LineProvider:
    name = "line"
    scope = "openid profile email"
    supports_pkce = True
    supports_oidc_nonce = True
    email_is_verified_by_default = False

    def build_authorize_url(self, *, client_id, redirect_uri, state, nonce, code_challenge) -> str:
        q = {"response_type": "code", "client_id": client_id,
             "redirect_uri": redirect_uri, "state": state, "scope": self.scope}
        if nonce:
            q["nonce"] = nonce
        if code_challenge:
            q["code_challenge"] = code_challenge
            q["code_challenge_method"] = "S256"
        return f"{AUTHORIZE}?{urlencode(q)}"

    async def exchange_code(self, *, code, client_id, client_secret, redirect_uri,
                            code_verifier, nonce, http) -> dict[str, Any]:
        data = {"grant_type": "authorization_code", "code": code,
                "redirect_uri": redirect_uri, "client_id": client_id,
                "client_secret": client_secret}
        if code_verifier:
            data["code_verifier"] = code_verifier
        r = await http.post(TOKEN, data=data)
        r.raise_for_status()
        return r.json()

    async def fetch_userinfo(self, *, token_response, http) -> UserInfo:
        tok = token_response["access_token"]
        r = await http.get(USERINFO, headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        d = r.json()
        return UserInfo(
            subject=str(d["sub"]),
            email=d.get("email"),
            email_verified=False,
            name=d.get("name"),
            avatar_url=d.get("picture"),
        )
```

- [ ] **Step 4: Register, test, commit as `feat(oauth): LINE OIDC adapter`.**

---

### Task 19: WeChat adapter (non-standard)

**Files:** `backend/app/core/oauth/wechat.py`, fixture, test.

Differences: `appid`/`secret` instead of `client_id`/`client_secret`; authorize URL has `#wechat_redirect` fragment; token endpoint returns `openid`/`unionid` JSON; separate userinfo endpoint; no email.

- [ ] **Step 1: Fixture**

```json
{"openid":"o_abc123","unionid":"u_xyz789","nickname":"Alice Wang",
 "headimgurl":"https://thirdwx.qlogo.cn/..."}
```

- [ ] **Step 2: Test**

```python
# backend/tests/oauth/test_wechat.py
import json, pathlib, httpx, pytest, respx
from app.core.oauth.wechat import WechatProvider

FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/wechat_userinfo.json").read_text())

def test_wechat_authorize_has_fragment():
    p = WechatProvider()
    url = p.build_authorize_url(client_id="appid", redirect_uri="http://x/cb",
                                state="st", nonce=None, code_challenge=None)
    assert url.endswith("#wechat_redirect")
    assert "appid=appid" in url


@pytest.mark.asyncio
async def test_wechat_prefers_unionid_over_openid():
    p = WechatProvider()
    with respx.mock() as rx:
        rx.get("https://api.weixin.qq.com/sns/userinfo").respond(200, json=FIXTURE)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(
                token_response={"access_token": "t", "openid": "o_abc123"}, http=c
            )
    assert info.subject == "u_xyz789"  # unionid wins
    assert info.email is None
    assert info.name == "Alice Wang"


@pytest.mark.asyncio
async def test_wechat_falls_back_to_openid_when_no_unionid():
    fx = {k: v for k, v in FIXTURE.items() if k != "unionid"}
    p = WechatProvider()
    with respx.mock() as rx:
        rx.get("https://api.weixin.qq.com/sns/userinfo").respond(200, json=fx)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(
                token_response={"access_token": "t", "openid": "o_abc123"}, http=c
            )
    assert info.subject == "o_abc123"
```

- [ ] **Step 3: Implementation**

```python
# backend/app/core/oauth/wechat.py
from __future__ import annotations
from typing import Any
from urllib.parse import urlencode
import httpx
from app.core.oauth.base import UserInfo

AUTHORIZE = "https://open.weixin.qq.com/connect/qrconnect"
TOKEN = "https://api.weixin.qq.com/sns/oauth2/access_token"
USERINFO = "https://api.weixin.qq.com/sns/userinfo"


class WechatProvider:
    name = "wechat"
    scope = "snsapi_login"
    supports_pkce = False
    supports_oidc_nonce = False
    email_is_verified_by_default = False  # WeChat does not return email

    def build_authorize_url(self, *, client_id, redirect_uri, state, nonce, code_challenge) -> str:
        q = {"appid": client_id, "redirect_uri": redirect_uri,
             "response_type": "code", "scope": self.scope, "state": state}
        return f"{AUTHORIZE}?{urlencode(q)}#wechat_redirect"

    async def exchange_code(self, *, code, client_id, client_secret, redirect_uri,
                            code_verifier, nonce, http) -> dict[str, Any]:
        r = await http.get(TOKEN, params={
            "appid": client_id, "secret": client_secret,
            "code": code, "grant_type": "authorization_code",
        })
        r.raise_for_status()
        # WeChat returns 200 + JSON body even on errors ({"errcode": ..., "errmsg": ...}).
        d = r.json()
        if "errcode" in d:
            raise RuntimeError(f"wechat_token_error: {d.get('errmsg')}")
        return d

    async def fetch_userinfo(self, *, token_response, http) -> UserInfo:
        r = await http.get(USERINFO, params={
            "access_token": token_response["access_token"],
            "openid": token_response["openid"],
        })
        r.raise_for_status()
        d = r.json()
        if "errcode" in d:
            raise RuntimeError(f"wechat_userinfo_error: {d.get('errmsg')}")
        subject = d.get("unionid") or token_response.get("openid") or d.get("openid")
        return UserInfo(
            subject=str(subject),
            email=None,
            email_verified=False,
            name=d.get("nickname"),
            avatar_url=d.get("headimgurl"),
        )
```

- [ ] **Step 4: Register, test, commit as `feat(oauth): WeChat adapter with unionid preference`.**

---

### Task 20: LinkedIn adapter (OIDC)

**Files:** `backend/app/core/oauth/linkedin.py`, fixture, test.

- [ ] **Step 1: Fixture**

```json
{"sub":"782j_h4h6K","email_verified":true,"email":"alice@linkedin.com",
 "name":"Alice Kim","picture":"https://media.licdn.com/..."}
```

- [ ] **Step 2: Test**

```python
# backend/tests/oauth/test_linkedin.py
import json, pathlib, httpx, pytest, respx
from app.core.oauth.linkedin import LinkedInProvider

FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/linkedin_userinfo.json").read_text())

@pytest.mark.asyncio
async def test_linkedin_oidc_userinfo():
    p = LinkedInProvider()
    with respx.mock() as rx:
        rx.get("https://api.linkedin.com/v2/userinfo").respond(200, json=FIXTURE)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(token_response={"access_token": "t"}, http=c)
    assert info.subject == FIXTURE["sub"]
    assert info.email == FIXTURE["email"]
    assert info.email_verified is True
```

- [ ] **Step 3: Implementation**

```python
# backend/app/core/oauth/linkedin.py
from __future__ import annotations
from typing import Any
from urllib.parse import urlencode
import httpx
from app.core.oauth.base import UserInfo

AUTHORIZE = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO = "https://api.linkedin.com/v2/userinfo"


class LinkedInProvider:
    name = "linkedin"
    scope = "openid profile email"
    supports_pkce = True
    supports_oidc_nonce = True
    email_is_verified_by_default = True

    def build_authorize_url(self, *, client_id, redirect_uri, state, nonce, code_challenge) -> str:
        q = {"response_type": "code", "client_id": client_id,
             "redirect_uri": redirect_uri, "state": state, "scope": self.scope}
        if nonce:
            q["nonce"] = nonce
        if code_challenge:
            q["code_challenge"] = code_challenge
            q["code_challenge_method"] = "S256"
        return f"{AUTHORIZE}?{urlencode(q)}"

    async def exchange_code(self, *, code, client_id, client_secret, redirect_uri,
                            code_verifier, nonce, http) -> dict[str, Any]:
        data = {"grant_type": "authorization_code", "code": code,
                "client_id": client_id, "client_secret": client_secret,
                "redirect_uri": redirect_uri}
        if code_verifier:
            data["code_verifier"] = code_verifier
        r = await http.post(TOKEN, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        r.raise_for_status()
        return r.json()

    async def fetch_userinfo(self, *, token_response, http) -> UserInfo:
        tok = token_response["access_token"]
        r = await http.get(USERINFO, headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        d = r.json()
        return UserInfo(
            subject=str(d["sub"]),
            email=d.get("email"),
            email_verified=bool(d.get("email_verified", False)),
            name=d.get("name"),
            avatar_url=d.get("picture"),
        )
```

- [ ] **Step 4: Register, test, commit as `feat(oauth): LinkedIn OIDC adapter`.**

---

### Task 21: Yahoo! JAPAN adapter (OIDC)

**Files:** `backend/app/core/oauth/yahoo_jp.py`, fixture, test.

- [ ] **Step 1: Fixture**

```json
{"sub":"XBCDEFGHIJK","name":"アリス","email":"alice@yahoo.co.jp",
 "email_verified":true,"picture":"https://profile.yimg.jp/..."}
```

- [ ] **Step 2: Test**

```python
# backend/tests/oauth/test_yahoo_jp.py
import json, pathlib, httpx, pytest, respx
from app.core.oauth.yahoo_jp import YahooJPProvider

FIXTURE = json.loads((pathlib.Path(__file__).parent / "fixtures/yahoo_jp_userinfo.json").read_text())

@pytest.mark.asyncio
async def test_yahoo_jp_oidc_userinfo():
    p = YahooJPProvider()
    with respx.mock() as rx:
        rx.get("https://userinfo.yahooapis.jp/yconnect/v2/attribute").respond(200, json=FIXTURE)
        async with httpx.AsyncClient() as c:
            info = await p.fetch_userinfo(token_response={"access_token": "t"}, http=c)
    assert info.subject == FIXTURE["sub"]
    assert info.email == FIXTURE["email"]
    assert info.email_verified is True
```

- [ ] **Step 3: Implementation**

```python
# backend/app/core/oauth/yahoo_jp.py
from __future__ import annotations
from typing import Any
from urllib.parse import urlencode
import httpx
from app.core.oauth.base import UserInfo

AUTHORIZE = "https://auth.login.yahoo.co.jp/yconnect/v2/authorization"
TOKEN = "https://auth.login.yahoo.co.jp/yconnect/v2/token"
USERINFO = "https://userinfo.yahooapis.jp/yconnect/v2/attribute"


class YahooJPProvider:
    name = "yahoo_jp"
    scope = "openid email profile"
    supports_pkce = True
    supports_oidc_nonce = True
    email_is_verified_by_default = True

    def build_authorize_url(self, *, client_id, redirect_uri, state, nonce, code_challenge) -> str:
        q = {"response_type": "code", "client_id": client_id,
             "redirect_uri": redirect_uri, "state": state, "scope": self.scope}
        if nonce:
            q["nonce"] = nonce
        if code_challenge:
            q["code_challenge"] = code_challenge
            q["code_challenge_method"] = "S256"
        return f"{AUTHORIZE}?{urlencode(q)}"

    async def exchange_code(self, *, code, client_id, client_secret, redirect_uri,
                            code_verifier, nonce, http) -> dict[str, Any]:
        data = {"grant_type": "authorization_code", "code": code,
                "redirect_uri": redirect_uri, "client_id": client_id,
                "client_secret": client_secret}
        if code_verifier:
            data["code_verifier"] = code_verifier
        r = await http.post(TOKEN, data=data)
        r.raise_for_status()
        return r.json()

    async def fetch_userinfo(self, *, token_response, http) -> UserInfo:
        tok = token_response["access_token"]
        r = await http.get(USERINFO, headers={"Authorization": f"Bearer {tok}"})
        r.raise_for_status()
        d = r.json()
        return UserInfo(
            subject=str(d["sub"]),
            email=d.get("email"),
            email_verified=bool(d.get("email_verified", False)),
            name=d.get("name"),
            avatar_url=d.get("picture"),
        )
```

- [ ] **Step 4: Register, test, commit as `feat(oauth): Yahoo! JAPAN OIDC adapter`.**

---

## Phase 8: Frontend — AuthGate + Login Page

### Task 22: `AuthGate` client guard

**Files:**
- Create: `web/components/AuthGate.tsx`
- Modify: `web/app/layout.tsx`
- Create: `web/tests/auth-gate.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
// web/tests/auth-gate.test.tsx
import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AuthGate from "@/components/AuthGate";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: push }),
  usePathname: () => "/game/new",
}));

describe("AuthGate", () => {
  beforeEach(() => {
    push.mockClear();
    global.fetch = vi.fn();
  });

  it("redirects to /login when unauthenticated", async () => {
    (global.fetch as any).mockResolvedValue({ status: 401 });
    render(<AuthGate>body</AuthGate>);
    await waitFor(() => expect(push).toHaveBeenCalledWith("/login?next=%2Fgame%2Fnew"));
  });

  it("redirects to /onboarding when needs_onboarding is true", async () => {
    (global.fetch as any).mockResolvedValue({
      status: 200,
      json: async () => ({ needs_onboarding: true }),
    });
    render(<AuthGate>body</AuthGate>);
    await waitFor(() => expect(push).toHaveBeenCalledWith("/onboarding"));
  });

  it("renders children when authorized and onboarded", async () => {
    (global.fetch as any).mockResolvedValue({
      status: 200,
      json: async () => ({ needs_onboarding: false }),
    });
    const { findByText } = render(<AuthGate>app-content</AuthGate>);
    await findByText("app-content");
    expect(push).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run — expect fail**

```bash
cd web && npm test -- --run tests/auth-gate.test.tsx
```

- [ ] **Step 3: Implement**

```tsx
// web/components/AuthGate.tsx
"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const PUBLIC = new Set(["/login", "/onboarding"]);

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname() ?? "/";
  const [ready, setReady] = useState(PUBLIC.has(pathname));

  useEffect(() => {
    if (PUBLIC.has(pathname)) { setReady(true); return; }
    let cancelled = false;
    (async () => {
      const r = await fetch("/api/auth/me", { credentials: "include" });
      if (cancelled) return;
      if (r.status === 401) {
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        return;
      }
      const me = await r.json();
      if (me.needs_onboarding) {
        router.replace("/onboarding");
        return;
      }
      setReady(true);
    })();
    return () => { cancelled = true; };
  }, [pathname, router]);

  if (!ready) return null;
  return <>{children}</>;
}
```

- [ ] **Step 4: Wrap layout**

In `web/app/layout.tsx`, wrap the body content with `<AuthGate>...</AuthGate>`. Example:

```tsx
import AuthGate from "@/components/AuthGate";

// ... inside <body>:
<AuthGate>{children}</AuthGate>
```

- [ ] **Step 5: Run tests**

```bash
npm test -- --run tests/auth-gate.test.tsx
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add web/components/AuthGate.tsx web/app/layout.tsx web/tests/auth-gate.test.tsx
git commit -m "feat(web): AuthGate client-side redirect for auth + onboarding"
```

---

### Task 23: Provider logo SVGs (8)

**Files:**
- Create: `web/components/editorial/icons/oauth/{google,naver,kakao,facebook,line,wechat,linkedin,yahoo_jp}.tsx`
- Create: `web/components/editorial/icons/oauth/index.ts`
- Create: `docs/oauth-brand-assets.md`

- [ ] **Step 1: Create placeholder SVG components (one file per provider)**

Each file exports a default React component with 24×24 SVG. Example for Google:

```tsx
// web/components/editorial/icons/oauth/google.tsx
export default function GoogleLogo({ className }: { className?: string }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" className={className}>
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.99.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.1A6.6 6.6 0 0 1 5.5 12c0-.73.13-1.44.34-2.1V7.07H2.18a11 11 0 0 0 0 9.86l3.66-2.83z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.07.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.83C6.71 7.3 9.14 5.38 12 5.38z"/>
    </svg>
  );
}
```

Use each provider's official brand SVG (24×24) from `docs/oauth-brand-assets.md`. For each provider file, copy the official monocolor or official-color mark according to that provider's brand guidelines. If an official asset is not yet sourced, use a neutral placeholder mark (the first letter of the provider's name in `fill="currentColor"` 16px) and leave a `TODO(brand-asset)` comment — the asset must be replaced before production launch.

Provide each of the remaining 7 files (`naver.tsx`, `kakao.tsx`, `facebook.tsx`, `line.tsx`, `wechat.tsx`, `linkedin.tsx`, `yahoo_jp.tsx`) with the same shape. Scaffold each as a placeholder now; swap in brand SVGs while writing `docs/oauth-brand-assets.md` in the next step.

Neutral placeholder scaffold:

```tsx
// web/components/editorial/icons/oauth/<provider>.tsx
// TODO(brand-asset): replace with the official <Provider> SVG before launch.
export default function <Provider>Logo({ className }: { className?: string }) {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" className={className}>
      <rect x="1" y="1" width="22" height="22" rx="4" fill="currentColor" opacity="0.08"/>
      <text x="12" y="16" textAnchor="middle" fontSize="11" fontFamily="sans-serif"
        fill="currentColor">{/* first letter e.g. "N" */}</text>
    </svg>
  );
}
```

- [ ] **Step 2: Create index file**

```ts
// web/components/editorial/icons/oauth/index.ts
import Google from "./google";
import Naver from "./naver";
import Kakao from "./kakao";
import Facebook from "./facebook";
import Line from "./line";
import Wechat from "./wechat";
import LinkedIn from "./linkedin";
import YahooJp from "./yahoo_jp";

export const OAUTH_LOGOS: Record<string, React.ComponentType<{ className?: string }>> = {
  google: Google, naver: Naver, kakao: Kakao, facebook: Facebook,
  line: Line, wechat: Wechat, linkedin: LinkedIn, yahoo_jp: YahooJp,
};
```

- [ ] **Step 3: Brand assets doc**

Create `docs/oauth-brand-assets.md`:

```markdown
# OAuth provider brand assets

Each provider has a brand guideline you MUST comply with for the login
button. Sources are linked here; update the SVG under
`web/components/editorial/icons/oauth/<provider>.tsx` before launch.

| Provider | Guideline URL | Asset status |
|----------|---------------|--------------|
| Google   | https://developers.google.com/identity/branding-guidelines | TODO: pull official SVG |
| Naver    | https://developers.naver.com/docs/login/bi/bi.md | TODO |
| Kakao    | https://developers.kakao.com/docs/latest/ko/reference/design-guide | TODO |
| Facebook | https://about.meta.com/brand/resources/facebook/logo/ | TODO |
| LINE     | https://developers.line.biz/en/docs/line-login/login-button/ | TODO |
| WeChat   | https://open.weixin.qq.com/cgi-bin/frame?t=resource/res_main_tmpl&lang=en_US | TODO |
| LinkedIn | https://brand.linkedin.com/downloads | TODO |
| Yahoo JP | https://developer.yahoo.co.jp/yconnect/v2/brand/ | TODO |
```

- [ ] **Step 4: Commit**

```bash
git add web/components/editorial/icons/oauth docs/oauth-brand-assets.md
git commit -m "feat(web): provider logo SVGs (placeholders) + brand-asset source doc"
```

---

### Task 24: Login page rewrite

**Files:**
- Modify: `web/app/login/page.tsx`
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`
- Create: `web/tests/login-page.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
// web/tests/login-page.test.tsx
import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LoginPage from "@/app/login/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    global.fetch = vi.fn().mockResolvedValue({
      status: 200,
      json: async () => ({ providers: ["google", "kakao"] }),
    });
  });

  it("renders only enabled providers", async () => {
    const { findByRole, queryByRole } = render(<LoginPage />);
    await findByRole("link", { name: /google/i });
    await findByRole("link", { name: /kakao/i });
    expect(queryByRole("link", { name: /naver/i })).toBeNull();
  });
});
```

- [ ] **Step 2: Failing run**

```bash
npm test -- --run tests/login-page.test.tsx
```

- [ ] **Step 3: Rewrite login page**

```tsx
// web/app/login/page.tsx
"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useT } from "@/lib/i18n";
import { OAUTH_LOGOS } from "@/components/editorial/icons/oauth";

const ORDER = ["google", "naver", "kakao", "facebook", "line", "wechat", "linkedin", "yahoo_jp"] as const;

function Content() {
  const t = useT();
  const search = useSearchParams();
  const next = search.get("next") || "/";
  const err = search.get("error");
  const with_ = search.get("with");
  const [enabled, setEnabled] = useState<string[]>([]);

  useEffect(() => {
    fetch("/api/auth/providers", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setEnabled((d.providers as string[]) ?? []));
  }, []);

  const ordered = ORDER.filter((p) => enabled.includes(p));

  return (
    <main className="mx-auto max-w-sm py-12">
      <h1 className="font-serif text-3xl mb-6">{t("auth.signInHeading")}</h1>
      {err && (
        <div role="alert" className="text-sm mb-4 text-ink-mute">
          {err === "oauth_email_conflict" && with_
            ? t("errors.oauth_email_conflict").replace("{existing}", t(`auth.providerName.${with_}`))
            : t(`errors.${err}`)}
        </div>
      )}
      <ul className="space-y-2">
        {ordered.map((p) => {
          const Logo = OAUTH_LOGOS[p];
          return (
            <li key={p}>
              <a
                href={`/api/auth/oauth/${p}/start?next=${encodeURIComponent(next)}`}
                className="flex items-center gap-3 border border-ink/10 rounded-sm px-4 py-3 hover:bg-paper-deep"
              >
                <Logo className="shrink-0" />
                <span>{t("auth.continueWith").replace("{provider}", t(`auth.providerName.${p}`))}</span>
              </a>
            </li>
          );
        })}
      </ul>
      <p className="text-ink-faint text-sm mt-6">{t("auth.onboardingHint")}</p>
    </main>
  );
}

export default function LoginPage() {
  return <Suspense fallback={null}><Content /></Suspense>;
}
```

- [ ] **Step 4: Update i18n files**

In `web/lib/i18n/ko.json` and `en.json`, remove the old `auth.email`, `auth.password`, `auth.displayName`, `auth.signup`, `auth.mustBeLongerPassword`, `errors.invalid_credentials`, `errors.email_already_registered` keys.

Add to both files (translated for each locale):

```json
// ko.json — auth block
"signInHeading": "로그인 / 가입",
"continueWith": "{provider}로 계속하기",
"onboardingHint": "소셜 로그인 후 국적을 한 번만 선택하면 가입이 완료됩니다.",
"providerName": {
  "google": "Google","naver":"Naver","kakao":"Kakao","facebook":"Facebook",
  "line":"LINE","wechat":"WeChat","linkedin":"LinkedIn","yahoo_jp":"Yahoo! JAPAN"
}
```

```json
// ko.json — errors block (add)
"oauth_state_invalid": "보안 검증에 실패했습니다. 다시 시도해주세요",
"oauth_provider_error": "소셜 로그인 중 오류가 발생했습니다",
"oauth_email_conflict": "이미 {existing}(으)로 가입된 이메일입니다. {existing}(으)로 로그인 후 설정에서 연결해주세요",
"oauth_already_linked": "이 계정은 이미 다른 사용자에 연결되어 있습니다",
"oauth_unlink_last": "마지막 로그인 수단은 해제할 수 없습니다",
"invalid_country": "국가를 선택해주세요",
"already_onboarded": "이미 가입이 완료된 계정입니다"
```

Provide `en.json` translations:

```json
// en.json — auth block
"signInHeading": "Sign in / Sign up",
"continueWith": "Continue with {provider}",
"onboardingHint": "After social sign-in, choose a nationality once to complete signup.",
"providerName": {
  "google": "Google","naver":"Naver","kakao":"Kakao","facebook":"Facebook",
  "line":"LINE","wechat":"WeChat","linkedin":"LinkedIn","yahoo_jp":"Yahoo! JAPAN"
}
```

```json
// en.json — errors
"oauth_state_invalid": "Security check failed. Please try again.",
"oauth_provider_error": "Social sign-in error. Please try again.",
"oauth_email_conflict": "This email is already registered with {existing}. Please sign in with {existing} and link the other provider from Settings.",
"oauth_already_linked": "This identity is already linked to another account.",
"oauth_unlink_last": "You can't remove your only sign-in method.",
"invalid_country": "Please choose a country.",
"already_onboarded": "This account has already completed onboarding."
```

- [ ] **Step 5: Run tests**

```bash
npm test -- --run tests/login-page.test.tsx
```

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add web/app/login/page.tsx web/tests/login-page.test.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): social-only login page + i18n cleanup"
```

---

## Phase 9: Onboarding page + Combobox

### Task 25: `<Combobox>` UI primitive

**Files:**
- Create: `web/components/ui/combobox.tsx`
- Create: `web/tests/combobox.test.tsx`

- [ ] **Step 1: Failing test**

```tsx
// web/tests/combobox.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import Combobox from "@/components/ui/combobox";

const OPTIONS = [
  { value: "KR", label: "Republic of Korea" },
  { value: "JP", label: "Japan" },
  { value: "US", label: "United States" },
];

describe("Combobox", () => {
  it("filters options by label", async () => {
    const u = userEvent.setup();
    render(<Combobox options={OPTIONS} value="KR" onChange={() => {}} placeholder="search" />);
    await u.click(screen.getByRole("combobox"));
    const input = await screen.findByPlaceholderText("search");
    await u.type(input, "Jap");
    expect(await screen.findByRole("option", { name: /Japan/i })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Republic of Korea/i })).toBeNull();
  });

  it("keyboard selects an option", async () => {
    const u = userEvent.setup();
    let picked = "";
    render(<Combobox options={OPTIONS} value={null} onChange={(v) => { picked = v; }} placeholder="x" />);
    await u.click(screen.getByRole("combobox"));
    await u.keyboard("{ArrowDown}{ArrowDown}{Enter}");
    expect(picked).toBe("JP");
  });
});
```

- [ ] **Step 2: Install a headless popover if missing**

`@radix-ui/react-popover` is already in the project — use it.

- [ ] **Step 3: Implement**

```tsx
// web/components/ui/combobox.tsx
"use client";
import * as Popover from "@radix-ui/react-popover";
import { useMemo, useRef, useState } from "react";

export interface Option { value: string; label: string; hint?: string; }

interface Props {
  options: Option[];
  value: string | null;
  onChange: (v: string) => void;
  placeholder?: string;
}

export default function Combobox({ options, value, onChange, placeholder }: Props) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return options;
    return options.filter(
      (o) => o.label.toLowerCase().includes(needle) || o.value.toLowerCase().includes(needle),
    );
  }, [q, options]);

  const selectedLabel = options.find((o) => o.value === value)?.label ?? placeholder ?? "";

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const pick = filtered[activeIndex];
      if (pick) { onChange(pick.value); setOpen(false); setQ(""); }
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <Popover.Root open={open} onOpenChange={(v) => { setOpen(v); if (v) setActiveIndex(0); }}>
      <Popover.Trigger asChild>
        <button
          role="combobox"
          aria-expanded={open}
          className="w-full flex items-center justify-between border border-ink/10 rounded-sm px-3 py-2 text-left"
          type="button"
        >
          <span>{selectedLabel}</span>
          <span className="font-mono text-ink-mute text-xs">{value ?? ""}</span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content sideOffset={4} className="w-[var(--radix-popover-trigger-width)] bg-paper border border-ink/10 rounded-sm p-1">
          <input
            ref={inputRef} autoFocus placeholder={placeholder}
            className="w-full border-b border-ink/10 bg-transparent px-2 py-1 outline-none"
            value={q} onChange={(e) => { setQ(e.target.value); setActiveIndex(0); }} onKeyDown={handleKey}
          />
          <ul role="listbox" className="max-h-64 overflow-auto mt-1">
            {filtered.map((o, i) => (
              <li
                key={o.value} role="option"
                aria-selected={o.value === value}
                className={`flex items-center justify-between px-2 py-1 cursor-pointer ${
                  i === activeIndex ? "bg-paper-deep" : ""
                }`}
                onMouseEnter={() => setActiveIndex(i)}
                onMouseDown={(e) => { e.preventDefault(); onChange(o.value); setOpen(false); setQ(""); }}
              >
                <span>{o.label}</span>
                <span className="font-mono text-ink-mute text-xs">{o.value}</span>
              </li>
            ))}
          </ul>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
```

- [ ] **Step 4: Run, commit**

```bash
npm test -- --run tests/combobox.test.tsx
git add web/components/ui/combobox.tsx web/tests/combobox.test.tsx
git commit -m "feat(ui): Combobox primitive with keyboard nav"
```

---

### Task 26: Onboarding page

**Files:**
- Create: `web/app/onboarding/page.tsx`
- Modify: i18n files

- [ ] **Step 1: i18n**

Add to `ko.json`:

```json
"onboarding": {
  "welcome": "환영합니다, {name}님",
  "subtitle": "대국을 시작하기 전에 몇 가지만 확인할게요",
  "displayName": "표시 이름",
  "country": "국적",
  "countrySearchPlaceholder": "국가 검색…",
  "submit": "시작하기"
}
```

Add equivalent English strings to `en.json`.

- [ ] **Step 2: Create page**

```tsx
// web/app/onboarding/page.tsx
"use client";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Combobox from "@/components/ui/combobox";
import { COUNTRY_CODES, guessCountryFromLocale } from "@/lib/countries";
import { useT, useLocale } from "@/lib/i18n";

export default function OnboardingPage() {
  const t = useT();
  const locale = useLocale();
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [country, setCountry] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" }).then(async (r) => {
      if (r.status === 401) { router.replace("/login"); return; }
      const me = await r.json();
      if (!me.needs_onboarding) { router.replace("/"); return; }
      setDisplayName(me.display_name ?? "");
      setCountry(guessCountryFromLocale(
        typeof navigator !== "undefined" ? navigator.language : locale,
      ));
    });
  }, [router, locale]);

  const dn = useMemo(() => {
    try {
      return new Intl.DisplayNames([locale], { type: "region" });
    } catch {
      return null;
    }
  }, [locale]);

  const options = useMemo(() => {
    return COUNTRY_CODES.map((code) => ({
      value: code,
      label: dn?.of(code) ?? code,
    })).sort((a, b) => a.label.localeCompare(b.label, locale));
  }, [dn, locale]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (!country) { setErr("invalid_country"); return; }
    const r = await fetch("/api/auth/onboarding", {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ country_code: country, display_name: displayName || undefined }),
    });
    if (r.ok) { router.replace("/"); return; }
    const body = await r.json().catch(() => ({} as { detail?: string }));
    setErr(body.detail || "validation");
  }

  return (
    <main className="mx-auto max-w-md py-12">
      <h1 className="font-serif text-3xl">{t("onboarding.welcome").replace("{name}", displayName || "")}</h1>
      <hr className="my-4 border-ink/10" />
      <p className="text-ink-mute mb-6">{t("onboarding.subtitle")}</p>
      <form onSubmit={submit} className="space-y-4">
        <label className="block">
          <span className="text-sm">{t("onboarding.displayName")}</span>
          <input
            className="mt-1 w-full border border-ink/10 rounded-sm px-3 py-2"
            value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={64}
          />
        </label>
        <div>
          <span className="text-sm">{t("onboarding.country")}</span>
          <div className="mt-1">
            <Combobox
              options={options} value={country} onChange={setCountry}
              placeholder={t("onboarding.countrySearchPlaceholder")}
            />
          </div>
        </div>
        {err && <div role="alert" className="text-sm text-ink-mute">{t(`errors.${err}`)}</div>}
        <button type="submit" className="border border-ink/10 rounded-sm px-4 py-2">
          {t("onboarding.submit")}
        </button>
      </form>
    </main>
  );
}
```

- [ ] **Step 3: Manual browser test**

```bash
cd web && npm run dev
```

Visit `http://localhost:3000/login`, click Mock (with `MOCK_OAUTH_ENABLED=true` on backend), land on `/onboarding`, pick country, submit, should route to `/`.

- [ ] **Step 4: Commit**

```bash
git add web/app/onboarding/page.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): onboarding page with country combobox + Intl names"
```

---

## Phase 10: Settings — Linked Accounts

### Task 27: "Linked Accounts" section in `/settings`

**Files:**
- Modify: `web/app/settings/page.tsx`
- Modify: i18n

- [ ] **Step 1: i18n additions**

Add to `ko.json` under `settings`:

```json
"linkedAccounts": "연결된 로그인",
"linkMore": "다른 방법으로도 로그인하기",
"unlink": "해제",
"unlinkLastTooltip": "마지막 로그인 수단은 해제할 수 없습니다",
"linkedSuccess": "{provider}가 연결되었습니다",
"unlinkedSuccess": "{provider} 연결이 해제되었습니다"
```

Mirror for `en.json`.

- [ ] **Step 2: Implement the section**

Inside `web/app/settings/page.tsx` add (preserving the existing UI; insert below existing blocks):

```tsx
"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { OAUTH_LOGOS } from "@/components/editorial/icons/oauth";
import { useT } from "@/lib/i18n";

interface Identity { id: number; provider: string; email: string | null; created_at: string; }

function LinkedAccounts() {
  const t = useT();
  const [items, setItems] = useState<Identity[]>([]);
  const [available, setAvailable] = useState<string[]>([]);
  const sp = useSearchParams();

  useEffect(() => {
    fetch("/api/auth/identities", { credentials: "include" })
      .then((r) => r.json())
      .then((data: Identity[]) => setItems(data));
    fetch("/api/auth/providers", { credentials: "include" })
      .then((r) => r.json())
      .then((d) => setAvailable((d.providers as string[]) ?? []));
  }, []);

  useEffect(() => {
    const linked = sp.get("linked");
    if (linked) toast.success(t("settings.linkedSuccess").replace("{provider}", t(`auth.providerName.${linked}`)));
    const err = sp.get("error");
    if (err) toast.error(t(`errors.${err}`));
  }, [sp, t]);

  async function unlink(id: number) {
    if (items.length <= 1) return;
    const r = await fetch(`/api/auth/identities/${id}`, { method: "DELETE", credentials: "include" });
    if (r.ok) {
      setItems((prev) => prev.filter((x) => x.id !== id));
      toast.success(t("settings.unlinkedSuccess").replace("{provider}", ""));
    } else {
      const d = await r.json().catch(() => ({ detail: "oauth_unlink_last" } as { detail?: string }));
      toast.error(t(`errors.${d.detail ?? "validation"}`));
    }
  }

  async function linkMore(provider: string) {
    const r = await fetch(`/api/auth/oauth/${provider}/link`, { method: "POST", credentials: "include" });
    if (!r.ok) { toast.error(t("errors.oauth_provider_error")); return; }
    const d = (await r.json()) as { authorize_url: string };
    window.location.assign(d.authorize_url);
  }

  const linkedSet = new Set(items.map((i) => i.provider));
  const unlinked = available.filter((p) => !linkedSet.has(p));
  const isLast = items.length <= 1;

  return (
    <section className="mt-8">
      <h2 className="font-serif text-xl mb-4">{t("settings.linkedAccounts")}</h2>
      <ul className="space-y-2">
        {items.map((i) => {
          const Logo = OAUTH_LOGOS[i.provider];
          return (
            <li key={i.id} className="flex items-center justify-between border border-ink/10 rounded-sm px-3 py-2">
              <div className="flex items-center gap-3">
                {Logo && <Logo />}
                <div>
                  <div>{t(`auth.providerName.${i.provider}`)}</div>
                  <div className="text-sm text-ink-mute">{i.email ?? "—"}</div>
                </div>
              </div>
              <button
                onClick={() => unlink(i.id)} disabled={isLast}
                title={isLast ? t("settings.unlinkLastTooltip") : ""}
                className="text-sm border border-ink/10 rounded-sm px-3 py-1 disabled:opacity-40"
              >{t("settings.unlink")}</button>
            </li>
          );
        })}
      </ul>
      {unlinked.length > 0 && (
        <div className="mt-4">
          <div className="text-sm text-ink-mute mb-2">{t("settings.linkMore")}</div>
          <div className="flex flex-wrap gap-2">
            {unlinked.map((p) => {
              const Logo = OAUTH_LOGOS[p];
              return (
                <button key={p} onClick={() => linkMore(p)}
                  className="flex items-center gap-2 border border-ink/10 rounded-sm px-3 py-1 text-sm">
                  {Logo && <Logo className="w-4 h-4" />} + {t(`auth.providerName.${p}`)}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

// Export `LinkedAccounts` and embed it in the existing settings page body.
```

Insert `<LinkedAccounts />` into the settings page's JSX (alongside the existing preferences sections).

- [ ] **Step 3: Manual browser test**

Login with mock → `/settings` → linked mock provider appears, unlink disabled (only one identity).

- [ ] **Step 4: Commit**

```bash
git add web/app/settings/page.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(web): settings linked-accounts section + link/unlink"
```

---

## Phase 11: Cleanup

### Task 28: Delete signup page + nav link; strip obsolete i18n

**Files:**
- Delete: `web/app/signup/page.tsx`
- Modify: `web/components/TopNav.tsx`
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

- [ ] **Step 1: Delete signup page**

```bash
rm web/app/signup/page.tsx
```

- [ ] **Step 2: Remove signup link from TopNav**

Open `web/components/TopNav.tsx` and remove any `Link` / anchor pointing to `/signup`. Ensure the "nav.signup" i18n key usage is also removed from the JSX.

- [ ] **Step 3: Remove dead i18n keys**

From both `ko.json` and `en.json`:
- Delete `nav.signup`
- Delete `home.guestSignup` OR keep the text and change its target URL in the home page to `/login` (prefer the latter).

In `web/app/page.tsx` (home), replace any `href="/signup"` with `href="/login"`.

- [ ] **Step 4: Type-check + lint**

```bash
cd web && npm run type-check && npm run lint
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add web/components/TopNav.tsx web/lib/i18n/ko.json web/lib/i18n/en.json web/app/page.tsx
git rm web/app/signup/page.tsx
git commit -m "feat(web): remove signup page, nav link, and obsolete i18n"
```

---

## Phase 12: E2E with Mock Provider

### Task 29: Playwright auth spec + docker-compose mock flag

**Files:**
- Create: `e2e/tests/auth.spec.ts`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Compose update**

In `docker-compose.yml`, add to the `backend` service's `environment`:

```yaml
MOCK_OAUTH_ENABLED: ${MOCK_OAUTH_ENABLED:-false}
```

The root `.env.example` must now document `MOCK_OAUTH_ENABLED=true` as an E2E-only flag.

- [ ] **Step 2: Write the test**

```ts
// e2e/tests/auth.spec.ts
import { test, expect } from "@playwright/test";

test.describe("social auth + onboarding", () => {
  test("mock login → onboarding → play → re-login skips onboarding", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("link", { name: /mock/i }).click();

    await expect(page).toHaveURL(/\/onboarding$/);
    await page.getByRole("combobox").click();
    await page.getByPlaceholder("국가 검색").fill("Republic");
    await page.getByRole("option", { name: /Republic of Korea/ }).click();
    await page.getByRole("button", { name: /시작하기/ }).click();

    await expect(page).toHaveURL(/\/$|\/game\/new$/);

    // Logout via an endpoint call, then log back in.
    await page.request.post("/api/auth/logout");
    await page.goto("/login");
    await page.getByRole("link", { name: /mock/i }).click();
    await expect(page).not.toHaveURL(/\/onboarding/);
  });
});
```

- [ ] **Step 3: Run Playwright**

```bash
cd /Users/daegong/projects/baduk
MOCK_OAUTH_ENABLED=true docker-compose up --build -d
cd e2e && npm test -- tests/auth.spec.ts
```

Expected: 1 passed. If the Mock button is not visible (provider not enabled), verify the backend container sees `MOCK_OAUTH_ENABLED=true`.

- [ ] **Step 4: Commit**

```bash
git add e2e/tests/auth.spec.ts docker-compose.yml .env.example
git commit -m "feat(e2e): mock-provider auth spec + docker flag"
```

---

## Phase 13: Provider Setup Docs

### Task 30: `docs/oauth-setup.md`

**Files:**
- Create: `docs/oauth-setup.md`

- [ ] **Step 1: Write the doc**

```markdown
# OAuth Provider Setup

One entry per provider. For each: register an application in the
provider's developer console, set the redirect URI, request scopes, and
copy the credentials into `.env`.

Redirect URI pattern for login:
  `${OAUTH_REDIRECT_BASE_URL}/api/auth/oauth/{provider}/callback`

Redirect URI pattern for link:
  `${OAUTH_REDIRECT_BASE_URL}/api/auth/oauth/{provider}/link/callback`

## Google
- Console: https://console.cloud.google.com/apis/credentials
- OAuth client type: Web
- Authorized redirect URIs: both patterns above
- Scopes: `openid email profile`
- ENV: OAUTH_GOOGLE_CLIENT_ID, OAUTH_GOOGLE_CLIENT_SECRET

## Naver
- Console: https://developers.naver.com/apps
- 서비스 URL: your production URL
- Callback URL: both patterns above
- 제공 정보: 이메일, 별명, 이름, 프로필 사진
- ENV: OAUTH_NAVER_CLIENT_ID, OAUTH_NAVER_CLIENT_SECRET

## Kakao
- Console: https://developers.kakao.com/console/app
- Redirect URI: both patterns above
- 동의 항목: 카카오계정(이메일), 프로필 정보
- ENV: OAUTH_KAKAO_CLIENT_ID, OAUTH_KAKAO_CLIENT_SECRET

## Facebook
- Console: https://developers.facebook.com/apps/
- OAuth Redirect URI: both patterns above
- Scope: `email,public_profile`
- App review required for `email` in production.
- ENV: OAUTH_FACEBOOK_CLIENT_ID, OAUTH_FACEBOOK_CLIENT_SECRET

## LINE
- Console: https://developers.line.biz/console/
- Channel type: LINE Login
- Callback URL: both patterns above
- Scopes: `openid profile email` (email requires channel permission review).
- ENV: OAUTH_LINE_CLIENT_ID, OAUTH_LINE_CLIENT_SECRET

## WeChat
- Console: https://open.weixin.qq.com/
- App type: 网站应用 (Web Application)
- 授权回调域: domain of `OAUTH_REDIRECT_BASE_URL`
- Scope: `snsapi_login`
- Open Platform verification takes several business days.
- ENV: OAUTH_WECHAT_APP_ID, OAUTH_WECHAT_APP_SECRET

## LinkedIn
- Console: https://www.linkedin.com/developers/
- Product: "Sign In with LinkedIn using OpenID Connect"
- Redirect URL: both patterns above
- Scopes: `openid profile email`
- ENV: OAUTH_LINKEDIN_CLIENT_ID, OAUTH_LINKEDIN_CLIENT_SECRET

## Yahoo! JAPAN
- Console: https://e.developer.yahoo.co.jp/register
- Application type: クライアントサイド / サーバーサイド — use サーバーサイド
- Callback URL: both patterns above
- Scopes: `openid email profile`
- ENV: OAUTH_YAHOO_JP_CLIENT_ID, OAUTH_YAHOO_JP_CLIENT_SECRET

## Manual QA Checklist (per provider before go-live)

For each enabled provider in production:
- [ ] New user sign-up lands on `/onboarding`
- [ ] Onboarding submit enters `/`
- [ ] Logout + re-login skips `/onboarding`
- [ ] Two accounts with the same verified email trigger `email_conflict` flow
- [ ] Link + unlink from settings works; last identity cannot be unlinked
- [ ] Logo renders; brand-asset matches guideline
- [ ] ko/en copy reads naturally
```

- [ ] **Step 2: Commit**

```bash
git add docs/oauth-setup.md
git commit -m "docs: per-provider OAuth console setup + manual QA checklist"
```

---

## Phase 14: Agent-based Quality Review

### Task 31: Parallel agent review + remediation

**Files:** (no code writes — this is a review gate)

- [ ] **Step 1: Dispatch the 5 agents in parallel**

Using the main session, invoke (single message, 5 parallel Agent calls):

1. `design-token-guardian` — scope: `web/app/login/page.tsx`, `web/app/onboarding/page.tsx`, `web/app/settings/page.tsx`, `web/components/AuthGate.tsx`, `web/components/ui/combobox.tsx`, `web/components/editorial/icons/oauth/*.tsx`. Check hardcoded hex, emoji, inline font-family, framer-motion, shadow, non-approved radii.

2. `visual-qa` — capture light + dark screenshots of `/login`, `/onboarding`, `/settings`, compare against Editorial spec. Target: no regressions, button typography matches `font-serif`/`font-sans` rules, rule dividers and ISO-code chip are rendered.

3. `korean-copy-qa` — review new keys under `auth.signInHeading`, `auth.continueWith`, `auth.providerName.*`, `auth.onboardingHint`, `onboarding.*`, `settings.linkedAccounts`, `settings.linkMore`, `settings.unlink`, `settings.unlinkLastTooltip`, `settings.linkedSuccess`, `settings.unlinkedSuccess`, `errors.oauth_*`, `errors.invalid_country`, `errors.already_onboarded`. Target: ko/en parity, natural bit-depth, consistent capitalization of provider brand names (LINE, Yahoo! JAPAN, LinkedIn).

4. `a11y-auditor` — run axe over `/login`, `/onboarding`, `/settings`. Verify combobox keyboard flow (ArrowUp/Down, Enter, Esc), ARIA roles (`combobox`, `listbox`, `option`, `aria-activedescendant`), error live regions, focus order.

5. `superpowers:code-reviewer` — scope: `backend/app/core/oauth/*`, `backend/app/services/oauth_service.py`, `backend/app/api/auth.py`, `backend/app/models/user.py`, `backend/app/models/user_identity.py`, `backend/migrations/versions/0005_social_auth.py`. Check the security checklist items (state signature, PKCE usage, open-redirect on `next`, email-conflict policy, no tokens logged, no stored OAuth tokens) and verify every spec section maps to a concrete implementation.

- [ ] **Step 2: Triage findings**

Aggregate the 5 reports. For each finding, open a follow-up commit in the form `fix(<scope>): <finding>`. Re-run the affected test suite before each commit.

- [ ] **Step 3: Final run of full test matrix**

```bash
cd backend && source .venv311/bin/activate && pytest --cov=app --cov-fail-under=80
cd ../web && npm test -- --run && npm run lint && npm run type-check
cd ../e2e && npm test
```

All three suites must be green.

- [ ] **Step 4: Commit a summary in the PR description**

When opening the pull request, include a short summary of each agent's verdict and any remediation commits.

---

## Self-Review (run after finishing the plan, before handing off)

**1. Spec coverage** — every spec section points to a task:
- Data model → Tasks 4, 5
- Provider adapter layer → Tasks 6–8, 14–21
- OAuth endpoints → Tasks 9, 10, 12
- Password auth removal → Task 13
- Onboarding → Tasks 11, 26
- Settings linking → Tasks 12, 27
- Login page → Task 24
- Security checklist → enforced by Task 10 (state), Task 9 (conflict), Task 31 (reviewer)
- Testing → Tasks 3, 6–12, 14–21, 22, 24–25, 29
- Configuration → Tasks 2, 29
- Agent QA → Task 31

**2. Placeholder scan** — no TBD/TODO in step bodies. Brand-asset placeholders are acknowledged explicitly (Task 23) with a follow-up gate before production.

**3. Type consistency** — `OAuthProvider` Protocol, `UserInfo` dataclass, `StatePayload`, `Identity` API shape, and `UserPublic` schema are used identically across backend + tests + frontend.

**4. Ambiguity** — `next` param sanitation is defined once (`_safe_next`); `email_verified` policy is explicit per-provider; `subject` selection for WeChat is explicit.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-21-social-auth.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Use `superpowers:subagent-driven-development`.

2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

**Which approach?**
