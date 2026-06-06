# 프로 목록 최근성 재분류·정렬·조회수 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** "최근" 탭을 최근 1년 대국일 기보로 한정하고(1년 경과/날짜없음은 명국·세계기전으로 동적 분류), 목록에 최근순(기본)·오래된순·인기순(조회수) 정렬을 추가한다.

**Architecture:** `collection`을 안정적 base 분류(masterpiece/world)로만 쓰고, "최근"은 질의 시점 `game_date >= 오늘-365일` 필터로 동적 처리한다. event 키워드로 base를 라우팅하는 헬퍼를 ingest·마이그레이션이 공유한다. `view_count` 컬럼을 추가해 상세 조회 시 +1, 인기순 정렬을 제공한다.

**Tech Stack:** FastAPI · SQLAlchemy 2 async · Alembic · pytest / Next.js 14 · TS · Vitest. 백엔드: `backend/`에서 `source .venv311/bin/activate`, pytest는 `KATAGO_MOCK=true`. 프론트: `web/`. 스펙: `docs/superpowers/specs/2026-06-06-pro-list-recency-sort-views-design.md`. 신규 `.ts`/`.py`는 첫 줄 한국어 헤더 주석.

---

## 파일 구조
- Create: `backend/app/core/pro/classify.py` — `classify_collection(event)`
- Create: `backend/migrations/versions/0015_pro_view_count.py` — view_count 추가 + cwi 재분류
- Modify: `backend/app/models/pro_game.py` — `view_count`
- Modify: `backend/scripts/ingest_cwi_weekly.py` — collection을 classify로
- Modify: `backend/app/api/spectate_pro.py` — 탭 필터 재정의 + sort + view_count(행/증가)
- Modify: `web/components/ProGameList.tsx` — 정렬 드롭다운
- Modify: `web/lib/i18n/ko.json`·`en.json` — 정렬 라벨
- Test: `backend/tests/core/pro/test_classify.py`(신규), `backend/tests/api/test_spectate_pro.py`(확장)

---

## Task 1: classify_collection 헬퍼

**Files:** Create `backend/app/core/pro/classify.py`; Test `backend/tests/core/pro/test_classify.py`

- [ ] **Step 1: 실패 테스트** — `backend/tests/core/pro/test_classify.py`:

```python
# classify_collection 단위 테스트.
from app.core.pro.classify import classify_collection


def test_world_events():
    assert classify_collection("10th Chunlan Cup Final") == "world"
    assert classify_collection("30th LG Cup Final") == "world"
    assert classify_collection("Samsung Cup") == "world"


def test_masterpiece_default():
    assert classify_collection("32nd Agon-Kiriyama Cup") == "masterpiece"
    assert classify_collection("Castle Game") == "masterpiece"
    assert classify_collection(None) == "masterpiece"
```
(`backend/tests/core/pro/__init__.py`가 없으면 빈 파일로 생성.)

- [ ] **Step 2: 실패 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/core/pro/test_classify.py -v`
Expected: FAIL — ModuleNotFoundError.

- [ ] **Step 3: 구현** — `backend/app/core/pro/classify.py`:

```python
# 프로 기보 event 문자열로 base 컬렉션(world/masterpiece)을 판정한다.
from __future__ import annotations

# 국제기전 키워드(소문자). 포함되면 'world', 아니면 'masterpiece'.
WORLD_EVENT_KEYS = ("chunlan", "fujitsu", "ing cup", "lg cup", "samsung", "toyota")


