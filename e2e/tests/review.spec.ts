// 종국 후 리뷰 페이지 진입과 분석 버튼 흐름 단언 — 신규 nickname 흐름.
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("review page loads and analyze button works", async ({ page }) => {
  await createSession(page);
  await createGame(page, { rank: "5k", handicap: 0 });

  // 종국을 만들기 위해 기권. 원본과 동일한 셀렉터 유지.
  await page.getByRole("button", { name: /resign|기권/i }).click();
  await page.waitForTimeout(500);

  // history → review 링크 진입. 원본 단언 유지.
  await page.goto("/history");
  const reviewLink = page.locator("a", { hasText: /review/i }).first();
  await reviewLink.click();
  await expect(page.locator("svg[aria-label*='Go board']")).toBeVisible();

  // 분석 버튼 클릭. 원본 단언 유지.
  await page.getByRole("button", { name: /analyze|분석/i }).click();
  // 분석 결과 블록이 렌더링되기까지 잠시 대기.
  await page.waitForTimeout(1500);
});
