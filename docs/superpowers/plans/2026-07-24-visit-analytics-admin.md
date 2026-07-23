# 방문 통계 어드민 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 어드민에서 방문 트래픽(페이지뷰·순방문자·유입경로·국가)과 검색 유입(구글 자동·네이버 CSV 검색어)을 조회하는 기능을 추가한다.

**Architecture:** 두 독립 모듈. (A) 클라이언트 비콘 → `POST /api/analytics/hit` → SQLite `visit_hits`, 집계는 `GET /api/admin/analytics`. (B) 구글 Search Console API(서비스 계정) 자동 동기화 + 네이버 CSV 임포트 → SQLite `search_queries`, 조회는 `GET /api/admin/search-queries`. 프론트는 `/admin/analytics` 2탭.

**Tech Stack:** FastAPI + SQLAlchemy 2 async + SQLite(Alembic), Next.js 14 App Router + TypeScript, google-auth(서비스 계정 토큰) + httpx(REST).

## Global Constraints

- 백엔드 모든 신규 `.py`는 첫 줄 `from __future__ import annotations`, modern generics(`X | None`, `list[…]`). ruff 룰 E,F,I,B,UP,S,W, line 100. `print` 금지 — structlog 사용.
- `mypy app` strict 통과. 주석 없는 `# type: ignore` 금지.
- 신규 소스 파일 첫 줄(디렉티브 직후)에 한국어 한 줄 역할 주석 필수. 콜론 종결 금지(마침표).
- 프론트 신규 파일도 첫 줄 한국어 주석(`'use client'` 직후). 디자인 토큰만(하드코딩 hex·이모지·framer-motion 금지), lucide 아이콘, i18n 키는 ko/en 동시 추가.
- **원본 IP 절대 저장 금지.** 방문자 식별은 일일솔트 해시만.
- 테스트: 신규 모델은 반드시 `backend/app/models/__init__.py`에 등록(conftest가 `import app.models`로 테이블 생성).
- 커버리지 게이트 `--cov-fail-under=80` 유지.

---

### Task 1: `visit_hits` 모델 + 마이그레이션

**Files:**
- Create: `backend/app/models/visit_hit.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0016_visit_hits.py`
- Test: `backend/tests/api/test_visit_hit_model.py`

**Interfaces:**
- Produces: `VisitHit` 모델 (`id, created_at, path, referrer_host, source, country, visitor_hash, device`).

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/api/test_visit_hit_model.py`

```python
# visit_hits 모델의 삽입·조회를 검증한다.
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.visit_hit import VisitHit


@pytest.mark.asyncio
async def test_visit_hit_insert(client):  # client 픽스처가 테스트 DB 바인딩
    async with AsyncSessionLocal() as db:
        db.add(VisitHit(path="/glossary/sahwal", referrer_host="google.com",
                        source="search", country="KR", visitor_hash="abc", device="mobile"))
        await db.commit()
        rows = (await db.execute(select(VisitHit))).scalars().all()
        assert len(rows) == 1
        assert rows[0].source == "search"
        assert rows[0].created_at is not None
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/api/test_visit_hit_model.py -v`
Expected: FAIL — `ModuleNotFoundError: app.models.visit_hit`

- [ ] **Step 3: 모델 작성** — `backend/app/models/visit_hit.py`

```python
# 익명 페이지 방문 1건을 담는 테이블 — 원본 IP 미저장, 국가·해시만 기록한다.
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class VisitHit(Base):
    __tablename__ = "visit_hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), index=True
    )
    path: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    referrer_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    visitor_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    device: Mapped[str | None] = mapped_column(String(16), nullable=True)
```

- [ ] **Step 4: 모델 등록** — `backend/app/models/__init__.py` 에 import + `__all__` 추가

```python
from app.models.visit_hit import VisitHit  # noqa: F401
# __all__ 리스트에 "VisitHit" 추가
```

- [ ] **Step 5: 마이그레이션 작성** — `backend/migrations/versions/0016_visit_hits.py`

```python
# visit_hits 테이블 생성 — 방문 통계 원장.
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "visit_hits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("referrer_host", sa.String(255), nullable=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("visitor_hash", sa.String(64), nullable=False),
        sa.Column("device", sa.String(16), nullable=True),
    )
    op.create_index("ix_visit_hits_created_at", "visit_hits", ["created_at"])
    op.create_index("ix_visit_hits_path", "visit_hits", ["path"])
    op.create_index("ix_visit_hits_source", "visit_hits", ["source"])
    op.create_index("ix_visit_hits_country", "visit_hits", ["country"])


def downgrade() -> None:
    op.drop_table("visit_hits")
```

- [ ] **Step 6: 테스트 통과 확인 + 마이그레이션 적용**

Run: `cd backend && pytest tests/api/test_visit_hit_model.py -v && alembic upgrade head`
Expected: PASS, 마이그레이션 0016 적용됨

- [ ] **Step 7: 커밋**

```bash
git add backend/app/models/visit_hit.py backend/app/models/__init__.py backend/migrations/versions/0016_visit_hits.py backend/tests/api/test_visit_hit_model.py
git commit -m "feat(analytics): visit_hits 모델 + 마이그레이션"
```

---

### Task 2: referrer 파싱·source 분류

**Files:**
- Create: `backend/app/core/analytics/__init__.py` (빈 파일)
- Create: `backend/app/core/analytics/referrer.py`
- Test: `backend/tests/analytics/test_referrer.py`

**Interfaces:**
- Produces: `parse_referrer_host(referrer: str) -> str | None`, `classify_source(referrer_host: str | None) -> str` (반환: `"search"|"social"|"referral"|"direct"|"internal"`), 상수 `INTERNAL_HOST = "inkbaduk.com"`.

- [ ] **Step 1: 실패 테스트** — `backend/tests/analytics/test_referrer.py`

```python
# referrer 파싱·source 분류 로직 검증.
from __future__ import annotations

import pytest

from app.core.analytics.referrer import classify_source, parse_referrer_host


@pytest.mark.parametrize("ref,host", [
    ("https://www.google.com/", "google.com"),
    ("https://search.naver.com/search.naver?query=x", "search.naver.com"),
    ("", None),
    ("not a url", None),
])
def test_parse_referrer_host(ref, host):
    assert parse_referrer_host(ref) == host


@pytest.mark.parametrize("host,source", [
    (None, "direct"),
    ("google.com", "search"),
    ("search.naver.com", "search"),
    ("m.search.daum.net", "search"),
    ("bing.com", "search"),
    ("facebook.com", "social"),
    ("t.co", "social"),
    ("inkbaduk.com", "internal"),
    ("someblog.tistory.com", "referral"),
])
def test_classify_source(host, source):
    assert classify_source(host) == source
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/analytics/test_referrer.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현** — `backend/app/core/analytics/referrer.py`

