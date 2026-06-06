# CWI 주간 ingest 재귀 크롤 정상화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CWI 주간 ingest가 인덱스 하위 디렉터리를 재귀 크롤해 실제 `.sgf`를 찾아 적재하고, 적재분을 "최근(recent)" 관전 탭에 노출한다.

**Architecture:** `ingest_cwi_weekly.py`에 디렉터리 재귀 크롤(`crawl_sgf_links`, 깊이·페이지 상한 + visited-set)을 추가하고, `main_async`가 단일 페이지 스캔 대신 이를 사용한다. 회당 신규 적재 상한(`MAX_NEW_PER_RUN`)을 두되 상한으로 중단된 회차는 인덱스 md5를 저장하지 않아 다음 회차가 잔여분을 이어받는다. 관전 API는 `recent` 요청을 `recent`+`cwi` 컬렉션으로 매핑한다.

**Tech Stack:** Python 3.11 · httpx(`MockTransport`로 테스트) · SQLAlchemy 2 async · FastAPI · pytest. 백엔드 명령은 `backend/`에서 `source .venv311/bin/activate` 후, pytest는 `KATAGO_MOCK=true`. 스펙: `docs/superpowers/specs/2026-06-06-cwi-ingest-recursive-crawl-design.md`.

---

## 파일 구조

- Modify: `backend/scripts/ingest_cwi_weekly.py` — `extract_subdir_links`·`crawl_sgf_links` 추가, 상수 추가, `main_async` 교체
- Modify: `backend/app/api/spectate_pro.py` — `list_pro_games` 컬렉션 필터에서 `recent`→`(recent, cwi)`
- Test: `backend/tests/scripts/test_ingest_cwi_weekly.py` — 크롤·상한·게이트 테스트 추가
- Test: `backend/tests/api/test_spectate_pro.py` — recent 탭이 cwi 포함하는지

DB 스키마 변경 없음(마이그레이션 불필요).

---

## Task 1: extract_subdir_links — 하위 디렉터리 링크 추출

**Files:**
- Modify: `backend/scripts/ingest_cwi_weekly.py`
- Test: `backend/tests/scripts/test_ingest_cwi_weekly.py`

- [ ] **Step 1: 실패 테스트 추가** (`test_ingest_cwi_weekly.py`의 import에 `extract_subdir_links` 추가 후 함수 추가)

기존 import 블록을 다음으로 교체:
```python
from scripts.ingest_cwi_weekly import (
    extract_sgf_links,
    extract_subdir_links,
    is_cwi_url,
)
```
파일에 테스트 추가:
```python
def test_extract_subdir_links_returns_cwi_dirs_only():
    html = (
        '<html><body>'
        '<a href="games/Agon/">Agon</a>'          # 하위 디렉터리 (통과)
        '<a href="?C=N;O=A">sort</a>'             # Apache 정렬 링크 (제외)
        '<a href="/~aeb/go/">parent</a>'          # 상위(prefix 밖) (제외)
        '<a href="foo.sgf">file</a>'              # 디렉터리 아님 (제외)
        '<a href="https://evil.com/x/">evil</a>'  # 외부 (제외)
        '</body></html>'
    )
    base = "https://homepages.cwi.nl/~aeb/go/games/"
    dirs = extract_subdir_links(html, base)
    assert dirs == ["https://homepages.cwi.nl/~aeb/go/games/games/Agon/"]
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/scripts/test_ingest_cwi_weekly.py -k subdir -v`
Expected: FAIL — `ImportError: cannot import name 'extract_subdir_links'`

- [ ] **Step 3: 구현** — `ingest_cwi_weekly.py`의 `extract_sgf_links` 함수 바로 아래에 추가:

```python
def extract_subdir_links(html: str, base_url: str) -> list[str]:
    """HTML에서 하위 디렉터리(/ 로 끝나는) 링크를 절대 URL로 추출. CWI만 통과.
    Apache 정렬 링크(?…)·상위(prefix 밖)·외부 도메인은 제외한다."""
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    out: list[str] = []
    for href in hrefs:
        if not href.endswith("/"):
            continue
        if href.startswith("?") or href.startswith("../") or href == "./":
            continue
        absolute = urljoin(base_url, href)
        if is_cwi_url(absolute):
            out.append(absolute)
    return list(dict.fromkeys(out))
```
참고: `is_cwi_url`은 `parsed.path.startswith("/~aeb/go/games/")`만 검사하므로 디렉터리 URL(`…/games/Agon/`)도 그대로 통과한다. Apache 정렬 링크(`?C=…`)·상위 디렉터리(`/~aeb/go/` 등 prefix 밖)는 위 필터와 `is_cwi_url`로 자연히 제외된다.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/scripts/test_ingest_cwi_weekly.py -k subdir -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/scripts/ingest_cwi_weekly.py backend/tests/scripts/test_ingest_cwi_weekly.py
git commit -m "feat(ingest): CWI 하위 디렉터리 링크 추출 extract_subdir_links 추가"
```

---

## Task 2: crawl_sgf_links — 재귀 크롤

**Files:**
- Modify: `backend/scripts/ingest_cwi_weekly.py`
- Test: `backend/tests/scripts/test_ingest_cwi_weekly.py`

- [ ] **Step 1: 실패 테스트 추가** (파일 상단 import에 `import httpx`가 이미 있으면 재사용; 없으면 추가. 함수 import에 `crawl_sgf_links` 추가)

import 블록을 다음으로 교체:
```python
from scripts.ingest_cwi_weekly import (
    crawl_sgf_links,
    extract_sgf_links,
    extract_subdir_links,
    is_cwi_url,
)
```
파일 상단에 `import httpx` 추가(없을 때만). 테스트 추가:
```python
_BASE = "https://homepages.cwi.nl/~aeb/go/games/"


def _tree_handler() -> "callable":
    """index → sub1/ → deep/ 3계층, .sgf 2개. 순환 링크 포함."""
    pages = {
        _BASE: '<a href="games/sub1/">sub1</a><a href="top.sgf">t</a>',
        _BASE + "games/sub1/": (
            '<a href="deep/">deep</a><a href="a.sgf">a</a>'
            '<a href="../">up</a>'          # 상위 — visited/ prefix로 무해
        ),
        _BASE + "games/sub1/deep/": '<a href="b.sgf">b</a>',
    }
    def handler(request: "httpx.Request") -> "httpx.Response":
        url = str(request.url)
        if url in pages:
            return httpx.Response(200, text=pages[url])
        if url.endswith(".sgf"):
            return httpx.Response(200, text="(;FF[4]SZ[19];B[pd])")
        return httpx.Response(404)
    return handler


@pytest.mark.asyncio
async def test_crawl_finds_nested_sgfs():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_tree_handler())) as http:
        links = await crawl_sgf_links(http, _BASE, max_depth=4, max_pages=50)
    assert _BASE + "top.sgf" in links
    assert _BASE + "games/sub1/a.sgf" in links
    assert _BASE + "games/sub1/deep/b.sgf" in links


@pytest.mark.asyncio
async def test_crawl_respects_max_depth():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_tree_handler())) as http:
        links = await crawl_sgf_links(http, _BASE, max_depth=1, max_pages=50)
    # depth 1: index(0) → sub1(1) 까지만. deep/(2)은 미방문 → b.sgf 없음.
    assert _BASE + "games/sub1/a.sgf" in links
    assert _BASE + "games/sub1/deep/b.sgf" not in links


