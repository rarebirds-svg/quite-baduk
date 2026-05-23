# Agentic Ops 테마·이 달의 명국 (하위 프로젝트 3b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 정적 테마 카탈로그(5-8개) + 결정적 월간 픽 알고리즘으로 프로기보 SEO 밀도와 탐색 깊이를 키운다.

**Architecture:** 테마는 backend `themes.py`에 slug→filter 매핑을 단일 진실 공급원으로 두고, `/api/spectate/pro/themes` 리스트 + `/api/spectate/pro/theme/<slug>` 게임 목록 두 endpoint로 노출. 픽은 `hashlib.sha256("YYYY-MM")` 시드로 후보 풀에서 결정적 단일 선택(`monthly_pick.py`). 프론트는 새 라우트 `/spectate/themes/[slug]`, `/spectate/picks/`, `/spectate/picks/monthly/[yyyymm]` + layout.tsx generateMetadata. 3a의 sitemap을 확장해 테마·픽 URL 포함.

**Tech Stack:** Python (FastAPI + SQLAlchemy async), hashlib, pytest, Next.js 14 App Router (server components + generateMetadata), Vitest.

**브랜치:** 모든 작업은 `feat/agentic-ops-content-3b`에서 수행한다(spec 커밋 `e5c69a3` 올라가 있음). base는 `feat/agentic-ops-sre`(3a 머지 후).

**전제:** 3a 머지 후 — `feat/agentic-ops-sre`에 sub-project 0~3a 커밋이 다 있다. backend `/api/spectate/pro/sitemap`·`/{id}` (3a)·기존 list endpoint 작동. `pro_games` 911국, `web/app/sitemap.ts`는 3a의 동적 버전.

**경로 상수:** 리포 루트 `/Users/daegong/projects/baduk`.

**주의 — 앱 코드 수정**: 3a와 동일. backend·web 파일 변경. 검증은 staging에서. prod 머지·반영은 별도 deploy.md 절차.

---

### Task 1: backend `themes.py` 모듈 + 2개 endpoint

테마 카탈로그를 backend에 단일 진실 공급원으로 두고 list/detail 2개 endpoint 추가.

**Files:**
- Create: `backend/app/core/pro/__init__.py`
- Create: `backend/app/core/pro/themes.py`
- Modify: `backend/app/api/spectate_pro.py`
- Test: `backend/tests/core/pro/__init__.py` (빈 파일)
- Test: `backend/tests/core/pro/test_themes.py`
- Modify: `backend/tests/api/test_spectate_pro.py`

- [ ] **Step 1: 패키지 디렉터리·init 생성**

Run:
```bash
mkdir -p /Users/daegong/projects/baduk/backend/app/core/pro
mkdir -p /Users/daegong/projects/baduk/backend/tests/core/pro
touch /Users/daegong/projects/baduk/backend/app/core/pro/__init__.py
touch /Users/daegong/projects/baduk/backend/tests/core/pro/__init__.py
```

`backend/app/core/pro/__init__.py`에 한 줄 docstring 첫줄(CLAUDE.md 규칙 6):
```python
# 프로기보 도메인 로직 — 테마 카탈로그·월간 픽 등.
```
`backend/tests/core/pro/__init__.py`는 빈 파일(테스트 패키지 마커, CLAUDE.md 규칙 6 예외).

- [ ] **Step 2: 테마 모듈 실패 테스트**

`backend/tests/core/pro/test_themes.py`:
```python
# 테마 카탈로그·필터 매핑 단위 테스트.
from app.core.pro.themes import THEMES, theme_by_slug, theme_query_clause


def test_themes_catalog_has_required_keys():
    assert len(THEMES) >= 5
    for t in THEMES:
        assert set(t.keys()) >= {"slug", "label", "description", "filter_type", "filter_value"}
        assert t["slug"] and isinstance(t["slug"], str)
        assert t["filter_type"] in {"collection", "event_like", "event_exact", "date_gte"}


def test_themes_slugs_unique():
    slugs = [t["slug"] for t in THEMES]
    assert len(slugs) == len(set(slugs))


def test_theme_by_slug_found_and_missing():
    assert theme_by_slug("masterpieces") is not None
    assert theme_by_slug("masterpieces")["slug"] == "masterpieces"
    assert theme_by_slug("does-not-exist") is None


def test_theme_query_clause_known_slug_returns_clause():
    clause = theme_query_clause("masterpieces")
    assert clause is not None  # SQLAlchemy BinaryExpression


def test_theme_query_clause_unknown_slug_returns_none():
    assert theme_query_clause("does-not-exist") is None


def test_theme_query_clause_unknown_filter_type_raises():
    # 카탈로그 자체엔 알 수 없는 type 없도록 보장 — 카탈로그 모든 슬러그가 clause 반환.
    for t in THEMES:
        clause = theme_query_clause(t["slug"])
        assert clause is not None, f"slug {t['slug']} returned None clause"
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/core/pro/test_themes.py -v`
Expected: ModuleNotFoundError (themes.py 미존재).

