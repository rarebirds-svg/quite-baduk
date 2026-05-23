# Agentic Ops 콘텐츠 수집·SEO 인덱스 (하위 프로젝트 3a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** inkbaduk의 프로기보 자동 수집(CWI 주1회) + 911개 프로 페이지의 검색 노출(동적 sitemap + per-page 메타)을 구축한다.

**Architecture:** ingest는 결정적 Python 스크립트 + 일요일 03:00 launchd. sitemap·메타는 Next.js 동적 라우트로 backend의 새 가벼운 `/api/spectate/pro/sitemap` endpoint를 호출 — ingest 후 최대 1시간(`revalidate`) 내 검색엔진 노출. CWI 외 도메인 fetch는 스크립트 도메인 화이트리스트가 차단.

**Tech Stack:** Python (httpx async + sqlalchemy async), pytest+respx HTTP mock, macOS launchd, FastAPI, Next.js 14 App Router (sitemap·generateMetadata), Vitest.

**브랜치:** 모든 작업은 `feat/agentic-ops-content-3a`에서 수행한다(spec 커밋 `798e9eb`가 이미 올라가 있음).

**전제:** sub-project 0~2가 머지된 상태(local `feat/agentic-ops-sre` tip). prod는 launchd `com.baduk.api`(:8000)·`com.baduk.web`(:3000)로 가동 중. staging worktree(`.worktrees/staging`)는 :3100/:8100 가용. `pro_games` 테이블에 911개 적재. backend venv는 prod와 staging 각각 독립.

**경로 상수:** 리포 루트 `/Users/daegong/projects/baduk`. `claude` CLI `/opt/homebrew/bin/claude`.

**주의 — 앱 코드 수정**: sub-project 0~2와 달리 3a는 backend(`app/api/spectate_pro.py`) + web(`app/sitemap.ts`, `app/spectate/pro/[id]/page.tsx`)를 수정한다. 검증은 staging worktree(:3100/:8100)에서 한다 — prod 무영향. 머지·prod 반영은 `deploy.md` 러닝북 따라 별도 단계.

---

### Task 1: backend `/api/spectate/pro/sitemap` endpoint

sitemap.ts가 호출할 경량 endpoint — 모든 pro_games의 `id`와 `updated_at`만 반환. 페이지네이션·세부 필드 없이 한 번에.

**Files:**
- Modify: `backend/app/api/spectate_pro.py`
- Test: `backend/tests/api/test_spectate_pro.py`

- [ ] **Step 1: 기존 endpoint 구조 확인**

Run: `grep -nE 'router|@router' backend/app/api/spectate_pro.py | head -10`
파일 첫 줄에 `from __future__ import annotations`과 `router = APIRouter(...)` 가 있는지 확인. 새 endpoint는 같은 라우터에 추가한다.

- [ ] **Step 2: 실패 테스트 작성**

`backend/tests/api/test_spectate_pro.py` 끝에 추가:
```python
async def test_sitemap_endpoint_returns_all_pro_games(client, seed_three_pro_games):
    # seed_three_pro_games fixture: 3개의 pro_games를 적재한다 (기존 fixture 재사용).
    resp = await client.get("/api/spectate/pro/sitemap")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    item = data[0]
    assert "id" in item
    assert "updated_at" in item
    assert set(item.keys()) == {"id", "updated_at"}  # 다른 필드 누설 안 됨
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_spectate_pro.py::test_sitemap_endpoint_returns_all_pro_games -v`
Expected: FAIL with 404 (route absent).

만약 `seed_three_pro_games` fixture가 없으면 — 기존 테스트에서 사용되는 fixture명을 찾아 그것을 쓰거나, 인라인으로 직접 `pro_games`에 3건 insert 후 endpoint 호출 + cleanup. 그 경우 테스트 코드를 적절히 수정한다.

- [ ] **Step 4: endpoint 구현 (최소)**

`backend/app/api/spectate_pro.py`에 추가 (적절한 위치에 — 기존 라우트 정의들 끝):
```python
@router.get("/api/spectate/pro/sitemap")
async def pro_sitemap(db: DbSession) -> list[dict[str, Any]]:
    """SEO sitemap용 경량 엔드포인트 — 전체 pro_games의 id·updated_at만 반환한다."""
    result = await db.execute(
        select(ProGame.id, ProGame.updated_at).order_by(ProGame.id)
    )
    return [
        {"id": row.id, "updated_at": row.updated_at.isoformat()}
        for row in result.all()
    ]
```

