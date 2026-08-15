// 원클릭 시작(QuickStart)의 형식 검증·2클릭 대국 진입·같은 닉네임 공존 3개 경로 검증.
import { test, expect } from "@playwright/test";
import { NICKNAME_INPUT, quickStart, uniqueNickname } from "./helpers";

const PLAY_BUTTON_NAME = /바로 두기|Play now/;
const HINT = "#quickstart-hint";

test("invalid nickname (single char) keeps the play button disabled", async ({ page }) => {
  await page.goto("/");
  await page.locator(NICKNAME_INPUT).fill("a"); // 2자 미만 → 형식 불충족
  await expect(page.getByRole("button", { name: PLAY_BUTTON_NAME })).toBeDisabled();
  await expect(page.locator(HINT)).toContainText(/문자|characters/i);
});

test("nickname + one click lands on the board", async ({ page }) => {
  await quickStart(page);
  await expect(page.locator("svg[aria-label*='Go board']")).toBeVisible();
});

test("the same nickname now gives each visitor their own session", async ({ browser }) => {
  // 중복 확인이 폐지되어 같은 닉네임이 공존한다 — 두 컨텍스트 모두 대국까지 간다.
  const nick = uniqueNickname("dup");

  const ctx1 = await browser.newContext();
  const page1 = await ctx1.newPage();
  await quickStart(page1, nick);
  const url1 = page1.url();

  const ctx2 = await browser.newContext();
  const page2 = await ctx2.newPage();
  await quickStart(page2, nick);
  const url2 = page2.url();

  // 각자 다른 대국 id — 세션이 공유되지 않았다는 뜻.
  expect(url1).not.toBe(url2);

  await ctx1.close();
  await ctx2.close();
});

test("returning visitor sees a one-button start instead of the nickname field", async ({ page }) => {
  await quickStart(page);
  await page.goto("/");
  // 세션이 있으면 입력창 없이 "바로 한 판" 버튼만 보인다.
  await expect(page.locator(NICKNAME_INPUT)).toHaveCount(0);
  const again = page.getByRole("button", { name: /바로 한 판|Play a game/ });
  await expect(again).toBeEnabled();
  await again.click();
  await expect(page).toHaveURL(/\/game\/play\/\d+$/, { timeout: 30000 });
});
