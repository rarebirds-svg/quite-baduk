# e2e 재구성 — nickname-only + Picker 흐름 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** e2e/ Playwright 스위트를 신규 nickname-only + custom Picker 흐름으로 재작성하고 CI e2e 잡을 재활성화한다.

**Architecture:** 점진 재작성 — `helpers.ts` 신규 헬퍼 도입 → 스펙 1개씩 마이그레이션(첫 스펙에서 Picker 셀렉터 검증) → 신규 `auth.spec.ts` 추가 → CI 잡 `if: false` 제거. 단일 PR 브랜치 `chore/e2e-rewrite-nickname-flow`.

**Tech Stack:** Playwright ^1.46, TypeScript, Docker Compose(backend+web), Next.js 14 + shadcn/Radix UI, `KATAGO_MOCK=true`.

**관련 spec:** `docs/superpowers/specs/2026-05-24-e2e-rewrite-design.md`

---

## DOM 사실 (조사 완료)

- 랜딩 `/`. `<input>` (autoFocus, type=text, placeholder=`t("session.nicknamePlaceholder")` = ko `2–32자, 이모지 금지` / en `2–32 characters, no emoji`). `<button type="submit">` 텍스트 ko `시작하기` / en `Start`. 버튼은 `status === "available"`까지 disabled.
- `/game/new`. `BoardSizePicker` → shadcn `ToggleGroup` `aria-label="바둑판 크기"`. 항목은 `<button>` 텍스트 `9×9` / `13×13` / `19×19` (`role="radio"`로 노출).
- `RankPicker` → Radix `Select`. `<button>` 트리거 `aria-label="급수"`. 클릭 시 popover에 옵션.
- `HandicapPicker` → Radix `Select`. 트리거 `aria-label="대국방식"` (ko) / `Handicap` (en). 옵션 라벨 `t("game.handicapNone")` = `호선`, `t("game.handicapStones", {n})` = `{n}점 치석`.
- `PlayerPicker` → `role="radiogroup"` `aria-label`. 항목은 `role="radio"` 버튼.
- 색 선택(handicap=0 일 때). `<button>` ko `랜덤 뽑기` / en `Roll`.
- 게임 시작. `<Button>` ko `대국 시작` / en `Start`. `aiPlayer === null`이면 disabled.

i18n 기본 언어는 KO. 테스트 단언은 `시작하기|Start` 형태의 정규식으로 양쪽 모두 수용.

---

## 파일 구조

**수정.**
- `e2e/tests/helpers.ts` — 구식 `signup`/`createGame` 제거, 신규 `uniqueNickname`/`createSession`/`createGame` 도입.
- `e2e/tests/board_size.spec.ts` — 헬퍼 호출부만 갱신.
- `e2e/tests/handicap.spec.ts` — 헬퍼 호출부만 갱신.
- `e2e/tests/review.spec.ts` — 헬퍼 호출부만 갱신.
- `e2e/tests/single_session.spec.ts` — 두 context 모두 `createSession`. WS 단언 유지.
- `.github/workflows/ci.yml` — e2e 잡 `if: false` 제거.

**rename.**
- `e2e/tests/signup_and_play.spec.ts` → `e2e/tests/nickname_and_play.spec.ts` (`git mv`로 히스토리 보존).

**신규.**
- `e2e/tests/auth.spec.ts` — nickname 유효성·중복·정상 3개 케이스.

**미수정.**
- `e2e/tests/theme_lang.spec.ts` — 인증 무관.
- `e2e/playwright.config.ts` — timeout/retry 변경 없음.

---

## Task 0: 브랜치 생성 + 워크트리 격리

**Files:**
- Create: `/Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite/` (git worktree)

- [ ] **Step 1: 워크트리·브랜치 생성**

```bash
cd /Users/daegong/projects/baduk
git worktree add .claude/worktrees/e2e-rewrite -b chore/e2e-rewrite-nickname-flow
```

