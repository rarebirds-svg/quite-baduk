import { expect, test } from "@playwright/test";

test("theme cycle puts html into dark mode", async ({ page }) => {
  // TopNav (which hosts the toggles) is hidden on `/` — go to `/game/new`
  // (storageState makes us already authenticated) so it's mounted.
  await page.goto("/game/new");

  // The theme button cycles light → dark → system → light. Click until the
  // resolved theme paints `dark` on <html> so the test is independent of
  // the user agent's preferred-color-scheme.
  const themeBtn = page.getByRole("button", { name: /^Theme:/i });
  for (let i = 0; i < 4; i++) {
    if (await page.locator("html.dark").count()) break;
    await themeBtn.click();
    await page.waitForTimeout(50);
  }
  await expect(page.locator("html")).toHaveClass(/dark/);
});

test("language toggle flips the EN/KO label", async ({ page }) => {
  await page.goto("/game/new");

  const langBtn = page.getByRole("button", { name: "Toggle language" });
  await expect(langBtn).toBeVisible();
  // The button label is the *target* locale (so "EN" means the page is in
  // ko and a click switches to en, and vice versa). After one click the
  // label must flip — that's enough to confirm the toggle is wired up.
  const before = (await langBtn.textContent())?.trim();
  await langBtn.click();
  await expect(langBtn).not.toHaveText(new RegExp(`^${before}$`));
});
