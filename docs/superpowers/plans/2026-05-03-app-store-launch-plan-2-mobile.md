# App Store Launch — Plan 2: Capacitor Mobile Shell

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap the Next.js app in a Capacitor 7 shell that produces installable iOS `.ipa` and Android `.aab` artifacts, with Tier 1 native enhancements (haptics, share sheet, system dark mode, splash, sound) plus the Tier 2 Files-app `.sgf` handler. Clear the residual frontend P0/P1 issues from the QA baseline (`docs/reviews/2026-05-03-pre-launch-qa-baseline.md`) so the apps ship without known regressions.

**Architecture:** The Next.js app keeps its standalone web build for the desktop site; a sibling **mobile build** (`NEXT_PUBLIC_PLATFORM=mobile`) emits `output: 'export'` static files into `web/out/`, which `npx cap sync` copies into `mobile/www/`. Capacitor wraps that bundle and points API/WS calls at `https://api.<domain>` (Plan 1). Native code is minimal — every plugin is invoked through a thin TypeScript wrapper (`web/lib/native/*.ts`) that no-ops on web, so the existing Vitest suite keeps passing.

**Tech Stack:** Next.js 14.2.35 + React 18 + TypeScript 5 + Tailwind + Zustand (existing); Capacitor 7 + 7 official plugins (`@capacitor/{haptics,share,app,network,status-bar,splash-screen,preferences}`); Xcode 15 + Android Studio Hedgehog (host tools); Vitest + Playwright (tests).

---

## Day 0 Prerequisites

- Plan 1 has shipped: `https://api.<domain>/api/health` returns 200 with security headers from a phone tethered off home Wi-Fi.
- Apple Developer Program membership has been issued (Plan 3) — needed at Task B1 step 6 for code signing.
- Bundle ID has been chosen and reserved in App Store Connect (Plan 3) — needed at Task B1 step 5.
- Local dev machine has Xcode 15+ and Android Studio with the latest stable Android SDK + cmdline-tools.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `web/next.config.js` | Modify | Branch on `NEXT_PUBLIC_PLATFORM` — `output: 'export'` for mobile, `'standalone'` for web |
| `web/package.json` | Modify | New scripts: `build:mobile`, `cap:sync`, `cap:open:ios`, `cap:open:android` |
| `web/lib/config.ts` | Create | Resolves `API_URL` and `WS_URL` per build (env var or absolute URL) |
| `web/lib/native/platform.ts` | Create | `isNative()` helper (`Capacitor.isNativePlatform()` with web fallback) |
| `web/lib/native/haptics.ts` | Create | Wrapper for `Haptics.impact / notification`, web no-ops |
| `web/lib/native/share.ts` | Create | `shareSgf(filename, content)` via `Filesystem` + `Share` |
| `web/lib/native/network.ts` | Create | Subscribes to `Network` plugin, exposes a Zustand store of `isOnline` |
| `web/lib/native/lifecycle.ts` | Create | Wires `App.appStateChange` → `wsClient.reconnect()`; intercepts Android back button |
| `web/lib/native/preferences.ts` | Create | `getPref/setPref` thin wrapper (Capacitor Preferences with localStorage fallback) |
| `web/lib/native/__mocks__/*.ts` | Create | Vitest manual mocks (jest-style) so plugin imports don't error in jsdom |
| `web/lib/i18n/detect.ts` | Create | First-run language detection from `Capacitor.Device.getLanguageCode()` |
| `web/lib/ws.ts` | Modify | Outbound queue: any `send()` while disconnected is buffered and flushed on reconnect (P0-11) |
| `web/store/gameStore.ts` | Modify | Resign result/winner update path (P1-3) |
| `web/components/ScorePanel.tsx` | Modify | Drop hardcoded Korean → use i18n keys (P1-4) |
| `web/components/Board.tsx` | Modify | Call `haptics.lightImpact()` on user move; `mediumImpact()` on capture |
| `web/app/settings/page.tsx` | Modify | Fix 5 design-token violations + add haptics/sound toggles |
| `web/lib/i18n/ko.json`, `en.json` | Modify | Apply 12 copy fixes (terms + naturalness) + new keys for native features |
| `web/app/layout.tsx` | Modify | Replace hardcoded meta title/description with i18n keys |
| `web/components/RankPicker.tsx` | Modify | Replace `${n}단`/`${n}급` literals with i18n suffix keys |
| `web/components/MobileBackGuard.tsx` | Create | Renders a confirm dialog when Android back is pressed mid-game |
| `web/styles/safe-area.css` (or in `globals.css`) | Modify | `env(safe-area-inset-*)` wrappers for board container + chrome |
| `mobile/` | Create | Capacitor project root (separate `package.json`, `capacitor.config.ts`, `ios/`, `android/`, `www/`) |
| `mobile/capacitor.config.ts` | Create | App ID, name, plugins, build dir |
| `mobile/resources/icon.png` (1024×1024) | Create | Master icon — black + white stone monogram |
| `mobile/resources/splash.png` (2732×2732) | Create | Paper background + BrandMark center |
| `mobile/resources/splash-dark.png` | Create | Dark variant |
| `mobile/ios/.../Info.plist` | Modify | Document type association for `.sgf` (Tier 2) |
| `mobile/android/.../AndroidManifest.xml` | Modify | Intent filter for `.sgf` (Tier 2) |
| `web/lib/sgf-import.ts` | Create | Reads an `.sgf` file URL passed via `App.appUrlOpen`, navigates to review |
| `e2e/tests/mobile/onboarding.spec.ts` | Create | First-run flow with mobile viewport |
| `e2e/tests/mobile/background-resume.spec.ts` | Create | WS disconnect → app foreground → reconnect |
| `e2e/tests/mobile/offline-banner.spec.ts` | Create | Network drop → banner → restore |
| `e2e/tests/mobile/share-sgf.spec.ts` | Create | Share triggers via mocked Capacitor plugin |
| `e2e/tests/mobile/dark-mode-auto.spec.ts` | Create | System theme change → instant UI swap |
| `web/tests/native/haptics.test.ts` | Create | Web no-op + native call assertions (mock plugin) |
| `web/tests/native/share.test.ts` | Create | Same shape |

---

## Phase A — Build environment + i18n detect

### Task A1: Branch `next.config.js` on platform

**Files:**
- Modify: `web/next.config.js`
- Modify: `web/package.json` (scripts)

- [ ] **Step 1: Read current `next.config.js`**

```bash
cat web/next.config.js
```

Confirm: `output: "standalone"` + a single `rewrites()` for `/api/:path*`. The mobile build can't use the rewrite (it runs from `file://` or `capacitor://`, no Next runtime).

- [ ] **Step 2: Replace `web/next.config.js`**

```js
/** @type {import('next').NextConfig} */
const isMobile = process.env.NEXT_PUBLIC_PLATFORM === "mobile";

const nextConfig = {
  output: isMobile ? "export" : "standalone",
  images: { unoptimized: isMobile },
  trailingSlash: isMobile,           // Capacitor file:// needs index.html per dir
  reactStrictMode: true,
  ...(isMobile
    ? {}
    : {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination:
                (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") +
                "/api/:path*",
            },
          ];
        },
      }),
};

module.exports = nextConfig;
```

- [ ] **Step 3: Add the mobile build script to `web/package.json`**

In `"scripts"`, add:

```json
    "build:mobile": "NEXT_PUBLIC_PLATFORM=mobile NEXT_PUBLIC_API_URL=https://api.example.com NEXT_PUBLIC_WS_URL=wss://api.example.com next build",
    "cap:sync": "cd ../mobile && npx cap sync",
    "cap:open:ios": "cd ../mobile && npx cap open ios",
    "cap:open:android": "cd ../mobile && npx cap open android"
```