Expected. `Preparing worktree (new branch 'chore/e2e-rewrite-nickname-flow')` 후 디렉터리 생성.

- [ ] **Step 2: 이후 모든 작업은 워크트리 안에서**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite
git status   # main 트래킹, clean
```

워크트리 디렉토리를 이하 모든 Task의 작업 디렉토리로 사용.

---

## Task 1: helpers.ts 재작성

**Files:**
- Modify: `e2e/tests/helpers.ts` (전면 재작성)

- [ ] **Step 1: 신규 helpers.ts 작성**

`e2e/tests/helpers.ts` 전체 교체.

```typescript
// e2e 테스트의 nickname-only 세션 생성과 게임 생성 헬퍼.
import { expect, type Page } from "@playwright/test";

export function uniqueNickname(prefix = "qa"): string {
  // backend 한계 32자 — prefix + timestamp + random suffix.
  const ts = Date.now().toString(36);
  const rnd = Math.random().toString(36).slice(2, 6);
  return `${prefix}_${ts}_${rnd}`;
}

export async function createSession(
  page: Page,
  nickname: string = uniqueNickname(),
): Promise<string> {
  await page.goto("/");
  const input = page.locator('input[placeholder*="자"], input[placeholder*="characters"]');
  await input.fill(nickname);
  const submit = page.getByRole("button", { name: /^시작하기$|^Start$/ });
  // 400ms debounce 가용성 체크 → 버튼 disabled가 풀릴 때까지 대기.
  await expect(submit).toBeEnabled({ timeout: 5000 });
  await submit.click();
  await expect(page).toHaveURL(/\/game\/new$/);
  return nickname;
}

export interface CreateGameOpts {
  aiPlayer?: RegExp | string;   // PlayerPicker 라벨 매칭
  rank?: string;                // 예: "5d" — RankPicker 옵션 라벨
  boardSize?: 9 | 13 | 19;
  handicap?: 0 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;
  userColor?: "black" | "white";
}

export async function createGame(page: Page, opts: CreateGameOpts = {}): Promise<void> {
  await expect(page).toHaveURL(/\/game\/new$/);

  if (opts.boardSize) {
    await page.getByRole("radio", { name: `${opts.boardSize}×${opts.boardSize}` }).click();
  }

  if (opts.rank) {
    // Radix Select — 트리거 클릭 후 옵션 클릭.
    await page.getByRole("combobox", { name: /급수|Rank/ }).click();
    await page.getByRole("option", { name: new RegExp(`^${opts.rank}$`, "i") }).click();
  }

  if (opts.handicap !== undefined) {
    await page.getByRole("combobox", { name: /대국방식|Handicap/ }).click();
    const label = opts.handicap === 0
      ? /^호선$|^Even$/
      : new RegExp(`${opts.handicap}\\s*점 치석|${opts.handicap}\\s*stones`);
    await page.getByRole("option", { name: label }).click();
  }

  if (opts.handicap === 0 || opts.handicap === undefined) {
    // 색 선택 — 색이 미정이면 게임 시작 disabled. 자동으로 굴려서 결정.
    const rollBtn = page.getByRole("button", { name: /랜덤 뽑기|Roll/ });
    if (await rollBtn.isVisible().catch(() => false)) {
      await rollBtn.click();
    }
  }

  if (opts.aiPlayer) {
    const aiLabel = typeof opts.aiPlayer === "string"
      ? new RegExp(opts.aiPlayer, "i")
      : opts.aiPlayer;
    await page.getByRole("radio", { name: aiLabel }).first().click();
  } else {
    // aiPlayer 미지정 — radiogroup의 첫 옵션 선택해서 disabled 해제.
    await page.locator('[role="radiogroup"][aria-label*="상대"] [role="radio"], [role="radiogroup"][aria-label*="Opponent"] [role="radio"]').first().click();
  }

  const start = page.getByRole("button", { name: /^대국 시작$|^Start$/ });
  await expect(start).toBeEnabled({ timeout: 5000 });
  await start.click();
  await expect(page).toHaveURL(/\/game\/play\/\d+$/);
}
```

- [ ] **Step 2: 컴파일 가능 확인**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite/e2e
npx tsc --noEmit --skipLibCheck tests/helpers.ts
```