```python
# referrer URL을 호스트로 파싱하고 유입 소스(search/social/referral/direct/internal)로 분류한다.
from __future__ import annotations

from urllib.parse import urlparse

INTERNAL_HOST = "inkbaduk.com"

_SEARCH = ("google.", "naver.", "daum.", "bing.", "duckduckgo.", "search.")
_SOCIAL = ("facebook.", "instagram.", "twitter.", "x.com", "t.co",
           "youtube.", "youtu.be", "threads.", "kakao.", "band.us")


def parse_referrer_host(referrer: str) -> str | None:
    if not referrer:
        return None
    try:
        host = urlparse(referrer).hostname
    except ValueError:
        return None
    if not host:
        return None
    return host.lower()


def classify_source(referrer_host: str | None) -> str:
    if referrer_host is None:
        return "direct"
    host = referrer_host.lower()
    if host == INTERNAL_HOST or host.endswith("." + INTERNAL_HOST):
        return "internal"
    if any(s in host for s in _SEARCH):
        return "search"
    if any(s in host for s in _SOCIAL):
        return "social"
    return "referral"
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && pytest tests/analytics/test_referrer.py -v`
Expected: PASS (전 케이스)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/core/analytics/
git commit -m "feat(analytics): referrer 파싱·source 분류"
```

---

### Task 3: 방문자 해시(일일 솔트)

**Files:**
- Create: `backend/app/core/analytics/hashing.py`
- Test: `backend/tests/analytics/test_hashing.py`

**Interfaces:**
- Produces: `visitor_hash(ip: str, salt: str) -> str`, `daily_salt(day: str) -> str` (같은 day면 같은 솔트, 다른 day면 다른 솔트).

- [ ] **Step 1: 실패 테스트** — `backend/tests/analytics/test_hashing.py`

```python
# 방문자 해시 결정성·일일 솔트 회전 검증.
from __future__ import annotations

from app.core.analytics.hashing import daily_salt, visitor_hash


def test_visitor_hash_deterministic():
    assert visitor_hash("1.2.3.4", "salt") == visitor_hash("1.2.3.4", "salt")


def test_visitor_hash_differs_by_ip_and_salt():
    assert visitor_hash("1.2.3.4", "s") != visitor_hash("9.9.9.9", "s")
    assert visitor_hash("1.2.3.4", "s1") != visitor_hash("1.2.3.4", "s2")


def test_daily_salt_stable_per_day_rotates_across_days():
    assert daily_salt("2026-07-24") == daily_salt("2026-07-24")
    assert daily_salt("2026-07-24") != daily_salt("2026-07-25")
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/analytics/test_hashing.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현** — `backend/app/core/analytics/hashing.py`

```python
# 방문자를 원본 IP 저장 없이 식별하기 위한 일일 솔트 해시 — 익일 재식별 불가.
from __future__ import annotations

import hashlib
import secrets

_salts: dict[str, str] = {}


def daily_salt(day: str) -> str:
    """UTC 날짜 문자열(YYYY-MM-DD)별 랜덤 솔트. 프로세스 생존 동안 캐시."""
    salt = _salts.get(day)
    if salt is None:
        salt = secrets.token_hex(16)
        _salts[day] = salt
    return salt


def visitor_hash(ip: str, salt: str) -> str:
    return hashlib.sha256(f"{ip}:{salt}".encode()).hexdigest()
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && pytest tests/analytics/test_hashing.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/core/analytics/hashing.py backend/tests/analytics/test_hashing.py
git commit -m "feat(analytics): 일일 솔트 방문자 해시"
```

---

### Task 4: 봇 필터

**Files:**
- Create: `backend/app/core/analytics/bots.py`
- Test: `backend/tests/analytics/test_bots.py`

**Interfaces:**
- Produces: `is_bot(user_agent: str | None) -> bool`.

- [ ] **Step 1: 실패 테스트** — `backend/tests/analytics/test_bots.py`

```python
# User-Agent 봇 판정 검증.
from __future__ import annotations

import pytest

from app.core.analytics.bots import is_bot


@pytest.mark.parametrize("ua,bot", [
    (None, True),
    ("", True),
    ("Mozilla/5.0 (iPhone) Safari", False),
    ("Googlebot/2.1 (+http://www.google.com/bot.html)", True),
    ("Mozilla/5.0 (compatible; Yeti/1.1; +http://naver.me/bot)", True),
    ("curl/8.0", True),
])
def test_is_bot(ua, bot):
    assert is_bot(ua) is bot
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/analytics/test_bots.py -v`
Expected: FAIL

- [ ] **Step 3: 구현** — `backend/app/core/analytics/bots.py`

```python
# 방문 통계에서 제외할 봇·크롤러를 User-Agent로 판정한다.
from __future__ import annotations

_BOT_MARKERS = (
    "bot", "crawler", "spider", "slurp", "yeti", "bingbot", "googlebot",
    "baiduspider", "yandex", "duckduckbot", "curl", "wget", "python-requests",
    "headless", "facebookexternalhit", "preview",
)


def is_bot(user_agent: str | None) -> bool:
    if not user_agent:
        return True
    ua = user_agent.lower()
    return any(m in ua for m in _BOT_MARKERS)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && pytest tests/analytics/test_bots.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/core/analytics/bots.py backend/tests/analytics/test_bots.py
git commit -m "feat(analytics): User-Agent 봇 필터"
```

---

### Task 5: `POST /api/analytics/hit` 수집 엔드포인트

**Files:**
- Create: `backend/app/api/analytics.py`
- Modify: `backend/app/main.py` (라우터 include)
- Test: `backend/tests/api/test_analytics_hit.py`

**Interfaces:**
- Consumes: Task 2/3/4 함수, `client_ip`·`client_country`(`app.client_ip`), `DbSession`.
- Produces: `POST /api/analytics/hit`, body `{path, referrer}`, 204 반환. `VisitHit` 1행 저장(봇 제외).

- [ ] **Step 1: 실패 테스트** — `backend/tests/api/test_analytics_hit.py`

```python
# 방문 수집 엔드포인트: 정상 저장·봇 스킵·직접유입 분류 검증.
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.visit_hit import VisitHit


@pytest.mark.asyncio
async def test_hit_saves_row(client):
    r = await client.post("/api/analytics/hit",
                          json={"path": "/glossary/sahwal", "referrer": "https://www.google.com/"},
                          headers={"User-Agent": "Mozilla/5.0 (iPhone) Safari"})
    assert r.status_code == 204
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(VisitHit))).scalars().all()
    assert len(rows) == 1
    assert rows[0].path == "/glossary/sahwal"
    assert rows[0].source == "search"
    assert rows[0].referrer_host == "google.com"


@pytest.mark.asyncio
async def test_hit_skips_bot(client):
    r = await client.post("/api/analytics/hit",
                          json={"path": "/", "referrer": ""},
                          headers={"User-Agent": "Googlebot/2.1"})
    assert r.status_code == 204
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(VisitHit))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_hit_direct_source(client):
    await client.post("/api/analytics/hit", json={"path": "/faq", "referrer": ""},
                      headers={"User-Agent": "Mozilla/5.0 (iPhone) Safari"})
    async with AsyncSessionLocal() as db:
        row = (await db.execute(select(VisitHit))).scalars().one()
    assert row.source == "direct"
    assert row.referrer_host is None
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/api/test_analytics_hit.py -v`
Expected: FAIL — 404 (엔드포인트 없음)

- [ ] **Step 3: 구현** — `backend/app/api/analytics.py`