- [ ] **Step 4: themes 모듈 구현**

`backend/app/core/pro/themes.py`:
```python
# 프로기보 테마 카탈로그 — slug → 필터 SQLAlchemy clause 매핑.
"""테마 카탈로그.

각 테마는 정적 dict로 정의된다. slug는 URL·canonical에 쓰이므로 변경 금지.
filter_type별로 ProGame 컬럼에 대한 SQLAlchemy 표현식을 반환한다.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.sql import ColumnElement

from app.models import ProGame

THEMES: list[dict[str, Any]] = [
    {
        "slug": "masterpieces",
        "label": "명국선",
        "description": "도사쿠·슈사쿠 등 옛 명인의 명국 모음.",
        "filter_type": "collection",
        "filter_value": "masterpiece",
    },
    {
        "slug": "world-finals",
        "label": "세계기전 결승",
        "description": "응씨배·잉씨배·LG·삼성·춘란 등 세계기전 결승국.",
        "filter_type": "collection",
        "filter_value": "world",
    },
    {
        "slug": "cwi",
        "label": "CWI 공개기보",
        "description": "Centrum Wiskunde & Informatica 퍼블릭 도메인 컬렉션.",
        "filter_type": "collection",
        "filter_value": "cwi",
    },
    {
        "slug": "honinbo",
        "label": "본인방전",
        "description": "일본 본인방전 관련 기보.",
        "filter_type": "event_like",
        "filter_value": "Honinbo",
    },
    {
        "slug": "castle-games",
        "label": "오성 (御城碁)",
        "description": "에도 시대 오성기보.",
        "filter_type": "event_exact",
        "filter_value": "Castle Game",
    },
    {
        "slug": "21st-century",
        "label": "21세기 명국",
        "description": "2000년 이후 대국.",
        "filter_type": "date_gte",
        "filter_value": "2000-01-01",
    },
]


def theme_by_slug(slug: str) -> dict[str, Any] | None:
    return next((t for t in THEMES if t["slug"] == slug), None)


def theme_query_clause(slug: str) -> ColumnElement[bool] | None:
    """slug에 해당하는 SQLAlchemy WHERE clause. 모르는 slug는 None."""
    theme = theme_by_slug(slug)
    if theme is None:
        return None
    ft = theme["filter_type"]
    fv = theme["filter_value"]
    if ft == "collection":
        return ProGame.collection == fv
    if ft == "event_like":
        return ProGame.event.like(f"%{fv}%")
    if ft == "event_exact":
        return ProGame.event == fv
    if ft == "date_gte":
        return ProGame.game_date >= fv
    raise ValueError(f"unknown filter_type: {ft}")
```

- [ ] **Step 5: 모듈 테스트 통과 확인**

Run: `pytest tests/core/pro/test_themes.py -v`
Expected: 6개 PASS.

- [ ] **Step 6: API endpoint 실패 테스트**

`backend/tests/api/test_spectate_pro.py` 끝에 추가:
```python
async def test_themes_list_endpoint_returns_catalog(client):
    resp = await client.get("/api/spectate/pro/themes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    slugs = [t["slug"] for t in data]
    assert "masterpieces" in slugs
    item = data[0]
    assert set(item.keys()) >= {"slug", "label", "description", "count"}


async def test_themes_list_includes_counts(client, db_session):
    # 기존 fixture로 pro_games가 어느 정도 있다고 가정. count는 0 이상 정수.
    resp = await client.get("/api/spectate/pro/themes")
    for item in resp.json():
        assert isinstance(item["count"], int)
        assert item["count"] >= 0


async def test_theme_detail_known_slug(client):
    resp = await client.get("/api/spectate/pro/theme/masterpieces")
    assert resp.status_code == 200
    data = resp.json()
    assert "games" in data
    assert "total" in data
    assert isinstance(data["games"], list)
    assert isinstance(data["total"], int)


async def test_theme_detail_unknown_slug_404(client):
    resp = await client.get("/api/spectate/pro/theme/does-not-exist")
    assert resp.status_code == 404
```

테스트의 `client` fixture명·기존 fixture가 다르면 그에 맞춰 수정. 기존 fixture는 `grep -n '@pytest.fixture\|client\|db_session' backend/tests/api/test_spectate_pro.py`로 확인.

- [ ] **Step 7: endpoint 실패 확인**

Run: `pytest tests/api/test_spectate_pro.py -v -k "themes"`
Expected: 4개 FAIL with 404 (routes absent).

- [ ] **Step 8: endpoint 구현**

