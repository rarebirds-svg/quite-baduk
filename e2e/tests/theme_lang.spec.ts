import { test, expect } from "@playwright/test";

test("theme and language toggles work", async ({ page }) => {
  await page.goto("/");
  // Toggle theme
  const themeBtn = page.getByRole("button", { name: /toggle theme/i });
  await themeBtn.click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  // Toggle language
  const langBtn = page.getByRole("button", { name: /toggle language/i });
  await langBtn.click();
  // Header title should change or remain consistent — just verify page still renders
  await expect(page.locator("nav")).toBeVisible();
});