필요한 import가 모듈 최상단에 없으면 추가: `from typing import Any`, `from sqlalchemy import select`, `from app.models import ProGame`, `from app.deps import DbSession`. 기존 import에 이미 있으면 추가하지 않는다.

`ProGame` 모델에 `updated_at` 필드가 없으면 `created_at`을 쓴다. 둘 다 없으면 `id` 단독으로(`updated_at`을 dynamic하게 `datetime.now()` 사용). 코드는 모델 확인 후 결정한다 — `head -50 backend/app/models/pro_game.py`로 확인.

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/api/test_spectate_pro.py::test_sitemap_endpoint_returns_all_pro_games -v`
Expected: PASS.

- [ ] **Step 6: 회귀 확인**

Run: `pytest tests/api/test_spectate_pro.py -q`
Expected: 기존 테스트 전부 PASS.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/api/spectate_pro.py backend/tests/api/test_spectate_pro.py
git commit -m "feat(api): /api/spectate/pro/sitemap — SEO sitemap용 경량 endpoint"
```

---

### Task 2: `backend/scripts/ingest_cwi_weekly.py` 자동 수집 스크립트

CWI 인덱스를 주1회 확인하고 신규 SGF를 자동 ingest. 결정적 Python.

**Files:**
- Create: `backend/scripts/ingest_cwi_weekly.py`
- Create: `backend/tests/scripts/test_ingest_cwi_weekly.py`

- [ ] **Step 1: 도메인 가드 + URL 파싱 실패 테스트**

`backend/tests/scripts/test_ingest_cwi_weekly.py`:
```python
# CWI 자동 수집 스크립트의 단위 테스트.
import pytest
from scripts.ingest_cwi_weekly import (
    is_cwi_url,
    extract_sgf_links,
)


def test_is_cwi_url_allows_cwi():
    assert is_cwi_url("https://homepages.cwi.nl/~aeb/go/games/foo.sgf") is True
    assert is_cwi_url("http://homepages.cwi.nl/~aeb/go/games/sub/bar.sgf") is True


def test_is_cwi_url_rejects_others():
    assert is_cwi_url("https://gokifu.com/foo.sgf") is False
    assert is_cwi_url("https://example.com/foo.sgf") is False
    assert is_cwi_url("https://homepages.cwi.nl/other/path.sgf") is False
    assert is_cwi_url("file:///etc/passwd") is False


def test_extract_sgf_links_returns_absolute_cwi_urls():
    html = (
        '<html><body>'
        '<a href="games/foo.sgf">foo</a>'
        '<a href="bar.html">bar</a>'
        '<a href="baz.sgf">baz</a>'
        '<a href="https://evil.com/danger.sgf">danger</a>'
        '</body></html>'
    )
    base = "https://homepages.cwi.nl/~aeb/go/games/"
    links = extract_sgf_links(html, base)
    assert "https://homepages.cwi.nl/~aeb/go/games/games/foo.sgf" in links
    assert "https://homepages.cwi.nl/~aeb/go/games/baz.sgf" in links
    assert all(is_cwi_url(u) for u in links)
    assert "https://evil.com/danger.sgf" not in links
    assert not any(u.endswith(".html") for u in links)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && pytest tests/scripts/test_ingest_cwi_weekly.py -v`
Expected: FAIL (ModuleNotFoundError 또는 ImportError).

- [ ] **Step 3: 스크립트 최소 골격 작성 (도메인 가드 + 링크 추출)**

