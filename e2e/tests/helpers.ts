import { Page, expect } from "@playwright/test";

export function randomEmail(prefix = "user") {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

export async function signup(page: Page, email: string, password = "password1", displayName = "Tester") {
  await page.goto("/signup");
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.fill('input[placeholder*="이름"], input[placeholder*="name"]', displayName);
  await page.getByRole("button", { name: /sign up|가입/i }).click();
  await expect(page).toHaveURL(/\/game\/new/);
}

export async function createGame(page: Page, opts: { rank?: string; handicap?: number } = {}) {
  await page.goto("/game/new");
  if (opts.rank) await page.selectOption("select >> nth=0", opts.rank);
  if (opts.handicap != null) await page.selectOption("select >> nth=1", String(opts.handicap));
  await page.getByRole("button", { name: /create|생성/i }).click();
  await expect(page).toHaveURL(/\/game\/play\/\d+/);
}
