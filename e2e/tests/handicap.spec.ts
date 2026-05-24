// 4점 핸디캡 게임 생성 후 화점에 흑돌 4개 배치되는지 단언 — 신규 nickname 흐름.
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("4-stone handicap creates game with handicap=4", async ({ page }) => {
  await createSession(page);
  await createGame(page, { boardSize: 19, handicap: 4 });

  // URL 패턴과 보드 SVG 가시성 — 원본 단언 유지.
  await expect(page).toHaveURL(/\/game\/play\/\d+/);
  await expect(page.locator("svg[role='grid']")).toBeVisible();

  // 핸디캡 4 → 보드에 흑돌 4개. Board.tsx는 <circle data-stone="B"|"W"/>로 그린다.
  const blackStones = page.locator('svg[role="grid"] circle[data-stone="B"]');
  await expect(blackStones).toHaveCount(4, { timeout: 10000 });
});