`backend/scripts/ingest_cwi_weekly.py`:
```python
# CWI 퍼블릭 도메인 컬렉션에서 신규 프로 SGF를 주1회 자동 ingest한다.
"""CWI 자동 수집 스크립트.

Usage (launchd가 호출):
    python -m scripts.ingest_cwi_weekly

소스: homepages.cwi.nl/~aeb/go/games/ 만 허용 (라이선스 정책).
캐시: ~/.baduk/ingest-cwi.cache 에 index 페이지 md5 저장.
중복: pro_games.content_hash로 차단.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from sqlalchemy import select

from app.core.sgf.import_sgf import InvalidProSgf, parse_pro_sgf
from app.db import AsyncSessionLocal
from app.models import ProGame

log = structlog.get_logger()

CWI_INDEX_URL = "https://homepages.cwi.nl/~aeb/go/games/"
ALLOWED_HOSTS = {"homepages.cwi.nl"}
ALLOWED_PATH_PREFIX = "/~aeb/go/games/"
CACHE_PATH = Path.home() / ".baduk" / "ingest-cwi.cache"


def is_cwi_url(url: str) -> bool:
    """CWI 컬렉션 도메인+경로 화이트리스트. 라이선스 정책 강제."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.hostname not in ALLOWED_HOSTS:
        return False
    if not parsed.path.startswith(ALLOWED_PATH_PREFIX):
        return False
    return True


def extract_sgf_links(html: str, base_url: str) -> list[str]:
    """HTML에서 .sgf 링크를 절대 URL로 추출. CWI 도메인만 통과."""
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    out: list[str] = []
    for href in hrefs:
        if not href.lower().endswith(".sgf"):
            continue
        absolute = urljoin(base_url, href)
        if is_cwi_url(absolute):
            out.append(absolute)
    # dedup, preserve order
    return list(dict.fromkeys(out))
```

- [ ] **Step 4: 도메인·링크 테스트 통과 확인**

Run: `pytest tests/scripts/test_ingest_cwi_weekly.py -v`
Expected: 3개 테스트 모두 PASS.

- [ ] **Step 5: 인덱스 캐시 + main async — 실패 테스트 추가**

같은 테스트 파일 끝에 추가:
```python
def test_cache_path_under_baduk_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from importlib import reload
    import scripts.ingest_cwi_weekly as mod
    reload(mod)
    assert str(mod.CACHE_PATH).startswith(str(tmp_path))
    assert ".baduk" in str(mod.CACHE_PATH)


def test_index_hash_skips_when_unchanged(tmp_path, monkeypatch):
    """index 페이지가 변경되지 않았으면 (캐시 일치) ingest는 0건으로 빠르게 종료."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from importlib import reload
    import scripts.ingest_cwi_weekly as mod
    reload(mod)

    html = "<html><a href='foo.sgf'>foo</a></html>"
    expected_md5 = hashlib.md5(html.encode("utf-8")).hexdigest()
    mod.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    mod.CACHE_PATH.write_text(expected_md5)

    result = mod.index_changed(html)
    assert result is False  # 캐시와 동일 → 변경 없음
```

- [ ] **Step 6: 캐시 함수 구현**

`ingest_cwi_weekly.py`에 추가 (`extract_sgf_links` 다음):
```python
def index_changed(html: str) -> bool:
    """index 페이지 md5가 캐시와 다르면 True (재처리 필요)."""
    current = hashlib.md5(html.encode("utf-8")).hexdigest()
    if not CACHE_PATH.exists():
        return True
    cached = CACHE_PATH.read_text().strip()
    return cached != current


def save_index_hash(html: str) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(hashlib.md5(html.encode("utf-8")).hexdigest())
```

- [ ] **Step 7: 캐시 테스트 통과 확인**

Run: `pytest tests/scripts/test_ingest_cwi_weekly.py -v`
Expected: 5개 테스트 PASS.

- [ ] **Step 8: main_async + HTTP/DB 통합 테스트 (mock)**

같은 파일에 추가:
```python
@pytest.mark.asyncio
async def test_main_async_ingests_new_sgfs(tmp_path, monkeypatch, respx_mock):
    """index → SGF → parse → insert 전체 경로. 모킹된 HTTP + 인메모리 DB."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    index_html = '<a href="game1.sgf">g1</a><a href="game2.sgf">g2</a>'
    sgf_body = b"(;FF[4]GM[1]SZ[19]KM[6.5]PB[Black]PW[White]DT[2024-01-01]RE[B+R];B[pd];W[dc])"

    base = "https://homepages.cwi.nl/~aeb/go/games/"
    respx_mock.get(base).respond(200, text=index_html)
    respx_mock.get(f"{base}game1.sgf").respond(200, content=sgf_body)
    respx_mock.get(f"{base}game2.sgf").respond(200, content=sgf_body)  # 동일 — 중복

    from importlib import reload
    import scripts.ingest_cwi_weekly as mod
    reload(mod)

    summary = await mod.main_async()
    assert summary["fetched"] == 2
    assert summary["new"] == 1   # 두 번째는 content_hash 중복으로 스킵
    assert summary["duplicate"] == 1
    assert summary["error"] == 0
```