```python
# 익명 방문 비콘 수집 엔드포인트 — 봇 제외 후 국가·해시를 붙여 visit_hits에 적재한다.
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.client_ip import client_country, client_ip
from app.core.analytics.bots import is_bot
from app.core.analytics.hashing import daily_salt, visitor_hash
from app.core.analytics.referrer import classify_source, parse_referrer_host
from app.deps import DbSession
from app.models.visit_hit import VisitHit

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class HitBody(BaseModel):
    path: str = Field(max_length=512)
    referrer: str = Field(default="", max_length=2048)


def _device(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    return "mobile" if "mobi" in user_agent.lower() else "desktop"


@router.post("/hit", status_code=204)
async def hit(body: HitBody, request: Request, db: DbSession) -> Response:
    ua = request.headers.get("user-agent")
    if is_bot(ua):
        return Response(status_code=204)
    host = parse_referrer_host(body.referrer)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ip = client_ip(request)
    db.add(
        VisitHit(
            path=body.path[:512],
            referrer_host=host,
            source=classify_source(host),
            country=client_country(request),
            visitor_hash=visitor_hash(ip, daily_salt(day)),
            device=_device(ua),
        )
    )
    await db.commit()
    return Response(status_code=204)
```

- [ ] **Step 4: 라우터 등록** — `backend/app/main.py` `create_app()` 안, 기존 `include_router` 근처에 추가

```python
from app.api import analytics as analytics_router
app.include_router(analytics_router.router)
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && pytest tests/api/test_analytics_hit.py -v`
Expected: PASS (3개)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api/analytics.py backend/app/main.py backend/tests/api/test_analytics_hit.py
git commit -m "feat(analytics): POST /api/analytics/hit 수집 엔드포인트"
```

---

### Task 6: `GET /api/admin/analytics` 집계

**Files:**
- Create: `backend/app/api/admin_analytics.py`
- Modify: `backend/app/main.py` (라우터 include)
- Test: `backend/tests/api/test_admin_analytics.py`

**Interfaces:**
- Consumes: `AdminSession`, `DbSession`, `VisitHit`.
- Produces: `GET /api/admin/analytics?days=&top=` → `AnalyticsOverview{totals, daily[], top_pages[], sources[], countries[]}`.

- [ ] **Step 1: 실패 테스트** — `backend/tests/api/test_admin_analytics.py`

```python
# 방문 집계 엔드포인트: admin 인증·집계 정확성·403 검증.
from __future__ import annotations

import pytest
from sqlalchemy import select  # noqa: F401

from app.db import AsyncSessionLocal
from app.models.visit_hit import VisitHit

ADMIN_NICK = "대공"


async def _signup(client, nickname):
    r = await client.post("/api/session", json={"nickname": nickname})
    assert r.status_code == 201


async def _seed(rows):
    async with AsyncSessionLocal() as db:
        for r in rows:
            db.add(VisitHit(**r))
        await db.commit()


@pytest.mark.asyncio
async def test_analytics_overview(client):
    await _seed([
        dict(path="/faq", referrer_host="google.com", source="search", country="KR",
             visitor_hash="v1", device="mobile"),
        dict(path="/faq", referrer_host=None, source="direct", country="US",
             visitor_hash="v2", device="desktop"),
        dict(path="/glossary", referrer_host="google.com", source="search", country="KR",
             visitor_hash="v1", device="mobile"),
    ])
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/analytics?days=30&top=10")
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["pageviews"] == 3
    paths = {p["path"]: p["pageviews"] for p in data["top_pages"]}
    assert paths["/faq"] == 2 and paths["/glossary"] == 1
    countries = {c["country"]: c["pageviews"] for c in data["countries"]}
    assert countries["KR"] == 2 and countries["US"] == 1
    sources = {s["source"] for s in data["sources"]}
    assert "search" in sources and "direct" in sources


@pytest.mark.asyncio
async def test_analytics_forbidden_for_non_admin(client):
    await _signup(client, "손님")
    r = await client.get("/api/admin/analytics")
    assert r.status_code == 403
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/api/test_admin_analytics.py -v`
Expected: FAIL — 404

- [ ] **Step 3: 구현** — `backend/app/api/admin_analytics.py`

```python
# 방문 통계 집계 API — 관리자에게 PV·순방문자·유입경로·국가·인기페이지를 반환한다.
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.deps import AdminSession, DbSession
from app.models.visit_hit import VisitHit

router = APIRouter(prefix="/api/admin", tags=["admin"])


class Totals(BaseModel):
    pageviews: int
    unique_visitors: int


class DailyRow(BaseModel):
    date: str
    pageviews: int
    uniques: int


class PageRow(BaseModel):
    path: str
    pageviews: int
    uniques: int


class SourceRow(BaseModel):
    source: str
    referrer_host: str | None
    pageviews: int


class CountryRow(BaseModel):
    country: str | None
    pageviews: int
    uniques: int


class AnalyticsOverview(BaseModel):
    totals: Totals
    daily: list[DailyRow]
    top_pages: list[PageRow]
    sources: list[SourceRow]
    countries: list[CountryRow]


@router.get("/analytics", response_model=AnalyticsOverview)
async def analytics(_: AdminSession, db: DbSession, days: int = 30, top: int = 20) -> AnalyticsOverview:
    days = max(1, min(days, 90))
    top = max(1, min(top, 50))
    start = datetime.utcnow() - timedelta(days=days)
    base = VisitHit.created_at >= start

    pv = (await db.execute(select(func.count(VisitHit.id)).where(base))).scalar_one()
    uv = (await db.execute(
        select(func.count(func.distinct(VisitHit.visitor_hash))).where(base)
    )).scalar_one()

    daily_rows = (await db.execute(
        select(func.date(VisitHit.created_at).label("d"),
               func.count(VisitHit.id),
               func.count(func.distinct(VisitHit.visitor_hash)))
        .where(base).group_by("d").order_by("d")
    )).all()

    page_rows = (await db.execute(
        select(VisitHit.path, func.count(VisitHit.id),
               func.count(func.distinct(VisitHit.visitor_hash)))
        .where(base).group_by(VisitHit.path)
        .order_by(func.count(VisitHit.id).desc()).limit(top)
    )).all()

    source_rows = (await db.execute(
        select(VisitHit.source, VisitHit.referrer_host, func.count(VisitHit.id))
        .where(base).group_by(VisitHit.source, VisitHit.referrer_host)
        .order_by(func.count(VisitHit.id).desc()).limit(top)
    )).all()

    country_rows = (await db.execute(
        select(VisitHit.country, func.count(VisitHit.id),
               func.count(func.distinct(VisitHit.visitor_hash)))
        .where(base).group_by(VisitHit.country)
        .order_by(func.count(VisitHit.id).desc()).limit(top)
    )).all()

    return AnalyticsOverview(
        totals=Totals(pageviews=int(pv), unique_visitors=int(uv)),
        daily=[DailyRow(date=str(r[0]), pageviews=int(r[1]), uniques=int(r[2])) for r in daily_rows],
        top_pages=[PageRow(path=r[0], pageviews=int(r[1]), uniques=int(r[2])) for r in page_rows],
        sources=[SourceRow(source=r[0], referrer_host=r[1], pageviews=int(r[2])) for r in source_rows],
        countries=[CountryRow(country=r[0], pageviews=int(r[1]), uniques=int(r[2])) for r in country_rows],
    )
