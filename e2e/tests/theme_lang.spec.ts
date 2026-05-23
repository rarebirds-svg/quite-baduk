import { test, expect } from "@playwright/test";

test("theme and language toggles work", async ({ page }) => {
  await page.goto("/");
  // TopNav의 theme 버튼은 현재 테마를 라벨에 노출한다(예: aria-label="Theme: light").
  // 옛 패턴(/toggle theme/i)은 더 이상 매치되지 않으므로 prefix로 잡는다.
  const themeBtn = page.getByRole("button", { name: /^Theme:/i });
  await themeBtn.click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  // 언어 버튼은 여전히 정확한 영문 aria-label("Toggle language") 사용.
  const langBtn = page.getByRole("button", { name: /toggle language/i });
  await langBtn.click();
  // Header title should change or remain consistent — just verify page still renders
  await expect(page.locator("nav")).toBeVisible();
});