`backend/app/api/spectate_pro.py`에 추가 (기존 `/sitemap` endpoint 다음):
```python
from app.core.pro.themes import THEMES, theme_by_slug, theme_query_clause


@router.get("/themes")
async def list_themes(db: DbSession) -> list[dict[str, Any]]:
    """테마 카탈로그 + 각 테마의 게임 수."""
    out: list[dict[str, Any]] = []
    for t in THEMES:
        clause = theme_query_clause(t["slug"])
        if clause is None:
            continue
        result = await db.execute(
            select(ProGame.id).where(clause)
        )
        count = len(result.scalars().all())
        out.append({
            "slug": t["slug"],
            "label": t["label"],
            "description": t["description"],
            "count": count,
        })
    return out


@router.get("/theme/{slug}")
async def theme_detail(slug: str, db: DbSession) -> dict[str, Any]:
    """테마별 게임 목록 + 메타. 알 수 없는 slug는 404."""
    theme = theme_by_slug(slug)
    if theme is None:
        raise HTTPException(status_code=404, detail="theme_not_found")
    clause = theme_query_clause(slug)
    result = await db.execute(
        select(ProGame).where(clause).order_by(ProGame.game_date.desc().nulls_last(), ProGame.id)
    )
    games = result.scalars().all()
    return {
        "slug": theme["slug"],
        "label": theme["label"],
        "description": theme["description"],
        "total": len(games),
        "games": [
            {
                "id": g.id,
                "black_player": g.black_player,
                "white_player": g.white_player,
                "event": g.event,
                "game_date": g.game_date.isoformat() if g.game_date else None,
                "result": g.result,
            }
            for g in games
        ],
    }
```

`HTTPException` import가 없으면 추가. `nulls_last()`가 SQLite에서 동작하지 않으면 단순 `order_by(ProGame.game_date.desc(), ProGame.id)`로 변경(NULLS는 SQLite에서 자연 정렬됨).

- [ ] **Step 9: endpoint 테스트 통과 확인**

Run: `pytest tests/api/test_spectate_pro.py -v`
Expected: 기존 + 신규 4개 모두 PASS.

- [ ] **Step 10: 회귀 + 린트**

Run:
```bash
pytest -q
ruff check .
mypy app
```
Expected: 통과.

- [ ] **Step 11: 커밋**

```bash
git add backend/app/core/pro backend/app/api/spectate_pro.py backend/tests/core/pro backend/tests/api/test_spectate_pro.py
git commit -m "feat(api): 프로기보 테마 카탈로그 + /themes·/theme/{slug} endpoint"
```

---

### Task 2: backend `monthly_pick` 모듈 + endpoint

결정적 월간 픽 알고리즘과 endpoint.

**Files:**
- Create: `backend/app/core/pro/monthly_pick.py`
- Create: `backend/tests/core/pro/test_monthly_pick.py`
- Modify: `backend/app/api/spectate_pro.py`
- Modify: `backend/tests/api/test_spectate_pro.py`

- [ ] **Step 1: monthly_pick 모듈 단위 테스트**

`backend/tests/core/pro/test_monthly_pick.py`:
```python
# 월간 픽 알고리즘 단위 테스트 — 결정적 시드와 fallback 동작.
import pytest

from app.core.pro.monthly_pick import (
    parse_yyyymm,
    pick_index,
    InvalidYearMonth,
)


def test_parse_yyyymm_valid():
    assert parse_yyyymm("2026-05") == (2026, 5)
    assert parse_yyyymm("1999-12") == (1999, 12)


def test_parse_yyyymm_rejects_bad_format():
    for bad in ["2026-13", "2026/05", "26-05", "2026-5", "2026-00", "abcd-ef"]:
        with pytest.raises(InvalidYearMonth):
            parse_yyyymm(bad)


def test_pick_index_deterministic():
    # 같은 입력 + 같은 길이 → 같은 인덱스
    assert pick_index("2026-05", 100) == pick_index("2026-05", 100)
    assert pick_index("2026-06", 100) == pick_index("2026-06", 100)


def test_pick_index_changes_with_input():
    # 다른 yyyymm은 (높은 확률로) 다른 인덱스
    a = pick_index("2026-05", 100)
    b = pick_index("2026-06", 100)
    assert a != b  # SHA256이므로 우연한 충돌 가능성 극히 낮음


def test_pick_index_in_range():
    for yyyymm in ["2024-01", "2024-06", "2025-12"]:
        assert 0 <= pick_index(yyyymm, 50) < 50


def test_pick_index_single_candidate():
    assert pick_index("2026-05", 1) == 0
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/pro/test_monthly_pick.py -v`
Expected: ImportError.

- [ ] **Step 3: monthly_pick 모듈 구현**