Replace `https://api.example.com` with the real domain when known. Keep this as the literal default in the committed file — production rebuilds with the env var set inline.

- [ ] **Step 4: Smoke-test mobile build**

```bash
cd web && npm run build:mobile
ls out/index.html
```

Expected: `out/index.html` exists. If `next` complains about server-only features (e.g. `getServerSideProps`, route handlers), fix or guard them — the project uses App Router and is mostly client-side, so this should succeed.

If it fails on a specific page, that page either (a) needs to be marked client-only via `"use client"` if it isn't, or (b) needs to be excluded from the mobile build (rare).

- [ ] **Step 5: Web build still passes**

```bash
npm run build
```

Expected: standalone build succeeds.

- [ ] **Step 6: Commit**

```bash
git add web/next.config.js web/package.json
git commit -m "build(web): branch on NEXT_PUBLIC_PLATFORM for mobile static export"
```

---

### Task A2: `lib/config.ts` for API/WS base URL

**Files:**
- Create: `web/lib/config.ts`
- Modify: any file currently building API URLs ad-hoc

- [ ] **Step 1: Identify current API URL plumbing**

```bash
grep -rEn "process\.env\.NEXT_PUBLIC_API_URL|fetch\(.[\"']/api" web/app web/lib web/store web/components | head -40
```

Most callers use relative `/api/...` paths because the rewrite handles it on web. For mobile, those calls must hit an absolute URL.

- [ ] **Step 2: Create `web/lib/config.ts`**

```typescript
/**
 * Resolves the API and WebSocket base URLs at build time.
 *
 * Web (standalone): empty base, relative `/api/...` paths get rewritten
 * by Next.js to the backend.
 *
 * Mobile (Capacitor `output:'export'`): absolute URL hard-coded into
 * the bundle. The build pipeline sets NEXT_PUBLIC_API_URL +
 * NEXT_PUBLIC_WS_URL via `package.json:build:mobile`.
 */
export const PLATFORM = (process.env.NEXT_PUBLIC_PLATFORM ?? "web") as
  | "web"
  | "mobile";

export const API_BASE: string =
  process.env.NEXT_PUBLIC_API_URL ?? "";

export const WS_BASE: string =
  process.env.NEXT_PUBLIC_WS_URL ??
  (typeof window !== "undefined"
    ? window.location.origin.replace(/^http/, "ws")
    : "");

export function apiUrl(path: string): string {
  if (!path.startsWith("/")) path = "/" + path;
  return `${API_BASE}${path}`;
}

export function wsUrl(path: string): string {
  if (!path.startsWith("/")) path = "/" + path;
  return `${WS_BASE}${path}`;
}
```

- [ ] **Step 3: Migrate existing `fetch` callers**

```bash
grep -rln 'fetch("/api/' web | head -20
```

For each file, change `fetch("/api/foo")` → `fetch(apiUrl("/api/foo"))` and add `import { apiUrl } from "@/lib/config";` (or relative — the project uses relative imports, so adjust to e.g. `../../lib/config`).

Same for WebSocket constructors:

```bash
grep -rln 'new WebSocket' web/lib web/store
```

`new WebSocket("ws://...")` → `new WebSocket(wsUrl("/api/ws/..."))`.

- [ ] **Step 4: Run frontend tests**

```bash
npm test -- --run
```

Expected: all 51 still pass. The fetch wrapper is functionally identical when `API_BASE === ""`.

- [ ] **Step 5: Verify build still works**

```bash
npm run build && npm run build:mobile
```

- [ ] **Step 6: Commit**

```bash
git add web/lib/config.ts web/lib web/store web/app
git commit -m "feat(config): centralize API/WS base URL resolution"
```

---

### Task A3: First-run language detection

**Files:**
- Create: `web/lib/i18n/detect.ts`
- Modify: `web/lib/i18n/<existing loader>.ts` to call detection on first launch

- [ ] **Step 1: Locate the i18n initialization point**

```bash
grep -rln "currentLocale\|useLocale\|i18n init" web/lib web/store web/app | head
```

Identify the module that decides which locale to load at startup.

- [ ] **Step 2: Create `web/lib/i18n/detect.ts`**

```typescript
import { isNative } from "@/lib/native/platform";

/**
 * Decide an initial locale on first launch when the user hasn't picked
 * one yet. On native we ask the OS; on web we fall back to
 * `navigator.language`.
 *
 * Stored to localStorage under key `baduk.locale` so subsequent loads
 * skip detection.
 */
export async function detectInitialLocale(): Promise<"ko" | "en"> {
  const stored = typeof localStorage !== "undefined"
    ? localStorage.getItem("baduk.locale")
    : null;
  if (stored === "ko" || stored === "en") return stored;

  let raw: string | undefined;
  if (isNative()) {
    try {
      const { Device } = await import("@capacitor/device");
      const r = await Device.getLanguageCode();
      raw = r.value;
    } catch {
      // plugin not installed in this build
    }
  }
  if (!raw && typeof navigator !== "undefined") {
    raw = navigator.language;
  }
  const lang = (raw ?? "en").toLowerCase();
  return lang.startsWith("ko") ? "ko" : "en";
}
```

(The `@capacitor/device` plugin will be installed in Task C6; the `await import` keeps web bundles from pulling it in.)

- [ ] **Step 3: Wire into the existing locale store**

Open whichever file initializes the locale (e.g. `web/lib/i18n/index.ts` or `web/store/localeStore.ts`). On store creation, if no stored locale, call `detectInitialLocale()`:

```typescript
import { detectInitialLocale } from "./detect";

// Inside store init:
detectInitialLocale().then((loc) => {
  if (!localStorage.getItem("baduk.locale")) {
    setLocale(loc);
  }
});
```

- [ ] **Step 4: Test**

```bash
npm test -- --run
```

Add a quick unit test if the locale store has tests; otherwise, manual smoke is sufficient.

- [ ] **Step 5: Commit**

```bash
git add web/lib/i18n
git commit -m "feat(i18n): first-run locale detection (Capacitor Device + navigator)"
```

---

## Phase B — Frontend P0/P1 + cleanup

### Task B1: WS outbound queue (P0-11)

**Files:**
- Modify: `web/lib/ws.ts`
- Test: `web/tests/lib/ws.test.ts` (create)

The current WebSocket client drops `send()` calls made while disconnected. On a phone, a network blip mid-move silently loses the move.

- [ ] **Step 1: Read current `lib/ws.ts`**

```bash
cat web/lib/ws.ts
```

- [ ] **Step 2: Write the failing test**

Create `web/tests/lib/ws.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { createWsClient } from "@/lib/ws";  // adjust import path

class FakeSocket {
  readyState = 0; // CONNECTING
  sent: string[] = [];
  send(s: string) {
    if (this.readyState !== 1) throw new Error("not open");
    this.sent.push(s);
  }
  open() {
    this.readyState = 1;
    this.onopen?.();
  }
  onopen?: () => void;
  onmessage?: (e: { data: string }) => void;
  onclose?: () => void;
}

describe("WS outbound queue", () => {
  it("buffers messages sent while disconnected and flushes on open", () => {
    const sock = new FakeSocket();
    const client = createWsClient(() => sock as unknown as WebSocket);
    client.send({ type: "move", coord: "D4" });
    expect(sock.sent).toHaveLength(0);
    sock.open();
    expect(sock.sent).toEqual([JSON.stringify({ type: "move", coord: "D4" })]);
  });
});
```

