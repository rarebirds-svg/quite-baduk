# e2e 스펙 재구성 — nickname-only + Picker 흐름 (2026-05-24)

## 배경

`e2e/` Playwright 스위트는 2026-05-23 커밋 `55505d5 chore(ci): e2e 잡 일시 disable`로 CI 잡이 `if: false`로 비활성화돼 있다. 이유는 헬퍼·스펙이 옛 인증 흐름(이메일 + 비밀번호 + `/signup` 페이지)을 가정하지만, 본 앱은 spec `2026-04-22-ephemeral-nickname-auth-design.md` 이후 **닉네임 단일 입력 + 커스텀 Picker 4종**(PlayerPicker / RankPicker / BoardSizePicker / HandicapPicker) 흐름으로 이동했기 때문이다. 본 spec은 e2e 스위트를 현 흐름에 정합하게 재작성하고 CI 잡을 재활성화하는 것을 목표로 한다.

## 목표

- 기존 5개 스펙(`board_size`, `handicap`, `review`, `signup_and_play`, `single_session`)을 신규 흐름으로 재작성.
- 신규 `auth.spec.ts` 1개 추가 — 닉네임 검증 3개 경로(유효성 거절·중복 거절·정상 가입).
- `theme_lang.spec.ts`는 인증 무관이므로 수정 없음.
- `.github/workflows/ci.yml`의 e2e 잡 `if: false` 제거.
- 모든 작업은 단일 PR(브랜치 `chore/e2e-rewrite-nickname-flow`)로 묶는다.

## 비목표 (YAGNI)

- 신규 시나리오 대규모 확장 — 위 1개 외 추가 안 함.
- `tests/.auth/user.json` storageState 패턴 부활 — nickname-only 흐름은 동적 nickname이 자연스러움.
- `e2e/scripts/spectate-qa.mjs`와의 헬퍼 통합 — 본 작업 범위 밖.
- Playwright timeout·retry·project 매트릭스 변경 — bee8bbf의 `120000ms`는 유효.

## 아키텍처

### 작업 단위

- `e2e/tests/helpers.ts` — 1개 파일 전면 재작성. 구식 `signup()` / `createGame()` 제거, 신규 `uniqueNickname()` / `createSession()` / `createGame()` 도입.
- 5개 기존 스펙 — 헬퍼 호출부만 갱신, 본 단언(돌 두기 · 기권 · WS 교체 등)은 유지.
- `e2e/tests/auth.spec.ts` — 신규 추가, 3개 `test()` 블록.
- `e2e/tests/signup_and_play.spec.ts` → `nickname_and_play.spec.ts` 파일명 변경.
- `.github/workflows/ci.yml` — 1줄 변경(`if: false` 제거).

### 브랜치·커밋 단위

브랜치 `chore/e2e-rewrite-nickname-flow`, 점진 4커밋.

1. `test(e2e): helpers nickname-only 흐름으로 재작성`
2. `test(e2e): board_size·handicap·review를 새 helpers로 마이그레이션`
3. `test(e2e): nickname_and_play·single_session 재작성 + auth.spec.ts 신규`
4. `chore(ci): e2e 잡 재활성화`

각 커밋 후 로컬 `docker compose up --build -d` + 해당 스펙만 `npx playwright test tests/<name>.spec.ts` 실행으로 통과 확인 후 다음 단계 진행.

## helpers.ts API

```typescript
// e2e 테스트의 nickname-only 세션 생성·게임 생성 헬퍼.
import { expect, type Page } from "@playwright/test";

export function uniqueNickname(prefix = "qa"): string {
  // 32자 한계 — prefix(<=10) + ts(13) + suffix(<=5) ≈ 28자.
  const ts = Date.now().toString(36);
  const rnd = Math.random().toString(36).slice(2, 6);
  return `${prefix}_${ts}_${rnd}`;
}

export async function createSession(
  page: Page,
  nickname: string = uniqueNickname(),
): Promise<string> {
  await page.goto("/");
  await page.fill('input[name="nickname"], input[placeholder*="닉네임"]', nickname);
  const submit = page.getByRole("button", { name: /시작|start|continue/i });
  // debounce 가용성 체크 → 버튼이 enabled로 전환될 때까지 대기.
  await expect(submit).toBeEnabled({ timeout: 5000 });
  await submit.click();
  await expect(page).toHaveURL(/\/game\/new$/);
  return nickname;
}

export interface CreateGameOpts {
  aiPlayer?: string;   // PlayerPicker label 정규식 매칭
  rank?: string;       // 예: "5d"
  boardSize?: 9 | 13 | 19;
  handicap?: 0 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;
  userColor?: "black" | "white";
}

export async function createGame(page: Page, opts: CreateGameOpts = {}): Promise<void> {
  await expect(page).toHaveURL(/\/game\/new$/);
  if (opts.boardSize) {
    await page.getByRole("button", { name: new RegExp(`^${opts.boardSize}\\s*[x×]\\s*${opts.boardSize}$`) }).click();
  }
  if (opts.rank) {
    await page.getByRole("button", { name: new RegExp(`^${opts.rank}$`, "i") }).click();
  }
  if (opts.handicap !== undefined) {
    await page.getByRole("button", { name: new RegExp(`^${opts.handicap}(\\s|$)|돌\\s*${opts.handicap}|^없음$`, "i") }).click();
  }
  if (opts.aiPlayer) {
    await page.getByRole("button", { name: new RegExp(opts.aiPlayer, "i") }).click();
  }
  await page.getByRole("button", { name: /^시작$|^start game$|대국 시작/i }).click();
  await expect(page).toHaveURL(/\/game\/play\/\d+$/);
}
```