`backend/app/core/pro/monthly_pick.py`:
```python
# 결정적 월간 픽 알고리즘 — SHA256 시드로 후보 풀에서 단일 선택.
"""월간 픽.

`YYYY-MM` 문자열을 받아 결정적으로 한 게임을 고른다. 같은 입력은 같은 결과.
알고리즘 변경 시 SEO 노출에 영향(URL 그대로지만 콘텐츠 바뀜) — 버전 주석 참조.

Version: v1 (2026-05) — sha256(yyyymm) % len(candidates).
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProGame

_YYYYMM_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


class InvalidYearMonth(ValueError):
    """yyyymm이 YYYY-MM 형식이 아닐 때."""


def parse_yyyymm(yyyymm: str) -> tuple[int, int]:
    m = _YYYYMM_RE.match(yyyymm)
    if m is None:
        raise InvalidYearMonth(f"expected YYYY-MM, got {yyyymm!r}")
    year = int(m.group(1))
    month = int(m.group(2))
    return year, month


def pick_index(yyyymm: str, n: int) -> int:
    """결정적 인덱스. n=0 호출하지 마라 (caller 검증)."""
    if n <= 0:
        raise ValueError("n must be positive")
    h = hashlib.sha256(yyyymm.encode("utf-8")).hexdigest()
    return int(h, 16) % n


async def candidates_for_month(db: AsyncSession, month: int) -> list[int]:
    """해당 달(1-12)의 후보 ID 리스트. masterpiece 우선, fallback 전체."""
    month_str = f"{month:02d}"
    masterpiece_q = select(ProGame.id).where(
        func.strftime("%m", ProGame.game_date) == month_str,
        ProGame.collection == "masterpiece",
    ).order_by(ProGame.id)
    result = await db.execute(masterpiece_q)
    ids = list(result.scalars().all())
    if ids:
        return ids
    all_q = select(ProGame.id).where(
        func.strftime("%m", ProGame.game_date) == month_str,
    ).order_by(ProGame.id)
    result = await db.execute(all_q)
    return list(result.scalars().all())


async def pick_for_month(db: AsyncSession, yyyymm: str) -> int | None:
    """yyyymm → game ID 또는 None(후보 0)."""
    _, month = parse_yyyymm(yyyymm)
    candidates = await candidates_for_month(db, month)
    if not candidates:
        return None
    return candidates[pick_index(yyyymm, len(candidates))]
```

- [ ] **Step 4: 모듈 테스트 통과 확인**

Run: `pytest tests/core/pro/test_monthly_pick.py -v`
Expected: 6개 PASS.

- [ ] **Step 5: endpoint 실패 테스트**

`backend/tests/api/test_spectate_pro.py` 끝에 추가:
```python
async def test_pick_monthly_returns_game(client):
    resp = await client.get("/api/spectate/pro/pick/monthly/2026-05")
    # 200(픽 성공) 또는 404(후보 0) 둘 다 허용 — DB 상태 의존
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert "id" in data
        assert "yyyymm" in data and data["yyyymm"] == "2026-05"


async def test_pick_monthly_deterministic(client):
    a = await client.get("/api/spectate/pro/pick/monthly/2026-05")
    b = await client.get("/api/spectate/pro/pick/monthly/2026-05")
    assert a.status_code == b.status_code
    if a.status_code == 200:
        assert a.json()["id"] == b.json()["id"]


async def test_pick_monthly_invalid_format(client):
    resp = await client.get("/api/spectate/pro/pick/monthly/2026-13")
    assert resp.status_code == 400
```

- [ ] **Step 6: 실패 확인**

Run: `pytest tests/api/test_spectate_pro.py -v -k "pick_monthly"`
Expected: 3개 FAIL with 404 (route absent).

- [ ] **Step 7: endpoint 구현**

`backend/app/api/spectate_pro.py`에 추가:
```python
from app.core.pro.monthly_pick import InvalidYearMonth, pick_for_month


@router.get("/pick/monthly/{yyyymm}")
async def pick_monthly(yyyymm: str, db: DbSession) -> dict[str, Any]:
    """결정적 월간 픽. yyyymm=YYYY-MM. 후보 0이면 404, 형식 오류 400."""
    try:
        picked_id = await pick_for_month(db, yyyymm)
    except InvalidYearMonth as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if picked_id is None:
        raise HTTPException(status_code=404, detail="no_candidates")
    game = (
        await db.execute(select(ProGame).where(ProGame.id == picked_id))
    ).scalar_one()
    return {
        "yyyymm": yyyymm,
        "id": game.id,
        "black_player": game.black_player,
        "white_player": game.white_player,
        "event": game.event,
        "game_date": game.game_date.isoformat() if game.game_date else None,
        "result": game.result,
    }
```

- [ ] **Step 8: endpoint 테스트 통과 확인**

Run: `pytest tests/api/test_spectate_pro.py -v -k "pick_monthly"`
Expected: 3개 PASS.

- [ ] **Step 9: 회귀**

Run: `pytest -q && ruff check . && mypy app`
Expected: 통과.

- [ ] **Step 10: 커밋**

```bash
git add backend/app/core/pro/monthly_pick.py backend/tests/core/pro/test_monthly_pick.py backend/app/api/spectate_pro.py backend/tests/api/test_spectate_pro.py
git commit -m "feat(api): 결정적 월간 픽 알고리즘 + /pick/monthly/{yyyymm} endpoint"
```

---

### Task 3: web 테마 라우트

`/spectate/themes/[slug]` 페이지 + layout(generateMetadata).

**Files:**
- Create: `web/app/spectate/themes/[slug]/page.tsx`
- Create: `web/app/spectate/themes/[slug]/layout.tsx`

