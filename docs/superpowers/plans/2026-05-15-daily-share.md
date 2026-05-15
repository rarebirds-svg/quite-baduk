# 일일 챌린지 결과 공유 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 일일 챌린지를 푼 직후 결과를 링크 + og:image로 공유해 카톡·트위터·디스코드에 자동 카드 프리뷰가 뜨고, 받는 사람이 같은 문제를 직접 풀 수 있도록 한다.

**Architecture:** 백엔드는 단건 조회 endpoint 하나만 추가. 프론트는 ① `ShareButton`(Web Share API + 클립보드 폴백), ② `StaticBoardSVG`(보드 정적 렌더 — 랜딩·OG 공유), ③ `/daily/share/[id]` 랜딩 페이지, ④ `/api/og/daily/[id]` Next.js OG 라우트(`next/og` `ImageResponse`)를 추가. 일일 페이지는 `?challenge=` 쿼리로 특정 문제 출제도 지원.

**Tech Stack:** FastAPI · Next.js 14 App Router · `next/og` (ImageResponse, Satori) · Web Share API · sonner toast · Vitest · pytest-asyncio · Tailwind 토큰.

**Spec:** `docs/superpowers/specs/2026-05-15-daily-share-design.md`

---

## File Structure (생성·변경 파일 한눈에)

**백엔드**
- Modify: `backend/app/api/daily.py` — `GET /api/daily-challenge/{id}` 라우트 추가
- Modify: `backend/tests/api/test_daily.py` — 신규 endpoint 200/404 케이스

**프론트엔드 (신규)**
- Create: `web/components/daily/StaticBoardSVG.tsx` — 보드 정적 SVG 컴포넌트
- Create: `web/components/daily/ShareButton.tsx` — 공유 버튼
- Create: `web/app/daily/share/[id]/page.tsx` — 공유 랜딩 페이지(서버 컴포넌트)
- Create: `web/app/api/og/daily/[id]/route.tsx` — OG 이미지 라우트
- Create: `web/tests/share-button.test.tsx` — ShareButton 단위 테스트
- Create: `web/tests/static-board-svg.test.tsx` — StaticBoardSVG 단위 테스트

**프론트엔드 (수정)**
- Modify: `web/app/daily/page.tsx` — 결과 패널에 ShareButton 노출 + `?challenge=` 분기
- Modify: `web/lib/i18n/ko.json` — 신규 키 8개
- Modify: `web/lib/i18n/en.json` — 신규 키 8개

---

## Task 1: 백엔드 — `GET /api/daily-challenge/{id}` endpoint

**Files:**
- Modify: `backend/tests/api/test_daily.py`
- Modify: `backend/app/api/daily.py`

- [ ] **Step 1: Write failing test for happy path**

`backend/tests/api/test_daily.py` 파일 끝에 추가.

```python
@pytest.mark.asyncio
async def test_get_by_id_returns_challenge(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "share_lookup"})
    target = CHALLENGES[0]
    r = await client.get(f"/api/daily-challenge/{target.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == target.id
    assert body["board_size"] == target.board_size
    assert body["to_move"] == target.to_move
    assert body["topic"] == target.topic
    assert body["difficulty"] == target.difficulty
    assert isinstance(body["setup"], list)


@pytest.mark.asyncio
async def test_get_by_id_unknown_returns_404(client: AsyncClient) -> None:
    await client.post("/api/session", json={"nickname": "share_404"})
    r = await client.get("/api/daily-challenge/ch-not-real")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_by_id_unauth_returns_401(client: AsyncClient) -> None:
    target = CHALLENGES[0]
    r = await client.get(f"/api/daily-challenge/{target.id}")
    assert r.status_code == 401
```

- [ ] **Step 2: Run tests — verify they fail with 404 / 405 (route absent)**

```bash
cd backend && source .venv311/bin/activate
pytest tests/api/test_daily.py::test_get_by_id_returns_challenge tests/api/test_daily.py::test_get_by_id_unknown_returns_404 tests/api/test_daily.py::test_get_by_id_unauth_returns_401 -v
```

Expected: 3 FAIL (route not registered → 404/405).

- [ ] **Step 3: Add endpoint to `backend/app/api/daily.py`**

기존 import 블록에서 `get_by_id`는 이미 import되어 있음. `random_challenge` 라우트 *바로 아래* (catalogue 위)에 추가.

```python
@router.get("/{challenge_id}")
async def get_one_challenge(
    sess: CurrentSession,
    challenge_id: str,
) -> dict[str, Any]:
    """Single puzzle lookup by id — backs the share landing page and OG
    image route. 404 when the id isn't in the catalogue."""
    challenge = get_by_id(challenge_id)
    if challenge is None:
        raise HTTPException(status_code=404, detail="challenge_not_found")
    return _serialise(challenge)
```

