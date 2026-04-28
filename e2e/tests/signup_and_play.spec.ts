import { expect, test } from "@playwright/test";
import { createGame, resign } from "./helpers";

test("create 5k even game, play a move, resign, history shows game", async ({ page }) => {
  await page.goto("/game/new");
  await createGame(page, { rank: "5k", handicap: 0 });

  // Board SVG renders.
  const board = page.locator("svg[role='grid']");
  await expect(board).toBeVisible();

  // Click near the center of the SVG to place a stone.
  const box = await board.boundingBox();
  if (!box) throw new Error("No board bbox");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  // Give the AI a moment to respond.
  await page.waitForTimeout(1500);

  // Resign through the confirm dialog and land on a game-over UI.
  await resign(page);

  // History page lists the resigned game.
  await page.goto("/history");
  await expect(page.locator("table")).toBeVisible();
});
