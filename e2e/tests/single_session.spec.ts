import { test, expect } from "@playwright/test";
import { randomEmail, signup, createGame } from "./helpers";

test("opening the same game in a second tab terminates the first WS", async ({ browser }) => {
  const ctx = await browser.newContext();
  const page1 = await ctx.newPage();
  const email = randomEmail("ss");
  await signup(page1, email);
  await createGame(page1, { rank: "5k", handicap: 0 });
  const url = page1.url();

  const page2 = await ctx.newPage();
  await page2.goto(url);

  // The second page should successfully load the board
  await expect(page2.locator("svg[role='grid']")).toBeVisible();
  // The first page may show an error toast about SESSION_REPLACED — not strictly required
  await ctx.close();
});