이 테스트는 `respx`와 `pytest-asyncio`를 사용한다. backend `pyproject.toml`의 `[dev]`에 둘 다 이미 있어야 한다 — 확인하고 없으면 추가하는 별도 커밋이 필요. `grep -E 'respx|pytest-asyncio' backend/pyproject.toml`로 확인.

`respx`가 없으면 monkeypatch + 직접 `httpx.MockTransport`로 대체 — 그 경우 테스트 코드를 그에 맞게 작성한다.

- [ ] **Step 9: 테스트 실패 확인**

Run: `pytest tests/scripts/test_ingest_cwi_weekly.py::test_main_async_ingests_new_sgfs -v`
Expected: FAIL (main_async 미정의).

- [ ] **Step 10: main_async 구현**

`ingest_cwi_weekly.py` 끝에 추가:
```python
async def main_async() -> dict[str, int]:
    """1회 ingest 루프. 결과 카운트 반환."""
    summary = {"fetched": 0, "new": 0, "duplicate": 0, "error": 0}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
        try:
            resp = await http.get(CWI_INDEX_URL)
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:
            log.error("cwi.index.fetch_failed", err=str(exc))
            return summary

        if not index_changed(html):
            log.info("cwi.index.unchanged")
            return summary

        links = extract_sgf_links(html, CWI_INDEX_URL)
        async with AsyncSessionLocal() as db:
            for url in links:
                summary["fetched"] += 1
                try:
                    sgf_resp = await http.get(url)
                    sgf_resp.raise_for_status()
                    sgf_bytes = sgf_resp.content
                except Exception as exc:
                    log.warning("cwi.sgf.fetch_failed", url=url, err=str(exc))
                    summary["error"] += 1
                    continue

                try:
                    parsed = parse_pro_sgf(sgf_bytes)
                except InvalidProSgf as exc:
                    log.warning("cwi.sgf.parse_failed", url=url, err=str(exc))
                    summary["error"] += 1
                    continue

                # 중복 차단
                existing = await db.execute(
                    select(ProGame.id).where(ProGame.content_hash == parsed.content_hash)
                )
                if existing.scalar() is not None:
                    summary["duplicate"] += 1
                    continue

                db.add(ProGame(
                    collection="cwi",
                    content_hash=parsed.content_hash,
                    sgf=parsed.sgf,
                    black=parsed.black,
                    white=parsed.white,
                    event=parsed.event,
                    date=parsed.date,
                    result=parsed.result,
                ))
                summary["new"] += 1

            await db.commit()

        save_index_hash(html)
        log.info("cwi.ingest.complete", **summary)
        return summary


def main() -> int:
    summary = asyncio.run(main_async())
    print(f"CWI ingest 완료: fetched={summary['fetched']} new={summary['new']} "
          f"duplicate={summary['duplicate']} error={summary['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`parsed.sgf/black/white/...` 필드명은 `app.core.sgf.import_sgf.parse_pro_sgf`의 반환 타입에 맞춰야 한다. 구현 전 `grep -n "class.*ProSgf\|return" backend/app/core/sgf/import_sgf.py | head` 로 정확한 dataclass 필드를 확인하고 위 코드의 필드명을 맞춰 수정한다.

`ProGame` 모델 필드도 마찬가지로 `head backend/app/models/pro_game.py`로 컬럼명을 확인하고 `db.add(ProGame(...))` 인자를 맞춘다.

- [ ] **Step 11: 통합 테스트 통과 확인**

Run: `pytest tests/scripts/test_ingest_cwi_weekly.py -v`
Expected: 6개 테스트 모두 PASS.

- [ ] **Step 12: 회귀 + 린트**

Run:
```bash
pytest -q
ruff check .
mypy app
```
Expected: 통과.

- [ ] **Step 13: 커밋**

```bash
git add backend/scripts/ingest_cwi_weekly.py backend/tests/scripts/test_ingest_cwi_weekly.py
git commit -m "feat(scripts): CWI 주1회 자동 수집 스크립트 ingest_cwi_weekly.py"
```

---

### Task 3: content-ingest launchd 작업 + 래퍼

매주 일요일 03:00 스크립트를 실행하는 launchd 작업.

**Files:**
- Create: `ops/run-content-ingest.sh`
- Create: `ops/launchd/com.inkbaduk.content-ingest.plist`

- [ ] **Step 1: `ops/run-content-ingest.sh` 작성**

```bash
#!/usr/bin/env bash
# launchd가 매주 일요일 03:00 호출 — prod venv에서 CWI 자동 수집 스크립트를 실행.
set -euo pipefail
ROOT="/Users/daegong/projects/baduk"
cd "$ROOT/backend"

