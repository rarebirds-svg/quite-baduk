import { Page, expect } from "@playwright/test";

/**
 * Generate a fresh nickname (2–32 chars, no emoji) so each test gets a
 * non-colliding session row. The backend rejects duplicates with 409.
 */
export function randomNickname(prefix = "user"): string {
  // 2–32 chars, alphanumerics only — backend `validate` accepts these.
  return `${prefix}${Date.now().toString(36)}${Math.floor(Math.random() * 1e6).toString(36)}`.slice(0, 32);
}

/**
 * Walk the ephemeral nickname gate at `/`:
 * 1. Type a nickname into the (only) input.
 * 2. Wait for the debounced availability check (~400 ms) to flip the hint
 *    to "Available / 사용 가능".
 * 3. Click the submit button — the page redirects to `/game/new`.
 *
 * Replaces the old email/password flow that the post-uplift UI no longer ships.
 */
export async function signup(page: Page, nickname?: string): Promise<string> {
  const nick = nickname ?? randomNickname();
  await page.goto("/");
  // The nickname gate has exactly one text input.
  const input = page.locator('input[type="text"]').first();
  await input.fill(nick);
  // Hint text turns into "사용 가능" (ko) or "Available" (en) once the
  // debounced /nickname/check call returns.
  await expect(page.getByText(/사용 가능|Available/i)).toBeVisible({ timeout: 5000 });
  // Submit — i18n key `session.nicknameSubmit` is "시작하기" (ko) or "Start" (en).
  await page.getByRole("button", { name: /시작하기|^Start$/i }).click();
  await expect(page).toHaveURL(/\/game\/new/);
  return nick;
}

interface CreateGameOpts {
  rank?: string;
  handicap?: number;
  boardSize?: 9 | 13 | 19;
}

/**
 * Drive the new-game form. Defaults (rank 5k, handicap 0, board 19, random
 * AI player) are server-side; we only override what the test asks for.
 */
export async function createGame(page: Page, opts: CreateGameOpts = {}): Promise<void> {
  // The signup helper lands here, but call sites that skip signup (a
  // re-test against an existing session) need an explicit nav.
  if (!page.url().endsWith("/game/new")) {
    await page.goto("/game/new");
  }

  if (opts.boardSize !== undefined) {
    // ToggleGroupItem renders the size as e.g. "9×9" (× U+00D7, not "x").
    await page
      .getByRole("radio", { name: `${opts.boardSize}×${opts.boardSize}` })
      .click();
  }

  // The form's defaults are rank=5k and handicap=0; when a test asks for
  // those exact values we deliberately skip the Radix Select interaction
  // because its portal-based listbox occasionally lingers and intercepts
  // the subsequent Start click.
  if (opts.rank !== undefined && opts.rank !== "5k") {
    await page.getByRole("combobox", { name: /급수|^Rank$/i }).click();
    await page.getByRole("option", { name: opts.rank }).click();
    // Keyboard-dismiss any stray listbox before moving on.
    await page.keyboard.press("Escape");
  }

  if (opts.handicap !== undefined && opts.handicap !== 0) {
    await page.getByRole("combobox", { name: /대국방식|^Handicap$/i }).click();
    // Handicap items render as "{n}점 치석" (ko) or "{n} stones" (en).
    const re = new RegExp(`^${opts.handicap}(점|\\s+stones)`);
    await page.getByRole("option", { name: re }).click();
    await page.keyboard.press("Escape");
  }

  // Start button — `t("game.start")` is "대국 시작" (ko) or "Start" (en).
  await page.getByRole("button", { name: /대국 시작|^Start$/i }).click();
  // Game creation goes through the rules engine + mock KataGo seeding +
  // adapter clear_board, which can spike past the default 5 s assertion
  // timeout under shared CI load. Give it explicit headroom.
  await page.waitForURL(/\/game\/play\/\d+/, { timeout: 20_000 });
}

/**
 * Resign a live game by clicking the GameControls resign button and
 * confirming the destructive dialog. The post-uplift UI added a confirm
 * step so an accidental keypress can't end a game.
 */
export async function resign(page: Page): Promise<void> {
  await page.getByRole("button", { name: /^기권$|^Resign$/ }).first().click();
  // Dialog now visible; click the destructive confirm (also labeled
  // "기권 / Resign"), pinning the locator to the dialog scope.
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: /^기권$|^Resign$/ }).click();
}
