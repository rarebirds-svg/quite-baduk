import { expect, test } from "@playwright/test";
import { createGame } from "./helpers";

test("opening the same game in a second tab loads the board", async ({ page }) => {
  // Same browser context already holds the shared session cookie thanks to
  // globalSetup, so opening a new tab in the same context is the natural
  // way to trigger the SESSION_REPLACED eviction inside the WS handler.
  await page.goto("/game/new");
  await createGame(page, { rank: "5k", handicap: 0 });
  const url = page.url();

  const second = await page.context().newPage();
  try {
    await second.goto(url);
    await expect(second.locator("svg[role='grid']")).toBeVisible();
    // The eviction toast on `page` is a soft signal; we don't pin it down
    // here since the WS layer races the visible UI.
  } finally {
    await second.close();
  }
});