@pytest.mark.asyncio
async def test_crawl_respects_max_pages():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_tree_handler())) as http:
        links = await crawl_sgf_links(http, _BASE, max_depth=4, max_pages=1)
    # 페이지 1장(index)만 → top.sgf만, 하위는 미방문.
    assert links == [_BASE + "top.sgf"]
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/scripts/test_ingest_cwi_weekly.py -k crawl -v`
Expected: FAIL — `ImportError: cannot import name 'crawl_sgf_links'`

- [ ] **Step 3: 구현** — `extract_subdir_links` 아래에 추가:

```python
async def crawl_sgf_links(
    http: httpx.AsyncClient,
    start_url: str,
    *,
    max_depth: int,
    max_pages: int,
) -> list[str]:
    """start_url에서 CWI 하위 디렉터리를 BFS로 따라가 .sgf 절대 URL을 수집한다.
    visited-set으로 순환 방지, max_depth/max_pages로 폭주 방지."""
    queue: list[tuple[str, int]] = [(start_url, 0)]
    visited: set[str] = set()
    found: list[str] = []
    pages = 0
    while queue and pages < max_pages:
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            resp = await http.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:  # noqa: BLE001 — 디렉터리 1장 실패는 건너뛰고 계속
            log.warning("cwi.dir.fetch_failed", url=url, err=str(exc))
            continue
        pages += 1
        for sgf in extract_sgf_links(html, url):
            if sgf not in found:
                found.append(sgf)
        if depth < max_depth:
            for sub in extract_subdir_links(html, url):
                if sub not in visited:
                    queue.append((sub, depth + 1))
    return found
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/scripts/test_ingest_cwi_weekly.py -k crawl -v`
Expected: PASS (3건)

- [ ] **Step 5: 커밋**

```bash
git add backend/scripts/ingest_cwi_weekly.py backend/tests/scripts/test_ingest_cwi_weekly.py
git commit -m "feat(ingest): 디렉터리 재귀 크롤 crawl_sgf_links 추가 (깊이·페이지 상한)"
```

---

## Task 3: main_async — 크롤 사용 + 적재 상한 + capped 시 해시 미저장

**Files:**
- Modify: `backend/scripts/ingest_cwi_weekly.py`
- Test: `backend/tests/scripts/test_ingest_cwi_weekly.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
@pytest.mark.asyncio
async def test_main_async_caps_new_and_skips_hash(tmp_path, monkeypatch):
    """신규가 상한을 넘으면 cap에서 멈추고, capped 회차는 인덱스 해시를 저장하지 않는다."""
    import scripts.ingest_cwi_weekly as mod
    monkeypatch.setattr(mod, "CACHE_PATH", tmp_path / ".baduk" / "ingest-cwi.cache")
    monkeypatch.setattr(mod, "MAX_NEW_PER_RUN", 2)

    base = "https://homepages.cwi.nl/~aeb/go/games/"
    # 서로 다른 본문 4개(서로 다른 content_hash) — 신규 4 후보
    index_html = "".join(f'<a href="g{i}.sgf">g{i}</a>' for i in range(4))

    def handler(request):
        url = str(request.url)
        if url == base:
            return httpx.Response(200, text=index_html)
        if url.endswith(".sgf"):
            n = url.rstrip(".sgf")[-1]
            body = f"(;FF[4]GM[1]SZ[19]EV[E{n}];B[pd];W[dc])"
            return httpx.Response(200, text=body)
        return httpx.Response(404)

    real_client = httpx.AsyncClient
    def patched_client(*args, **kwargs):
        kwargs.pop("timeout", None)
        kwargs.pop("follow_redirects", None)
        return real_client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    from sqlalchemy.ext.asyncio import (
        AsyncSession, async_sessionmaker, create_async_engine,
    )
    import app.models  # noqa: F401
    from app.db import Base
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(
        mod, "AsyncSessionLocal",
        async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession),
    )

    summary = await mod.main_async()
    assert summary["new"] == 2                 # 상한에서 멈춤
    assert mod.CACHE_PATH.exists() is False     # capped → 해시 미저장
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/scripts/test_ingest_cwi_weekly.py -k caps -v`
Expected: FAIL (현재 `MAX_NEW_PER_RUN` 미존재 → AttributeError; 또는 상한 없이 4건 적재)

- [ ] **Step 3: 구현** — 두 부분 수정.

(a) 상수 — `CACHE_PATH = ...` 줄 아래에 추가:
```python
MAX_DEPTH = 4
MAX_PAGES = 500
MAX_NEW_PER_RUN = 200
```

(b) `main_async` 본문에서 `links = extract_sgf_links(html, CWI_INDEX_URL)` 줄을 다음으로 교체:
```python
        links = await crawl_sgf_links(
            http, CWI_INDEX_URL, max_depth=MAX_DEPTH, max_pages=MAX_PAGES
        )
        capped = False