# prod backend의 .env 환경(DB_PATH 등)을 사용한다.
[ -f "$HOME/.baduk.env" ] && { set -a; . "$HOME/.baduk.env"; set +a; }

mkdir -p "$ROOT/docs/ops/state/log"
RUNLOG="$ROOT/docs/ops/state/log/content-ingest-runs.log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-ingest 시작" >> "$RUNLOG"

source .venv311/bin/activate
python -m scripts.ingest_cwi_weekly >> "$RUNLOG" 2>&1 \
  || echo "[$(date '+%Y-%m-%d %H:%M:%S')] 비정상 종료" >> "$RUNLOG"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] content-ingest 종료" >> "$RUNLOG"
```

- [ ] **Step 2: 실행 권한**

Run: `chmod +x /Users/daegong/projects/baduk/ops/run-content-ingest.sh`

- [ ] **Step 3: `ops/launchd/com.inkbaduk.content-ingest.plist` 작성**

`Weekday` 값 7은 일요일(launchd 컨벤션 — 일요일=0 또는 7 둘 다 허용).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!-- 매주 일요일 03:00 CWI 자동 수집을 실행하는 launchd 작업. -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.inkbaduk.content-ingest</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/daegong/projects/baduk/ops/run-content-ingest.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>0</integer>
    <key>Hour</key><integer>3</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/content-ingest.out.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/daegong/projects/baduk/docs/ops/state/log/content-ingest.err.log</string>
</dict>
</plist>
```

- [ ] **Step 4: 등록**

```bash
cp /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.content-ingest.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.inkbaduk.content-ingest.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.inkbaduk.content-ingest.plist
launchctl list | grep com.inkbaduk.content-ingest
```
Expected: 등록 확인.

- [ ] **Step 5: plist·문법 검사**

Run:
```bash
bash -n /Users/daegong/projects/baduk/ops/run-content-ingest.sh && echo "shell OK"
plutil -lint /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.content-ingest.plist
xmllint --noout /Users/daegong/projects/baduk/ops/launchd/com.inkbaduk.content-ingest.plist && echo "xmllint OK"
```
Expected: 셋 다 OK.

- [ ] **Step 6: 커밋** — 이 태스크에서 launchctl start는 하지 않는다. 실제 실행 검증은 Task 7.

```bash
git add ops/run-content-ingest.sh ops/launchd/com.inkbaduk.content-ingest.plist
git commit -m "feat(ops): content-ingest launchd 작업 + 래퍼 (일요일 03시)"
```

---

### Task 4: 동적 sitemap.ts

정적 5개에서 동적으로 — 모든 pro_games 페이지 포함.

