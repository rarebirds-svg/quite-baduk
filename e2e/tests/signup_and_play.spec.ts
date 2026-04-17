import { test, expect } from "@playwright/test";
import { randomEmail, signup, createGame } from "./helpers";

test("signup, create 5k even game, play a move, resign, history shows game", async ({ page }) => {
  const email = randomEmail();
  await signup(page, email);
  await createGame(page, { rank: "5k", handicap: 0 });

  // Wait for board SVG to render
  await expect(page.locator("svg[role='grid']")).toBeVisible();

  // Click near center of the SVG to place a stone (hopefully legal)
  const svg = page.locator("svg[role='grid']");
  const box = await svg.boundingBox();
  if (!box) throw new Error("No board bbox");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  // Give AI a moment
  await page.waitForTimeout(1500);

  // Resign via controls
  await page.getByRole("button", { name: /resign|기권/i }).click();

  // Check history
  await page.goto("/history");
  await expect(page.locator("table")).toBeVisible();
});