- [ ] **Step 1: 페이지 컴포넌트 작성**

`web/app/spectate/themes/[slug]/page.tsx`:
```tsx
// 테마 페이지 — backend API 결과를 서버 컴포넌트로 렌더.
import { notFound } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ThemeGame {
  id: number;
  black_player: string;
  white_player: string;
  event: string | null;
  game_date: string | null;
  result: string | null;
}

interface ThemeDetail {
  slug: string;
  label: string;
  description: string;
  total: number;
  games: ThemeGame[];
}

async function fetchTheme(slug: string): Promise<ThemeDetail | null> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/theme/${slug}`, {
      next: { revalidate: 3600 },
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return (await res.json()) as ThemeDetail;
  } catch {
    return null;
  }
}

export default async function ThemePage({
  params,
}: {
  params: { slug: string };
}) {
  const data = await fetchTheme(params.slug);
  if (data === null) notFound();
  return (
    <article className="prose">
      <header>
        <h1>{data.label}</h1>
        <p className="text-ink-mute">{data.description}</p>
        <p className="text-ink-faint">총 {data.total}국</p>
      </header>
      <ul className="not-prose grid gap-2">
        {data.games.map((g) => (
          <li key={g.id}>
            <a href={`/spectate/pro/${g.id}`} className="block py-2 border-b border-ink-faint/20">
              <span className="font-medium">
                {g.black_player} vs {g.white_player}
              </span>
              {g.event && <span className="text-ink-mute"> · {g.event}</span>}
              {g.game_date && <span className="text-ink-faint"> · {g.game_date}</span>}
              {g.result && <span className="text-ink-faint"> · {g.result}</span>}
            </a>
          </li>
        ))}
      </ul>
    </article>
  );
}
```

className은 기존 디자인 토큰(`bg-paper`·`text-ink-mute` 등)을 따른다 — 토큰이 다르면 실제 globals.css 토큰명으로 맞춤.

- [ ] **Step 2: layout.tsx 작성 (generateMetadata)**

`web/app/spectate/themes/[slug]/layout.tsx`:
```tsx
// 테마 페이지 SEO 메타 — server component layout.
import type { Metadata } from "next";
import type { ReactNode } from "react";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ThemeMeta {
  slug: string;
  label: string;
  description: string;
  total: number;
}

export async function generateMetadata(
  { params }: { params: { slug: string } },
): Promise<Metadata> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/theme/${params.slug}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return { robots: { index: false, follow: false } };
    const t = (await res.json()) as ThemeMeta;
    const title = `${t.label} — inkbaduk`;
    const description = `${t.description} (총 ${t.total}국)`;
    const canonical = `${BASE}/spectate/themes/${t.slug}`;
    return {
      title,
      description,
      alternates: { canonical },
      openGraph: { title, description, url: canonical },
    };
  } catch {
    return {};
  }
}

export default function ThemeLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 3: 빌드 확인**

Run: `cd web && npm run type-check && npm run build 2>&1 | tail -5`
Expected: type-check OK, build 성공. 새 라우트 `/spectate/themes/[slug]`가 Dynamic으로 나옴.

- [ ] **Step 4: 커밋**

```bash
git add web/app/spectate/themes
git commit -m "feat(web): /spectate/themes/[slug] 테마 페이지 + generateMetadata"
```

---

### Task 4: web 월간 픽 라우트

`/spectate/picks/monthly/[yyyymm]` 페이지 + layout.

**Files:**
- Create: `web/app/spectate/picks/monthly/[yyyymm]/page.tsx`
- Create: `web/app/spectate/picks/monthly/[yyyymm]/layout.tsx`

- [ ] **Step 1: 페이지 컴포넌트 작성**

`web/app/spectate/picks/monthly/[yyyymm]/page.tsx`:
```tsx
// 이 달의 명국 — 결정적 픽 단일 게임 랜딩 페이지.
import { notFound } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface MonthlyPick {
  yyyymm: string;
  id: number;
  black_player: string;
  white_player: string;
  event: string | null;
  game_date: string | null;
  result: string | null;
}

async function fetchPick(yyyymm: string): Promise<MonthlyPick | null> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/pick/monthly/${yyyymm}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return (await res.json()) as MonthlyPick;
  } catch {
    return null;
  }
}

function adjacentMonth(yyyymm: string, delta: number): string {
  const [y, m] = yyyymm.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
}

export default async function MonthlyPickPage({
  params,
}: {
  params: { yyyymm: string };
}) {
  const data = await fetchPick(params.yyyymm);
  if (data === null) notFound();
  const [y, m] = data.yyyymm.split("-");
  const prev = adjacentMonth(data.yyyymm, -1);
  const next = adjacentMonth(data.yyyymm, +1);
  return (
    <article className="prose">
      <header>
        <p className="text-ink-mute">{y}년 {Number(m)}월 이 달의 명국</p>
        <h1>
          {data.black_player} vs {data.white_player}
        </h1>
        {data.event && <p className="text-ink-mute">{data.event}</p>}
        {data.game_date && <p className="text-ink-faint">{data.game_date}</p>}
        {data.result && <p className="text-ink-faint">결과 {data.result}</p>}
      </header>
      <p className="not-prose">
        <a href={`/spectate/pro/${data.id}`}>관전·복기 →</a>
      </p>
      <nav className="not-prose flex gap-4 text-ink-mute text-sm">
        <a href={`/spectate/picks/monthly/${prev}`}>← {prev}</a>
        <a href={`/spectate/picks/monthly/${next}`}>{next} →</a>
        <a href={`/spectate/picks`}>전체 픽</a>
      </nav>
    </article>
  );
}
```

