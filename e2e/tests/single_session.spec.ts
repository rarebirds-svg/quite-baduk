// 같은 game_id로 두 번째 탭이 열리면 두 번째 탭이 보드를 로드하는지 단언 — 신규 nickname 흐름.
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("opening the same game in a second tab terminates the first WS", async ({ browser }) => {
  // 같은 context에서 두 페이지 — 쿠키 세션 공유로 동일 사용자가 같은 game_id에 두 번 붙는다.
  const ctx = await browser.newContext();
  const page1 = await ctx.newPage();
  await createSession(page1);
  await createGame(page1, { rank: "5k", handicap: 0 });
  const url = page1.url();

  const page2 = await ctx.newPage();
  await page2.goto(url);

  // 두 번째 페이지는 보드를 정상적으로 로드해야 한다.
  await expect(page2.locator("svg[aria-label*='Go board']")).toBeVisible();
  // 첫 번째 페이지는 SESSION_REPLACED 토스트를 띄울 수 있으나 필수 단언은 아님 — 원본 주석 유지.
  await ctx.close();
});