```

- [ ] **Step 4: 라우터 등록** — `backend/app/main.py` `create_app()` 안

```python
from app.api import admin_analytics as admin_analytics_router
app.include_router(admin_analytics_router.router)
```

- [ ] **Step 5: 통과 확인 + 린트·타입**

Run: `cd backend && pytest tests/api/test_admin_analytics.py -v && ruff check app && mypy app`
Expected: PASS, 린트·타입 클린

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api/admin_analytics.py backend/app/main.py backend/tests/api/test_admin_analytics.py
git commit -m "feat(analytics): GET /api/admin/analytics 집계"
```

---

### Task 7: `search_queries` 모델 + 마이그레이션

**Files:**
- Create: `backend/app/models/search_query.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0017_search_queries.py`
- Test: `backend/tests/api/test_search_query_model.py`

**Interfaces:**
- Produces: `SearchQuery` 모델(`id, source, query, page, clicks, impressions, ctr, position, date, fetched_at`). 유니크 `(source, query, page, date)`.

- [ ] **Step 1: 실패 테스트** — `backend/tests/api/test_search_query_model.py`

```python
# search_queries 모델 삽입 검증.
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.search_query import SearchQuery


@pytest.mark.asyncio
async def test_search_query_insert(client):
    async with AsyncSessionLocal() as db:
        db.add(SearchQuery(source="google", query="바둑 단수 뜻", page="/glossary/dansu",
                           clicks=0, impressions=36, ctr=0.0, position=13.2, date=date(2026, 7, 20)))
        await db.commit()
        row = (await db.execute(select(SearchQuery))).scalars().one()
        assert row.query == "바둑 단수 뜻"
        assert row.source == "google"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/api/test_search_query_model.py -v`
Expected: FAIL

- [ ] **Step 3: 모델 작성** — `backend/app/models/search_query.py`

```python
# 검색 콘솔 검색어 통계 1행 — 구글(API)·네이버(CSV 임포트) 공용 저장소.
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"
    __table_args__ = (
        UniqueConstraint("source", "query", "page", "date", name="uq_search_query"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(255), nullable=False)
    page: Mapped[str | None] = mapped_column(String(512), nullable=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position: Mapped[float | None] = mapped_column(Float, nullable=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
```

- [ ] **Step 4: 모델 등록** — `backend/app/models/__init__.py` 에 `from app.models.search_query import SearchQuery  # noqa: F401` + `__all__`

- [ ] **Step 5: 마이그레이션** — `backend/migrations/versions/0017_search_queries.py`

```python
# search_queries 테이블 생성 — 검색 콘솔 검색어 통계.
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(8), nullable=False),
        sa.Column("query", sa.String(255), nullable=False),
        sa.Column("page", sa.String(512), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=False, server_default="0"),
        sa.Column("position", sa.Float(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "query", "page", "date", name="uq_search_query"),
    )
    op.create_index("ix_search_queries_source", "search_queries", ["source"])
    op.create_index("ix_search_queries_date", "search_queries", ["date"])


def downgrade() -> None:
    op.drop_table("search_queries")
```

- [ ] **Step 6: 통과 확인 + 마이그레이션**

Run: `cd backend && pytest tests/api/test_search_query_model.py -v && alembic upgrade head`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add backend/app/models/search_query.py backend/app/models/__init__.py backend/migrations/versions/0017_search_queries.py backend/tests/api/test_search_query_model.py
git commit -m "feat(analytics): search_queries 모델 + 마이그레이션"
```

---

### Task 8: 네이버 CSV 파서

**Files:**
- Create: `backend/app/core/search_console/__init__.py` (빈 파일)
- Create: `backend/app/core/search_console/naver_csv.py`
- Test: `backend/tests/analytics/test_naver_csv.py`

**Interfaces:**
- Produces: `parse_naver_csv(text: str) -> list[NaverRow]`, `NaverRow` = pydantic `{query, clicks, impressions, ctr}`.

- [ ] **Step 1: 실패 테스트** — `backend/tests/analytics/test_naver_csv.py`

```python
# 네이버 검색어 CSV 파서 검증.
from __future__ import annotations

from app.core.search_console.naver_csv import parse_naver_csv

CSV = "﻿검색어,클릭,노출,CTR(%)\n바둑 단수 뜻,0,36,0\n계가,0,5,0\n"


def test_parse_naver_csv():
    rows = parse_naver_csv(CSV)
    assert len(rows) == 2
    assert rows[0].query == "바둑 단수 뜻"
    assert rows[0].impressions == 36
    assert rows[0].clicks == 0


def test_parse_naver_csv_skips_blank():
    rows = parse_naver_csv("검색어,클릭,노출,CTR(%)\n\n,,,\n")
    assert rows == []
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/analytics/test_naver_csv.py -v`
Expected: FAIL

- [ ] **Step 3: 구현** — `backend/app/core/search_console/naver_csv.py`

```python
# 네이버 서치어드바이저 '검색 키워드' CSV export를 파싱한다(검색어·클릭·노출·CTR).
from __future__ import annotations

import csv
import io

from pydantic import BaseModel


class NaverRow(BaseModel):
    query: str
    clicks: int
    impressions: int
    ctr: float


def _num(value: str) -> float:
    try:
        return float(value.replace(",", "").replace("%", "").strip())
    except ValueError:
        return 0.0


def parse_naver_csv(text: str) -> list[NaverRow]:
    text = text.lstrip("﻿")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    out: list[NaverRow] = []
    for r in rows[1:]:  # 헤더 스킵
        if len(r) < 3 or not r[0].strip():
            continue
        out.append(NaverRow(
            query=r[0].strip(),
            clicks=int(_num(r[1])),
            impressions=int(_num(r[2])),
            ctr=_num(r[3]) if len(r) > 3 else 0.0,
        ))
    return out
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && pytest tests/analytics/test_naver_csv.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/core/search_console/__init__.py backend/app/core/search_console/naver_csv.py backend/tests/analytics/test_naver_csv.py
git commit -m "feat(analytics): 네이버 검색어 CSV 파서"
```

---

### Task 9: `POST /api/admin/search-queries/import` (네이버 CSV)

**Files:**
- Create: `backend/app/api/admin_search.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_admin_search_import.py`

**Interfaces:**
- Consumes: `AdminSession`, `DbSession`, `parse_naver_csv`, `SearchQuery`.
- Produces: `POST /api/admin/search-queries/import` (multipart `file`) → `source="naver"` 스냅샷 교체, `{imported: int}` 반환.

- [ ] **Step 1: 실패 테스트** — `backend/tests/api/test_admin_search_import.py`

```python
# 네이버 CSV 임포트 엔드포인트: 적재·스냅샷 교체·403 검증.
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models.search_query import SearchQuery

ADMIN_NICK = "대공"
CSV = "검색어,클릭,노출,CTR(%)\n바둑 사활,2,40,5\n삼삼,3,8,37.5\n"


async def _signup(client, nickname):
    assert (await client.post("/api/session", json={"nickname": nickname})).status_code == 201


@pytest.mark.asyncio
async def test_import_naver_csv(client):
    await _signup(client, ADMIN_NICK)
    r = await client.post("/api/admin/search-queries/import",
                          files={"file": ("naver.csv", CSV, "text/csv")})
    assert r.status_code == 200
    assert r.json()["imported"] == 2
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(SearchQuery).where(SearchQuery.source == "naver"))).scalars().all()
    assert {x.query for x in rows} == {"바둑 사활", "삼삼"}