- [ ] **Step 2: layout.tsx (generateMetadata)**

`web/app/spectate/picks/monthly/[yyyymm]/layout.tsx`:
```tsx
// 월간 픽 페이지 SEO 메타.
import type { Metadata } from "next";
import type { ReactNode } from "react";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface PickMeta {
  yyyymm: string;
  id: number;
  black_player: string;
  white_player: string;
  event: string | null;
  game_date: string | null;
  result: string | null;
}

export async function generateMetadata(
  { params }: { params: { yyyymm: string } },
): Promise<Metadata> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/pick/monthly/${params.yyyymm}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return { robots: { index: false, follow: false } };
    const p = (await res.json()) as PickMeta;
    const [y, m] = p.yyyymm.split("-");
    const title = `${y}년 ${Number(m)}월 이 달의 명국 — ${p.black_player} vs ${p.white_player} — inkbaduk`;
    const description = [p.event, p.game_date, p.result ? `결과 ${p.result}` : null]
      .filter(Boolean)
      .join(" · ") || "inkbaduk 이 달의 명국";
    const canonical = `${BASE}/spectate/picks/monthly/${p.yyyymm}`;
    return {
      title,
      description,
      alternates: { canonical },
      openGraph: { title, description, url: canonical },
    };
  } catch {
    return {};
  }
}

export default function MonthlyPickLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
```

- [ ] **Step 3: 빌드 확인**

Run: `cd web && npm run type-check && npm run build 2>&1 | tail -5`
Expected: 통과 + `/spectate/picks/monthly/[yyyymm]` Dynamic 라우트 등록.

- [ ] **Step 4: 커밋**

```bash
git add web/app/spectate/picks/monthly
git commit -m "feat(web): /spectate/picks/monthly/[yyyymm] 이 달의 명국 랜딩 + 메타"
```

---

### Task 5: web 픽 인덱스 페이지

`/spectate/picks` — 최근 12개월 + 현재 + 향후 1개월 픽 리스트.

**Files:**
- Create: `web/app/spectate/picks/page.tsx`

- [ ] **Step 1: 인덱스 페이지 작성**

`web/app/spectate/picks/page.tsx`:
```tsx
// 이 달의 명국 인덱스 — 최근 12개월 + 현재 + 다음 달 픽 리스트.
import type { Metadata } from "next";

const BASE = "https://inkbaduk.com";

export const metadata: Metadata = {
  title: "이 달의 명국 — inkbaduk",
  description: "매월 결정적 알고리즘으로 고른 inkbaduk의 이 달의 명국 픽.",
  alternates: { canonical: `${BASE}/spectate/picks` },
};

function monthList(): string[] {
  const now = new Date();
  const months: string[] = [];
  for (let delta = -12; delta <= 1; delta++) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + delta, 1));
    months.push(
      `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`,
    );
  }
  return months;
}

export default function PicksIndex() {
  const months = monthList();
  return (
    <article className="prose">
      <h1>이 달의 명국</h1>
      <p>매월 결정적 알고리즘으로 한 게임을 고릅니다. 같은 달은 같은 픽.</p>
      <ul className="not-prose grid gap-1">
        {months.map((m) => {
          const [y, mm] = m.split("-");
          return (
            <li key={m}>
              <a href={`/spectate/picks/monthly/${m}`}>
                {y}년 {Number(mm)}월
              </a>
            </li>
          );
        })}
      </ul>
    </article>
  );
}
```

- [ ] **Step 2: 빌드 확인**

Run: `cd web && npm run type-check && npm run build 2>&1 | tail -5`
Expected: 통과.

- [ ] **Step 3: 커밋**

```bash
git add web/app/spectate/picks/page.tsx
git commit -m "feat(web): /spectate/picks 인덱스 페이지"
```

---

### Task 6: sitemap.ts 확장 + 테스트

테마·픽 URL을 sitemap에 추가.

**Files:**
- Modify: `web/app/sitemap.ts`
- Modify: `web/tests/sitemap.test.ts`

- [ ] **Step 1: 실패 테스트 추가**