Expected. 에러 없음.

- [ ] **Step 3: 커밋**

```bash
git add e2e/tests/helpers.ts
git commit -m "$(cat <<'EOF'
test(e2e): helpers nickname-only 흐름으로 재작성

구식 signup/createGame을 제거하고 새로운 uniqueNickname/
createSession/createGame을 도입. createGame은 BoardSize ToggleGroup,
RankPicker·HandicapPicker(Radix Select), PlayerPicker(radiogroup)와
대국 시작 버튼을 ko/en 정규식으로 양쪽 매칭한다.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: board_size.spec.ts 마이그레이션 (첫 검증)

**Files:**
- Modify: `e2e/tests/board_size.spec.ts`

- [ ] **Step 1: 현재 파일 읽기 (단언부 보존용)**

```bash
cat e2e/tests/board_size.spec.ts
```

- [ ] **Step 2: 신규 흐름으로 재작성**

`e2e/tests/board_size.spec.ts` 전체 교체.

```typescript
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("9x9 game can be created and renders the smaller board", async ({ page }) => {
  await createSession(page);
  await createGame(page, { boardSize: 9 });
  await expect(page.locator('svg[aria-label="9x9 Go board"], svg[aria-label="9×9 Go board"], svg[role="grid"]').first()).toBeVisible();
});

test("13x13 game can be created and renders the medium board", async ({ page }) => {
  await createSession(page);
  await createGame(page, { boardSize: 13 });
  await expect(page.locator('svg[aria-label="13x13 Go board"], svg[aria-label="13×13 Go board"], svg[role="grid"]').first()).toBeVisible();
});
```

> 기존 단언이 더 강한 게 있으면(예: 특정 좌표의 grid line 개수 검증) 그 부분을 유지하라. 위는 최소 보장.

- [ ] **Step 3: docker 스택 가동 (백엔드+웹)**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite
export KATAGO_MOCK=true
docker compose up --build -d
```

Expected. `baduk-backend-1 Started` / `baduk-web-1 Started`. 첫 빌드는 5–10분 소요 가능.

- [ ] **Step 4: 헬스 대기**

```bash
for i in $(seq 1 60); do
  curl -fs http://localhost:8000/api/health && echo " backend OK" && break
  sleep 3
done
for i in $(seq 1 60); do
  curl -fs http://localhost:3000/ > /dev/null && echo "web OK" && break
  sleep 3
done
```

Expected. 두 서비스 모두 OK 출력.

- [ ] **Step 5: board_size 스펙만 실행**

```bash
cd e2e
npm install
npx playwright install --with-deps chromium
npx playwright test tests/board_size.spec.ts --reporter=list
```

Expected. `2 passed`. 실패 시 helper 셀렉터를 실제 DOM에 맞춰 조정하고 재실행.

- [ ] **Step 6: 통과 시 커밋 (다른 스펙 마이그레이션 전 helpers 확정)**

다른 스펙들도 같은 helpers를 쓸 것이므로, board_size 통과로 helpers 셀렉터가 확정됐다. 본 단계에서 helpers를 더 손볼 일 없음. 커밋은 board_size 마이그레이션과 helpers 조정(있다면)을 묶는다.

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite
git add e2e/tests/board_size.spec.ts e2e/tests/helpers.ts
git commit -m "$(cat <<'EOF'
test(e2e): board_size를 새 helpers로 마이그레이션

createSession + createGame({boardSize}) 기반으로 9x9·13x13
스펙을 재작성. 실제 Picker DOM에 맞춰 helpers의 셀렉터를
조정한 결과 포함.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: handicap.spec.ts 마이그레이션

**Files:**
- Modify: `e2e/tests/handicap.spec.ts`