@pytest.mark.asyncio
async def test_import_forbidden(client):
    await _signup(client, "손님")
    r = await client.post("/api/admin/search-queries/import",
                          files={"file": ("n.csv", CSV, "text/csv")})
    assert r.status_code == 403
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/api/test_admin_search_import.py -v`
Expected: FAIL — 404

- [ ] **Step 3: 구현** — `backend/app/api/admin_search.py`

```python
# 검색어 임포트·조회 어드민 API — 네이버 CSV 업로드와 통합 조회를 제공한다.
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete

from app.core.search_console.naver_csv import parse_naver_csv
from app.deps import AdminSession, DbSession
from app.models.search_query import SearchQuery

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ImportResult(BaseModel):
    imported: int


@router.post("/search-queries/import", response_model=ImportResult)
async def import_naver(_: AdminSession, db: DbSession, file: UploadFile) -> ImportResult:
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    rows = parse_naver_csv(raw)
    today = datetime.now(timezone.utc).date()
    # 네이버 스냅샷 교체 — 기존 naver 행 삭제 후 재적재.
    await db.execute(delete(SearchQuery).where(SearchQuery.source == "naver"))
    for r in rows:
        db.add(SearchQuery(source="naver", query=r.query, page=None,
                           clicks=r.clicks, impressions=r.impressions,
                           ctr=r.ctr, position=None, date=today))
    await db.commit()
    return ImportResult(imported=len(rows))
```

- [ ] **Step 4: 라우터 등록** — `backend/app/main.py` `create_app()` 안

```python
from app.api import admin_search as admin_search_router
app.include_router(admin_search_router.router)
```

`UploadFile` 사용을 위해 `python-multipart`가 설치돼 있어야 한다(FastAPI 폼). 없으면 `backend/pyproject.toml` deps에 `python-multipart` 추가 후 `pip install -e ".[dev]"`.

- [ ] **Step 5: 통과 확인**

Run: `cd backend && pytest tests/api/test_admin_search_import.py -v`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add backend/app/api/admin_search.py backend/app/main.py backend/tests/api/test_admin_search_import.py backend/pyproject.toml
git commit -m "feat(analytics): 네이버 검색어 CSV 임포트 엔드포인트"
```

---

### Task 10: 구글 Search Console 클라이언트

**Files:**
- Modify: `backend/app/config.py` (GSC 설정 추가)
- Create: `backend/app/core/search_console/gsc.py`
- Modify: `backend/pyproject.toml` (google-auth 추가)
- Test: `backend/tests/analytics/test_gsc.py`

**Interfaces:**
- Consumes: `settings.gsc_property_url`, `settings.gsc_service_account_json`.
- Produces: `async def fetch_search_analytics(start: str, end: str) -> list[GscRow]`, `GscRow` = `{query, page, clicks, impressions, ctr, position, date}`. 설정 없으면 `[]` 반환. `parse_gsc_response(payload: dict) -> list[GscRow]` (순수, 테스트 대상).

- [ ] **Step 1: config 필드 추가** — `backend/app/config.py` Settings 클래스에

```python
    gsc_property_url: str = ""          # env: GSC_PROPERTY_URL (예: sc-domain:inkbaduk.com)
    gsc_service_account_json: str = ""  # env: GSC_SERVICE_ACCOUNT_JSON (키 파일 경로)
```

- [ ] **Step 2: 실패 테스트** — `backend/tests/analytics/test_gsc.py`

```python
# GSC 응답 파서 검증(순수 함수). HTTP·인증은 통합 범위 밖.
from __future__ import annotations

from app.core.search_console.gsc import parse_gsc_response


def test_parse_gsc_response():
    payload = {"rows": [
        {"keys": ["바둑 단수 뜻", "https://inkbaduk.com/glossary/dansu", "2026-07-20"],
         "clicks": 0, "impressions": 36, "ctr": 0.0, "position": 13.2},
    ]}
    rows = parse_gsc_response(payload)
    assert len(rows) == 1
    assert rows[0].query == "바둑 단수 뜻"
    assert rows[0].page == "https://inkbaduk.com/glossary/dansu"
    assert rows[0].impressions == 36
    assert rows[0].date == "2026-07-20"


def test_parse_gsc_response_empty():
    assert parse_gsc_response({}) == []
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && pytest tests/analytics/test_gsc.py -v`
Expected: FAIL

- [ ] **Step 4: 구현** — `backend/app/core/search_console/gsc.py`

```python
# 구글 Search Console Search Analytics API 클라이언트 — 서비스 계정으로 검색어 통계를 가져온다.
from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from app.config import settings

_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


class GscRow(BaseModel):
    query: str
    page: str | None
    clicks: int
    impressions: int
    ctr: float
    position: float
    date: str


def parse_gsc_response(payload: dict[str, Any]) -> list[GscRow]:
    out: list[GscRow] = []
    for r in payload.get("rows", []):
        keys = r.get("keys", [])
        out.append(GscRow(
            query=keys[0] if len(keys) > 0 else "",
            page=keys[1] if len(keys) > 1 else None,
            date=keys[2] if len(keys) > 2 else "",
            clicks=int(r.get("clicks", 0)),
            impressions=int(r.get("impressions", 0)),
            ctr=float(r.get("ctr", 0.0)),
            position=float(r.get("position", 0.0)),
        ))
    return out


def _access_token() -> str | None:
    if not settings.gsc_service_account_json:
        return None
    # google-auth로 서비스 계정 토큰 발급.
    from google.auth.transport.requests import Request as GAuthRequest
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        settings.gsc_service_account_json, scopes=[_SCOPE]
    )
    creds.refresh(GAuthRequest())
    return str(creds.token)


async def fetch_search_analytics(start: str, end: str) -> list[GscRow]:
    """지정 기간의 검색어·페이지·날짜별 통계. 설정 없으면 빈 리스트."""
    token = _access_token()
    if not token or not settings.gsc_property_url:
        return []
    url = (
        "https://searchconsole.googleapis.com/webmasters/v3/sites/"
        f"{quote(settings.gsc_property_url, safe='')}/searchAnalytics/query"
    )
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["query", "page", "date"],
        "rowLimit": 5000,
    }
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        return parse_gsc_response(resp.json())
```

- [ ] **Step 5: 의존성 추가** — `backend/pyproject.toml` deps에 `"google-auth>=2.0"` 추가 후 `cd backend && pip install -e ".[dev]"`

- [ ] **Step 6: 통과 확인**

Run: `cd backend && pytest tests/analytics/test_gsc.py -v && mypy app`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add backend/app/core/search_console/gsc.py backend/app/config.py backend/pyproject.toml backend/tests/analytics/test_gsc.py
git commit -m "feat(analytics): 구글 Search Console API 클라이언트"
```

---

### Task 11: GSC 동기화 함수 + 스크립트

**Files:**
- Create: `backend/app/core/search_console/sync.py`
- Create: `backend/scripts/sync_gsc.py`
- Test: `backend/tests/analytics/test_gsc_sync.py`

**Interfaces:**
- Consumes: `fetch_search_analytics`, `SearchQuery`, `DbSession`/세션 팩토리.
- Produces: `async def sync_gsc(db, rows: list[GscRow]) -> int` (rows를 `source="google"`로 upsert, 저장 건수 반환).

- [ ] **Step 1: 실패 테스트** — `backend/tests/analytics/test_gsc_sync.py`

```python
# GSC 동기화 upsert 검증 — 같은 (query,page,date) 재삽입 시 갱신.
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.search_console.gsc import GscRow
from app.core.search_console.sync import sync_gsc
from app.db import AsyncSessionLocal
from app.models.search_query import SearchQuery