```
그리고 적재 루프에서 `db.add(pro)` / `summary["new"] += 1` 직후에 상한 검사를 넣는다. 기존:
```python
                db.add(pro)
                summary["new"] += 1

            await db.commit()
```
교체:
```python
                db.add(pro)
                summary["new"] += 1
                if summary["new"] >= MAX_NEW_PER_RUN:
                    capped = True
                    log.info("cwi.ingest.capped", cap=MAX_NEW_PER_RUN)
                    break

            await db.commit()
```
마지막으로 `save_index_hash(html)` 줄을 조건부로:
```python
    if not capped:
        save_index_hash(html)
    log.info("cwi.ingest.complete", **summary)
    return summary
```

- [ ] **Step 4: 통과 확인 (신규 + 회귀)**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/scripts/test_ingest_cwi_weekly.py -v`
Expected: 신규 cap 테스트 PASS + 기존 `test_main_async_ingests_new_sgfs`(flat 인덱스 2 sgf)도 여전히 PASS — crawl_sgf_links가 시작 페이지의 .sgf를 그대로 수집하므로 `fetched==2` 유지.

- [ ] **Step 5: 커밋**

```bash
git add backend/scripts/ingest_cwi_weekly.py backend/tests/scripts/test_ingest_cwi_weekly.py
git commit -m "feat(ingest): main_async 재귀 크롤 사용 + 회당 적재 상한(capped 시 해시 미저장)"
```

---

## Task 4: 관전 API — recent 탭에 cwi 포함

**Files:**
- Modify: `backend/app/api/spectate_pro.py`
- Test: `backend/tests/api/test_spectate_pro.py`

- [ ] **Step 1: 실패 테스트 추가** (`test_spectate_pro.py` — 기존 `_insert_pro_game(db_session, collection=...)` 헬퍼 사용)

```python
@pytest.mark.asyncio
async def test_recent_tab_includes_cwi(client: AsyncClient, db_session) -> None:
    # recent 탭은 'recent'와 'cwi' 컬렉션을 함께 보여주고 masterpiece/world는 제외한다.
    cwi_id = await _insert_pro_game(db_session, collection="cwi")
    mp_id = await _insert_pro_game(db_session, collection="masterpiece")
    r = await client.get("/api/spectate/pro?collection=recent")
    assert r.status_code == 200
    ids = {row["id"] for row in r.json()["rows"]}
    assert cwi_id in ids
    assert mp_id not in ids
```
주의: `_insert_pro_game`은 동일 `_SGF`로 같은 content_hash를 만들어 두 번째 insert가 UNIQUE 충돌할 수 있다. 충돌 시, 두 행의 content_hash가 달라지도록 헬퍼를 보지 말고 이 테스트에서 직접 삽입한다:
```python
@pytest.mark.asyncio
async def test_recent_tab_includes_cwi(client: AsyncClient, db_session) -> None:
    from app.core.sgf.import_sgf import parse_pro_sgf
    from app.models import ProGame
    cwi = ProGame.from_parsed(
        parse_pro_sgf("(;GM[1]FF[4]SZ[19]KM[6.5]EV[CWI A];B[pd];W[dp])"),
        collection="cwi",
    )
    mp = ProGame.from_parsed(
        parse_pro_sgf("(;GM[1]FF[4]SZ[19]KM[6.5]EV[MP B];B[pd];W[dq])"),
        collection="masterpiece",
    )
    db_session.add_all([cwi, mp])
    await db_session.commit()
    await db_session.refresh(cwi)
    await db_session.refresh(mp)
    r = await client.get("/api/spectate/pro?collection=recent")
    assert r.status_code == 200
    ids = {row["id"] for row in r.json()["rows"]}
    assert cwi.id in ids
    assert mp.id not in ids
```
(위 두 SGF는 마지막 수가 달라 content_hash가 달라 UNIQUE 충돌 없음.)