`web/tests/sitemap.test.ts` 끝에 추가:
```ts
describe("sitemap themes and picks", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it("includes theme + picks index + monthly pick URLs", async () => {
    const themesList = [
      { slug: "masterpieces", label: "명국선", description: "", count: 10 },
      { slug: "honinbo", label: "본인방전", description: "", count: 5 },
    ];
    const proList = [{ id: 1, created_at: "2024-01-01T00:00:00" }];

    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (url: string) => {
        if (url.endsWith("/api/spectate/pro/sitemap")) {
          return { ok: true, json: async () => proList };
        }
        if (url.endsWith("/api/spectate/pro/themes")) {
          return { ok: true, json: async () => themesList };
        }
        return { ok: false, json: async () => [] };
      }),
    );

    const { default: sitemap } = await import("../app/sitemap");
    const urls = await sitemap();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/themes/masterpieces")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/themes/honinbo")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/picks")).toBeDefined();
    // monthly picks 최근 12 + 현재 + 다음 = 14 URL
    const monthlyCount = urls.filter((u) =>
      u.url.startsWith("https://inkbaduk.com/spectate/picks/monthly/"),
    ).length;
    expect(monthlyCount).toBe(14);
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd web && npm test -- --run sitemap.test`
Expected: 새 테스트 FAIL, 기존 2개 PASS.

- [ ] **Step 3: sitemap.ts 확장**

`web/app/sitemap.ts`에서 `fetchProList` 함수 다음에 추가:
```ts
interface ThemeItem {
  slug: string;
  label: string;
  description: string;
  count: number;
}

async function fetchThemesList(): Promise<ThemeItem[]> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/themes`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return (await res.json()) as ThemeItem[];
  } catch {
    return [];
  }
}

function monthlyPickMonths(): string[] {
  const now = new Date();
  const months: string[] = [];
  for (let delta = -12; delta <= 1; delta++) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + delta, 1));
    months.push(
      `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`,
    );
  }
  return months;
}
```

그리고 default export 함수 안 `return` 직전에 다음 블록을 추가 (기존 `proUrls` 다음에):
```ts
  const themesList = await fetchThemesList();
  const now2 = new Date();
  const themeUrls: MetadataRoute.Sitemap = themesList.map((t) => ({
    url: `${BASE}/spectate/themes/${t.slug}`,
    lastModified: now2,
    changeFrequency: "monthly",
    priority: 0.5,
  }));
  const picksIndex: MetadataRoute.Sitemap = [{
    url: `${BASE}/spectate/picks`,
    lastModified: now2,
    changeFrequency: "monthly",
    priority: 0.5,
  }];
  const pickUrls: MetadataRoute.Sitemap = monthlyPickMonths().map((m) => ({
    url: `${BASE}/spectate/picks/monthly/${m}`,
    lastModified: now2,
    changeFrequency: "yearly",
    priority: 0.4,
  }));
```

그리고 `return [...staticUrls, ...proUrls];`를 다음으로 교체:
```ts
  return [...staticUrls, ...proUrls, ...themeUrls, ...picksIndex, ...pickUrls];
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd web && npm test -- --run sitemap.test`
Expected: 3개 PASS (기존 2 + 신규 1).

- [ ] **Step 5: 회귀 + 빌드**

Run:
```bash
npm run lint
npm run type-check
npm run build 2>&1 | tail -5
```
Expected: 통과.

- [ ] **Step 6: 커밋**

```bash
git add web/app/sitemap.ts web/tests/sitemap.test.ts
git commit -m "feat(web): sitemap에 테마·픽 인덱스·월간 픽 URL 추가"
```

---

### Task 7: staging 검증 (검증 기준 4)

staging 스택에서 4가지 기준 실증. prod 무영향.

**Files:** 없음 (실행 검증).

- [ ] **Step 1: staging worktree를 3b 브랜치 tip으로 갱신**

```bash
cd /Users/daegong/projects/baduk
git -C .worktrees/staging fetch
git -C .worktrees/staging checkout --detach feat/agentic-ops-content-3b
```

- [ ] **Step 2: staging 의존성 갱신 + DB 동기화**

```bash
cd /Users/daegong/projects/baduk/.worktrees/staging/backend
source .venv311/bin/activate
pip install -e ".[dev]" -q
alembic upgrade head
cd /Users/daegong/projects/baduk
sqlite3 backend/data/baduk.db ".backup .worktrees/staging/backend/data/baduk-staging.db"
```
prod DB 스냅샷으로 staging이 911개 데이터 보유. (sub-project 1 spec의 "주기적 prod 스냅샷" 패턴.)

- [ ] **Step 3: staging 재기동**

```bash
ops/stack.sh down staging
sleep 3
ops/stack.sh up staging
sleep 60
ops/stack.sh ps staging
```
Expected: backend·web 정상.

- [ ] **Step 4: 검증 기준 #1 — 테마 카탈로그 + 페이지**

```bash
curl -fs http://localhost:8100/api/spectate/pro/themes | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'{len(d)}개 테마: {[t[\"slug\"] for t in d]}')"
for slug in masterpieces world-finals cwi honinbo castle-games 21st-century; do
  code=$(curl -fs -o /dev/null -w '%{http_code}' "http://localhost:3100/spectate/themes/$slug")
  echo "  $slug: HTTP $code"