@pytest.mark.asyncio
async def test_sync_upsert(client):
    rows = [GscRow(query="바둑 사활", page="https://inkbaduk.com/glossary/sahwal",
                   clicks=1, impressions=10, ctr=0.1, position=5.0, date="2026-07-22")]
    async with AsyncSessionLocal() as db:
        n = await sync_gsc(db, rows)
        assert n == 1
    rows2 = [GscRow(query="바둑 사활", page="https://inkbaduk.com/glossary/sahwal",
                    clicks=3, impressions=20, ctr=0.15, position=4.0, date="2026-07-22")]
    async with AsyncSessionLocal() as db:
        await sync_gsc(db, rows2)
        stored = (await db.execute(select(SearchQuery).where(SearchQuery.source == "google"))).scalars().all()
    assert len(stored) == 1
    assert stored[0].clicks == 3
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/analytics/test_gsc_sync.py -v`
Expected: FAIL

- [ ] **Step 3: 구현** — `backend/app/core/search_console/sync.py`

```python
# GSC 응답 행을 search_queries에 upsert하는 동기화 로직.
from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.search_console.gsc import GscRow
from app.models.search_query import SearchQuery


async def sync_gsc(db: AsyncSession, rows: list[GscRow]) -> int:
    for r in rows:
        d = date_type.fromisoformat(r.date)
        existing = (await db.execute(
            select(SearchQuery).where(
                SearchQuery.source == "google",
                SearchQuery.query == r.query,
                SearchQuery.page == r.page,
                SearchQuery.date == d,
            )
        )).scalars().first()
        if existing is None:
            db.add(SearchQuery(source="google", query=r.query, page=r.page,
                               clicks=r.clicks, impressions=r.impressions,
                               ctr=r.ctr, position=r.position, date=d))
        else:
            existing.clicks = r.clicks
            existing.impressions = r.impressions
            existing.ctr = r.ctr
            existing.position = r.position
    await db.commit()
    return len(rows)
```

- [ ] **Step 4: 크론 스크립트** — `backend/scripts/sync_gsc.py`

```python
# GSC 검색어를 최근 며칠분 가져와 DB에 동기화하는 크론 엔트리포인트.
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import structlog

from app.core.search_console.gsc import fetch_search_analytics
from app.core.search_console.sync import sync_gsc
from app.db import AsyncSessionLocal

log = structlog.get_logger()


async def main() -> None:
    end = date.today() - timedelta(days=2)   # GSC 2~3일 지연
    start = end - timedelta(days=5)
    rows = await fetch_search_analytics(start.isoformat(), end.isoformat())
    if not rows:
        log.info("gsc_sync_skip", reason="no_rows_or_not_configured")
        return
    async with AsyncSessionLocal() as db:
        n = await sync_gsc(db, rows)
    log.info("gsc_sync_done", rows=n)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && pytest tests/analytics/test_gsc_sync.py -v`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add backend/app/core/search_console/sync.py backend/scripts/sync_gsc.py backend/tests/analytics/test_gsc_sync.py
git commit -m "feat(analytics): GSC 동기화 함수 + 크론 스크립트"
```

---

### Task 12: `GET /api/admin/search-queries` 조회

**Files:**
- Modify: `backend/app/api/admin_search.py`
- Test: `backend/tests/api/test_admin_search_list.py`

**Interfaces:**
- Consumes: `AdminSession`, `DbSession`, `SearchQuery`.
- Produces: `GET /api/admin/search-queries?source=&days=&top=` → `list[SearchQueryRow]` (클릭·노출 내림차순).

- [ ] **Step 1: 실패 테스트** — `backend/tests/api/test_admin_search_list.py`

```python
# 검색어 조회 엔드포인트: 소스 필터·정렬·403 검증.
from __future__ import annotations

from datetime import date

import pytest

from app.db import AsyncSessionLocal
from app.models.search_query import SearchQuery

ADMIN_NICK = "대공"


async def _signup(client, nickname):
    assert (await client.post("/api/session", json={"nickname": nickname})).status_code == 201


@pytest.mark.asyncio
async def test_list_search_queries(client):
    async with AsyncSessionLocal() as db:
        db.add(SearchQuery(source="google", query="바둑 사활", page="/g/s",
                           clicks=5, impressions=50, ctr=0.1, position=3.0, date=date(2026, 7, 22)))
        db.add(SearchQuery(source="naver", query="접바둑 덤", page=None,
                           clicks=3, impressions=40, ctr=0.075, position=None, date=date(2026, 7, 22)))
        await db.commit()
    await _signup(client, ADMIN_NICK)
    r = await client.get("/api/admin/search-queries?source=all&days=90&top=10")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["query"] == "바둑 사활"  # 클릭 내림차순
    r2 = await client.get("/api/admin/search-queries?source=naver")
    assert {x["query"] for x in r2.json()} == {"접바둑 덤"}


@pytest.mark.asyncio
async def test_list_forbidden(client):
    await _signup(client, "손님")
    assert (await client.get("/api/admin/search-queries")).status_code == 403
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && pytest tests/api/test_admin_search_list.py -v`
Expected: FAIL — 404

- [ ] **Step 3: 구현** — `backend/app/api/admin_search.py` 에 추가

```python
from datetime import timedelta

from sqlalchemy import select


class SearchQueryRow(BaseModel):
    query: str
    page: str | None
    clicks: int
    impressions: int
    ctr: float
    position: float | None
    source: str


@router.get("/search-queries", response_model=list[SearchQueryRow])
async def list_search_queries(
    _: AdminSession, db: DbSession, source: str = "all", days: int = 90, top: int = 50
) -> list[SearchQueryRow]:
    from datetime import date as _date
    days = max(1, min(days, 480))
    top = max(1, min(top, 200))
    start = _date.today() - timedelta(days=days)
    stmt = select(SearchQuery).where(SearchQuery.date >= start)
    if source in ("google", "naver"):
        stmt = stmt.where(SearchQuery.source == source)
    stmt = stmt.order_by(SearchQuery.clicks.desc(), SearchQuery.impressions.desc()).limit(top)
    rows = (await db.execute(stmt)).scalars().all()
    return [SearchQueryRow(query=r.query, page=r.page, clicks=r.clicks,
                           impressions=r.impressions, ctr=r.ctr, position=r.position,
                           source=r.source) for r in rows]
```

- [ ] **Step 4: 통과 확인 + 린트·타입**

Run: `cd backend && pytest tests/api/test_admin_search_list.py -v && ruff check app && mypy app`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/admin_search.py backend/tests/api/test_admin_search_list.py
git commit -m "feat(analytics): GET /api/admin/search-queries 조회"
```

---

### Task 13: 방문 비콘 (프론트)

**Files:**
- Create: `web/components/VisitBeacon.tsx`
- Modify: `web/app/layout.tsx`
- Test: `web/tests/visit-beacon.test.tsx`

**Interfaces:**
- Produces: `<VisitBeacon />` — 마운트·경로 변경 시 `/api/analytics/hit`로 1회 sendBeacon. 앱셸(`IS_APP_SHELL`)에서는 no-op.

- [ ] **Step 1: 실패 테스트** — `web/tests/visit-beacon.test.tsx`

```tsx
// 방문 비콘이 경로당 1회 전송되고 앱셸에서 비활성인지 검증.
import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ usePathname: () => "/glossary/sahwal" }));
vi.mock("@/lib/appShell", () => ({ IS_APP_SHELL: false }));