- [ ] **Step 2: 실패 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/api/test_spectate_pro.py -k recent_tab -v`
Expected: FAIL — cwi 행이 recent 결과에 없어 `cwi.id in ids` 단언 실패.

- [ ] **Step 3: 구현** — `spectate_pro.py`의 `list_pro_games` 안, 현재:
```python
    filters = []
    if collection in ("masterpiece", "recent", "world"):
        filters.append(ProGame.collection == collection)
```
교체:
```python
    filters = []
    if collection == "recent":
        filters.append(ProGame.collection.in_(("recent", "cwi")))
    elif collection in ("masterpiece", "world"):
        filters.append(ProGame.collection == collection)
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest tests/api/test_spectate_pro.py -v`
Expected: 신규 PASS + 기존 전부 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/spectate_pro.py backend/tests/api/test_spectate_pro.py
git commit -m "feat(spectate): recent 탭이 cwi 적재분을 포함하도록 필터 매핑"
```

---

## Task 5: 전체 검증

- [ ] **Step 1: 백엔드 전체**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m pytest -q && ruff check . && mypy app`
Expected: 전부 PASS / 클린. (ingest 스크립트는 `app` 밖이라 mypy 대상 아님 — ruff는 `.`로 스크립트 포함 검사되므로 ruff 클린 필수.)

- [ ] **Step 2: 동작 무변동 확인 (게이트 dormant)**

Run: `cd backend && source .venv311/bin/activate && KATAGO_MOCK=true python -m scripts.ingest_cwi_weekly`
Expected: `cwi.index.unchanged` / `fetched=0 new=0 …` — 실제 prod DB 인덱스 캐시가 현재와 동일하므로 무변동(대량 유입 0). pro_games 수 불변.

---

## Self-Review 메모

- **Spec 커버리지**: extract_subdir_links(T1)·crawl_sgf_links 재귀+상한(T2)·main_async 크롤/적재상한/capped-해시미저장(T3)·recent→cwi 필터(T4)·검증(T5) — 스펙 전 항목 매핑.
- **capped 시 해시 미저장** 규칙(스펙 핵심 안전): T3에서 `if not capped: save_index_hash` + 테스트 `CACHE_PATH.exists() is False`로 검증.
- **회귀**: T3가 기존 `test_main_async_ingests_new_sgfs`(flat 인덱스)를 유지 — crawl이 시작 페이지 .sgf를 그대로 수집.
- **타입 일관성**: `crawl_sgf_links(http, start_url, *, max_depth, max_pages) -> list[str]` 시그니처가 T2 정의·T3 호출에서 동일. 상수 `MAX_DEPTH/MAX_PAGES/MAX_NEW_PER_RUN`가 T3에서 정의·사용.
- **화이트리스트**: 모든 fetch 대상은 `is_cwi_url` 통과분(extract_sgf_links·extract_subdir_links 둘 다 적용) — 라이선스 정책 유지.
- **No placeholders**: Task 1 Step 3에 "정정" 안내가 있으나 최종형 코드(단순 `if is_cwi_url(absolute):`)를 명시함.
