import { test, expect } from "@playwright/test";
import { randomEmail, signup, createGame } from "./helpers";

test("signup and create a 9x9 game, verify board aria label", async ({ page }) => {
  const email = randomEmail("bs9");
  await signup(page, email);
  await createGame(page, { rank: "5k", handicap: 0, boardSize: 9 });

  // Board SVG should have aria-label indicating 9x9
  await expect(page.locator("svg[aria-label='9x9 Go board']")).toBeVisible();
});

test("create a 13x13 game via the picker", async ({ page }) => {
  const email = randomEmail("bs13");
  await signup(page, email);
  await createGame(page, { rank: "5k", handicap: 0, boardSize: 13 });

  await expect(page.locator("svg[aria-label='13x13 Go board']")).toBeVisible();
});
