import { defineConfig, devices } from "@playwright/test";

const STORAGE_STATE = "tests/.auth/user.json";

export default defineConfig({
  testDir: "./tests",
  testMatch: /.*\.spec\.ts/,
  timeout: 60_000,
  retries: 0,
  fullyParallel: false,
  reporter: [["list"], ["html", { open: "never" }]],
  // Sign up one shared user before any test runs and reuse the session
  // across the whole suite — keeps us under the per-IP `/api/session`
  // rate limit when running ≥ 6 tests against the same backend.
  globalSetup: "./tests/global-setup.ts",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    storageState: STORAGE_STATE,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