Picker 컴포넌트의 정확한 ARIA name·DOM 구조는 구현 단계에서 확인해 조정한다. 위 정규식은 합리적 추정이며 실제 셀렉터는 첫 스펙 마이그레이션(`board_size`) 중 확정한다.

## 스펙별 마이그레이션 매핑

| 기존 | 신규 | 변경 |
|---|---|---|
| `signup_and_play.spec.ts` | `nickname_and_play.spec.ts` | 파일명 변경. `signup()` → `createSession()` + `createGame()`. 본 흐름(가입·생성·플레이·기권·히스토리) 유지 |
| `board_size.spec.ts` | (이름 유지) | `createSession()` + `createGame({boardSize: 9})` / `({boardSize: 13})` |
| `handicap.spec.ts` | (이름 유지) | `createSession()` + `createGame({handicap: 4})` |
| `review.spec.ts` | (이름 유지) | `createSession()` + `createGame()` + 종국 후 review 페이지 진입 |
| `single_session.spec.ts` | (이름 유지) | 두 context 모두 `createSession()` 호출 후 같은 `game_id` 진입. WS replacement 단언 유지 |
| 신규 | `auth.spec.ts` | 3 케이스. ①유효성 거절(특수문자 → 버튼 disabled). ②중복 거절(선행 세션과 동일 nickname → "이미 사용 중" 표시). ③정상 가입 후 새로고침해도 `/game/new` 유지 |
| `theme_lang.spec.ts` | (수정 없음) | 인증 무관 |

## 데이터 흐름

```
playwright test 시작
  ↓
각 test() 시작 → new browser context (cookie 격리)
  ↓
createSession(page) → uniqueNickname() 생성 → POST /api/session
  ↓
HttpOnly cookie 설정 → 자동 /game/new 이동
  ↓
createGame(page, opts) → Picker 4개 선택 → 시작 버튼 → POST /api/games
  ↓
/game/play/{id} 도달 → 테스트 본문(돌 두기, 기권 등)
```

### 격리

각 `test()` 블록은 Playwright의 새 context를 받으므로 nickname 충돌 없음. 매 test가 새 nickname 생성.

### DB 정리

별도 정리 코드 없음. 로컬·CI 모두 매 실행 `docker compose up --build -d`로 컨테이너·DB가 새로 빌드돼 자동 초기화된다.

## 에러 처리·안정성

- **Picker 셀렉터 미스매치** — 첫 스펙 마이그레이션에서 발견 시 `web/components/`의 실제 DOM을 점검해 helper 정규식 조정. 1회성 작업.
- **debounce 가용성 체크 race** — `expect(submit).toBeEnabled({timeout: 5000})`로 안전 대기. nickname-only 흐름의 debounce는 400ms이므로 5s 여유는 충분.
- **nickname 중복 우연 충돌** — `Date.now().toString(36) + 4자 random`으로 사실상 0.
- **Playwright timeout** — `playwright.config.ts`의 `120000ms` 유지. bee8bbf 커밋(60s→120s)의 사유(컨테이너 cold start)는 변경 없음.

## 검증 기준

1. 로컬 `docker compose up --build -d` 후 `cd e2e && npx playwright test`가 6개 spec 모두 통과(theme_lang 포함).
2. `.github/workflows/ci.yml`에서 `if: false` 제거 후 PR을 열어 GitHub Actions e2e 잡이 GREEN.
3. 누락·skip된 test 없음. retry 0으로도 안정.

## 위험·미해결

- **PlayerPicker DOM 구조 미확인** — 헬퍼의 ARIA name 매칭이 실제와 다를 가능성. 첫 스펙에서 발견 시 helper 조정. 위험도 낮음.
- **`tests/.auth/user.json` 잔존** — 더 이상 사용 안 함. 정리 권장하지만 본 작업에 포함하지 않음 (CLAUDE.md §3 외과적 변경).
- **`spectate-qa.mjs`와의 중복** — 자체 nickname 세션 로직을 보유한 별도 스크립트. 본 helper와 통합 가능하나 작업 범위 밖.

## 추정

helpers 재작성 15m + 스펙 5개 마이그레이션 ~50m + `auth.spec.ts` 신규 20m + CI 5m = **약 90분**.