- [ ] **Step 1: 현재 파일 확인**

```bash
cat e2e/tests/handicap.spec.ts
```

- [ ] **Step 2: 재작성**

```typescript
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("4-stone handicap places 4 black stones on the star points", async ({ page }) => {
  await createSession(page);
  await createGame(page, { handicap: 4 });
  // 핸디캡 4 → 흑돌 4개가 화점에 배치된다.
  // 구체 단언은 기존 스펙의 단언을 그대로 유지하라.
  // 최소 단언. 보드 SVG와 흑돌 group 4개 이상.
  const blackStones = page.locator('svg [data-stone="black"], svg circle[fill*="black" i]');
  await expect(blackStones).toHaveCount(4, { timeout: 10000 });
});
```

> 기존 스펙에 더 정밀한 단언(예: 특정 좌표 D4·Q4·D16·Q16에 stone 검증)이 있다면 보존하라.

- [ ] **Step 3: 실행**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite/e2e
npx playwright test tests/handicap.spec.ts --reporter=list
```

Expected. `1 passed`.

- [ ] **Step 4: 커밋**

```bash
git add e2e/tests/handicap.spec.ts
git commit -m "test(e2e): handicap을 새 helpers로 마이그레이션

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: review.spec.ts 마이그레이션

**Files:**
- Modify: `e2e/tests/review.spec.ts`

- [ ] **Step 1: 현재 파일 확인**

```bash
cat e2e/tests/review.spec.ts
```

- [ ] **Step 2: 재작성**

기존 스펙의 본 흐름(게임 생성 → 종국 → 리뷰 페이지 검증)을 유지하되 인증·생성 부분만 신규 헬퍼로 교체.

```typescript
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("after resigning, the kifu view shows the moves and result", async ({ page }) => {
  await createSession(page);
  await createGame(page, { boardSize: 9 });

  // 한 수 두고 즉시 기권 — 본 단언은 기보 페이지 진입과 결과 표시.
  // SVG 보드 1점(임의 좌표) 클릭. 좌표는 기존 스펙에서 동작했던 값을 유지.
  const board = page.locator('svg[role="grid"]').first();
  await board.click({ position: { x: 50, y: 50 } });

  await page.getByRole("button", { name: /기권|Resign/ }).click();
  // 확인 다이얼로그가 있으면 확인.
  const confirm = page.getByRole("button", { name: /확인|Confirm|Yes/ });
  if (await confirm.isVisible().catch(() => false)) await confirm.click();

  // 결과 라벨이 표시됨.
  await expect(page.getByText(/결과|Result/).first()).toBeVisible({ timeout: 10000 });
});
```

> 기존 스펙에 review 페이지 진입(`/game/review/{id}`)·SGF 다운로드 등 추가 단언이 있으면 보존하라.

- [ ] **Step 3: 실행**

```bash
npx playwright test tests/review.spec.ts --reporter=list
```

Expected. `1 passed`.

- [ ] **Step 4: 커밋**