- [ ] **Step 3: Run — fails because the existing client either throws or drops on closed-state send**

```bash
npm test -- --run web/tests/lib/ws.test.ts
```

- [ ] **Step 4: Refactor `web/lib/ws.ts` to expose `createWsClient` + queue**

The exact diff depends on the existing shape. The patch in concept:

```typescript
// Add a queue alongside the socket:
const outbox: string[] = [];

function send(payload: unknown): void {
  const msg = JSON.stringify(payload);
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(msg);
  } else {
    outbox.push(msg);
  }
}

function onOpen() {
  while (outbox.length > 0) {
    const msg = outbox.shift()!;
    socket!.send(msg);
  }
  // ... existing onOpen
}
```

If the file currently exports a singleton, refactor minimally to expose `createWsClient` for testability while keeping the singleton convenience export intact.

- [ ] **Step 5: Run — passes**

- [ ] **Step 6: Add a second test — flushes don't double-send after a reconnect**

```typescript
it("does not replay messages from a previous open after reconnect", () => {
  const sock1 = new FakeSocket();
  const client = createWsClient(() => sock1 as unknown as WebSocket);
  sock1.open();
  client.send({ type: "move", coord: "D4" });
  expect(sock1.sent).toHaveLength(1);

  // Disconnect + reconnect
  sock1.onclose?.();
  const sock2 = new FakeSocket();
  // ... use the factory to create a fresh socket
  // At minimum: outbox is empty after a successful send, so no double-send.
});
```

- [ ] **Step 7: Commit**

```bash
git add web/lib/ws.ts web/tests/lib/ws.test.ts
git commit -m "fix(ws): buffer outbound messages across reconnect (P0-11)"
```

---

### Task B2: Resign UI updates result/winner (P1-3)

**Files:**
- Modify: `web/store/gameStore.ts`
- Modify: `web/components/<wherever the resign action is wired>` (likely `GameControls.tsx` or `play/[id]/page.tsx`)

- [ ] **Step 1: Trace the current resign flow**

```bash
grep -rn "resign" web/store web/components web/app | head
```

Confirm: REST `POST /api/games/:id/resign` is called, but the response (`GameSummary` with `result`, `winner`) isn't applied to the gameStore — UI keeps showing the active board.

- [ ] **Step 2: Find or add a `gameStore.applyResult(summary)` action**

In `web/store/gameStore.ts`:

```typescript
applyResult(summary: { result: string; winner: string; status: string }) {
  set((state) => ({
    ...state,
    result: summary.result,
    winner: summary.winner,
    status: summary.status,
    gameOver: summary.status !== "active",
  }));
},
```

- [ ] **Step 3: Update the resign caller to apply the response**

Wherever `fetch(apiUrl("/api/games/" + id + "/resign"), { method: "POST" })` is called, add:

```typescript
const r = await fetch(apiUrl(`/api/games/${id}/resign`), { method: "POST" });
if (r.ok) {
  const summary = await r.json();
  gameStore.getState().applyResult(summary);
}
```

- [ ] **Step 4: Verify with manual smoke test**

`npm run dev` (with backend running), start a game, resign, observe the result banner appear immediately.

- [ ] **Step 5: Commit**

```bash
git add web/store web/components web/app
git commit -m "fix(ui): apply resign response to gameStore so result banner renders (P1-3)"
```

---

### Task B3: ScorePanel i18n (P1-4) + 12 copy fixes

**Files:**
- Modify: `web/components/ScorePanel.tsx`
- Modify: `web/lib/i18n/ko.json`
- Modify: `web/lib/i18n/en.json`
- Modify: `web/app/layout.tsx`
- Modify: `web/app/settings/page.tsx`
- Modify: `web/components/RankPicker.tsx`

- [ ] **Step 1: Inspect ScorePanel hardcoded strings**

```bash
grep -nE "[가-힣]" web/components/ScorePanel.tsx
```

For each Korean string, add an i18n key under a sensible namespace (e.g. `score.*`) in both ko.json and en.json, then replace the literal in JSX with the translation function call.

- [ ] **Step 2: Apply the QA report's 12 copy fixes**

Open both `web/lib/i18n/ko.json` and `web/lib/i18n/en.json` and apply the changes from the baseline report §6.3–6.5:

| Key | Before | After |
|---|---|---|
| `game.komiLabel` (ko) | "코미" | "덤" |
| `game.handicap` (ko) | "대국방식" | "핸디캡" |
| `admin.inProgress` (ko) | "진행중" | "진행 중" |
| `admin.endReasonActive` (ko) | "진행중" | "진행 중" |
| `home.valueDesc3` (ko) | "...scoreLead..." | "...집 차이..." (rewrite without English jargon) |
| `home.valueDesc3` (ko) | "...ownership..." | "...영역 판정..." |
| `game.color` (en) | "Order" | "Color" |
| `game.info`, `moves`, `move`, `captures`, `toMove`, `winrate` (en) | ALL CAPS | sentence case (`Info`, `Moves`, `Move`, `Captures`, `To move`, `Winrate`) |
| `game.colorYou` (ko) | "당신" | "나" |
| `game.yourTurn` (ko) | "당신 차례" | "내 차례" |
| `errors.NOT_YOUR_TURN` (ko) | "당신 차례가 아닙니다" | "지금은 내 차례가 아닙니다" |
| `admin.refreshed` (ko) | "자동 새로고침 {sec}초" | "{sec}초마다 자동 새로고침" |
| `session.expiredDesc` (en) | "Please set a nickname to continue" | "Your session has expired. Please choose a nickname to continue." |

- [ ] **Step 3: Replace hardcoded strings in `layout.tsx`**

`web/app/layout.tsx` lines 14–15 currently have hardcoded Korean meta. Replace with i18n keys:

```typescript
// Add to ko.json + en.json:
//   "app.metaTitle": "AI 바둑" / "AI Baduk"
//   "app.metaDescription": "KataGo Human-SL과 두는 한국식 바둑 (9×9 · 13×13 · 19×19)"
//                          / "Play Korean-rules Go vs KataGo Human-SL (9×9 / 13×13 / 19×19)"

// In layout.tsx, since metadata is server-side, use the dictionary
// directly (not a hook):
import koDict from "@/lib/i18n/ko.json";
export const metadata = {
  title: koDict.app.metaTitle,
  description: koDict.app.metaDescription,
};
```

