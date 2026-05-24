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
  const input = page.locator('input[placeholder*="2–32"]');
  await input.fill(nickname);
  const submit = page.getByRole("button", { name: /^시작하기$|^Start$/ });
  // 400ms debounce 가용성 체크 → 버튼 disabled가 풀릴 때까지 대기.
  await expect(submit).toBeEnabled({ timeout: 5000 });
  await submit.click();
  await expect(page).toHaveURL(/\/game\/new$/);
  return nickname;
}

export interface CreateGameOpts {
  aiPlayer?: RegExp | string;
  rank?: string;
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
    await page.getByRole("radiogroup", { name: /상대|opponent/i }).getByRole("radio").first().click();
  }

  const start = page.getByRole("button", { name: /^대국 시작$|^Start$/ });
  await expect(start).toBeEnabled({ timeout: 5000 });
  await start.click();
  await expect(page).toHaveURL(/\/game\/play\/\d+$/);
}