import VisitBeacon from "@/components/VisitBeacon";

describe("VisitBeacon", () => {
  beforeEach(() => {
    (navigator as unknown as { sendBeacon: unknown }).sendBeacon = vi.fn();
  });

  it("경로당 1회 전송", () => {
    render(<VisitBeacon />);
    expect(navigator.sendBeacon).toHaveBeenCalledTimes(1);
    const [url] = (navigator.sendBeacon as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toBe("/api/analytics/hit");
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd web && npm test -- --run tests/visit-beacon.test.tsx`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현** — `web/components/VisitBeacon.tsx`

```tsx
"use client";
// 익명 방문을 백엔드로 통보하는 비콘 — 경로 변경마다 1회, 앱셸에서는 비활성.
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { IS_APP_SHELL } from "@/lib/appShell";

export default function VisitBeacon() {
  const pathname = usePathname();
  useEffect(() => {
    if (IS_APP_SHELL) return;
    if (typeof navigator === "undefined" || !navigator.sendBeacon) return;
    const body = JSON.stringify({ path: pathname, referrer: document.referrer });
    navigator.sendBeacon("/api/analytics/hit", new Blob([body], { type: "application/json" }));
  }, [pathname]);
  return null;
}
```

- [ ] **Step 4: 레이아웃 마운트** — `web/app/layout.tsx` `<body>` 안 `<AppShellBridge />` 근처에 추가

```tsx
import VisitBeacon from "@/components/VisitBeacon";
// ... <ThemeProviderClient> 아래:
<VisitBeacon />
```

- [ ] **Step 5: 통과 확인**

Run: `cd web && npm test -- --run tests/visit-beacon.test.tsx && npm run type-check`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add web/components/VisitBeacon.tsx web/app/layout.tsx web/tests/visit-beacon.test.tsx
git commit -m "feat(analytics): 방문 비콘 클라이언트"
```

---

### Task 14: 어드민 방문 통계 페이지 (탭 1)

**Files:**
- Create: `web/app/admin/analytics/page.tsx`
- Modify: `web/app/admin/page.tsx` (네비 링크)
- Test: `web/tests/admin-analytics.test.tsx`

**Interfaces:**
- Consumes: `api<AnalyticsOverview>("/api/admin/analytics?days=…")`. 타입은 이 파일 상단에 정의.

- [ ] **Step 1: 실패 테스트** — `web/tests/admin-analytics.test.tsx`

```tsx
// 어드민 방문 통계 페이지가 집계를 렌더하는지 검증.
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/store/authStore", () => ({ useAuthStore: () => ({ session: { nickname: "대공" } }) }));
vi.mock("@/lib/api", () => ({
  api: vi.fn().mockResolvedValue({
    totals: { pageviews: 42, unique_visitors: 30 },
    daily: [], top_pages: [{ path: "/faq", pageviews: 20, uniques: 15 }],
    sources: [{ source: "search", referrer_host: "google.com", pageviews: 30 }],
    countries: [{ country: "KR", pageviews: 40, uniques: 28 }],
  }),
  ApiError: class extends Error { status = 0 },
}));

import AnalyticsPage from "@/app/admin/analytics/page";

describe("AnalyticsPage", () => {
  it("KPI·인기페이지 렌더", async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText("42")).toBeInTheDocument());
    expect(screen.getByText("/faq")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd web && npm test -- --run tests/admin-analytics.test.tsx`
Expected: FAIL

- [ ] **Step 3: 구현** — `web/app/admin/analytics/page.tsx` (탭 1만; 탭 2는 Task 15에서 추가)

```tsx
"use client";
// 어드민 방문 통계 화면 — 방문 현황(PV·UV·유입경로·국가·인기페이지) 탭.
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

interface Overview {
  totals: { pageviews: number; unique_visitors: number };
  daily: { date: string; pageviews: number; uniques: number }[];
  top_pages: { path: string; pageviews: number; uniques: number }[];
  sources: { source: string; referrer_host: string | null; pageviews: number }[];
  countries: { country: string | null; pageviews: number; uniques: number }[];
}

export default function AnalyticsPage() {
  const { session } = useAuthStore();
  const router = useRouter();
  const [days, setDays] = useState(30);
  const [data, setData] = useState<Overview | null>(null);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    if (!session) { router.replace("/"); return; }
  }, [session, router]);

  useEffect(() => {
    api<Overview>(`/api/admin/analytics?days=${days}`)
      .then(setData)
      .catch((e) => { if (e instanceof ApiError && e.status === 403) setForbidden(true); });
  }, [days]);

  if (forbidden) return <p className="p-8 text-ink-mute">관리자 전용 페이지입니다.</p>;

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-serif text-2xl text-ink">방문 통계</h1>
        <Link href="/admin" className="font-mono text-xs text-ink-mute hover:text-oxblood">← 어드민</Link>
      </div>

      <div className="mb-6 flex gap-2">
        {[7, 30, 90].map((d) => (
          <button key={d} onClick={() => setDays(d)}
            className={`border border-ink-faint px-3 py-1 font-mono text-xs ${days === d ? "bg-ink text-paper" : "text-ink-mute"}`}>
            {d}일
          </button>
        ))}
      </div>

      <div className="mb-8 grid grid-cols-2 gap-4">
        <div className="border border-ink-faint p-4">
          <div className="font-mono text-xs uppercase tracking-label text-ink-faint">방문수(PV)</div>
          <div className="font-mono text-3xl tabular-nums text-ink">{data?.totals.pageviews ?? "–"}</div>
        </div>
        <div className="border border-ink-faint p-4">
          <div className="font-mono text-xs uppercase tracking-label text-ink-faint">순방문자</div>
          <div className="font-mono text-3xl tabular-nums text-ink">{data?.totals.unique_visitors ?? "–"}</div>
        </div>
      </div>

      <Section title="유입 경로">
        {data?.sources.map((s, i) => (
          <Row key={i} label={`${s.source}${s.referrer_host ? ` · ${s.referrer_host}` : ""}`} value={s.pageviews} />
        ))}
      </Section>
      <Section title="국가별">
        {data?.countries.map((c, i) => <Row key={i} label={c.country ?? "미상"} value={c.pageviews} />)}
      </Section>
      <Section title="인기 페이지">
        {data?.top_pages.map((p, i) => <Row key={i} label={p.path} value={p.pageviews} />)}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-2 border-b border-ink-faint pb-1 font-mono text-xs uppercase tracking-label text-ink-faint">{title}</h2>
      <ul className="divide-y divide-ink-faint">{children}</ul>
    </section>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <li className="flex items-center justify-between py-2 font-sans text-sm text-ink">
      <span className="truncate">{label}</span>
      <span className="font-mono tabular-nums text-ink-mute">{value}</span>
    </li>
  );
}
```

- [ ] **Step 4: 네비 링크** — `web/app/admin/page.tsx`의 어드민 링크 묶음(`/admin/stats` 옆)에 추가

```tsx
<Link href="/admin/analytics">방문 통계</Link>
```

- [ ] **Step 5: 통과 확인**

Run: `cd web && npm test -- --run tests/admin-analytics.test.tsx && npm run type-check && npm run lint`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add web/app/admin/analytics/page.tsx web/app/admin/page.tsx web/tests/admin-analytics.test.tsx
git commit -m "feat(analytics): 어드민 방문 통계 페이지(탭1)"
```

---

### Task 15: 검색 유입 탭 (탭 2) + 네이버 CSV 업로드

**Files:**
- Modify: `web/app/admin/analytics/page.tsx`
- Test: `web/tests/admin-search.test.tsx`

**Interfaces:**
- Consumes: `api<SearchQueryRow[]>("/api/admin/search-queries?…")`, CSV 업로드는 `fetch("/api/admin/search-queries/import", {method:"POST", body: FormData})`.

- [ ] **Step 1: 실패 테스트** — `web/tests/admin-search.test.tsx`

```tsx
// 검색 유입 탭이 검색어 표를 렌더하는지 검증.
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/store/authStore", () => ({ useAuthStore: () => ({ session: { nickname: "대공" } }) }));
vi.mock("@/lib/api", () => ({
  api: vi.fn((path: string) =>
    path.startsWith("/api/admin/search-queries")
      ? Promise.resolve([{ query: "바둑 사활", page: "/g/s", clicks: 5, impressions: 50, ctr: 0.1, position: 3, source: "google" }])
      : Promise.resolve({ totals: { pageviews: 0, unique_visitors: 0 }, daily: [], top_pages: [], sources: [], countries: [] })),
  ApiError: class extends Error { status = 0 },
}));

import AnalyticsPage from "@/app/admin/analytics/page";

describe("검색 유입 탭", () => {
  it("검색어 렌더", async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText("바둑 사활")).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd web && npm test -- --run tests/admin-search.test.tsx`
Expected: FAIL — 검색어 미렌더

- [ ] **Step 3: 구현** — `web/app/admin/analytics/page.tsx`에 검색어 상태·섹션 추가

컴포넌트 상단 상태에 추가:

```tsx
interface SearchRow { query: string; page: string | null; clicks: number; impressions: number; ctr: number; position: number | null; source: string; }
const [queries, setQueries] = useState<SearchRow[]>([]);

useEffect(() => {
  api<SearchRow[]>("/api/admin/search-queries?source=all&days=90&top=50")
    .then(setQueries).catch(() => {});
}, []);

async function uploadNaver(e: React.ChangeEvent<HTMLInputElement>) {
  const file = e.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  await fetch("/api/admin/search-queries/import", { method: "POST", body: fd, credentials: "include" });
  const rows = await api<SearchRow[]>("/api/admin/search-queries?source=all&days=90&top=50");
  setQueries(rows);
}
```

렌더 하단(마지막 `</div>` 직전)에 검색어 섹션 추가:

```tsx
<Section title="검색 유입 (검색어)">
  <li className="flex justify-end py-2">
    <label className="cursor-pointer font-mono text-xs text-oxblood hover:underline">
      네이버 CSV 업로드
      <input type="file" accept=".csv" onChange={uploadNaver} className="hidden" />
    </label>
  </li>
  {queries.map((q, i) => (
    <li key={i} className="flex items-center justify-between py-2 font-sans text-sm text-ink">
      <span className="truncate">{q.query} <span className="font-mono text-xs text-ink-faint">· {q.source}</span></span>
      <span className="font-mono tabular-nums text-ink-mute">{q.clicks}↑ / {q.impressions}노출</span>
    </li>
  ))}
</Section>
```

- [ ] **Step 4: 통과 확인**

Run: `cd web && npm test -- --run tests/admin-search.test.tsx && npm run type-check && npm run lint`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add web/app/admin/analytics/page.tsx web/tests/admin-search.test.tsx
git commit -m "feat(analytics): 검색 유입 탭 + 네이버 CSV 업로드"
```

---

### Task 16: 배포 설정·프라이버시·크론 문서화

**Files:**
- Modify: `backend/.env.example`
- Modify: `web/content/` 또는 프라이버시 페이지 (`web/app/privacy/` 내 문구 파일)
- Modify: `docs/ai-orchestration-setup.md` 또는 신규 `docs/ops/runbooks/gsc-sync.md`

**Interfaces:** 없음(문서·설정만).

- [ ] **Step 1: env 예시 추가** — `backend/.env.example`에

```bash
# 방문 통계 — 구글 Search Console (검색어 자동 동기화). 미설정 시 기능 off.
GSC_PROPERTY_URL=sc-domain:inkbaduk.com
GSC_SERVICE_ACCOUNT_JSON=/Users/daegong/.baduk-gsc-key.json
```

- [ ] **Step 2: 프라이버시 문구 한 줄 추가** — 프라이버시 페이지에 "자체 방문 분석을 운영하며 원본 IP는 저장하지 않고 국가코드와 일일 익명 해시만 집계합니다." 문장 추가(기존 문구 파일 위치는 `web/app/privacy/` 확인 후 삽입).

- [ ] **Step 3: 크론 런북 작성** — `docs/ops/runbooks/gsc-sync.md`

```markdown
# GSC 검색어 동기화

매일 1회 `cd backend && python -m scripts.sync_gsc` 실행(launchd 또는 기존 ops 스케줄러).
사전: `~/.baduk.env`에 GSC_PROPERTY_URL, GSC_SERVICE_ACCOUNT_JSON 설정 + 서비스 계정을
GSC 속성 사용자로 추가. 미설정이면 no-op 로그만 남기고 종료.
```

- [ ] **Step 4: 전체 검증**

Run: `cd backend && pytest --cov=app --cov-fail-under=80 && ruff check . && mypy app`
Run: `cd web && npm test -- --run && npm run type-check && npm run lint`
Expected: 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/.env.example docs/ops/runbooks/gsc-sync.md web/app/privacy
git commit -m "docs(analytics): GSC 동기화 런북·env 예시·프라이버시 문구"
```

---

## Self-Review 결과

- **스펙 커버리지**: 모듈 A(수집 Task5·집계 Task6·모델 Task1·분류 Task2·해시 Task3·봇 Task4), 모듈 B(모델 Task7·네이버 Task8·9·구글 Task10·11·조회 Task12), 프론트(비콘 Task13·탭1 Task14·탭2 Task15), 설정·프라이버시·크론(Task16) — 스펙 전 항목 매핑됨.
- **플레이스홀더**: 각 스텝에 실제 코드·명령·기대결과 포함. Task16 프라이버시 삽입 위치만 "확인 후 삽입"으로 남김(파일 위치가 구현 시점 확인 필요 — 나머지는 전부 구체).
- **타입 일관성**: `GscRow`·`NaverRow`·`SearchQuery`·`VisitHit`·`AnalyticsOverview`·`SearchQueryRow` 명칭·필드가 태스크 간 일치. `visitor_hash(ip,salt)`·`classify_source`·`parse_referrer_host` 시그니처 일관.
- **의존성 순서**: 1→6(A), 7→12(B, 7이 모델 선행), 13→15(프론트, 6·12 API 선행), 16 마지막. 모듈 A와 B는 독립이라 병렬 가능.
