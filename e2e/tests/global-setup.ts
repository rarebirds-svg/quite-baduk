import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { chromium, FullConfig } from "@playwright/test";
import { signup } from "./helpers";

/**
 * Sign up a single shared user and persist the session cookie. Every test
 * project that loads the resulting `storageState` starts already past the
 * nickname gate, which keeps us under the per-IP rate limit on
 * `/api/session` (5 hits / 60 s) when the suite runs more than a handful
 * of tests against one backend.
 */
export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseURL =
    config.projects[0]?.use.baseURL || process.env.E2E_BASE_URL || "http://localhost:3000";
  const storagePath = resolve(__dirname, ".auth/user.json");
  mkdirSync(dirname(storagePath), { recursive: true });

  const browser = await chromium.launch();
  const ctx = await browser.newContext({ baseURL });
  const page = await ctx.newPage();
  try {
    await signup(page);
    // Save cookies + localStorage so each spec starts authenticated.
    await ctx.storageState({ path: storagePath });
  } finally {
    await ctx.close();
    await browser.close();
  }
}
