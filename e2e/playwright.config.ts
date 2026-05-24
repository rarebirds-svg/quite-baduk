import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  // CI runner는 cold start + 컨테이너 부팅 직후라 첫 navigation·page.fill이
  // 느리다. 60s에서는 7개 테스트가 page.fill timeout으로 만성 실패했음 —
  // 120s로 늘려 안전 마진 확보. 로컬에서는 어차피 test가 빨라 영향 없음.
  timeout: 120_000,
  retries: 0,
  fullyParallel: false,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${process.env.BADUK_WEB_PORT || 3000}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } }
  ]
});