def classify_collection(event: str | None) -> str:
    if not event:
        return "masterpiece"
    low = event.lower()
    return "world" if any(k in low for k in WORLD_EVENT_KEYS) else "masterpiece"
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/core/pro/test_classify.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/core/pro/classify.py backend/tests/core/pro/
git commit -m "feat(pro): event→base 컬렉션 분류 헬퍼 classify_collection"
```

---

## Task 2: 마이그레이션 0015 — view_count + cwi 재분류 + 모델

**Files:** Create `backend/migrations/versions/0015_pro_view_count.py`; Modify `backend/app/models/pro_game.py`

- [ ] **Step 1: 마이그레이션 작성** — `backend/migrations/versions/0015_pro_view_count.py`:

```python
# pro_games에 view_count 추가 + 기존 cwi/recent 행을 base(world/masterpiece)로 재분류
"""Add view_count and reclassify cwi/recent rows into base collections.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-06

view_count(인기순 정렬용)을 추가하고, ingest가 'cwi'로 적재했던 행을 event 기준
국제기전→'world', 그 외→'masterpiece'로 재분류한다. 재분류는 비가역이라 downgrade는
view_count 컬럼만 제거한다.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pro_games",
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        "UPDATE pro_games SET collection='world' "
        "WHERE collection IN ('cwi','recent') AND ("
        "lower(event) LIKE '%chunlan%' OR lower(event) LIKE '%fujitsu%' "
        "OR lower(event) LIKE '%ing cup%' OR lower(event) LIKE '%lg cup%' "
        "OR lower(event) LIKE '%samsung%' OR lower(event) LIKE '%toyota%')"
    )
    op.execute(
        "UPDATE pro_games SET collection='masterpiece' "
        "WHERE collection IN ('cwi','recent')"
    )


def downgrade() -> None:
    op.drop_column("pro_games", "view_count")
```

- [ ] **Step 2: 모델에 컬럼 추가** — `backend/app/models/pro_game.py`, `move_count` 컬럼 다음 줄에:

```python
    move_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 인기순 정렬용 조회수 — 상세 열람 시 +1.
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
```

- [ ] **Step 3: 임포트/기존 테스트 스모크** (마이그레이션을 실제 DB에 적용하지 말 것 — 배포 단계. 테스트는 conftest가 테이블을 생성)

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/api/test_spectate_pro.py -q`
Expected: PASS (새 컬럼으로 기존 테스트 깨지지 않음)

- [ ] **Step 4: 커밋**

```bash
git add backend/migrations/versions/0015_pro_view_count.py backend/app/models/pro_game.py
git commit -m "feat(pro): view_count 컬럼 + cwi 행 base 재분류 마이그레이션 0015"
```

---

## Task 3: ingest가 base로 분류

**Files:** Modify `backend/scripts/ingest_cwi_weekly.py`

- [ ] **Step 1: 구현** — import에 추가:
```python
from app.core.pro.classify import classify_collection
```
`_build_pro_game`의 `from_parsed(..., collection="cwi", ...)`를 다음으로:
```python
        return ProGame.from_parsed(
            parsed,
            collection=classify_collection(parsed.event),
            source_note=CWI_INDEX_URL,
        )
```

- [ ] **Step 2: 컴파일/기존 ingest 테스트**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/scripts/test_ingest_cwi_weekly.py -q`
Expected: PASS. (기존 ingest 테스트는 collection 값을 단언하지 않으므로 영향 없음. 만약 'cwi' 단언이 있으면 base 값으로 갱신.)

- [ ] **Step 3: 커밋**

```bash
git add backend/scripts/ingest_cwi_weekly.py
git commit -m "feat(ingest): CWI 적재 시 event 기준 base 컬렉션으로 분류"
```

---

## Task 4: API 탭 필터 재정의 + 정렬 + view_count 노출

**Files:** Modify `backend/app/api/spectate_pro.py`; Test `backend/tests/api/test_spectate_pro.py`

- [ ] **Step 1: 실패 테스트 추가** — `backend/tests/api/test_spectate_pro.py`. 파일 상단에 `from datetime import date, timedelta` 추가(없으면). 헬퍼 `_insert_pro_game`은 기존 것 사용하되, 날짜/컬렉션/조회수를 직접 넣는 헬퍼를 추가:

```python
from datetime import date, timedelta
from app.models import ProGame
from app.core.sgf.import_sgf import parse_pro_sgf


async def _add(db_session, *, collection, game_date, event="E", views=0, suffix="pd"):
    g = ProGame.from_parsed(
        parse_pro_sgf(f"(;GM[1]FF[4]SZ[19]KM[6.5]EV[{event}];B[{suffix}];W[dp])"),
        collection=collection,
    )
    g.game_date = game_date
    g.view_count = views
    db_session.add(g)
    await db_session.commit()
    await db_session.refresh(g)
    return g.id


@pytest.mark.asyncio
async def test_recent_tab_only_within_one_year(client, db_session):
    recent_id = await _add(db_session, collection="masterpiece",
                           game_date=date.today() - timedelta(days=30), suffix="pd")
    old_id = await _add(db_session, collection="masterpiece",
                        game_date=date.today() - timedelta(days=400), suffix="pp")
    null_id = await _add(db_session, collection="world",
                         game_date=None, suffix="dd")
    r = await client.get("/api/spectate/pro?collection=recent")
    ids = {row["id"] for row in r.json()["rows"]}
    assert recent_id in ids
    assert old_id not in ids and null_id not in ids


@pytest.mark.asyncio
async def test_masterpiece_tab_excludes_recent_includes_null(client, db_session):
    recent_id = await _add(db_session, collection="masterpiece",
                           game_date=date.today() - timedelta(days=30), suffix="pd")
    old_id = await _add(db_session, collection="masterpiece",
                        game_date=date.today() - timedelta(days=400), suffix="pp")
    null_id = await _add(db_session, collection="masterpiece",
                         game_date=None, suffix="dd")
    r = await client.get("/api/spectate/pro?collection=masterpiece")
    ids = {row["id"] for row in r.json()["rows"]}
    assert old_id in ids and null_id in ids
    assert recent_id not in ids


@pytest.mark.asyncio
async def test_sort_popular(client, db_session):
    low = await _add(db_session, collection="masterpiece",
                     game_date=date.today() - timedelta(days=400), views=1, suffix="pd")
    high = await _add(db_session, collection="masterpiece",
                      game_date=date.today() - timedelta(days=400), views=99, suffix="pp")
    r = await client.get("/api/spectate/pro?collection=masterpiece&sort=popular")
    ids = [row["id"] for row in r.json()["rows"]]
    assert ids.index(high) < ids.index(low)


@pytest.mark.asyncio
async def test_detail_increments_view_count(client, db_session):
    gid = await _add(db_session, collection="masterpiece",
                     game_date=date.today() - timedelta(days=400), views=5, suffix="pd")
    r1 = await client.get(f"/api/spectate/pro/{gid}")
    assert r1.json()["view_count"] == 6
    r2 = await client.get(f"/api/spectate/pro/{gid}")
    assert r2.json()["view_count"] == 7
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/api/test_spectate_pro.py -k "recent_tab or masterpiece_tab or sort_popular or increments" -v`
Expected: FAIL (recent 탭이 컬렉션 in_(recent,cwi)라 날짜 무관, view_count 키 없음 등).

- [ ] **Step 3: 구현** — `backend/app/api/spectate_pro.py`.

(a) 상단 import에 `from datetime import date, timedelta` 추가(기존 `from datetime import date`가 있으면 `timedelta`만 합치기). `from sqlalchemy import func, or_, select`에 변화 없음.

(b) `ProGameRow`에 필드 추가(`move_count` 다음):
```python
    move_count: int
    view_count: int
```

(c) `list_pro_games` 시그니처에 `sort` 추가:
```python
async def list_pro_games(
    db: DbSession,
    collection: str | None = Query(None),
    q: str | None = Query(None),
    sort: str = Query("recent"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ProGameList:
```

(d) 필터 블록 교체(현재 `if collection == "recent": … elif …` 부분):
```python
    cutoff = date.today() - timedelta(days=365)
    filters: list[ColumnElement[bool]] = []
    if collection == "recent":
        filters.append(ProGame.game_date >= cutoff)
    elif collection in ("masterpiece", "world"):
        filters.append(ProGame.collection == collection)
        filters.append(
            or_(ProGame.game_date < cutoff, ProGame.game_date.is_(None))
        )
```

(e) 정렬 — `stmt`의 `.order_by(...)`를 sort 분기로 교체:
```python
    if sort == "oldest":
        order = (ProGame.game_date.asc().nullslast(), ProGame.id.asc())
    elif sort == "popular":
        order = (
            ProGame.view_count.desc(),
            ProGame.game_date.desc().nullslast(),
            ProGame.id.desc(),
        )
    else:  # recent (기본 · 알 수 없는 값 폴백)
        order = (ProGame.game_date.desc().nullslast(), ProGame.id.desc())
    stmt = (
        select(ProGame)
        .where(*filters)
        .order_by(*order)
        .limit(limit)
        .offset(offset)
    )
```

(f) `get_pro_game`에서 조회수 증가 — `game`을 가져온 직후(404 체크 후)에:
```python
    game.view_count += 1
    await db.commit()
    await db.refresh(game)
```
그다음 기존 `ProGameRow.model_validate(game, ...)` / `ProGameDetail(...)` 로직 유지(증가된 view_count가 반영됨).

- [ ] **Step 4: 통과 확인 (신규 + 기존)**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/api/test_spectate_pro.py -v`
Expected: 신규 4건 PASS + 기존 전부 PASS. (기존 `test_recent_tab_includes_cwi`가 있으면 이 모델로 의미가 바뀌므로, cwi 컬렉션을 직접 넣던 그 테스트는 **삭제 또는 갱신**한다 — 이제 cwi 컬렉션은 없고 recent는 날짜 기준. 해당 테스트를 새 모델에 맞게 갱신하거나 제거할 것.)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/spectate_pro.py backend/tests/api/test_spectate_pro.py
git commit -m "feat(spectate): 탭을 동적 최근성으로 재정의 + 정렬(최근/오래된/인기) + view_count"
```

---

## Task 5: 프론트 정렬 드롭다운

**Files:** Modify `web/components/ProGameList.tsx`, `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

- [ ] **Step 1: i18n 라벨 추가** — `spectate` 객체에 추가.

ko.json:
```json
    "sortLabel": "정렬",
    "sortRecent": "최근순",
    "sortOldest": "오래된순",
    "sortPopular": "인기순",
```
en.json:
```json
    "sortLabel": "Sort",
    "sortRecent": "Newest",
    "sortOldest": "Oldest",
    "sortPopular": "Popular",
```
JSON 유효성: `cd web && node -e "require('./lib/i18n/ko.json');require('./lib/i18n/en.json');console.log('ok')"`.

- [ ] **Step 2: ProGameList에 정렬 상태·Select·요청 파라미터**

import 추가:
```typescript
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";
```
`interface ProRow`에 추가:
```typescript
  move_count: number;
  view_count: number;
```
상태 추가(`const [q, setQ] = useState("");` 부근):
```typescript
  const [sort, setSort] = useState<"recent" | "oldest" | "popular">("recent");
```
데이터 요청 `useEffect`의 `params`에 sort 추가, 의존성에 sort 추가:
```typescript
    const params = new URLSearchParams({
      collection,
      sort,
      limit: String(PAGE_SIZE),
      offset: String(page * PAGE_SIZE),
    });
```
그리고 그 useEffect 의존성 배열을 `[collection, page, debouncedQ, sort, router]`로.

탭 변경/검색처럼 sort 변경 시 첫 페이지로 가도록, Select onValueChange에서 처리(아래 UI).

검색 Input 옆(같은 flex 행)에 Select 추가:
```tsx
        <Select
          value={sort}
          onValueChange={(v) => {
            setSort(v as "recent" | "oldest" | "popular");
            setPage(0);
          }}
        >
          <SelectTrigger aria-label={t("spectate.sortLabel")} className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="recent">{t("spectate.sortRecent")}</SelectItem>
            <SelectItem value="oldest">{t("spectate.sortOldest")}</SelectItem>
            <SelectItem value="popular">{t("spectate.sortPopular")}</SelectItem>
          </SelectContent>
        </Select>
```
(`SelectValue`가 현재 선택 라벨을 표시. 기본 recent.)

- [ ] **Step 3: 타입체크·린트**

Run: `cd web && npm run type-check && npm run lint`
Expected: 통과.

- [ ] **Step 4: 커밋**

```bash
git add web/components/ProGameList.tsx web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(spectate): 목록 정렬 드롭다운(최근/오래된/인기) 추가"
```

---

## Task 6: 전체 검증

- [ ] **Step 1: 백엔드 전체**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest -q && ruff check . && mypy app`
Expected: 전부 PASS / 클린.

- [ ] **Step 2: 프론트 전체**

Run: `cd web && npm run test -- --run && npm run type-check && npm run lint`
Expected: 전부 PASS.

---

## Self-Review 메모

- **Spec 커버리지**: classify(T1)·view_count+재분류 마이그(T2)·ingest base(T3)·탭필터+정렬+조회수(T4)·정렬 UI(T5)·검증(T6) — 스펙 전 항목 매핑.
- **직전 recent→cwi 테스트 충돌**: T4 Step4에 기존 `test_recent_tab_includes_cwi` 갱신/제거 명시.
- **타입 일관성**: `classify_collection(event)->str`(T1)이 T2 마이그 SQL·T3 ingest와 동일 규칙. `sort` 값 `recent|oldest|popular`가 T4(백)·T5(프론트) 동일. `view_count`가 모델·스키마·행타입 일관.
- **동적 cutoff**: `date.today()-365d` — 테스트는 상대 날짜로 삽입해 안정.
- **No placeholders**: 모든 코드 블록 완비.
- **배포**: 머지 후 prod 백업 → `alembic upgrade head`(재분류 포함) → api·web 재빌드/재시작.
