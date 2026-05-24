// nickname-only 세션 가입 → 5k 호선 게임 생성 → 한 수 → 기권 → 히스토리 단언 — 전체 happy path.
import { test, expect } from "@playwright/test";
import { createSession, createGame } from "./helpers";

test("nickname session, create 5k even game, play a move, resign, history shows game", async ({ page }) => {
  await createSession(page);
  await createGame(page, { rank: "5k", handicap: 0 });

  // 보드 SVG 렌더 단언 — 원본 유지.
  await expect(page.locator("svg[aria-label*='Go board']")).toBeVisible();

  // 보드 중앙을 클릭해 한 수 두기 — 원본 좌표 계산 유지.
  const svg = page.locator("svg[aria-label*='Go board']");
  const box = await svg.boundingBox();
  if (!box) throw new Error("No board bbox");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  // AI 응수 대기 — 원본 유지.
  await page.waitForTimeout(1500);

  // 컨트롤의 기권 — 원본 셀렉터 유지.
  await page.getByRole("button", { name: /resign|기권/i }).click();

  // 히스토리 확인 — 원본 단언 유지.
  await page.goto("/history");
  await expect(page.locator("table")).toBeVisible();
});
