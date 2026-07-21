// 9x9·13x13 보드 크기 생성과 SVG 렌더링 단언 — 신규 nickname 흐름.
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("9x9 game can be created and renders the smaller board", async ({ page }) => {
  await createSession(page);
  await createGame(page, { boardSize: 9 });

  // interactive 대국판은 aria-label에 키보드 힌트가 접미(e6b139c)되므로 크기 접두 매치로 확인.
  await expect(page.locator("svg[aria-label^='9×9 Go board']")).toBeVisible();
});

test("13x13 game can be created and renders the medium board", async ({ page }) => {
  await createSession(page);
  await createGame(page, { boardSize: 13 });

  await expect(page.locator("svg[aria-label^='13×13 Go board']")).toBeVisible();
});
