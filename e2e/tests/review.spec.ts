import { test, expect } from "@playwright/test";
import { randomEmail, signup, createGame } from "./helpers";

test("review page loads and analyze button works", async ({ page }) => {
  const email = randomEmail("rev");
  await signup(page, email);
  await createGame(page, { rank: "5k", handicap: 0 });

  // Resign so we have a finished game
  await page.getByRole("button", { name: /resign|기권/i }).click();
  await page.waitForTimeout(500);

  // Navigate to history and click review
  await page.goto("/history");
  const reviewLink = page.locator("a", { hasText: /review/i }).first();
  await reviewLink.click();
  await expect(page.locator("svg[role='grid']")).toBeVisible();

  // Click analyze
  await page.getByRole("button", { name: /analyze|분석/i }).click();
  // Analysis result block may take a moment
  await page.waitForTimeout(1500);
});