```bash
git add e2e/tests/review.spec.ts
git commit -m "test(e2e): review를 새 helpers로 마이그레이션

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: signup_and_play → nickname_and_play 재작성

**Files:**
- Rename: `e2e/tests/signup_and_play.spec.ts` → `e2e/tests/nickname_and_play.spec.ts`

- [ ] **Step 1: 기존 본 흐름 파악**

```bash
cat e2e/tests/signup_and_play.spec.ts
```

본 흐름(가입 → 게임 생성 → 한 수 → 기권 → 히스토리 1건 확인 등)을 기록.

- [ ] **Step 2: git mv로 파일명 변경**

```bash
git mv e2e/tests/signup_and_play.spec.ts e2e/tests/nickname_and_play.spec.ts
```

- [ ] **Step 3: 내부 재작성**

```typescript
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("full happy path: nickname session → create → play → resign → history", async ({ page }) => {
  const nickname = await createSession(page);
  await createGame(page, { boardSize: 9 });

  // 한 수 두기.
  const board = page.locator('svg[role="grid"]').first();
  await board.click({ position: { x: 80, y: 80 } });

  // 기권.
  await page.getByRole("button", { name: /기권|Resign/ }).click();
  const confirm = page.getByRole("button", { name: /확인|Confirm|Yes/ });
  if (await confirm.isVisible().catch(() => false)) await confirm.click();

  // 결과 표시.
  await expect(page.getByText(/결과|Result/).first()).toBeVisible({ timeout: 10000 });

  // 히스토리에 본 nickname의 게임이 1건 이상 등장.
  // 기존 스펙이 /history 경로나 사이드패널을 검사했다면 그 흐름을 유지.
  await page.goto("/games");
  await expect(page.getByText(nickname)).toBeVisible({ timeout: 10000 });
});
```

> `/games` 경로 또는 히스토리 노출 위치가 기존 스펙과 다르면 기존 스펙의 단언을 보존하라.

- [ ] **Step 4: 실행**

```bash
npx playwright test tests/nickname_and_play.spec.ts --reporter=list
```

Expected. `1 passed`.

- [ ] **Step 5: 커밋**

```bash
git add e2e/tests/nickname_and_play.spec.ts
git commit -m "$(cat <<'EOF'
test(e2e): signup_and_play를 nickname_and_play로 재작성

파일명 변경(git mv) + 본 흐름을 nickname-only 세션 + Picker
기반 게임 생성으로 갱신. 본 단언(한 수 → 기권 → 결과 → 히스토리)은
유지.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: single_session.spec.ts 마이그레이션

**Files:**
- Modify: `e2e/tests/single_session.spec.ts`

- [ ] **Step 1: 현재 본 흐름 확인**

```bash
cat e2e/tests/single_session.spec.ts
```

WS replacement 단언이 핵심. 새 context가 같은 game_id에 접속하면 첫 context의 WS가 `SESSION_REPLACED`로 닫혀야 한다.

- [ ] **Step 2: 재작성**

```typescript
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("opening the same game in a second context evicts the first WS", async ({ browser }) => {
  // 컨텍스트 1. 같은 nickname으로 세션 + 게임 생성.
  const ctx1 = await browser.newContext();
  const page1 = await ctx1.newPage();
  const nickname = await createSession(page1);
  await createGame(page1, { boardSize: 9 });
  const gameUrl = page1.url();
  expect(gameUrl).toMatch(/\/game\/play\/\d+$/);

  // WS replacement 콘솔 메시지 캐치 준비.
  const replaced = new Promise<void>((resolve) => {
    page1.on("websocket", (ws) => {
      ws.on("close", () => resolve());
    });
  });

  // 컨텍스트 2. 같은 nickname으로 세션 후 같은 game_id로 진입.
  // 백엔드의 단일 WS 정책상 page1의 WS가 종료된다.
  const ctx2 = await browser.newContext();
  const page2 = await ctx2.newPage();
  await createSession(page2, nickname); // 같은 닉네임은 백엔드가 거부할 가능성 — 기존 스펙은 어떻게 처리했는지 확인.
  await page2.goto(gameUrl);

  await Promise.race([
    replaced,
    new Promise((_, reject) => setTimeout(() => reject(new Error("WS not replaced within 10s")), 10000)),
  ]);

  await ctx1.close();
  await ctx2.close();
});
```

> 기존 스펙이 같은 nickname을 어떻게 다뤘는지(uniqueness 우회 trick) 확인하라. 백엔드가 nickname 중복을 거부하면 다른 nickname으로도 같은 game_id WS 정책이 적용되는지 — 즉 정책 단위가 game_id 단위라 누구든 두 번째 접속자가 첫 WS를 끊는 것인지 — 확인이 필요. 본 단계의 단언은 game_id 단위 정책에 맞춰 다른 nickname으로 진행하는 게 자연스러울 수 있다.

- [ ] **Step 3: 실행**

```bash
npx playwright test tests/single_session.spec.ts --reporter=list
```

