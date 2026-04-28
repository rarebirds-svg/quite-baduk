import { expect, test } from "@playwright/test";
import { createGame } from "./helpers";

test("4-stone handicap creates game with handicap=4", async ({ page }) => {
  await page.goto("/game/new");
  await createGame(page, { rank: "1d", handicap: 4 });
  await expect(page).toHaveURL(/\/game\/play\/\d+/);
  await expect(page.locator("svg[role='grid']")).toBeVisible();
});
