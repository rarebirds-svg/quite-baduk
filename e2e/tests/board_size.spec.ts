import { expect, test } from "@playwright/test";
import { createGame } from "./helpers";

// `globalSetup` already signed up a shared user and stashed cookies in
// `tests/.auth/user.json`; every test below starts authenticated and
// drives `/game/new` directly.

test("create a 9×9 game, verify board aria label", async ({ page }) => {
  await page.goto("/game/new");
  await createGame(page, { rank: "5k", handicap: 0, boardSize: 9 });
  // Post-uplift Board.tsx labels with U+00D7 (×), not ASCII 'x'.
  await expect(page.locator("svg[aria-label='9×9 Go board']")).toBeVisible();
});

test("create a 13×13 game via the picker", async ({ page }) => {
  await page.goto("/game/new");
  await createGame(page, { rank: "5k", handicap: 0, boardSize: 13 });
  await expect(page.locator("svg[aria-label='13×13 Go board']")).toBeVisible();
});
