import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  // CI runner는 cold start + 컨테이너 부팅 직후라 첫 navigation·page.fill이
  // 느리다. 60s에서는 7개 테스트가 page.fill timeout으로 만성 실패했음 —
  // 120s로 늘려 안전 마진 확보. 로컬에서는 어차피 test가 빨라 영향 없음.
  timeout: 120_000,
  // 옛 인증 흐름(이메일/비밀번호 signup, <select> 드롭다운)을 가정한
  // helpers·spec이 새 nickname-only + Picker 컴포넌트 흐름과 호환 안 됨.
  // 본 PR(stage-1)에서는 theme_lang 하나만 갱신해 enable하고 나머지 5건은
  // 명시적으로 testIgnore에 박아둔다. 다음 PR에서 helpers + createGame
  // 흐름을 재작성하며 한 줄씩 제거해 점진 re-enable.
  testIgnore: [
    "**/board_size.spec.ts",
    "**/handicap.spec.ts",
    "**/review.spec.ts",
    "**/signup_and_play.spec.ts",
    "**/single_session.spec.ts",
  ],
  retries: 0,
  fullyParallel: false,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure"
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } }
  ]
});
