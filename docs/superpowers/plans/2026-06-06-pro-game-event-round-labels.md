# 프로 기보 리스트 기전명·단계·국수 로케일 표기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 프로 기보 리스트·상세에 "제10회 춘란배 결승 제3국"처럼 기전명·단계·국수를 표기하고, 한국어 모드에선 한국어로 보여준다.

**Architecture:** 하이브리드(A안). 백엔드는 SGF `RO`를 `pro_games.round`(원문 문자열) 컬럼 1개로 저장하고 API가 그대로 반환한다. 표기용 파싱·매핑·로컬라이즈는 프론트 `formatProEvent`가 담당하며, 영어 모드는 기존 영문 원문 + " · Game N", 한국어 모드는 i18n 라벨로 재조립한다. `clean_sgf`에 RO를 넣지 않아 content_hash가 불변이므로 기존 911국은 깔끔한 UPDATE backfill로 채운다.

**Tech Stack:** FastAPI · SQLAlchemy 2 · Alembic · pytest / Next.js 14 · TypeScript · Vitest. 모든 백엔드 명령은 `backend/`에서 `source .venv311/bin/activate` 후 실행. 모든 프론트 명령은 `web/`에서 실행. 설계 스펙: `docs/superpowers/specs/2026-06-06-pro-game-event-round-labels-design.md`.

---

## 파일 구조

**백엔드 (생성/수정)**
- Modify: `backend/app/core/sgf/import_sgf.py` — `ParsedProGame.round` 파싱 추가
- Create: `backend/migrations/versions/0014_pro_game_round.py` — `round` 컬럼 추가
- Modify: `backend/app/models/pro_game.py` — `round` 컬럼 + `from_parsed`
- Modify: `backend/scripts/seed_pro_games.py` — content_hash 매칭 시 `round` backfill UPDATE
- Modify: `backend/app/api/spectate_pro.py` — `ProGameRow`에 `round` 필드
- Test: `backend/tests/core/test_sgf_import.py`, `backend/tests/api/test_spectate_pro.py`

**프론트 (생성/수정)**
- Create: `web/lib/proEvent.ts` — `formatProEvent(event, round, locale)`
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json` — 기전·단계·번호 라벨
- Modify: `web/components/ProGameList.tsx` — 행 타입 `round` + 포매터 렌더
- Modify: `web/app/spectate/pro/[id]/page.tsx` — 상세 타입 `round` + 포매터 렌더
- Test: `web/tests/proEvent.test.ts` (신규)

---

## Task 1: 백엔드 — SGF RO 파싱

**Files:**
- Modify: `backend/app/core/sgf/import_sgf.py` (`ParsedProGame` 데이터클래스 + `parse_pro_sgf`)
- Test: `backend/tests/core/test_sgf_import.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/core/test_sgf_import.py` 끝에 추가. (최소 SGF는 19로 사이즈·착수 1수 포함.)

```python
def test_parse_pro_sgf_extracts_round():
    sgf_text = "(;FF[4]GM[1]SZ[19]EV[10th Chunlan Cup Final]RO[3];B[pd];W[dp])"
    parsed = parse_pro_sgf(sgf_text)
    assert parsed.round == "3"


def test_parse_pro_sgf_round_none_when_absent():
    sgf_text = "(;FF[4]GM[1]SZ[19]EV[Dosaku Castle Game];B[pd];W[dp])"
    parsed = parse_pro_sgf(sgf_text)
    assert parsed.round is None


def test_parse_pro_sgf_round_keeps_final_prefix_text():
    sgf_text = "(;FF[4]GM[1]SZ[19]RO[Final 2];B[pd];W[dp])"
    parsed = parse_pro_sgf(sgf_text)
    assert parsed.round == "Final 2"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/core/test_sgf_import.py -k round -v`
Expected: FAIL — `AttributeError: 'ParsedProGame' object has no attribute 'round'`

- [ ] **Step 3: 최소 구현**

`backend/app/core/sgf/import_sgf.py`의 `ParsedProGame`에 `round` 필드를 `event` 다음 줄에 추가:

```python
    event: str | None
    round: str | None
    game_date: date | None
```

`parse_pro_sgf` 안, `event = _opt("EV")` 다음 줄에:

```python
    event = _opt("EV")
    round_ = _opt("RO")
    result = _opt("RE")