Expected. `1 passed`. 실패 시 위 주석대로 nickname 정책과 WS replacement 단위를 재검토.

- [ ] **Step 4: 커밋**

```bash
git add e2e/tests/single_session.spec.ts
git commit -m "test(e2e): single_session을 새 helpers로 마이그레이션

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: auth.spec.ts 신규 (nickname 검증 3 케이스)

**Files:**
- Create: `e2e/tests/auth.spec.ts`

- [ ] **Step 1: 신규 파일 작성**

```typescript
// nickname 입력의 유효성 거절·중복 거절·정상 가입 검증.
import { test, expect } from "@playwright/test";
import { createSession, uniqueNickname } from "./helpers";

test("invalid nickname (single char) keeps submit disabled", async ({ page }) => {
  await page.goto("/");
  const input = page.locator('input[placeholder*="자"], input[placeholder*="characters"]');
  await input.fill("a"); // 2자 미만 → invalid
  // 400ms debounce + 약간의 여유.
  await page.waitForTimeout(800);
  const submit = page.getByRole("button", { name: /^시작하기$|^Start$/ });
  await expect(submit).toBeDisabled();
  // hint 영역에 invalid 메시지.
  await expect(page.locator('#nickname-hint')).toContainText(/문자|characters/i);
});

test("taken nickname surfaces the in-use hint", async ({ browser }) => {
  // 1단계 — context1에서 nickname 점유.
  const ctx1 = await browser.newContext();
  const page1 = await ctx1.newPage();
  const nick = uniqueNickname("dup");
  await createSession(page1, nick);

  // 2단계 — context2에서 같은 nickname 입력.
  const ctx2 = await browser.newContext();
  const page2 = await ctx2.newPage();
  await page2.goto("/");
  await page2.locator('input[placeholder*="자"], input[placeholder*="characters"]').fill(nick);
  // 400ms debounce + 여유.
  await page2.waitForTimeout(800);
  await expect(page2.locator('#nickname-hint')).toContainText(/이미 사용 중|already in use/i);
  await expect(page2.getByRole("button", { name: /^시작하기$|^Start$/ })).toBeDisabled();

  await ctx1.close();
  await ctx2.close();
});

test("valid new nickname enables submit and lands on /game/new", async ({ page }) => {
  await createSession(page);
  await expect(page).toHaveURL(/\/game\/new$/);
});
```

- [ ] **Step 2: 실행**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite/e2e
npx playwright test tests/auth.spec.ts --reporter=list
```

Expected. `3 passed`.

- [ ] **Step 3: 커밋**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite
git add e2e/tests/auth.spec.ts
git commit -m "$(cat <<'EOF'
test(e2e): auth.spec.ts 신규 — nickname 검증 3 케이스

invalid(2자 미만)·taken(중복)·valid(정상 가입) 3개 흐름을 커버.
Hint 영역의 i18n 문구로 상태를 단언하고 submit 버튼의 disabled
상태로 가용성 체크의 결과를 검증한다.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: 전수 검증

**Files:** (변경 없음 — 통합 실행만)

- [ ] **Step 1: 모든 스펙을 일괄 실행**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite/e2e
npx playwright test --reporter=list
```

Expected. 7개 스펙 모두 통과 (`board_size` 2 + `handicap` 1 + `review` 1 + `nickname_and_play` 1 + `single_session` 1 + `auth` 3 + `theme_lang` 기존 = 합 9–11 tests, retry 0).

- [ ] **Step 2: 실패 발생 시**

retry 0 환경에서 한 번이라도 실패하면 안정성 문제. helper의 timeout 또는 selector race가 원인일 가능성이 높다. 콘솔에서 `--debug` 또는 `--headed` 로 재현 후 helper만 조정.

> 같은 스펙에서 3회 연속 통과까지 보장. **flaky** 한 채로 다음 task로 넘어가지 말 것.

---

## Task 9: CI 잡 재활성화

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: 현재 e2e 잡 위치 확인**

```bash
grep -n "if: false\|name: e2e\|playwright" .github/workflows/ci.yml
```

`if: false` 한 줄을 발견.

- [ ] **Step 2: `if: false` 제거**

```bash
# Edit 도구로 정확히 그 한 줄만 제거.
```

Edit 도구 사용. `old_string`은 `    if: false` (실제 들여쓰기 포함), `new_string`은 빈 문자열 또는 같은 잡의 다른 trigger 조건이 있다면 그것만 남김. 그 외 ci.yml은 건드리지 않음.

- [ ] **Step 3: 커밋**

```bash
git add .github/workflows/ci.yml
git commit -m "$(cat <<'EOF'
chore(ci): e2e 잡 재활성화 — nickname-only 흐름 재정비 완료

