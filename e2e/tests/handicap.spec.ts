import { test, expect } from "@playwright/test";
import { randomEmail, signup, createGame } from "./helpers";

test("4-stone handicap creates game with handicap=4", async ({ page }) => {
  const email = randomEmail("ha");
  await signup(page, email);
  await createGame(page, { rank: "1d", handicap: 4 });
  await expect(page).toHaveURL(/\/game\/play\/\d+/);
  // Board renders
  await expect(page.locator("svg[role='grid']")).toBeVisible();
});