done
```
Expected: ≥5 테마 보이고, 각 페이지 HTTP 200.

- [ ] **Step 5: 검증 기준 #2 — 월간 픽 결정성**

```bash
NOW_MM=$(date '+%Y-%m')
echo "현재 달: $NOW_MM"
A=$(curl -fs "http://localhost:8100/api/spectate/pro/pick/monthly/$NOW_MM" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id'))")
B=$(curl -fs "http://localhost:8100/api/spectate/pro/pick/monthly/$NOW_MM" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id'))")
echo "A=$A B=$B"
[ "$A" = "$B" ] && echo "결정적: 같은 입력 같은 결과" || echo "FAIL: 결정 안 됨"
curl -fs -o /dev/null -w "monthly 페이지 HTTP %{http_code}\n" "http://localhost:3100/spectate/picks/monthly/$NOW_MM"
curl -fs -o /dev/null -w "picks index HTTP %{http_code}\n" "http://localhost:3100/spectate/picks"
```
Expected: A=B(같은 id), 두 페이지 모두 200.

- [ ] **Step 6: 검증 기준 #3 — sitemap에 신규 URL 포함**

```bash
SITEMAP=$(curl -fs http://localhost:3100/sitemap.xml)
echo "프로 게임 URL: $(echo "$SITEMAP" | grep -c '/spectate/pro/')"
echo "테마 URL: $(echo "$SITEMAP" | grep -c '/spectate/themes/')"
echo "픽 URL: $(echo "$SITEMAP" | grep -c '/spectate/picks/monthly/')"
echo "픽 인덱스: $(echo "$SITEMAP" | grep -c 'spectate/picks<')"  # </loc> 직전 정확 매칭은 어렵지만 대략 확인
```
Expected: 프로 911+, 테마 5+, 픽 monthly 14, 픽 인덱스 1.

- [ ] **Step 7: 검증 기준 #4 — 페이지별 generateMetadata**

```bash
curl -fs "http://localhost:3100/spectate/themes/masterpieces" | grep -oE '<title>[^<]+</title>|<link rel="canonical" href="[^"]+"' | head -2
curl -fs "http://localhost:3100/spectate/picks/monthly/$NOW_MM" | grep -oE '<title>[^<]+</title>|<link rel="canonical" href="[^"]+"' | head -2
```
Expected: 두 페이지 모두 고유 title + canonical URL 보임.

- [ ] **Step 8: prod 무손상**

```bash
curl -fs http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs http://localhost:3000 >/dev/null && echo "prod-web OK"
```
Expected: 둘 다 OK.

- [ ] **Step 9: 커밋 없음** — 실행 검증.

---

### Task 8: 통합 검증 + 대시보드 갱신

검증 기준 4가지 일괄 재확인 + 대시보드·로그 갱신.

**Files:**
- Modify: `docs/ops/state/dashboard.md`
- Modify: `docs/ops/state/log/2026-05-23.md`

- [ ] **Step 1: 4가지 기준 일괄 확인**

Task 7 Step 4~7의 명령을 묶어 실행하고 출력 캡처.

- [ ] **Step 2: 대시보드 갱신**

`docs/ops/state/dashboard.md`의 `## 콘텐츠 인덱스` 표(3a에서 추가)에 행 보강 — Task 7 Step 6의 sitemap URL 수를 새 합계로 채운다:
```markdown
| 프로 기보 수 | 911 |
| 테마 수 | 6 |
| 월간 픽 URL | 14 |
| sitemap URL 수 | 936 (5 + 911 + 6 + 1 + 14) |
| 최근 CWI ingest | 2026-05-23 (fetched=0 new=0) |
```
실측값으로 채운다. 기존 표 구조 보존.

- [ ] **Step 3: 로그**

`docs/ops/state/log/2026-05-23.md`에 시간순 추가(기존 항목 보존):
```
## (현재시각) — 테마·이 달의 명국(sub-project 3b) 구축 완료
- 검증 기준 4/4 통과: ① 테마 카탈로그 + 페이지 ② 결정적 월간 픽 ③ sitemap 신규 URL ④ generateMetadata
- staging에서 검증 완료. prod 반영은 별도 deploy.md 절차.
```
`(현재시각)`은 `date '+%H:%M'`.

- [ ] **Step 4: 커밋**

```bash
git add docs/ops/state
git commit -m "feat(ops): 테마·이 달의 명국 구축 완료 — 검증 기준 4/4 통과"
```

- [ ] **Step 5: 최종 보고**

---

## 검증 기준 (spec)

1. 테마 5+ 정의 + 각 페이지 200 + 필터 결과 일치. → Task 1, 3, 7
2. 월간 픽 결정적(같은 입력 같은 결과). → Task 2, 4, 5, 7
3. sitemap에 911(프로) + 5+(테마) + 14(픽) + 1(픽 인덱스) URL. → Task 6, 7
4. 각 새 페이지 generateMetadata로 고유 title·canonical. → Task 3, 4, 7