(The default locale for SSR is Korean per the project; `en` users get translated on the client. If you want locale-aware metadata across SSR, that's a separate refactor — V1.1.)

- [ ] **Step 4: Replace `${n}단` / `${n}급` literals in `RankPicker.tsx`**

```bash
grep -n "단\|급" web/components/RankPicker.tsx
```

Add to ko.json/en.json:

```json
"settings.suffixDan": "단" / "-dan",
"settings.suffixKyu": "급" / "-kyu"
```

In RankPicker:

```typescript
// Before: const label = `${n}${n >= 1 ? "단" : "급"}`;
// After:
const label = `${n}${n >= 1 ? t("settings.suffixDan") : t("settings.suffixKyu")}`;
```

- [ ] **Step 5: Run i18n parity test**

```bash
npm test -- --run web/tests/i18n.test.ts
```

Expected: parity preserved.

- [ ] **Step 6: Commit**

```bash
git add web/components/ScorePanel.tsx web/lib/i18n web/app/layout.tsx web/components/RankPicker.tsx
git commit -m "i18n: 12-item copy polish (덤/핸디캡/내 차례 etc.) + ScorePanel keys"
```

---

### Task B4: Fix 5 design-token violations in settings page

**Files:**
- Modify: `web/app/settings/page.tsx`

- [ ] **Step 1: Open the file**

```bash
sed -n '40,60p' web/app/settings/page.tsx
```

The QA report identified lines 48 and 55 with `rounded` and `dark:bg-gray-900`, plus a hardcoded `한국어` literal at line 49.

- [ ] **Step 2: Apply fixes**

For each `<select>` (or wrapper) that has the violation:

```diff
- className="border rounded px-2 py-1 dark:bg-gray-900"
+ className="border rounded-sm px-2 py-1 bg-paper dark:bg-paper-deep"
```

For the language `<option>`:

```diff
- <option value="ko">한국어</option>
+ <option value="ko">{t("settings.langKo")}</option>
```

Add to `ko.json` / `en.json`:

```json
"settings.langKo": "한국어" / "Korean",
"settings.langEn": "English" / "English"
```

Update both options accordingly.

- [ ] **Step 3: Run design-token-guardian agent**

This step is run by Claude Code, not the human. From a Claude session, dispatch:

> `design-token-guardian` agent: re-audit `web/app/settings/page.tsx` after the latest commit. Confirm 0 violations.

If running manually, just visually verify against the rules in CLAUDE.md.

- [ ] **Step 4: Commit**

```bash
git add web/app/settings/page.tsx web/lib/i18n
git commit -m "fix(settings): drop rounded/gray-900 + i18n-ize language picker"
```

---

## Phase C — Capacitor scaffold

### Task C1: Create `mobile/` Capacitor project

**Files:**
- Create: `mobile/package.json`
- Create: `mobile/capacitor.config.ts`
- Modify: `.gitignore`

- [ ] **Step 1: Make sure Plan 3 has reserved a Bundle ID**

Use the agreed value (placeholder here: `<reverse.domain>.baduk`).

- [ ] **Step 2: Scaffold from the repo root**

```bash
cd /Users/<you>/projects/baduk
mkdir mobile && cd mobile
npm init -y
npm install @capacitor/core @capacitor/cli
npx cap init "AI Baduk" "<reverse.domain>.baduk" \
  --web-dir=www
```

This creates `mobile/capacitor.config.ts`, `mobile/package.json`, and an empty `mobile/www/`.

- [ ] **Step 3: Replace `mobile/capacitor.config.ts`**

```typescript
import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "<reverse.domain>.baduk",
  appName: "AI Baduk",
  webDir: "www",
  // server: {
  //   // for `npx cap run ios -l --external` live-reload during dev
  //   url: "http://192.168.1.10:3000",
  //   cleartext: true,
  // },
  ios: {
    contentInset: "always",
  },
  android: {
    allowMixedContent: false,
  },
};
export default config;
```

- [ ] **Step 4: Sync the empty bundle**

```bash
# From web/, populate mobile/www first
cd ../web && npm run build:mobile && cp -r out/* ../mobile/www/
cd ../mobile && npx cap sync
```

- [ ] **Step 5: Update `.gitignore`** (root)

Add:

```
mobile/www/
mobile/node_modules/
mobile/ios/App/build/
mobile/ios/App/Pods/
mobile/android/.gradle/
mobile/android/app/build/
mobile/android/build/
mobile/android/local.properties
```

- [ ] **Step 6: Commit**

```bash
git add mobile .gitignore
git commit -m "feat(mobile): bootstrap Capacitor project (web bundle only, no platforms yet)"
```

---

### Task C2: Add iOS platform

**Files:**
- Create: `mobile/ios/` (generated)

- [ ] **Step 1: Add iOS**

```bash
cd mobile
npm install @capacitor/ios
npx cap add ios
```

This creates `mobile/ios/App/App.xcworkspace`.

- [ ] **Step 2: Open the workspace**

```bash
npx cap open ios
```

Xcode opens. In **Signing & Capabilities**:
- Team: select your Apple Developer team (Plan 3 prereq)
- Bundle Identifier: confirm `<reverse.domain>.baduk`
- Automatically manage signing: ON

- [ ] **Step 3: First simulator run**

In Xcode: choose a simulator (iPhone 15 Pro), click ▶︎. Expected: app launches, board renders, but **API calls fail** because the simulator can't reach `https://api.<domain>` if the domain isn't live yet OR no `NEXT_PUBLIC_API_URL` was baked. Fix by re-building the web bundle with the production env, then `cap sync`:

```bash
cd ../web
NEXT_PUBLIC_API_URL=https://api.<domain> NEXT_PUBLIC_WS_URL=wss://api.<domain> \
  npm run build:mobile
cd ../mobile && npx cap sync
```

Re-run from Xcode — board appears + API calls hit production.

- [ ] **Step 4: Commit (only the generated iOS scaffold)**

```bash
git add mobile/ios mobile/package.json mobile/package-lock.json
git commit -m "feat(mobile): add iOS platform"
```

---

### Task C3: Add Android platform

```bash
cd mobile
npm install @capacitor/android
npx cap add android
```

- [ ] **Step 1: Open Android Studio**

```bash
npx cap open android
```

- [ ] **Step 2: First emulator run**

In Android Studio: pick a Pixel 6 emulator with API 35. Run. Expected: same as iOS — board renders, API calls hit production.

- [ ] **Step 3: Commit**

```bash
git add mobile/android
git commit -m "feat(mobile): add Android platform"
```

---

### Task C4: Master icon + splash + auto-generate

**Files:**
- Create: `mobile/resources/icon.png` (1024×1024)
- Create: `mobile/resources/icon-foreground.png` (1024×1024)
- Create: `mobile/resources/icon-background.png` (1024×1024)
- Create: `mobile/resources/splash.png` (2732×2732)
- Create: `mobile/resources/splash-dark.png` (2732×2732)

- [ ] **Step 1: Design the 1024×1024 icon**

Concept agreed in Plan 3: a black + white stone monogram on a `bg-paper` (`#F5EFE6`) background. Two stones overlapping at ~30% offset, black on left, white on right; subtle 1px stroke on the white stone for separation. Sized so the bounding box uses ~85% of the canvas, leaving safe-area margin for iOS rounded-corner masking.

Tools: Figma, Sketch, Pixelmator, Affinity Designer — any vector tool. Export 1024×1024 PNG.

- [ ] **Step 2: Design the splash (2732×2732)**

`bg-paper` background, BrandMark centered at ~30% of the canvas, no text. Provide a `splash-dark.png` with `bg-paper-deep` background.

- [ ] **Step 3: Install `@capacitor/assets` and generate**

```bash
cd mobile
npm install --save-dev @capacitor/assets
npx capacitor-assets generate --iconBackgroundColor "#F5EFE6" \
  --iconBackgroundColorDark "#1A1814" \
  --splashBackgroundColor "#F5EFE6" \
  --splashBackgroundColorDark "#1A1814"
```

This populates iOS asset catalogs and Android `mipmap-*/` and `drawable-*/`.

- [ ] **Step 4: Re-build + run**

```bash
cd ../web && npm run build:mobile
cd ../mobile && npx cap sync
npx cap open ios   # check icon + splash visible
```

- [ ] **Step 5: Commit**

```bash
git add mobile/resources mobile/ios mobile/android
git commit -m "feat(mobile): icon + splash assets (stone monogram)"
```

---

### Task C5: Install plugins + create `lib/native/platform.ts`

**Files:**
- Modify: `mobile/package.json`
- Create: `web/lib/native/platform.ts`

- [ ] **Step 1: Install all 7 plugins inside `mobile/`**

```bash
cd mobile
npm install \
  @capacitor/haptics \
  @capacitor/share \
  @capacitor/app \
  @capacitor/network \
  @capacitor/status-bar \
  @capacitor/splash-screen \
  @capacitor/preferences \
  @capacitor/device \
  @capacitor/filesystem
npx cap sync
```

- [ ] **Step 2: ALSO install in `web/` so types resolve in TS**

```bash
cd ../web
npm install --save \
  @capacitor/core \
  @capacitor/haptics \
  @capacitor/share \
  @capacitor/app \
  @capacitor/network \
  @capacitor/status-bar \
  @capacitor/splash-screen \
  @capacitor/preferences \
  @capacitor/device \
  @capacitor/filesystem
```

The web bundle won't actually invoke native code (the wrappers in `lib/native/` short-circuit on web), but the TS types must resolve. Tree-shaking removes unused plugin code at build time.

- [ ] **Step 3: Create `web/lib/native/platform.ts`**

```typescript
import { Capacitor } from "@capacitor/core";

export function isNative(): boolean {
  return Capacitor.isNativePlatform?.() ?? false;
}

export function platformName(): "ios" | "android" | "web" {
  if (!isNative()) return "web";
  return (Capacitor.getPlatform?.() ?? "web") as "ios" | "android" | "web";
}
```

- [ ] **Step 4: Commit**

```bash
git add web/package.json web/package-lock.json mobile/package.json mobile/package-lock.json web/lib/native/platform.ts
git commit -m "feat(native): install Capacitor plugins + platform helper"
```

---

### Task C6: Vitest mocks for plugins

**Files:**
- Create: `web/lib/native/__mocks__/haptics.ts`
- Create: `web/lib/native/__mocks__/share.ts`
- (One mock file per plugin we wrap.)
- Modify: `web/vitest.config.ts`

Without these, every test that imports a wrapper file pulls in the plugin and fails in jsdom because `Capacitor.isNativePlatform` is undefined. The wrappers themselves tolerate web — but for stricter tests we want explicit mocks.

- [ ] **Step 1: Add a global vitest setup hook**

Add to `web/tests/setup.ts`:

```typescript
import { vi } from "vitest";

vi.mock("@capacitor/core", () => ({
  Capacitor: {
    isNativePlatform: () => false,
    getPlatform: () => "web",
  },
}));
```

This is enough for most cases. Per-plugin mocks are added on demand by individual tests.

- [ ] **Step 2: Run vitest**

```bash
cd web && npm test -- --run
```

Expected: still 51+ tests passing.

- [ ] **Step 3: Commit**

```bash
git add web/tests/setup.ts
git commit -m "test(native): mock @capacitor/core in jsdom"
```

---

## Phase D — Tier 1 native enhancements

### Task D1: Haptics wrapper + Board integration

**Files:**
- Create: `web/lib/native/haptics.ts`
- Create: `web/tests/native/haptics.test.ts`
- Modify: `web/components/Board.tsx` (or wherever stone-place is dispatched)
- Modify: `web/app/settings/page.tsx` (toggle)

- [ ] **Step 1: Create `web/lib/native/haptics.ts`**

```typescript
import { isNative } from "./platform";
import { getPref } from "./preferences";

const PREF_ENABLED = "haptics.enabled";

async function enabled(): Promise<boolean> {
  const v = await getPref(PREF_ENABLED);
  return v !== "false";  // default ON
}

export async function lightImpact(): Promise<void> {
  if (!isNative() || !(await enabled())) return;
  const { Haptics, ImpactStyle } = await import("@capacitor/haptics");
  await Haptics.impact({ style: ImpactStyle.Light });
}

export async function mediumImpact(): Promise<void> {
  if (!isNative() || !(await enabled())) return;
  const { Haptics, ImpactStyle } = await import("@capacitor/haptics");
  await Haptics.impact({ style: ImpactStyle.Medium });
}

export async function warning(): Promise<void> {
  if (!isNative() || !(await enabled())) return;
  const { Haptics, NotificationType } = await import("@capacitor/haptics");
  await Haptics.notification({ type: NotificationType.Warning });
}

export async function success(): Promise<void> {
  if (!isNative() || !(await enabled())) return;
  const { Haptics, NotificationType } = await import("@capacitor/haptics");
  await Haptics.notification({ type: NotificationType.Success });
}
```

- [ ] **Step 2: Create `web/lib/native/preferences.ts`**

```typescript
import { isNative } from "./platform";

export async function getPref(key: string): Promise<string | null> {
  if (isNative()) {
    const { Preferences } = await import("@capacitor/preferences");
    const r = await Preferences.get({ key });
    return r.value ?? null;
  }
  return typeof localStorage !== "undefined"
    ? localStorage.getItem(key)
    : null;
}

export async function setPref(key: string, value: string): Promise<void> {
  if (isNative()) {
    const { Preferences } = await import("@capacitor/preferences");
    await Preferences.set({ key, value });
    return;
  }
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(key, value);
  }
}
```

- [ ] **Step 3: Write the failing test**

```typescript
// web/tests/native/haptics.test.ts
import { describe, it, expect, vi } from "vitest";

describe("haptics wrapper", () => {
  it("is a no-op on web", async () => {
    const haptics = await import("@/lib/native/haptics");
    // Should not throw, should not import @capacitor/haptics
    await haptics.lightImpact();
    await haptics.mediumImpact();
  });
});
```

- [ ] **Step 4: Run — passes (web no-op)**

```bash
cd web && npm test -- --run web/tests/native/haptics.test.ts
```

- [ ] **Step 5: Wire into Board.tsx**

Find the user-move dispatcher in `web/components/Board.tsx`. After the click handler accepts the move (just before WS send):

```typescript
import { lightImpact, mediumImpact, warning } from "@/lib/native/haptics";

// in onIntersectionClick or equivalent:
await lightImpact();
```

For capture detection, the existing animation logic likely flags captures — call `mediumImpact()` there. For the "illegal move" toast path, call `warning()`.

- [ ] **Step 6: Add the toggle to settings page**

In `web/app/settings/page.tsx`, add a toggle row:

```typescript
import { getPref, setPref } from "@/lib/native/preferences";
import { useEffect, useState } from "react";

const [hapticsOn, setHapticsOn] = useState(true);
useEffect(() => {
  getPref("haptics.enabled").then((v) => setHapticsOn(v !== "false"));
}, []);

// JSX:
<label className="flex items-center justify-between py-2">
  <span>{t("settings.hapticsEnabled")}</span>
  <input
    type="checkbox"
    checked={hapticsOn}
    onChange={(e) => {
      setHapticsOn(e.target.checked);
      setPref("haptics.enabled", String(e.target.checked));
    }}
  />
</label>
```

Add to ko/en.json:
- `settings.hapticsEnabled`: "햅틱 사용" / "Haptic feedback"

- [ ] **Step 7: Commit**

```bash
git add web/lib/native web/components/Board.tsx web/app/settings/page.tsx web/lib/i18n
git commit -m "feat(native): haptic feedback on stone placement + capture + warnings"
```

---

### Task D2: Share sheet for SGF

**Files:**
- Create: `web/lib/native/share.ts`
- Modify: SGF download caller (search for "/api/games/.+/sgf" usages)

- [ ] **Step 1: Create `web/lib/native/share.ts`**

```typescript
import { isNative } from "./platform";

/**
 * Share an SGF file. On native, writes to a temp file then opens the
 * system share sheet. On web, falls back to a download anchor.
 */
export async function shareSgf(
  filename: string,
  sgfContent: string
): Promise<void> {
  if (!isNative()) {
    const blob = new Blob([sgfContent], { type: "application/x-go-sgf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    return;
  }

  const { Filesystem, Directory, Encoding } =
    await import("@capacitor/filesystem");
  const { Share } = await import("@capacitor/share");

  const writeRes = await Filesystem.writeFile({
    path: filename,
    data: sgfContent,
    directory: Directory.Cache,
    encoding: Encoding.UTF8,
  });
  await Share.share({
    title: "AI Baduk SGF",
    files: [writeRes.uri],
  });
}
```

- [ ] **Step 2: Replace the existing SGF download caller**

```bash
grep -rn "/sgf" web/app web/components | head
```

Replace the `<a href="/api/games/{id}/sgf" download>` pattern with a button that calls:

```typescript
import { shareSgf, } from "@/lib/native/share";
import { apiUrl } from "@/lib/config";

async function onShareSgf(gameId: number) {
  const r = await fetch(apiUrl(`/api/games/${gameId}/sgf`));
  const sgf = await r.text();
  await shareSgf(`baduk-${gameId}.sgf`, sgf);
}
```

- [ ] **Step 3: Smoke test on iOS simulator**

```bash
cd web && npm run build:mobile
cd ../mobile && npx cap sync && npx cap open ios
# In Xcode, run on simulator. Finish a game, tap Share — should see the
# system share sheet.
```

- [ ] **Step 4: Commit**

```bash
git add web/lib/native/share.ts web/components web/app
git commit -m "feat(native): share SGF via system share sheet"
```

---

### Task D3: Sound effects + toggle

**Files:**
- Modify: `web/lib/soundfx.ts` (existing) or create
- Modify: `web/public/sounds/` (existing audio files; CHANGELOG says they're real samples already)

The 0.3.0 polish pack added real stone samples already. This task only adds the **mute toggle in settings** and ensures **iOS silent mode is respected**.

- [ ] **Step 1: Confirm samples exist**

```bash
ls web/public/sounds/
```

Expected: at least three `stone-*.mp3`. If fewer, see Plan 1 design for the agreed sample list and source from freesound.org with a CC-0 license.

- [ ] **Step 2: Add toggle to settings**

In `web/app/settings/page.tsx`, mirror the haptics toggle from Task D1:

```typescript
const [soundOn, setSoundOn] = useState(true);
useEffect(() => {
  getPref("sound.enabled").then((v) => setSoundOn(v !== "false"));
}, []);
```

- [ ] **Step 3: Update `soundfx.ts` to read the pref**

```typescript
import { getPref } from "./native/preferences";

export async function playStoneClick(): Promise<void> {
  const enabled = await getPref("sound.enabled");
  if (enabled === "false") return;
  // ... existing audio playback
}
```

- [ ] **Step 4: Add i18n keys**

`settings.soundEnabled`: "효과음" / "Sound effects"

- [ ] **Step 5: Commit**

```bash
git add web/lib web/app/settings web/lib/i18n
git commit -m "feat(settings): mute toggle for stone-click effect"
```

---

### Task D4: Status bar + dark mode sync

**Files:**
- Create: `web/lib/native/status-bar.ts`
- Modify: top-level layout or theme provider

- [ ] **Step 1: Create wrapper**

```typescript
// web/lib/native/status-bar.ts
import { isNative } from "./platform";

export async function setStatusBarStyle(theme: "light" | "dark"): Promise<void> {
  if (!isNative()) return;
  const { StatusBar, Style } = await import("@capacitor/status-bar");
  await StatusBar.setStyle({
    style: theme === "dark" ? Style.Dark : Style.Light,
  });
  await StatusBar.setBackgroundColor?.({
    color: theme === "dark" ? "#1A1814" : "#F5EFE6",
  });
}
```

- [ ] **Step 2: Wire into the theme provider**

The project uses `next-themes`. Locate the `ThemeProvider` setup in `web/app/layout.tsx`. Add a `useEffect` listener that calls `setStatusBarStyle` when the resolved theme changes:

```typescript
"use client";
import { useTheme } from "next-themes";
import { useEffect } from "react";
import { setStatusBarStyle } from "@/lib/native/status-bar";

export function StatusBarSync() {
  const { resolvedTheme } = useTheme();
  useEffect(() => {
    if (resolvedTheme === "dark" || resolvedTheme === "light") {
      setStatusBarStyle(resolvedTheme);
    }
  }, [resolvedTheme]);
  return null;
}
```

Mount `<StatusBarSync />` in the root layout.

- [ ] **Step 3: Smoke test**

Build + run iOS simulator. Toggle system Dark Mode (`⌘+Shift+A`). The status bar should switch to dark text on light bg + vice-versa.

- [ ] **Step 4: Commit**

```bash
git add web/lib/native/status-bar.ts web/app/layout.tsx
git commit -m "feat(native): status bar follows next-themes resolvedTheme"
```

---

### Task D5: Splash screen

**Files:**
- Modify: `mobile/capacitor.config.ts`

Asset generation in Task C4 already populated the platform assets. Add the runtime config so the splash auto-hides:

- [ ] **Step 1: Edit `mobile/capacitor.config.ts`**

```typescript
const config: CapacitorConfig = {
  // ... existing
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      launchShowDuration: 1000,
      backgroundColor: "#F5EFE6",
      androidScaleType: "CENTER_CROP",
      showSpinner: false,
    },
  },
};
```

- [ ] **Step 2: Sync + run**

```bash
cd mobile && npx cap sync && npx cap open ios
# Run on simulator — splash should fade after ~300ms
```

- [ ] **Step 3: Commit**

```bash
git add mobile/capacitor.config.ts
git commit -m "feat(mobile): splash screen runtime config"
```

---

## Phase E — Mobile UX

### Task E1: Safe-area padding

**Files:**
- Modify: `web/app/globals.css`
- Modify: top-level layout component

- [ ] **Step 1: Add CSS variables**

In `web/app/globals.css`:

```css
:root {
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
}

@supports (padding: env(safe-area-inset-top)) {
  body {
    padding-top: var(--safe-top);
    padding-bottom: var(--safe-bottom);
  }
}
```

- [ ] **Step 2: Add `viewport-fit=cover` meta**

In `web/app/layout.tsx`:

```tsx
export const viewport = {
  themeColor: "#F5EFE6",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};
```

- [ ] **Step 3: Smoke test**

Build, run iOS simulator with notched iPhone — board no longer hidden under the notch.

- [ ] **Step 4: Commit**

```bash
git add web/app
git commit -m "feat(mobile): safe-area padding for notched iPhones"
```

---

### Task E2: Disable pull-to-refresh

**Files:**
- Modify: `web/app/globals.css`

- [ ] **Step 1: Add overscroll behavior**

```css
html, body {
  overscroll-behavior-y: none;
}
```

- [ ] **Step 2: Verify on iOS simulator**

Try to drag down from the board top — the WebView no longer reloads.

- [ ] **Step 3: Commit**

```bash
git add web/app/globals.css
git commit -m "feat(mobile): block accidental pull-to-refresh"
```

---

### Task E3: Android back button intercept

**Files:**
- Create: `web/lib/native/back-button.ts`
- Create: `web/components/MobileBackGuard.tsx`
- Modify: `web/app/game/play/[id]/page.tsx` (mount the guard)

- [ ] **Step 1: Wrapper**

```typescript
// web/lib/native/back-button.ts
import { isNative } from "./platform";

type Handler = () => Promise<boolean> | boolean; // return true to prevent default

export async function onBackButton(handler: Handler): Promise<() => void> {
  if (!isNative()) return () => {};
  const { App } = await import("@capacitor/app");
  const sub = await App.addListener("backButton", async () => {
    const handled = await handler();
    if (!handled) {
      App.exitApp();
    }
  });
  return () => sub.remove();
}
```

- [ ] **Step 2: Guard component**

```typescript
// web/components/MobileBackGuard.tsx
"use client";
import { useEffect, useState } from "react";
import { onBackButton } from "@/lib/native/back-button";
import { useTranslation } from "@/lib/i18n";  // adjust hook name

export function MobileBackGuard({ active }: { active: boolean }) {
  const { t } = useTranslation();
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    let cancel: (() => void) | undefined;
    onBackButton(() => {
      if (!active) return false; // allow normal back
      setConfirmOpen(true);
      return true;
    }).then((c) => { cancel = c; });
    return () => { cancel?.(); };
  }, [active]);

  if (!confirmOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/50 grid place-items-center z-50">
      <div className="bg-paper dark:bg-paper-deep p-6 rounded-sm">
        <p className="mb-4">{t("game.backConfirm")}</p>
        <div className="flex gap-2 justify-end">
          <button onClick={() => setConfirmOpen(false)}>{t("common.cancel")}</button>
          <button onClick={() => { setConfirmOpen(false); window.history.back(); }}>
            {t("common.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
```

Add i18n keys: `game.backConfirm`, `common.cancel`, `common.confirm`.

- [ ] **Step 3: Mount in the game page**

```tsx
import { MobileBackGuard } from "@/components/MobileBackGuard";

// inside the game component, near the top of the JSX:
<MobileBackGuard active={!gameOver} />
```

- [ ] **Step 4: Test on Android emulator**

Run, start a game, hit the back button — confirm dialog. Hit on the home screen — exits the app.

- [ ] **Step 5: Commit**

```bash
git add web/lib/native/back-button.ts web/components/MobileBackGuard.tsx web/app web/lib/i18n
git commit -m "feat(mobile): Android back-button confirms before leaving an active game"
```

---

### Task E4: Network status banner

**Files:**
- Create: `web/lib/native/network.ts`
- Create: `web/components/OfflineBanner.tsx`
- Modify: top-level layout to mount it

- [ ] **Step 1: Network store**

```typescript
// web/lib/native/network.ts
import { create } from "zustand";
import { isNative } from "./platform";

interface NetState {
  online: boolean;
  setOnline: (v: boolean) => void;
}

export const useNetwork = create<NetState>((set) => ({
  online: typeof navigator !== "undefined" ? navigator.onLine : true,
  setOnline: (online) => set({ online }),
}));

export async function startNetworkMonitor(): Promise<() => void> {
  const { setOnline } = useNetwork.getState();
  if (isNative()) {
    const { Network } = await import("@capacitor/network");
    const sub = await Network.addListener("networkStatusChange", (s) => {
      setOnline(s.connected);
    });
    const initial = await Network.getStatus();
    setOnline(initial.connected);
    return () => sub.remove();
  }
  const onOn = () => setOnline(true);
  const onOff = () => setOnline(false);
  window.addEventListener("online", onOn);
  window.addEventListener("offline", onOff);
  return () => {
    window.removeEventListener("online", onOn);
    window.removeEventListener("offline", onOff);
  };
}
```

- [ ] **Step 2: Banner component**

```tsx
// web/components/OfflineBanner.tsx
"use client";
import { useEffect } from "react";
import { useNetwork, startNetworkMonitor } from "@/lib/native/network";
import { useTranslation } from "@/lib/i18n";

export function OfflineBanner() {
  const online = useNetwork((s) => s.online);
  const { t } = useTranslation();
  useEffect(() => { startNetworkMonitor(); }, []);
  if (online) return null;
  return (
    <div className="fixed top-0 inset-x-0 bg-oxblood text-paper px-4 py-2 text-center z-50">
      {t("network.offline")}
    </div>
  );
}
```

i18n: `network.offline`: "오프라인 — 다시 연결될 때까지 대기 중" / "Offline — waiting to reconnect"

- [ ] **Step 3: Mount in layout**

In `web/app/layout.tsx`, render `<OfflineBanner />` once.

- [ ] **Step 4: Smoke test on iOS simulator**

Toggle Airplane Mode. Banner appears. Restore. Banner clears.

- [ ] **Step 5: Commit**

```bash
git add web/lib/native/network.ts web/components/OfflineBanner.tsx web/app web/lib/i18n
git commit -m "feat(mobile): offline banner driven by Network plugin"
```

---

### Task E5: App lifecycle → WS reconnect

**Files:**
- Modify: `web/lib/ws.ts` (or its singleton init)
- Use: `web/lib/native/lifecycle.ts` (create)

- [ ] **Step 1: Create wrapper**

```typescript
// web/lib/native/lifecycle.ts
import { isNative } from "./platform";

export async function onAppForeground(handler: () => void): Promise<() => void> {
  if (!isNative()) return () => {};
  const { App } = await import("@capacitor/app");
  const sub = await App.addListener("appStateChange", (s) => {
    if (s.isActive) handler();
  });
  return () => sub.remove();
}
```

- [ ] **Step 2: Wire into WS singleton**

Wherever the WS is created (likely `web/lib/ws.ts` on first import), add:

```typescript
import { onAppForeground } from "@/lib/native/lifecycle";

if (typeof window !== "undefined") {
  onAppForeground(() => {
    // Force reconnect if socket is closed
    if (socket && socket.readyState !== WebSocket.OPEN) {
      reconnect();
    }
  });
}
```

- [ ] **Step 3: Test on iOS simulator**

Start a game, send the app to background (`⌘+Shift+H`), wait 60s, reopen. Game state restores instantly without manual refresh.

- [ ] **Step 4: Commit**

```bash
git add web/lib/native/lifecycle.ts web/lib/ws.ts
git commit -m "feat(mobile): force WS reconnect on appStateChange→active"
```

---

### Task E6: Files-app `.sgf` handler (Tier 2)

**Files:**
- Modify: `mobile/ios/App/App/Info.plist`
- Modify: `mobile/android/app/src/main/AndroidManifest.xml`
- Create: `web/lib/sgf-import.ts`
- Modify: `web/app/layout.tsx` to register the URL listener

- [ ] **Step 1: iOS — add document type to Info.plist**

In Xcode, open `App/Info.plist`. Add a `CFBundleDocumentTypes` array with:

```xml
<key>CFBundleDocumentTypes</key>
<array>
  <dict>
    <key>CFBundleTypeName</key>
    <string>SGF Game Record</string>
    <key>LSHandlerRank</key>
    <string>Default</string>
    <key>LSItemContentTypes</key>
    <array>
      <string>public.sgf</string>
    </array>
  </dict>
</array>
<key>UTImportedTypeDeclarations</key>
<array>
  <dict>
    <key>UTTypeIdentifier</key>
    <string>public.sgf</string>
    <key>UTTypeDescription</key>
    <string>Smart Game Format</string>
    <key>UTTypeConformsTo</key>
    <array><string>public.text</string></array>
    <key>UTTypeTagSpecification</key>
    <dict>
      <key>public.filename-extension</key>
      <array><string>sgf</string></array>
      <key>public.mime-type</key>
      <array><string>application/x-go-sgf</string></array>
    </dict>
  </dict>
</array>
```

- [ ] **Step 2: Android — intent filter**

In `mobile/android/app/src/main/AndroidManifest.xml`, inside the main `<activity>`:

```xml
<intent-filter android:label="@string/title_activity_main">
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="file" />
  <data android:scheme="content" />
  <data android:mimeType="*/*" />
  <data android:pathPattern=".*\\.sgf" />
</intent-filter>
```

- [ ] **Step 3: Create `web/lib/sgf-import.ts`**

```typescript
import { isNative } from "./native/platform";

export async function startSgfUrlListener(navigateToReview: (sgf: string) => void): Promise<() => void> {
  if (!isNative()) return () => {};
  const { App } = await import("@capacitor/app");
  const { Filesystem } = await import("@capacitor/filesystem");
  const sub = await App.addListener("appUrlOpen", async (e) => {
    if (!e.url.endsWith(".sgf")) return;
    try {
      const r = await Filesystem.readFile({ path: e.url });
      const sgf = typeof r.data === "string" ? r.data : "";
      navigateToReview(sgf);
    } catch {
      // user opened a file we don't have access to
    }
  });
  return () => sub.remove();
}
```

- [ ] **Step 4: Register in layout**

```typescript
import { startSgfUrlListener } from "@/lib/sgf-import";
import { useRouter } from "next/navigation";

useEffect(() => {
  let cancel: (() => void) | undefined;
  startSgfUrlListener((sgf) => {
    sessionStorage.setItem("baduk.import.sgf", sgf);
    router.push("/review/import");
  }).then((c) => { cancel = c; });
  return () => { cancel?.(); };
}, []);
```

(`/review/import` is a route that reads from sessionStorage and renders the existing review UI. If the import flow doesn't fit V1, this task can be cut to defer to V1.1.)

- [ ] **Step 5: Smoke test on iOS**

In the simulator: open Files app, place an `.sgf` file in iCloud Drive, tap it. The Share Sheet shows AI Baduk as an option. Tap → app opens to review.

- [ ] **Step 6: Commit**

```bash
git add mobile/ios mobile/android web/lib/sgf-import.ts web/app
git commit -m "feat(mobile): Files app .sgf handler (Tier 2 native enhancement)"
```

---

## Phase F — Mobile E2E + final smoke

### Task F1: Playwright mobile viewport scenarios

**Files:**
- Modify: `e2e/playwright.config.ts` (mobile project)
- Create: `e2e/tests/mobile/onboarding.spec.ts`
- Create: `e2e/tests/mobile/offline-banner.spec.ts`
- Create: `e2e/tests/mobile/dark-mode-auto.spec.ts`

The two more network-dependent scenarios (background-resume, share-sgf) are deferred to manual TestFlight QA — mocking Capacitor lifecycle in Playwright is complex and the value is low.

- [ ] **Step 1: Add a mobile project to playwright.config.ts**

```typescript
projects: [
  // ... existing
  {
    name: "mobile-iphone",
    use: { ...devices["iPhone 14 Pro"] },
  },
],
```

- [ ] **Step 2: Onboarding scenario**

```typescript
// e2e/tests/mobile/onboarding.spec.ts
import { test, expect } from "@playwright/test";

test.use({ viewport: { width: 393, height: 852 } });

test("first-run nickname → new game → first stone", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("textbox", { name: /nickname/i }).fill("e2etester");
  await page.getByRole("button", { name: /start|시작/i }).click();
  await page.getByRole("button", { name: /new game|새 게임/i }).click();
  await page.getByText(/19×19/i).click();
  await page.getByRole("button", { name: /start|시작/i }).click();
  // First stone — click center
  const board = page.locator("svg[data-testid='board']");
  const box = await board.boundingBox();
  if (!box) throw new Error("no board");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  // Expect captures = 0 + my move recorded
  await expect(page.locator("[data-testid='move-count']")).toContainText("1");
});
```

- [ ] **Step 3: Offline banner scenario**

```typescript
// e2e/tests/mobile/offline-banner.spec.ts
import { test, expect } from "@playwright/test";

test("offline banner appears on network drop and clears on restore", async ({
  page,
  context,
}) => {
  await page.goto("/");
  await context.setOffline(true);
  await expect(page.getByText(/offline|오프라인/i)).toBeVisible();
  await context.setOffline(false);
  await expect(page.getByText(/offline|오프라인/i)).toBeHidden({ timeout: 5_000 });
});
```

- [ ] **Step 4: Dark-mode scenario**

```typescript
// e2e/tests/mobile/dark-mode-auto.spec.ts
import { test, expect } from "@playwright/test";

test("system colorScheme switch updates body class", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).not.toHaveClass(/dark/);
});
```

- [ ] **Step 5: Run**

```bash
cd e2e && npm test -- mobile
```

Expected: 3 passing.

- [ ] **Step 6: Commit**

```bash
git add e2e
git commit -m "test(e2e): mobile-viewport onboarding/offline/dark scenarios"
```

---

### Task F2: Manual TestFlight smoke

**Files:** none (runbook)

Before declaring Plan 2 done, verify on a real iPhone via TestFlight Internal Testing:

- [ ] **Step 1: Archive in Xcode**

Product → Archive. After ~5 min, Organizer opens.

- [ ] **Step 2: Distribute → App Store Connect → Upload**

Sign with the production cert (Plan 3 prereq). Wait ~10 min for processing.

- [ ] **Step 3: Add yourself as an Internal Tester**

App Store Connect → TestFlight → Internal Testing → Create Group → Add yourself by Apple ID. Internal testing distributes within minutes; no Beta App Review.

- [ ] **Step 4: Install via TestFlight on your iPhone**

Launch. Verify all of:

- [ ] App launches in < 3s on first run
- [ ] Splash screen renders, fades cleanly
- [ ] Nickname picker accepts input, taps land precisely
- [ ] New game starts; board renders fully (no Notch overlap)
- [ ] First move places stone immediately + light haptic fires
- [ ] AI replies within 3s (KataGo Metal pool from Plan 1)
- [ ] Capture event triggers medium haptic
- [ ] Background → 30s → foreground → game state restored
- [ ] Toggle Wi-Fi/cellular → offline banner appears + clears
- [ ] Resign → result modal renders correctly
- [ ] Share SGF → system share sheet opens, can save to Files
- [ ] System Dark Mode → app follows immediately, status bar inverts
- [ ] Settings page haptics + sound toggles persist across kills

If any item fails, file an issue and fix before tagging.

- [ ] **Step 5: Repeat on Android**

Build a debug APK from Android Studio (`Build → Build APK`), install via `adb install`. Same checklist except where noted (`Android back button confirms instead of share-sheet test`).

- [ ] **Step 6: Tag**

```bash
git tag -a mobile-shell-ready -m "Plan 2 complete — Capacitor builds work end-to-end"
```

---

## Final Verification

- [ ] **Web tests still green**

```bash
cd web && npm test -- --run && npm run type-check && npm run lint
```

- [ ] **Backend tests still green**

```bash
cd backend && source .venv311/bin/activate && KATAGO_MOCK=true pytest --cov=app --cov-fail-under=80 -q
```

- [ ] **Mobile builds**

```bash
cd web && npm run build && npm run build:mobile
cd ../mobile && npx cap sync && npx cap copy
```

- [ ] **No new design-token violations**

Dispatch the `design-token-guardian` agent on `web/components/`, `web/app/`, `web/lib/native/`. Expected: 0 violations.

- [ ] **Korean copy QA pass**

Dispatch `korean-copy-qa` agent. Expected: parity preserved + 12 polish items applied.

---

## Sign-off

Plan 2 is done when **all** are true:

- iOS .ipa archives in Xcode and uploads to App Store Connect; TestFlight Internal install works on device
- Android debug APK installs and runs through the smoke checklist on emulator + (ideally) a real device
- The 5 design-token violations are gone; the 12 i18n copy fixes have shipped
- Frontend P0/P1 items (P0-11 WS queue, P1-3 resign UI, P1-4 ScorePanel) are committed
- All Phase A–F commits merged to `main`
- All tests + lints + builds pass on a clean clone

Plan 3 (Store launch ops) starts from this baseline.