> **주의:** path 위치가 중요하다. `/{challenge_id}`는 `/random`, `/catalogue`, `/answer` *뒤* 또는 prefix 충돌이 없는 자리에 두어야 한다. FastAPI는 등록 순으로 매칭하므로 *catalogue/random/answer 위* 에 두면 안 된다. 위 예시는 `catalogue` 핸들러 *뒤*, `answer` 핸들러 *앞* 또는 파일 맨 아래에 추가.

- [ ] **Step 4: Re-run tests — verify they pass**

```bash
pytest tests/api/test_daily.py -v
```

Expected: 모두 PASS (기존 테스트 포함).

- [ ] **Step 5: Lint + type-check**

```bash
ruff check app/api/daily.py
mypy app/api/daily.py
```

Expected: 오류 없음.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/daily.py backend/tests/api/test_daily.py
git commit -m "feat(daily): 단건 조회 endpoint 추가 (공유 랜딩용)"
```

---

## Task 2: `StaticBoardSVG` 컴포넌트

**Files:**
- Create: `web/components/daily/StaticBoardSVG.tsx`
- Create: `web/tests/static-board-svg.test.tsx`

- [ ] **Step 1: Write failing test**

`web/tests/static-board-svg.test.tsx` 신규 작성.

```tsx
// 일일 챌린지 공유용 정적 보드 SVG 컴포넌트 테스트.
import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { StaticBoardSVG } from "@/components/daily/StaticBoardSVG";

