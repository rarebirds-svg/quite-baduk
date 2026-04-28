import { expect, test } from "@playwright/test";
import { createGame, resign } from "./helpers";

test("review page loads and analyze button works", async ({ page }) => {
  await page.goto("/game/new");
  await createGame(page, { rank: "5k", handicap: 0 });

  // Resign through the confirm dialog so we have a finished game in history.
  await resign(page);
  await page.waitForTimeout(500);

  // History → review link.
  await page.goto("/history");
  await page.locator("a", { hasText: /review/i }).first().click();
  await expect(page.locator("svg[role='grid']")).toBeVisible();

  // Analyze — i18n key `review.analyze`: "분석" / "Analyze".
  await page.getByRole("button", { name: /^분석$|^Analyze$/ }).click();
  // Analysis is asynchronous — give the engine a beat.
  await page.waitForTimeout(1500);
});