```

그리고 `return ParsedProGame(...)`에서 `event=event,` 다음 줄에 추가:

```python
        event=event,
        round=round_,
        game_date=_parse_dt(dt_raw),
```

`_build_clean_sgf` 의 `meta` dict 는 **변경하지 않는다** (RO를 넣지 않아 content_hash 불변).

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/core/test_sgf_import.py -v`
Expected: PASS (신규 3건 포함 전부)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/core/sgf/import_sgf.py backend/tests/core/test_sgf_import.py
git commit -m "feat(pro): SGF RO(국수)를 ParsedProGame.round로 파싱"
```

---

## Task 2: 백엔드 — round 컬럼 마이그레이션 + 모델

**Files:**
- Create: `backend/migrations/versions/0014_pro_game_round.py`
- Modify: `backend/app/models/pro_game.py`

- [ ] **Step 1: 마이그레이션 작성**

`backend/migrations/versions/0014_pro_game_round.py` 생성:

```python
# 프로 기보에 RO(결승 제N국 등) 원문을 담는 round 컬럼을 추가하는 마이그레이션
"""Add round column to pro_games for SGF RO (game-in-series) labels.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-06

Nullable free-text column holding the raw SGF ``RO`` value (e.g. "3",
"Final 2"). Display formatting/localization happens in the web layer.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pro_games",
        sa.Column("round", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pro_games", "round")
```

- [ ] **Step 2: 모델에 컬럼 + from_parsed 추가**

`backend/app/models/pro_game.py` 에서 `event` 컬럼 다음 줄에:

```python
    event: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # SGF RO 원문 — 결승 제N국 등. 표기 로컬라이즈는 web 계층.
    round: Mapped[str | None] = mapped_column(String(32), nullable=True)
    game_date: Mapped[date | None] = mapped_column(Date, nullable=True)
```

`from_parsed` 의 `event=parsed.event,` 다음 줄에:

```python
            event=parsed.event,
            round=parsed.round,
            game_date=parsed.game_date,
```

- [ ] **Step 3: 마이그레이션 적용 + 확인**

Run:
```bash
cd backend && source .venv311/bin/activate && alembic upgrade head
python -c "import sqlite3; print([c[1] for c in sqlite3.connect('data/baduk.db').execute('PRAGMA table_info(pro_games)')])"
```
Expected: 컬럼 목록에 `'round'` 포함.

- [ ] **Step 4: 모델 임포트 정상 확인 (스모크)**

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_spectate_pro.py -q`
Expected: PASS (기존 테스트가 새 컬럼으로 깨지지 않음)

- [ ] **Step 5: 커밋**

```bash
git add backend/migrations/versions/0014_pro_game_round.py backend/app/models/pro_game.py
git commit -m "feat(pro): pro_games.round 컬럼 추가 (마이그레이션 0014 + 모델)"
```

---

## Task 3: 백엔드 — 기존 기보 round backfill

**Files:**
- Modify: `backend/scripts/seed_pro_games.py`

content_hash 가 이미 있으면 통째로 skip하던 것을, `round`가 비어 있고 새로 파싱한 round가 있으면 UPDATE 하도록 바꾼다.

- [ ] **Step 1: seed 스크립트의 dedup 분기 수정**

`backend/scripts/seed_pro_games.py` 에서 dup 조회·처리 블록을 교체한다.

기존:
```python
                dup = (
                    await db.execute(
                        select(ProGame.id).where(
                            ProGame.content_hash == parsed.content_hash
                        )
                    )
                ).scalar_one_or_none()
                if dup is not None:
                    skipped += 1
                    continue
                db.add(ProGame.from_parsed(parsed, collection=collection))
                seen.add(parsed.content_hash)
                inserted += 1
```

교체:
```python
                dup = (
                    await db.execute(
                        select(ProGame).where(
                            ProGame.content_hash == parsed.content_hash
                        )
                    )
                ).scalar_one_or_none()
                if dup is not None:
                    # 기적재분 — round 가 비어 있으면 채우고(backfill), 그 외엔 스킵.
                    if dup.round is None and parsed.round is not None:
                        dup.round = parsed.round
                        updated += 1
                    else:
                        skipped += 1
                    seen.add(parsed.content_hash)
                    continue
                db.add(ProGame.from_parsed(parsed, collection=collection))
                seen.add(parsed.content_hash)
                inserted += 1
```

`inserted = skipped = failed = 0` 줄을 다음으로 교체:
```python
            inserted = skipped = failed = updated = 0
```

`log.info("seed_pro_games.done", ...)` 호출에 `updated=updated,` 인자 추가:
```python
            log.info(
                "seed_pro_games.done",
                collection=collection,
                inserted=inserted,
                updated=updated,
                skipped=skipped,
                failed=failed,
            )
```

- [ ] **Step 2: backfill 실행**

Run: `cd backend && source .venv311/bin/activate && python -m scripts.seed_pro_games`
Expected: 로그에 `world` updated≈286, `masterpiece` updated≈85 (정확 수치는 RO 보유 파일 수). inserted=0.

- [ ] **Step 3: DB 반영 확인**

Run:
```bash
cd backend && source .venv311/bin/activate && python -c "
import sqlite3; db=sqlite3.connect('data/baduk.db')
print('world round 채워짐:', db.execute(\"select count(*) from pro_games where collection='world' and round is not null\").fetchone()[0], '/ 286')
print('샘플:', db.execute(\"select event, round from pro_games where collection='world' and round is not null limit 3\").fetchall())
"
```
Expected: world round 채워짐 286 / 286, 샘플에 (event, round) 쌍 출력.

- [ ] **Step 4: 커밋**

```bash
git add backend/scripts/seed_pro_games.py
git commit -m "feat(pro): seed 스크립트가 기존 기보 round를 backfill하도록 보강"
```

---

## Task 4: 백엔드 — API 응답에 round 노출

**Files:**
- Modify: `backend/app/api/spectate_pro.py` (`ProGameRow`)
- Test: `backend/tests/api/test_spectate_pro.py`

`ProGameRow` 는 `model_validate(g, from_attributes=True)` 로 채워지므로 필드만 추가하면 리스트·상세 양쪽에 자동 노출된다.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/api/test_spectate_pro.py` 에 추가. (기존 테스트가 ProGame을 만드는 헬퍼/픽스처를 쓰면 그 패턴을 따른다. 없으면 아래처럼 직접 삽입.)

```python
@pytest.mark.asyncio
async def test_list_pro_games_includes_round(client, db_session):
    from app.models import ProGame

    db_session.add(
        ProGame(
            collection="world",
            black_player="Lee Changho",
            white_player="Cho Hunhyun",
            event="10th Chunlan Cup Final",
            round="3",
            board_size=19,
            handicap=0,
            komi=6.5,
            move_count=1,
            sgf="(;FF[4]GM[1]SZ[19];B[pd])",
            content_hash="hash-round-test-1",
        )
    )
    await db_session.commit()

    resp = await client.get("/api/spectate/pro?collection=world")
    assert resp.status_code == 200
    rows = resp.json()["rows"]
    target = next(r for r in rows if r["event"] == "10th Chunlan Cup Final")
    assert target["round"] == "3"
```

주의: `client`/`db_session` 픽스처명은 `backend/tests/conftest.py` 의 기존 픽스처에 맞춘다. 기존 `test_spectate_pro.py` 가 게임을 삽입하는 방식을 먼저 읽고 동일 패턴으로 작성할 것.

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_spectate_pro.py -k round -v`
Expected: FAIL — 응답 row 에 `"round"` 키 없음 (`KeyError`).

- [ ] **Step 3: 스키마에 필드 추가**

`backend/app/api/spectate_pro.py` 의 `ProGameRow` 에서 `event` 다음 줄에:

```python
    event: str | None
    round: str | None
    game_date: date | None
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && source .venv311/bin/activate && pytest tests/api/test_spectate_pro.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/api/spectate_pro.py backend/tests/api/test_spectate_pro.py
git commit -m "feat(pro): 관전 API 응답에 round 필드 노출"
```

---

## Task 5: 프론트 — formatProEvent 포매터

**Files:**
- Create: `web/lib/proEvent.ts`
- Test: `web/tests/proEvent.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

`web/tests/proEvent.test.ts` 생성. 테스트는 `t`가 ko/en JSON을 읽으므로 `setLocale`로 로케일을 바꿔가며 검증한다.

```typescript
// 프로 기보 기전·단계·국수 표기 포매터 테스트.
import { describe, it, expect, beforeEach } from "vitest";
import { formatProEvent } from "@/lib/proEvent";
import { setLocale } from "@/lib/i18n";

describe("formatProEvent (ko)", () => {
  beforeEach(() => setLocale("ko"));

  it("기전+단계+국수", () => {
    expect(formatProEvent("10th Chunlan Cup Final", "Final 3", "ko")).toBe(
      "제10회 춘란배 결승 제3국",
    );
  });
  it("Final 키워드 없어도 국수로 결승 판정", () => {
    expect(formatProEvent("10th Ing Cup", "2", "ko")).toBe(
      "제10회 응씨배 결승 제2국",
    );
  });
  it("예선", () => {
    expect(formatProEvent("Ing Cup, Korean preliminary", null, "ko")).toBe(
      "응씨배 예선",
    );
  });
  it("미지 기전은 원문 + 국수", () => {
    expect(formatProEvent("Dosaku Castle Game", "1", "ko")).toBe(
      "Dosaku Castle Game 제1국",
    );
  });
  it("event 없으면 빈 문자열", () => {
    expect(formatProEvent(null, "3", "ko")).toBe("");
  });
});

describe("formatProEvent (en)", () => {
  beforeEach(() => setLocale("en"));

  it("원문 유지 + Game N", () => {
    expect(formatProEvent("10th Chunlan Cup Final", "Final 3", "en")).toBe(
      "10th Chunlan Cup Final · Game 3",
    );
  });
  it("국수 없으면 원문만", () => {
    expect(formatProEvent("Ing Cup, Korean preliminary", null, "en")).toBe(
      "Ing Cup, Korean preliminary",
    );
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd web && npx vitest run tests/proEvent.test.ts`
Expected: FAIL — `Failed to resolve import "@/lib/proEvent"`.

- [ ] **Step 3: 포매터 구현**

`web/lib/proEvent.ts` 생성:

```typescript
// 프로 기보 EV(기전)·RO(국수)를 로케일별 표기 문자열로 조립한다.
import { t, type Locale } from "@/lib/i18n";

// EV 이름 토큰(소문자) → i18n 기전 키.
const NAME_TO_KEY: Record<string, string> = {
  chunlan: "chunlan",
  fujitsu: "fujitsu",
  ing: "ing",
  lg: "lg",
  samsung: "samsung",
  toyota: "toyota",
};

const EVENT_RE = /^(?:(\d+)(?:st|nd|rd|th)\s+)?(.+?)\s+Cup(?:\s+(Final))?(?:,\s*(.+))?$/i;

interface ParsedEvent {
  editionNum?: number;
  tournamentKey?: string;
  stage?: "final" | "prelim";
}

function parseEvent(event: string): ParsedEvent {
  const m = EVENT_RE.exec(event.trim());
  if (!m) return {};
  const [, edition, name, finalWord, tail] = m;
  const key = NAME_TO_KEY[name.trim().toLowerCase()];
  let stage: "final" | "prelim" | undefined;
  if (tail && /prelim/i.test(tail)) stage = "prelim";
  else if (finalWord) stage = "final";
  return {
    editionNum: edition ? Number(edition) : undefined,
    tournamentKey: key,
    stage,
  };
}

// RO 원문에서 후행 정수(국수)를 뽑는다. "Final 2" → 2, "Final" → undefined.
function parseGameNo(round: string | null): number | undefined {
  if (!round) return undefined;
  const m = /(\d+)\s*$/.exec(round.trim());
  return m ? Number(m[1]) : undefined;
}

export function formatProEvent(
  event: string | null,
  round: string | null,
  locale: Locale,
): string {
  if (!event) return "";
  const { editionNum, tournamentKey, stage } = parseEvent(event);
  const gameNo = parseGameNo(round);

  // 미지 기전 — 원문을 살리고 국수만 로케일에 맞게 덧붙인다.
  if (!tournamentKey) {
    if (gameNo === undefined) return event;
    return locale === "ko"
      ? `${event} ${t("spectate.proGameNo", { n: gameNo })}`
      : `${event} · ${t("spectate.proGameNo", { n: gameNo })}`;
  }

  // 국수가 있으면 결승 best-of 시리즈를 함의 → stage 보강.
  const stageKey = stage ?? (gameNo !== undefined ? "final" : undefined);

  if (locale === "ko") {
    const parts = [
      editionNum !== undefined ? t("spectate.proEdition", { n: editionNum }) : null,
      t(`spectate.proTournament.${tournamentKey}`),
      stageKey ? t(`spectate.proStage.${stageKey}`) : null,
      gameNo !== undefined ? t("spectate.proGameNo", { n: gameNo }) : null,
    ].filter(Boolean);
    return parts.join(" ");
  }

  // en — 국제 표준 영문 원문 유지 + Game N.
  return gameNo === undefined
    ? event
    : `${event} · ${t("spectate.proGameNo", { n: gameNo })}`;
}
```

- [ ] **Step 4: 테스트 통과 확인** (Task 6 라벨이 아직 없으면 ko 케이스가 키를 그대로 반환해 실패할 수 있다 — 그 경우 Task 6을 먼저 한 뒤 재실행)

Run: `cd web && npx vitest run tests/proEvent.test.ts`
Expected: en 케이스는 PASS. ko 케이스는 i18n 라벨이 추가된 뒤 PASS — Task 6 완료 후 최종 확인.

- [ ] **Step 5: 커밋**

```bash
git add web/lib/proEvent.ts web/tests/proEvent.test.ts
git commit -m "feat(pro): formatProEvent 로케일 표기 포매터 + 테스트"
```

---

## Task 6: 프론트 — i18n 기전·단계·번호 라벨

**Files:**
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

`spectate` 객체 안에 키를 추가한다. (`spectate.proMasterpiece` 등이 이미 있는 그 블록.)

- [ ] **Step 1: ko.json 에 추가**

`web/lib/i18n/ko.json` 의 `"spectate"` 객체 안, `"proWorld": "세계 기전",` 근처에 다음 키들을 추가:

```json
    "proEdition": "제{n}회",
    "proGameNo": "제{n}국",
    "proTournament": {
      "chunlan": "춘란배",
      "fujitsu": "후지쯔배",
      "ing": "응씨배",
      "lg": "LG배",
      "samsung": "삼성화재배",
      "toyota": "도요타배"
    },
    "proStage": {
      "final": "결승",
      "prelim": "예선"
    },
```

- [ ] **Step 2: en.json 에 동일 키 추가 (영문 값)**

`web/lib/i18n/en.json` 의 `"spectate"` 객체 안에:

```json
    "proEdition": "{n}",
    "proGameNo": "Game {n}",
    "proTournament": {
      "chunlan": "Chunlan Cup",
      "fujitsu": "Fujitsu Cup",
      "ing": "Ing Cup",
      "lg": "LG Cup",
      "samsung": "Samsung Cup",
      "toyota": "Toyota Cup"
    },
    "proStage": {
      "final": "Final",
      "prelim": "Preliminary"
    },
```

- [ ] **Step 3: JSON 유효성 + 포매터 테스트 통과 확인**

Run: `cd web && node -e "require('./lib/i18n/ko.json');require('./lib/i18n/en.json');console.log('json ok')" && npx vitest run tests/proEvent.test.ts`
Expected: `json ok` + 포매터 테스트 전부 PASS (ko 포함).

- [ ] **Step 4: 커밋**

```bash
git add web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "feat(pro): 기전·단계·국수 i18n 라벨 추가 (ko/en)"
```

---

## Task 7: 프론트 — ProGameList 렌더 연결

**Files:**
- Modify: `web/components/ProGameList.tsx`

- [ ] **Step 1: 행 타입 + import + locale 추가**

`web/components/ProGameList.tsx` 상단 import 에 추가:
```typescript
import { useT, useLocale } from "@/lib/i18n";
import { formatProEvent } from "@/lib/proEvent";
```
(기존 `import { useT } from "@/lib/i18n";` 줄을 위 첫 줄로 교체.)

`interface ProRow` 의 `event: string | null;` 다음 줄에:
```typescript
  event: string | null;
  round: string | null;
```

`export function ProGameList()` 본문 `const t = useT();` 다음 줄에:
```typescript
  const t = useT();
  const [locale] = useLocale();
```

- [ ] **Step 2: event 표시부 교체**

`{r.event && <span>{r.event}</span>}` 를 다음으로 교체:
```tsx
                    {formatProEvent(r.event, r.round, locale) && (
                      <span>{formatProEvent(r.event, r.round, locale)}</span>
                    )}
```

- [ ] **Step 3: 타입체크 + 린트**

Run: `cd web && npm run type-check && npm run lint`
Expected: 통과 (에러 없음)

- [ ] **Step 4: 커밋**

```bash
git add web/components/ProGameList.tsx
git commit -m "feat(pro): 프로 리스트에 기전명·단계·국수 로케일 표기 적용"
```

---

## Task 8: 프론트 — 프로 상세 페이지 렌더 연결

**Files:**
- Modify: `web/app/spectate/pro/[id]/page.tsx`

- [ ] **Step 1: 타입 + import + locale 추가**

`web/app/spectate/pro/[id]/page.tsx` 상단:
```typescript
import { useT, useLocale } from "@/lib/i18n";
import { formatProEvent } from "@/lib/proEvent";
```
(기존 `import { useT } from "@/lib/i18n";` 교체.)

`interface ProGameDetail` 의 `event: string | null;` 다음 줄에:
```typescript
  event: string | null;
  round: string | null;
```

컴포넌트 본문에서 `const t = useT();` 다음 줄에 `const [locale] = useLocale();` 추가. (해당 파일에서 `useT()` 호출 위치를 찾아 바로 다음 줄에 둔다.)

- [ ] **Step 2: event 표시부 교체**

```tsx
      {(game.event || game.game_date) && (
        <p className="font-sans text-xs text-ink-faint">
          {[game.event, game.game_date].filter(Boolean).join(" · ")}
        </p>
      )}
```
를 다음으로 교체:
```tsx
      {(game.event || game.game_date) && (
        <p className="font-sans text-xs text-ink-faint">
          {[formatProEvent(game.event, game.round, locale) || null, game.game_date]
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
```

- [ ] **Step 3: 타입체크 + 린트**

Run: `cd web && npm run type-check && npm run lint`
Expected: 통과

- [ ] **Step 4: 커밋**

```bash
git add web/app/spectate/pro/[id]/page.tsx
git commit -m "feat(pro): 프로 상세 페이지에 기전명·단계·국수 로케일 표기 적용"
```

---

## Task 9: 전체 검증

- [ ] **Step 1: 백엔드 전체 테스트**

Run: `cd backend && source .venv311/bin/activate && pytest -q && ruff check . && mypy app`
Expected: 전부 PASS / 클린

- [ ] **Step 2: 프론트 전체 테스트 + 빌드 점검**

Run: `cd web && npm run test -- --run && npm run type-check && npm run lint`
Expected: 전부 PASS

- [ ] **Step 3: 수동 확인 (선택)**

`KATAGO_MOCK=true`로 스택을 띄워 `/spectate/pro` 세계 기전 탭에서 "제N회 …배 결승 제N국" 표기를 ko/en 토글로 확인.

- [ ] **Step 4: 디자인 토큰 가드 확인**

`web/components`·`web/app` 수정분에 하드코딩 hex·이모지 없음(포매터는 텍스트만). `design-token-check.sh` 경고 없을 것.

---

## Self-Review 메모

- **Spec coverage**: RO 파싱(T1)·컬럼/마이그(T2)·backfill(T3)·API(T4)·포매터(T5)·i18n(T6)·리스트(T7)·상세(T8)·검증(T9) — 스펙 전 항목 매핑됨.
- **content_hash 불변**: T1에서 `_build_clean_sgf` 미변경 명시 → T3 backfill이 UPDATE로 성립.
- **타입 일관성**: `round: str | None`(파이썬)·`round: string | null`(TS)·`formatProEvent(event, round, locale)` 시그니처가 T5·T7·T8에서 동일.
- **영어 경로**: 원문 + `· Game N`만 — tournament/stage 라벨 미사용(스펙 표와 일치). en i18n 키는 parity·향후용으로 등록.
- **fallback**: 미지 기전·event null·국수 없음 모두 T5에서 처리, 테스트로 커버.