describe("StaticBoardSVG", () => {
  it("renders one svg with the requested board size", () => {
    const { container } = render(
      <StaticBoardSVG
        boardSize={9}
        setup={[{ color: "B", coord: "E5" }]}
      />,
    );
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute("data-board-size")).toBe("9");
  });

  it("renders one stone circle per setup entry", () => {
    const { container } = render(
      <StaticBoardSVG
        boardSize={9}
        setup={[
          { color: "B", coord: "E5" },
          { color: "W", coord: "F5" },
          { color: "B", coord: "D5" },
        ]}
      />,
    );
    expect(container.querySelectorAll("circle[data-stone]").length).toBe(3);
  });

  it("ignores stones outside the board", () => {
    const { container } = render(
      <StaticBoardSVG
        boardSize={9}
        setup={[
          { color: "B", coord: "E5" },
          { color: "W", coord: "Z9" },
        ]}
      />,
    );
    expect(container.querySelectorAll("circle[data-stone]").length).toBe(1);
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd web
npm test -- --run tests/static-board-svg.test.tsx
```

Expected: FAIL — 모듈 import 실패(`Cannot find module`).

- [ ] **Step 3: Implement `StaticBoardSVG`**

`web/components/daily/StaticBoardSVG.tsx` 신규.

```tsx
// 일일 챌린지 공유 랜딩과 OG 이미지에서 공유하는 정적 보드 SVG.
import * as React from "react";

export type Stone = { color: "B" | "W"; coord: string };

export interface StaticBoardSVGProps {
  boardSize: 9 | 13 | 19 | number;
  setup: Stone[];
  /** width/height in px; defaults to 480. Aspect is square. */
  size?: number;
  /** Optional className for wrapper sizing in landing page. OG ignores this. */
  className?: string;
}

const COL_LETTERS = "ABCDEFGHJKLMNOPQRST";

function gtpToXy(coord: string, boardSize: number): [number, number] | null {
  if (coord.length < 2) return null;
  const col = COL_LETTERS.indexOf(coord[0].toUpperCase());
  const row = parseInt(coord.slice(1), 10);
  if (col < 0 || col >= boardSize) return null;
  if (!Number.isInteger(row) || row < 1 || row > boardSize) return null;
  return [col, boardSize - row];
}

function starPoints(n: number): Array<[number, number]> {
  if (n === 19) {
    return [3, 9, 15].flatMap((y) => [3, 9, 15].map((x) => [x, y] as [number, number]));
  }
  if (n === 13) {
    return [3, 6, 9].flatMap((y) => [3, 6, 9].map((x) => [x, y] as [number, number]));
  }
  if (n === 9) {
    return [2, 4, 6].flatMap((y) => [2, 4, 6].map((x) => [x, y] as [number, number]));
  }
  return [];
}

export function StaticBoardSVG({
  boardSize,
  setup,
  size = 480,
  className,
}: StaticBoardSVGProps) {
  const PAD = 24;
  const inner = size - PAD * 2;
  const step = inner / (boardSize - 1);
  const stoneR = step * 0.46;
  const stars = starPoints(boardSize);

  return (
    <svg
      data-board-size={boardSize}
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect x={0} y={0} width={size} height={size} fill="#F2EDE2" />
      {Array.from({ length: boardSize }).map((_, i) => (
        <line
          key={`h${i}`}
          x1={PAD}
          y1={PAD + i * step}
          x2={PAD + inner}
          y2={PAD + i * step}
          stroke="#2E2A24"
          strokeWidth={1}
        />
      ))}
      {Array.from({ length: boardSize }).map((_, i) => (
        <line
          key={`v${i}`}
          x1={PAD + i * step}
          y1={PAD}
          x2={PAD + i * step}
          y2={PAD + inner}
          stroke="#2E2A24"
          strokeWidth={1}
        />
      ))}
      {stars.map(([x, y]) => (
        <circle
          key={`star-${x}-${y}`}
          cx={PAD + x * step}
          cy={PAD + y * step}
          r={Math.max(2, step * 0.06)}
          fill="#2E2A24"
        />
      ))}
      {setup
        .map((s) => {
          const xy = gtpToXy(s.coord, boardSize);
          if (!xy) return null;
          const [x, y] = xy;
          return (
            <circle
              key={`${s.coord}-${s.color}`}
              data-stone={s.color}
              cx={PAD + x * step}
              cy={PAD + y * step}
              r={stoneR}
              fill={s.color === "B" ? "#1A1814" : "#F8F4EA"}
              stroke="#2E2A24"
              strokeWidth={s.color === "W" ? 1 : 0}
            />
          );
        })
        .filter(Boolean)}
    </svg>
  );
}
```

> **색상 결정:** OG 이미지는 Satori 환경에서 Tailwind 클래스를 다 못 읽으므로 보드 SVG는 토큰 hex를 *인라인 fill로 직접* 적는다. `globals.css`의 paper/ink/oxblood 값과 일치시키되 이 한 파일은 디자인 토큰 가드의 예외(OG render 한정). 인접 PR로 별도 색 정합 검토는 불필요.

- [ ] **Step 4: Run test — verify pass**

```bash
npm test -- --run tests/static-board-svg.test.tsx
```

Expected: 3 PASS.

- [ ] **Step 5: Type-check + lint**

```bash
npm run type-check
npm run lint
```

Expected: 오류 없음.

- [ ] **Step 6: Commit**

```bash
git add web/components/daily/StaticBoardSVG.tsx web/tests/static-board-svg.test.tsx
git commit -m "feat(daily): 정적 보드 SVG 컴포넌트 추가"
```

---

## Task 3: i18n 키 추가

**Files:**
- Modify: `web/lib/i18n/ko.json`
- Modify: `web/lib/i18n/en.json`

- [ ] **Step 1: 추가할 키 결정 후 ko.json `daily` 블록 안에 삽입**

`web/lib/i18n/ko.json`에서 `"daily": { ... }` 블록의 닫는 `}` 직전에 다음 필드 추가(콤마 처리 주의).

```json
"share": {
  "button": "공유",
  "title": "조용한 승부 · 일일 챌린지",
  "copied": "링크가 복사되었습니다",
  "shareFailed": "공유에 실패했습니다",
  "tryIt": "직접 풀어보기",
  "byFriend": "친구의 도전",
  "notFound": "문제를 찾을 수 없습니다",
  "goToDaily": "오늘의 챌린지로 가기"
}
```

- [ ] **Step 2: en.json에 동일 키 추가**

`web/lib/i18n/en.json`에서 `"daily": { ... }` 블록 끝에 추가.

```json
"share": {
  "button": "Share",
  "title": "K-Baduk · Daily Challenge",
  "copied": "Link copied",
  "shareFailed": "Could not share",
  "tryIt": "Try this puzzle",
  "byFriend": "A friend's challenge",
  "notFound": "Puzzle not found",
  "goToDaily": "Go to today's challenge"
}
```

- [ ] **Step 3: JSON 유효성 검증**

```bash
cd web && node -e "JSON.parse(require('fs').readFileSync('lib/i18n/ko.json','utf8')); JSON.parse(require('fs').readFileSync('lib/i18n/en.json','utf8')); console.log('OK')"
```

Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add web/lib/i18n/ko.json web/lib/i18n/en.json
git commit -m "i18n(daily): 공유 기능 한/영 문구 추가"
```

---

## Task 4: `ShareButton` 컴포넌트 + 단위 테스트

**Files:**
- Create: `web/components/daily/ShareButton.tsx`
- Create: `web/tests/share-button.test.tsx`

- [ ] **Step 1: Write failing test**

`web/tests/share-button.test.tsx` 신규.

```tsx
// 일일 챌린지 결과 공유 버튼 — Web Share API와 클립보드 폴백 테스트.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ShareButton } from "@/components/daily/ShareButton";

const TOAST = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock("sonner", () => ({ toast: TOAST }));

describe("ShareButton", () => {
  beforeEach(() => {
    TOAST.success.mockReset();
    TOAST.error.mockReset();
    // jsdom default has no navigator.share
    Object.defineProperty(window, "location", {
      value: { origin: "https://example.test", href: "https://example.test/daily" },
      writable: true,
    });
  });

  afterEach(() => {
    // Clean up any share mock we attached
    // @ts-expect-error — share is optional
    delete (navigator as Navigator).share;
    // @ts-expect-error — clipboard is read-only in some envs
    delete (navigator as Navigator).clipboard;
  });

  it("calls navigator.share with the share URL when supported", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", { value: share, configurable: true });

    render(
      <ShareButton
        challengeId="ch-1"
        verdict="best"
        topicLabel="사활"
        diffLabel="중급"
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    await Promise.resolve();
    expect(share).toHaveBeenCalledTimes(1);
    expect(share.mock.calls[0][0].url).toContain("/daily/share/ch-1?v=best");
  });

  it("falls back to clipboard.writeText when share is unsupported", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    render(
      <ShareButton
        challengeId="ch-2"
        verdict="ok"
        topicLabel="포석"
        diffLabel="초급"
      />,
    );
    fireEvent.click(screen.getByRole("button"));
    await Promise.resolve();
    await Promise.resolve();
    expect(writeText).toHaveBeenCalledTimes(1);
    expect(writeText.mock.calls[0][0]).toContain("/daily/share/ch-2?v=ok");
    expect(TOAST.success).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npm test -- --run tests/share-button.test.tsx
```

Expected: FAIL — module import 실패.

- [ ] **Step 3: Implement `ShareButton`**

`web/components/daily/ShareButton.tsx` 신규.

```tsx
"use client";
// 일일 챌린지 결과를 Web Share API 또는 클립보드로 공유하는 버튼.
import * as React from "react";
import { Share2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n";

export interface ShareButtonProps {
  challengeId: string;
  verdict?: "best" | "ok" | "weak" | "miss" | "illegal";
  topicLabel?: string;
  diffLabel?: string;
}

export function ShareButton({
  challengeId,
  verdict,
  topicLabel,
  diffLabel,
}: ShareButtonProps) {
  const t = useT();
  const onClick = React.useCallback(async () => {
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const params = new URLSearchParams();
    if (verdict) params.set("v", verdict);
    const url = `${origin}/daily/share/${challengeId}${params.toString() ? `?${params.toString()}` : ""}`;
    const text = [topicLabel, diffLabel].filter(Boolean).join(" · ");
    const title = t("daily.share.title");
    try {
      // Web Share API — mobile + Safari desktop
      if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
        await navigator.share({ url, title, text });
        return;
      }
      // Clipboard fallback — modern desktop browsers
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url);
        toast.success(t("daily.share.copied"));
        return;
      }
      // Last-resort fallback — prompt() exposes the URL even in restricted envs
      window.prompt(t("daily.share.copied"), url);
    } catch {
      // navigator.share rejects on user cancel — treat as no-op, but a real
      // error path (clipboard denied, etc.) surfaces a toast.
      if (typeof navigator !== "undefined" && !navigator.share) {
        toast.error(t("daily.share.shareFailed"));
      }
    }
  }, [challengeId, verdict, topicLabel, diffLabel, t]);

  return (
    <Button
      type="button"
      variant="outline"
      onClick={onClick}
      aria-label={t("daily.share.button")}
      className="text-ink"
    >
      <Share2 size={16} strokeWidth={1.5} aria-hidden />
      <span className="ml-1">{t("daily.share.button")}</span>
    </Button>
  );
}
```

- [ ] **Step 4: Run test — verify pass**

```bash
npm test -- --run tests/share-button.test.tsx
```

Expected: 2 PASS.

- [ ] **Step 5: Type-check + lint**

```bash
npm run type-check && npm run lint
```

Expected: 오류 없음.

- [ ] **Step 6: Commit**

```bash
git add web/components/daily/ShareButton.tsx web/tests/share-button.test.tsx
git commit -m "feat(daily): 결과 공유 버튼 컴포넌트 추가"
```

---

## Task 5: 결과 패널에 `ShareButton` 통합

**Files:**
- Modify: `web/app/daily/page.tsx`

- [ ] **Step 1: Import 추가**

`web/app/daily/page.tsx` import 블록에 추가:

```tsx
import { ShareButton } from "@/components/daily/ShareButton";
```

- [ ] **Step 2: 결과 패널의 action row에 ShareButton 삽입**

기존 코드(약 539~544행):

```tsx
              <div className="flex justify-end gap-2 mt-1">
                <Button variant="outline" onClick={tryAgain} className="text-ink">
                  {t("daily.tryAgain")}
                </Button>
                <Button onClick={nextPuzzle}>
                  {t("daily.nextPuzzle")}
                </Button>
              </div>
```

를 다음으로 교체.

```tsx
              <div className="flex flex-wrap justify-end gap-2 mt-1">
                <ShareButton
                  challengeId={challenge.id}
                  verdict={result.verdict}
                  topicLabel={t(`daily.topic.${challenge.topic}`)}
                  diffLabel={t(`daily.difficulty.${challenge.difficulty}`)}
                />
                <Button variant="outline" onClick={tryAgain} className="text-ink">
                  {t("daily.tryAgain")}
                </Button>
                <Button onClick={nextPuzzle}>
                  {t("daily.nextPuzzle")}
                </Button>
              </div>
```

> **주의:** `challenge`가 non-null인 블록 안에서만 ShareButton이 렌더됨(`result && (...)` 안쪽 + 같은 화면에서 challenge가 이미 잡혀 있음). 만약 TS가 narrowing 부족으로 불평하면 `challenge?.id ?? ""`로 가드.

- [ ] **Step 3: Type-check + lint + 기존 테스트**

```bash
cd web && npm run type-check && npm run lint && npm test -- --run
```

Expected: 오류 없음, 기존 테스트도 PASS.

- [ ] **Step 4: 수동 확인 — dev 서버에서 결과 패널에 공유 버튼 노출**

```bash
# backend (다른 터미널)
cd backend && source .venv311/bin/activate && KATAGO_MOCK=true uvicorn app.main:app --reload
# web
cd web && npm run dev
```

브라우저 → http://localhost:3000/daily → 닉네임 입력 → 문제 풀이 → 채점 → 결과 박스에 "공유" 버튼이 보이는지.

- [ ] **Step 5: Commit**

```bash
git add web/app/daily/page.tsx
git commit -m "feat(daily): 결과 패널에 공유 버튼 노출"
```

---

## Task 6: 일일 페이지 `?challenge=[id]` 분기

**Files:**
- Modify: `web/app/daily/page.tsx`

- [ ] **Step 1: URL 파라미터를 읽어 특정 ID 출제로 분기**

`useSearchParams`로 `challenge` 파라미터를 읽고, 있으면 random 호출 대신 단건 조회.

`web/app/daily/page.tsx` 상단 import 추가:

```tsx
import { useSearchParams } from "next/navigation";
```

`DailyChallengePage()` 본문 상단(다른 useState들 아래)에 추가:

```tsx
const searchParams = useSearchParams();
const forcedChallengeId = searchParams?.get("challenge") ?? null;
```

문제 fetch 로직(기존 `fetchChallenge` 또는 random 호출 위치)에서 분기 추가. 정확한 라인은 파일을 열어 확인하되, 패턴:

```tsx
// 기존:
// const data = await api<Challenge>(`/api/daily-challenge/random?${params}`);
// 변경:
const url = forcedChallengeId
  ? `/api/daily-challenge/${encodeURIComponent(forcedChallengeId)}`
  : `/api/daily-challenge/random?${params}`;
const data = await api<Challenge>(url);
```

> **YAGNI:** 강제 ID로 출제된 경우 "다음 문제"를 누르면 random으로 돌아간다 — `?challenge=` 파라미터를 비우는 처리는 안 한다. 사용자가 다른 문제로 옮기는 즉시 URL이 자연스럽게 갱신되도록 `router.replace(...)` 같은 것도 안 한다. 첫 진입 시 강제 출제만 만족하면 v1 목적은 달성.

- [ ] **Step 2: Type-check + lint**

```bash
npm run type-check && npm run lint
```

Expected: 오류 없음.

- [ ] **Step 3: 수동 확인**

dev 서버에서 `http://localhost:3000/daily?challenge=<실제 catalogue ID>`로 들어갔을 때 해당 문제가 출제되는지. 잘못된 ID면 기존 에러 처리(`gradeFailed` 등) 경로 그대로.

- [ ] **Step 4: Commit**

```bash
git add web/app/daily/page.tsx
git commit -m "feat(daily): ?challenge= 쿼리로 특정 문제 출제 지원"
```

---

## Task 7: 공유 랜딩 페이지 `/daily/share/[id]`

**Files:**
- Create: `web/app/daily/share/[id]/page.tsx`

- [ ] **Step 1: 신규 페이지 작성**

`web/app/daily/share/[id]/page.tsx` 신규.

```tsx
// 친구에게 공유받은 일일 챌린지를 미리 보여주고, 직접 풀어보기로 유도하는 랜딩.
import type { Metadata } from "next";
import Link from "next/link";
import { StaticBoardSVG } from "@/components/daily/StaticBoardSVG";
import { Hero } from "@/components/editorial/Hero";

type Verdict = "best" | "ok" | "weak" | "miss" | "illegal";

interface ChallengeResponse {
  id: string;
  board_size: number;
  setup: Array<{ color: "B" | "W"; coord: string }>;
  to_move: "B" | "W";
  difficulty: "easy" | "medium" | "hard";
  topic: string;
  prompt_key: string;
}

const BACKEND_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function fetchChallenge(id: string): Promise<ChallengeResponse | null> {
  try {
    const r = await fetch(`${BACKEND_BASE}/api/daily-challenge/${encodeURIComponent(id)}`, {
      cache: "no-store",
    });
    if (!r.ok) return null;
    return (await r.json()) as ChallengeResponse;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { v?: string };
}): Promise<Metadata> {
  const verdict = searchParams.v ?? "";
  const ogPath = `/api/og/daily/${encodeURIComponent(params.id)}${verdict ? `?v=${encodeURIComponent(verdict)}` : ""}`;
  return {
    title: "K-Baduk · Daily Challenge",
    description: "조용한 승부 · 일일 챌린지",
    openGraph: {
      title: "조용한 승부 · 일일 챌린지",
      description: "친구가 푼 일일 챌린지에 도전해 보세요.",
      images: [{ url: ogPath, width: 1200, height: 630 }],
    },
    twitter: {
      card: "summary_large_image",
      images: [ogPath],
    },
  };
}

export default async function SharePage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams: { v?: string };
}) {
  const challenge = await fetchChallenge(params.id);
  if (!challenge) {
    return (
      <div className="mx-auto max-w-xl py-16 px-4 text-center">
        <Hero title="문제를 찾을 수 없습니다" subtitle="공유 링크가 만료되었거나 올바르지 않습니다." />
        <div className="mt-6">
          <Link href="/daily" className="font-sans uppercase tracking-label text-oxblood hover:underline">
            오늘의 챌린지로 가기 →
          </Link>
        </div>
      </div>
    );
  }

  const verdict = (searchParams.v as Verdict | undefined) ?? undefined;
  const verdictTone: Record<Verdict, string> = {
    best: "text-moss",
    ok: "text-ink",
    weak: "text-ink-mute",
    miss: "text-oxblood",
    illegal: "text-ink-mute",
  };

  return (
    <div className="mx-auto max-w-2xl py-10 px-4">
      <Hero
        title="친구의 도전"
        subtitle={`${challenge.topic} · ${challenge.difficulty}`}
      />
      {verdict && (
        <p className={`mt-2 font-mono text-sm ${verdictTone[verdict]}`}>
          {verdict.toUpperCase()}
        </p>
      )}
      <div className="mt-6 flex justify-center">
        <StaticBoardSVG
          boardSize={challenge.board_size}
          setup={challenge.setup}
          size={420}
        />
      </div>
      <div className="mt-8 flex justify-center">
        <Link
          href={`/daily?challenge=${encodeURIComponent(challenge.id)}`}
          className="border border-ink px-4 py-2 font-sans uppercase tracking-label text-ink hover:bg-ink hover:text-paper transition-base"
        >
          직접 풀어보기 →
        </Link>
      </div>
    </div>
  );
}
```

> **i18n note:** 이 페이지는 서버 컴포넌트라 `useT` 훅을 못 쓴다. 한국어 하드코딩이 일시적으로 들어간다. v1 범위에서 허용 — 디자인 토큰 가드도 한국어 하드코딩 자체는 차단하지 않는다(쿠키 기반 로케일 분기를 서버 컴포넌트에 추가하는 작업은 별도 스펙).

- [ ] **Step 2: Type-check + lint**

```bash
cd web && npm run type-check && npm run lint
```

Expected: 오류 없음.

- [ ] **Step 3: 수동 확인 — 랜딩 페이지 렌더**

dev 서버에서 `http://localhost:3000/daily/share/<실제 ID>?v=best` 접속 → 보드 + verdict 표시 + "직접 풀어보기" 버튼 동작. 잘못된 ID는 404 fallback.

- [ ] **Step 4: Commit**

```bash
git add web/app/daily/share/[id]/page.tsx
git commit -m "feat(daily): 공유 랜딩 페이지 추가"
```

---

## Task 8: OG 이미지 라우트 `/api/og/daily/[id]`

**Files:**
- Create: `web/app/api/og/daily/[id]/route.tsx`

- [ ] **Step 1: OG 라우트 작성**

`web/app/api/og/daily/[id]/route.tsx` 신규.

```tsx
// 일일 챌린지 공유 카드(1200×630) — next/og ImageResponse로 즉석 생성.
import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";

export const runtime = "edge";

type Verdict = "best" | "ok" | "weak" | "miss" | "illegal";

interface ChallengeResponse {
  id: string;
  board_size: number;
  setup: Array<{ color: "B" | "W"; coord: string }>;
  topic: string;
  difficulty: string;
}

const BACKEND_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const COL_LETTERS = "ABCDEFGHJKLMNOPQRST";

function gtpToXy(coord: string, n: number): [number, number] | null {
  if (coord.length < 2) return null;
  const col = COL_LETTERS.indexOf(coord[0].toUpperCase());
  const row = parseInt(coord.slice(1), 10);
  if (col < 0 || col >= n) return null;
  if (!Number.isInteger(row) || row < 1 || row > n) return null;
  return [col, n - row];
}

function verdictLabel(v: Verdict | undefined): string {
  switch (v) {
    case "best":
      return "최선의 한 수";
    case "ok":
      return "괜찮은 수";
    case "weak":
      return "아쉬운 수";
    case "miss":
      return "오답";
    default:
      return "일일 챌린지";
  }
}

function verdictColor(v: Verdict | undefined): string {
  switch (v) {
    case "best":
      return "#56624D"; // moss
    case "ok":
      return "#2E2A24"; // ink
    case "weak":
      return "#7A7468"; // ink-mute
    case "miss":
      return "#6B1F26"; // oxblood
    default:
      return "#2E2A24";
  }
}

async function fetchChallenge(id: string): Promise<ChallengeResponse | null> {
  try {
    const r = await fetch(`${BACKEND_BASE}/api/daily-challenge/${encodeURIComponent(id)}`, {
      cache: "no-store",
    });
    if (!r.ok) return null;
    return (await r.json()) as ChallengeResponse;
  } catch {
    return null;
  }
}

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  const { searchParams } = new URL(req.url);
  const verdict = (searchParams.get("v") as Verdict | null) ?? undefined;
  const challenge = await fetchChallenge(params.id);

  const W = 1200;
  const H = 630;
  const BG = "#F2EDE2";
  const INK = "#2E2A24";

  // Default fallback card when challenge cannot be loaded.
  const setup = challenge?.setup ?? [];
  const boardSize = challenge?.board_size ?? 9;
  const topic = challenge?.topic ?? "";
  const difficulty = challenge?.difficulty ?? "";

  // Board geometry — left half of card.
  const boardSide = 480;
  const boardPad = 24;
  const inner = boardSide - boardPad * 2;
  const step = inner / (boardSize - 1);
  const stoneR = step * 0.46;

  return new ImageResponse(
    (
      <div
        style={{
          width: W,
          height: H,
          background: BG,
          color: INK,
          display: "flex",
          flexDirection: "column",
          padding: 56,
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <div style={{ fontSize: 32, fontWeight: 600 }}>조용한 승부</div>
          <div style={{ fontSize: 22, color: "#7A7468" }}>일일 챌린지</div>
        </div>

        <div style={{ flex: 1, display: "flex", marginTop: 24, gap: 48 }}>
          {/* Board */}
          <svg width={boardSide} height={boardSide} viewBox={`0 0 ${boardSide} ${boardSide}`}>
            <rect x={0} y={0} width={boardSide} height={boardSide} fill={BG} />
            {Array.from({ length: boardSize }).map((_, i) => (
              <line
                key={`h${i}`}
                x1={boardPad}
                y1={boardPad + i * step}
                x2={boardPad + inner}
                y2={boardPad + i * step}
                stroke={INK}
                strokeWidth={1}
              />
            ))}
            {Array.from({ length: boardSize }).map((_, i) => (
              <line
                key={`v${i}`}
                x1={boardPad + i * step}
                y1={boardPad}
                x2={boardPad + i * step}
                y2={boardPad + inner}
                stroke={INK}
                strokeWidth={1}
              />
            ))}
            {setup
              .map((s, idx) => {
                const xy = gtpToXy(s.coord, boardSize);
                if (!xy) return null;
                const [x, y] = xy;
                return (
                  <circle
                    key={idx}
                    cx={boardPad + x * step}
                    cy={boardPad + y * step}
                    r={stoneR}
                    fill={s.color === "B" ? "#1A1814" : "#F8F4EA"}
                    stroke={INK}
                    strokeWidth={s.color === "W" ? 1 : 0}
                  />
                );
              })
              .filter(Boolean)}
          </svg>

          {/* Right column */}
          <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 16 }}>
            {(topic || difficulty) && (
              <div style={{ fontSize: 28, color: "#7A7468" }}>
                {[topic, difficulty].filter(Boolean).join(" · ")}
              </div>
            )}
            <div style={{ width: 80, height: 2, background: INK }} />
            <div style={{ fontSize: 48, color: verdictColor(verdict), fontWeight: 600 }}>
              {verdictLabel(verdict)}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24 }}>
          <div style={{ fontSize: 20, color: "#7A7468" }}>k-baduk.com</div>
          <div style={{ fontSize: 20, color: INK }}>직접 풀어보기 →</div>
        </div>
      </div>
    ),
    { width: W, height: H },
  );
}
```

> **Edge runtime 주의:** `runtime = "edge"`는 Vercel/Edge에서만 의미가 있다. Docker(Node) 배포에서는 Node 런타임으로 자동 fallback. 폰트는 시스템 sans-serif로 두는 v1 — 한국어 글리프가 sans-serif 폴백으로 충분히 보임. 폰트 임베드는 별도 PR에서 고도화.

- [ ] **Step 2: Type-check + lint**

```bash
cd web && npm run type-check && npm run lint
```

Expected: 오류 없음. `next/og` 타입이 잡히지 않으면 `npm install` 재실행 (Next.js 14에 내장이라 추가 의존성 불필요하나 IDE 캐시 이슈 가능).

- [ ] **Step 3: 수동 확인 — OG 이미지 직접 호출**

```bash
curl -s -o /tmp/og.png "http://localhost:3000/api/og/daily/<실제 ID>?v=best" && file /tmp/og.png
```

Expected: `PNG image data, 1200 x 630`.

브라우저로 직접 열어 카드가 의도대로 보이는지 확인.

- [ ] **Step 4: Commit**

```bash
git add web/app/api/og/daily/[id]/route.tsx
git commit -m "feat(daily): OG 이미지 라우트 (next/og) 추가"
```

---

## Task 9: 통합 수동 QA

**Files:** 없음(검증만).

- [ ] **Step 1: 전체 플로우 수동 검증**

dev 서버 가동 후 체크리스트:

```
[ ] /daily 진입 → 문제 풀이 → 결과 박스에 "공유" 버튼 노출
[ ] 데스크탑 Chrome에서 공유 클릭 → 링크 클립보드 복사 + 토스트 "링크가 복사되었습니다"
[ ] iOS Safari / Android Chrome에서 공유 클릭 → 시스템 공유 시트 호출
[ ] 복사된 링크 (/daily/share/<id>?v=best) 새 탭에서 열기 → 랜딩 페이지 보드·verdict 정상
[ ] 랜딩 페이지 "직접 풀어보기" 클릭 → /daily?challenge=<id>로 이동 + 같은 문제 출제
[ ] /api/og/daily/<id>?v=best 직접 호출 → 1200×630 PNG 반환
[ ] /daily/share/잘못된-id → "문제를 찾을 수 없습니다" + "오늘의 챌린지로 가기" 링크
[ ] 다크모드 토글 시 랜딩 페이지 토큰 준수
[ ] 카카오톡 PC/모바일에 링크 붙여넣어 og 카드 프리뷰 표시
[ ] 트위터/X에 링크 붙여 og 카드 프리뷰 표시
[ ] 디스코드에 링크 붙여 og 카드 프리뷰 표시
```

- [ ] **Step 2: design-token-guardian 에이전트 실행**

```
.claude/agents/design-token-guardian
```

대상: `web/components/daily/StaticBoardSVG.tsx`, `web/components/daily/ShareButton.tsx`, `web/app/daily/share/[id]/page.tsx`. 

> **알려진 예외:** OG 이미지 라우트(`api/og/daily/[id]/route.tsx`)와 `StaticBoardSVG`는 Satori/SVG 호환을 위해 hex가 인라인으로 들어간다. 가드의 경고는 *이 두 파일에 한해서만* 허용.

- [ ] **Step 3: a11y-auditor 에이전트 실행**

대상: 결과 패널의 공유 버튼, 랜딩 페이지 키보드 흐름·포커스 링·`aria-label`·다크모드 대비.

- [ ] **Step 4: korean-copy-qa 에이전트 실행**

대상: 신규 i18n 키 ko/en 자연스러움 + 바둑 용어 일관성. 특히 verdict 라벨("최선의 한 수" 등) 톤이 기존 `daily.verdict.*`와 정합한지.

- [ ] **Step 5: 최종 점검 후 PR 본문에 체크리스트 결과 첨부**

수동 QA 체크박스 결과를 PR 본문 "Test plan" 섹션에 옮겨 적는다.

- [ ] **Step 6: 통합 커밋 (필요 시)**

이번 task는 수정 파일이 없지만 위 에이전트 검토 과정에서 hex 색상 정합·문구 미세조정 등이 발생하면 단일 commit으로 정리.

```bash
git add -A
git commit -m "polish(daily): 공유 기능 QA 후속 보정"
```

(보정이 없으면 commit 생략)

---

## Self-Review 메모

- 스펙의 §4.2 i18n 키 8개 — Task 3에서 모두 정의.
- 스펙의 §5 엣지케이스 — Task 1(404), Task 7(랜딩 fallback), Task 4(클립보드 폴백·prompt 최후 폴백), Task 8(OG generic fallback) 모두 커버.
- 스펙의 §6 테스트 — Task 1(백엔드 3개), Task 2(StaticBoardSVG 3개), Task 4(ShareButton 2개), Task 9(수동 + 에이전트).
- 스펙의 §7 디자인 시스템 — `ShareButton`은 lucide `Share2` 사용, 토큰만 적용, 이모지 없음. OG·StaticBoardSVG의 인라인 hex 예외는 Task 9에 명시.
- 스펙의 §2 비목표(streak/리더보드/카카오 SDK/서명 토큰) — 본 플랜에 포함되지 않음. 확인.

플레이스홀더·미정 항목 점검: 없음. 모든 step에 실제 코드·명령·기대 출력이 포함됨.