**Files:**
- Modify: `web/app/sitemap.ts`
- Test: `web/tests/sitemap.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

`web/tests/sitemap.test.ts`:
```ts
// sitemap.ts의 동적 생성 테스트 — fetch 모킹으로 검증한다.
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("sitemap", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it("includes static + dynamic pro game URLs", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          { id: 1, updated_at: "2024-01-01T00:00:00" },
          { id: 42, updated_at: "2024-06-15T12:00:00" },
        ],
      }),
    );
    const { default: sitemap } = await import("../app/sitemap");
    const urls = await sitemap();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/pro/1")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/pro/42")).toBeDefined();
  });

  it("falls back to static URLs when API fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    const { default: sitemap } = await import("../app/sitemap");
    const urls = await sitemap();
    // 정적 5개는 그대로
    expect(urls.find((u) => u.url === "https://inkbaduk.com/")).toBeDefined();
    // 동적 항목은 없음
    expect(urls.find((u) => u.url?.includes("/spectate/pro/"))).toBeUndefined();
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd web && npm test -- --run sitemap.test`
Expected: FAIL (현재 sitemap.ts는 동기·정적이라 fetch 호출 없음).

- [ ] **Step 3: sitemap.ts 동적 버전 작성**

`web/app/sitemap.ts` 전체 교체:
```ts
// 검색엔진 제출용 사이트맵 — 정적 공개 페이지 + 동적 프로 기보 페이지(911+).
import type { MetadataRoute } from "next";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const revalidate = 3600; // 1시간 캐시 — ingest 후 최대 1시간 내 노출.

interface ProSitemapItem {
  id: number;
  updated_at: string;
}

async function fetchProList(): Promise<ProSitemapItem[]> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/sitemap`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return (await res.json()) as ProSitemapItem[];
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const proList = await fetchProList();

  const staticUrls: MetadataRoute.Sitemap = [
    { url: `${BASE}/`,           lastModified: now, changeFrequency: "weekly",  priority: 1 },
    { url: `${BASE}/support`,    lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${BASE}/supporters`, lastModified: now, changeFrequency: "weekly",  priority: 0.4 },
    { url: `${BASE}/privacy`,    lastModified: now, changeFrequency: "yearly",  priority: 0.3 },
    { url: `${BASE}/terms`,      lastModified: now, changeFrequency: "yearly",  priority: 0.3 },
  ];

  const proUrls: MetadataRoute.Sitemap = proList.map((p) => ({
    url: `${BASE}/spectate/pro/${p.id}`,
    lastModified: new Date(p.updated_at),
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  return [...staticUrls, ...proUrls];
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `npm test -- --run sitemap.test`
Expected: 2개 PASS.

- [ ] **Step 5: 회귀 + 린트**

Run:
```bash
npm run lint
npm run type-check
```
Expected: 통과.

- [ ] **Step 6: 커밋**

```bash
git add web/app/sitemap.ts web/tests/sitemap.test.ts
git commit -m "feat(web): 동적 sitemap — 모든 프로 기보 페이지 포함"
```

---

### Task 5: 프로 기보 페이지 `generateMetadata`

각 `/spectate/pro/[id]` 페이지에 고유 title·description·canonical 추가.

**Files:**
- Modify: `web/app/spectate/pro/[id]/page.tsx`

- [ ] **Step 1: 현재 구조 확인**

Run: `head -40 web/app/spectate/pro/'[id]'/page.tsx`
이 페이지는 server component인지 확인(`async function ...`). client component면 `generateMetadata`는 같은 파일의 별도 export로 추가 가능. 컴포넌트가 `"use client"` 면, metadata는 server component인 `page.tsx`가 export하고 client UI는 별도 children component로 분리되어 있을 것 — 그 구조를 보존한다.

- [ ] **Step 2: `generateMetadata` 추가**

`page.tsx`의 import에 `import type { Metadata } from "next"; import { notFound } from "next/navigation";` 추가(이미 있으면 생략). 그리고 컴포넌트 export 위에 추가:

```tsx
const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ProGameMeta {
  id: number;
  black?: string | null;
  white?: string | null;
  event?: string | null;
  date?: string | null;
  result?: string | null;
}

export async function generateMetadata(
  { params }: { params: { id: string } },
): Promise<Metadata> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/${params.id}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) {
      return { robots: { index: false, follow: false } };
    }
    const g = (await res.json()) as ProGameMeta;
    const black = g.black ?? "Black";
    const white = g.white ?? "White";
    const event = g.event ? ` (${g.event}${g.date ? `, ${g.date}` : ""})` : "";
    const title = `${black} vs ${white}${event} — inkbaduk`;
    const description = [
      g.event,
      g.date,
      g.result ? `결과 ${g.result}` : null,
    ].filter(Boolean).join(" · ") || "inkbaduk 프로 기보 관전";
    const canonical = `${BASE}/spectate/pro/${g.id}`;
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
```

기존 API endpoint `GET /api/spectate/pro/<id>`가 반환하는 실제 필드명을 `grep -nE 'pro_id|black|white|event' backend/app/api/spectate_pro.py | head -20`로 확인하고 `ProGameMeta` 인터페이스를 맞춘다. 필드명이 다르면 위 코드에서 매핑 수정.

- [ ] **Step 3: 빌드 + 타입 확인**

Run:
```bash
cd web
npm run type-check
npm run build 2>&1 | tail -5
```
Expected: type-check 통과, build 성공.

- [ ] **Step 4: 커밋**

```bash
git add web/app/spectate/pro/'[id]'/page.tsx
git commit -m "feat(web): /spectate/pro/[id] generateMetadata — title·description·canonical"
```

---

### Task 6: 오케스트레이터 일일 요약에 ingest 결과 한 줄

**Files:**
- Modify: `docs/ops/orchestrator-prompt.md`

- [ ] **Step 1: 변경 위치 확인**

Run: `grep -nE 'pending-approvals|보고\|요약' docs/ops/orchestrator-prompt.md | head -5`
"4. **보고**" 섹션이 일일 요약을 담당. 거기에 ingest 결과 한 줄 추가.

- [ ] **Step 2: 4번 보고 섹션 수정**

`docs/ops/orchestrator-prompt.md`에서 다음 블록을 찾는다:
```
4. **보고** — `docs/ops/runbooks/telegram-protocol.md` 형식으로 Telegram에 보낸다.
   - prod 이상이 있으면 경보를 보낸다.
   - 이상이 없어도 매 실행 시 상태 요약을 1건 보낸다 — 헬스 OK 여부와
     `state/pending-approvals.md` "대기 중" 건수를 포함한다. 하루 2회라 과하지 않다.
```
다음으로 교체:
```
4. **보고** — `docs/ops/runbooks/telegram-protocol.md` 형식으로 Telegram에 보낸다.
   - prod 이상이 있으면 경보를 보낸다.
   - 이상이 없어도 매 실행 시 상태 요약을 1건 보낸다 — 헬스 OK 여부,
     `state/pending-approvals.md` "대기 중" 건수, `state/log/content-ingest-runs.log`에서
     읽은 가장 최근 CWI ingest 결과(0건이면 "신규 0")를 포함한다. 하루 2회라 과하지 않다.
```

- [ ] **Step 3: 커밋**

```bash
git add docs/ops/orchestrator-prompt.md
git commit -m "feat(ops): 오케스트레이터 일일 요약에 CWI ingest 결과 한 줄"
```

---

### Task 7: 검증 (검증 기준 #1, #2, #3, #4)

staging 스택을 3a 코드로 띄워 4가지 검증 기준을 실증한다. prod 무영향.

**Files:** 없음 (실행 검증).

- [ ] **Step 1: staging worktree를 3a 브랜치 tip으로 갱신**

Run:
```bash
cd /Users/daegong/projects/baduk
git -C .worktrees/staging fetch
git -C .worktrees/staging checkout --detach feat/agentic-ops-content-3a
```
Expected: detached HEAD가 현재 작업 브랜치 tip이 됨.

- [ ] **Step 2: staging backend 의존성 갱신(필요시)**

이 PR에서 backend 코드만 추가됐고 새 deps은 없다. 그래도 안전하게:
```bash
cd /Users/daegong/projects/baduk/.worktrees/staging/backend
source .venv311/bin/activate
pip install -e ".[dev]" -q
alembic upgrade head
```

- [ ] **Step 3: staging 스택 기동**

```bash
cd /Users/daegong/projects/baduk
ops/stack.sh down staging 2>/dev/null || true
ops/stack.sh up staging
sleep 45
ops/stack.sh ps staging
```
Expected: backend·web 가동.

- [ ] **Step 4: 검증 기준 #1 — ingest 수동 1회 실행**

```bash
launchctl start com.inkbaduk.content-ingest
sleep 60
tail -30 /Users/daegong/projects/baduk/docs/ops/state/log/content-ingest-runs.log
```
Expected: 시작·종료 로그, `python -m scripts.ingest_cwi_weekly` 출력. 신규 0건이어도 OK. 실패면 err.log 전문 보고.

- [ ] **Step 5: 검증 기준 #2 — 동적 sitemap.xml**

```bash
curl -fs --max-time 15 http://localhost:3100/sitemap.xml | grep -c '/spectate/pro/'
```
Expected: 911 이상.

- [ ] **Step 6: 검증 기준 #3 — 프로 페이지 메타**

유효한 pro game id 한 개를 골라(예: `gh issue` 도구로 알아낸 ID, 또는 `sqlite3 backend/data/baduk.db 'SELECT id FROM pro_games LIMIT 1;'`) 메타를 확인:
```bash
PRO_ID=$(sqlite3 backend/data/baduk.db 'SELECT id FROM pro_games LIMIT 1;')
echo "선택된 id: $PRO_ID"
curl -fs --max-time 10 "http://localhost:3100/spectate/pro/$PRO_ID" \
  | grep -E '<title>|<meta name="description"|<link rel="canonical"' | head -3
```
Expected: `<title>`, `<meta name="description"`, `<link rel="canonical"` 세 라인이 출력되고, title이 `inkbaduk` 사이트 기본이 아닌 게임별 고유 텍스트.

- [ ] **Step 7: 검증 기준 #4 — 오케스트레이터 프롬프트 갱신**

```bash
grep -A2 'content-ingest-runs.log' docs/ops/orchestrator-prompt.md
```
Expected: ingest 결과를 일일 요약에 포함하라는 지시 라인이 보인다.

- [ ] **Step 8: prod 무손상 확인**

```bash
curl -fs http://localhost:8000/api/health && echo " prod-backend OK"
curl -fs http://localhost:3000 >/dev/null && echo "prod-web OK"
```
Expected: 둘 다 OK.

- [ ] **Step 9: 커밋 없음** — 실행 검증.

---

### Task 8: 통합 검증 + 대시보드 갱신

검증 기준 4가지를 한 번에 통과시키고 상태 파일을 갱신한다.

**Files:**
- Modify: `docs/ops/state/dashboard.md`
- Modify: `docs/ops/state/log/2026-05-23.md` (없으면 Create)

- [ ] **Step 1: 4가지 기준 일괄 재확인**

```bash
echo "=== #1 ingest ===" && launchctl list | grep com.inkbaduk.content-ingest \
  && tail -3 docs/ops/state/log/content-ingest-runs.log
echo "=== #2 sitemap ===" && curl -fs http://localhost:3100/sitemap.xml | grep -c '/spectate/pro/'
echo "=== #3 metadata ===" && PRO_ID=$(sqlite3 backend/data/baduk.db 'SELECT id FROM pro_games LIMIT 1;') \
  && curl -fs "http://localhost:3100/spectate/pro/$PRO_ID" | grep -cE '<title>|canonical|"description"'
echo "=== #4 orchestrator ===" && grep -c 'content-ingest-runs.log' docs/ops/orchestrator-prompt.md
```
Expected: #1 등록 + 로그, #2 ≥ 911, #3 ≥ 3, #4 = 1.

- [ ] **Step 2: 대시보드 갱신**

`docs/ops/state/dashboard.md`에 콘텐츠 행 추가(어디에 둘지는 기존 구조 보고 결정 — `## 백업 상태` 다음·`## 개발 현황` 직전에 빈 줄 띄우고 삽입):
```
## 콘텐츠 인덱스

| 항목 | 값 |
|---|---|
| 프로 기보 수 | 911 (확정값으로 채움) |
| sitemap URL 수 | 916 (정적 5 + 프로 911) |
| 최근 CWI ingest | 2026-05-23 (확정값) |
```

`(확정값)`은 Step 1의 실제 출력으로 채운다. "프로 기보 수"는 `sqlite3 backend/data/baduk.db 'SELECT count(*) FROM pro_games;'`.

- [ ] **Step 3: 로그**

`docs/ops/state/log/2026-05-23.md`에 시간순 추가:
```
## (현재시각) — 콘텐츠 수집·SEO 인덱스(sub-project 3a) 구축 완료
- 검증 기준 4/4 통과: ① CWI ingest+launchd ② 동적 sitemap (N URL) ③ 프로 페이지 메타 ④ 오케스트레이터 통합
```

`(현재시각)` `date '+%H:%M'`. `N`은 sitemap URL 수.

- [ ] **Step 4: 커밋**

```bash
git add docs/ops/state
git commit -m "feat(ops): 콘텐츠 수집·SEO 인덱스 구축 완료 — 검증 기준 4/4 통과"
```

- [ ] **Step 5: 최종 보고** — 검증 기준 4가지 실제 출력 보고.

---

## 검증 기준 (spec)

1. `ingest_cwi_weekly.py`가 CWI에 접근하고 정상 종료, `com.inkbaduk.content-ingest` launchd 등록 + 수동 트리거 로그. → Task 2, 3, 7
2. `curl localhost:3100/sitemap.xml`에 911+ 프로 페이지 URL 포함. → Task 1, 4, 7
3. `curl localhost:3100/spectate/pro/<id>` 응답에 고유 `<title>`·`<meta description>`·`<link rel="canonical">`. → Task 5, 7
4. 오케스트레이터 일일 요약에 ingest 결과 한 줄 포함(orchestrator-prompt.md 갱신). → Task 6, 7
