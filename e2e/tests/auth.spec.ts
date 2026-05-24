// nickname 입력의 유효성·중복·정상 가입 3개 경로 검증.
import { test, expect } from "@playwright/test";
import { createSession, uniqueNickname } from "./helpers";

const NICKNAME_INPUT = 'input[placeholder*="2–32"]';
const SUBMIT_BUTTON_NAME = /^시작하기$|^Start$/;
const HINT = "#nickname-hint";

test("invalid nickname (single char) keeps submit disabled with invalid hint", async ({ page }) => {
  await page.goto("/");
  await page.locator(NICKNAME_INPUT).fill("a"); // 2자 미만 → invalid
  // 400ms debounce + 여유.
  await page.waitForTimeout(800);
  await expect(page.getByRole("button", { name: SUBMIT_BUTTON_NAME })).toBeDisabled();
  await expect(page.locator(HINT)).toContainText(/문자|characters/i);
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
  await page2.locator(NICKNAME_INPUT).fill(nick);
  await page2.waitForTimeout(800);
  await expect(page2.locator(HINT)).toContainText(/이미 사용 중|already in use/i);
  await expect(page2.getByRole("button", { name: SUBMIT_BUTTON_NAME })).toBeDisabled();

  await ctx1.close();
  await ctx2.close();
});

test("valid new nickname enables submit and lands on /game/new", async ({ page }) => {
  await createSession(page);
  await expect(page).toHaveURL(/\/game\/new$/);
});