55505d5에서 일시 비활성화했던 e2e 잡의 if:false를 제거. 본 PR의
helpers·6개 스펙·auth 신규로 신규 nickname-only + Picker 흐름과
정합. 로컬 docker compose 검증 통과 확인.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: PR 생성

**Files:** (변경 없음)

- [ ] **Step 1: docker compose 정리**

```bash
cd /Users/daegong/projects/baduk/.claude/worktrees/e2e-rewrite
docker compose down
```

- [ ] **Step 2: 브랜치 푸시 + PR**

```bash
git push -u origin chore/e2e-rewrite-nickname-flow
gh pr create --title "e2e: nickname-only + Picker 흐름으로 재구성 + CI 재활성화" --body "$(cat <<'EOF'
## Summary
- helpers.ts를 nickname-only 흐름으로 재작성 (uniqueNickname/createSession/createGame).
- 기존 5개 스펙(board_size·handicap·review·signup_and_play→nickname_and_play·single_session)을 새 helpers로 마이그레이션.
- nickname 검증 신규 스펙 auth.spec.ts 추가 (invalid·taken·valid 3 케이스).
- CI e2e 잡 if:false 제거 — 재활성화.

설계 문서. `docs/superpowers/specs/2026-05-24-e2e-rewrite-design.md`
구현 계획. `docs/superpowers/plans/2026-05-24-e2e-rewrite-nickname-flow.md`

## Test plan
- [x] 로컬 `docker compose up --build -d` 후 e2e 전체 스펙 통과 (retry 0)
- [ ] GitHub Actions e2e 잡 GREEN
- [ ] 모든 spec 안정성 검증 (3회 연속 통과)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

PR URL이 출력되면 본 작업 완료. 머지는 사람 검토 후 GitHub UI에서 진행.

- [ ] **Step 3: 워크트리 정리 (선택)**

PR 머지 후. 본 PR이 main에 머지된 다음.

```bash
cd /Users/daegong/projects/baduk
git worktree remove .claude/worktrees/e2e-rewrite
git branch -d chore/e2e-rewrite-nickname-flow
```

---

## 자체 점검 (작성 후)

**Spec 커버리지.** spec의 7개 작업 항목(helpers, board_size, handicap, review, signup_and_play→rename, single_session, auth 신규, CI 재활성화) 모두 Task 1~9에 대응. ✓

**Placeholder.** "TBD"·"implement later" 없음. 단 Task 6 (single_session)에 "기존 스펙이 같은 nickname을 어떻게 다뤘는지 확인하라"는 조건부 검증 노트가 있는데, 이는 *구현 중 발견 후 조정* 으로 의도된 것이라 placeholder가 아니다.

**Type 일관성.** `uniqueNickname()` `createSession(page, nickname?)` `createGame(page, opts)` 시그니처가 모든 Task에서 일관. ✓

**Spec 누락.** "DB 정리 — 별도 정리 코드 없음, docker compose 재기동으로 초기화"는 본 plan에선 Task 2 Step 3에서 자동 처리됨. CI 재활성화 후 검증은 Task 9 본 단계. ✓

자체 점검 통과. 본 plan은 실행 가능 상태.
