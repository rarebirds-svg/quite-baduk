# App Store Launch — Plan 3: Store Launch Operations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the working backend (Plan 1) + working mobile builds (Plan 2) and ship them through Apple App Store and Google Play Store as **AI 바둑 / AI Baduk**, free, no IAP, target launch **2026-06-03 ± a few days**.

**Architecture:** Almost no code. The bulk of this plan is **runbook entries** — domain registrar, Cloudflare DNS, Apple Developer Program, App Store Connect, Google Play Console — with a few small frontend changes to update Privacy/Terms content for the anonymous-session model (P0-6, P0-7) and add a mobile menu entry-point to those pages. The plan also includes the asset pipeline (icon, splash, screenshots), all store-listing copy in ko/en, and the 14-day Play Closed Testing operation.

**Tech Stack:** Web consoles (Cloudflare, App Store Connect, Play Console), Apple Developer enrollment, design tooling for icons/screenshots (any vector tool), Playwright for capturing screenshots in mobile viewports.

---

## Critical Path & Dates

Today is **Sunday 2026-05-03**. The dates below assume launch is on track. **Each ⏰-marked task must start on its target day or the launch slips.**

```
Day 1  — 5/3 (today, ⏰)  Domain purchase + Apple Developer + Play Console
                          enrollments + Cloudflare account
Day 2~5                   Apple/Play account approvals trickle in
Day 5  — 5/7              Privacy/Terms content + mobile menu entry
Day 7  — 5/9              Icons + splash master design + auto-generate
Day 8  — 5/10             Screenshots captured (ko + en, 12 total)
Day 10 — 5/13 (⏰)        First .aab to Play Closed Testing
                          → 14-day mandatory window starts
Day 14 — 5/17             First .ipa to TestFlight Internal Testing
Day 14~24                 Beta feedback loop, store listing copy filled
Day 24 — 5/27 (⏰)        App Store: submit for review
                          Play: request Production access (14 days complete)
Day 27~30                 Apple review (24-48h typical) + Play review (1-3 days)
Day 30 — 6/3 (target)     Manual production release on both stores
```

Beta tester recruitment runs **continuously from Day 1 through Day 10**. Aim for 12+ opt-ins by Day 9.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `web/app/privacy/page.tsx` | Modify | Reflect anonymous-session model; remove email/password mentions; data-collection statement |
| `web/app/terms/page.tsx` | Modify | GRAC self-rating block; youth-protection officer notice |
| `web/app/support/page.tsx` | Create | Public support page (`mailto:` + FAQ entries from issues seen during beta) |
| `web/app/layout.tsx` | Modify | Footer / settings link to Privacy + Terms + Support so reviewers can find them in-app |
| `web/components/MobileMenu.tsx` (or settings page) | Modify | Visible link to Privacy/Terms/Support inside the app |
| `web/lib/i18n/ko.json`, `en.json` | Modify | Privacy/Terms/Support strings (must mirror Plan 2 changes — apply on top of Plan 2) |
| `mobile/resources/icon.png` | Create | 1024×1024 master icon (delivered in Plan 2 Phase C4 if not done) |
| `mobile/resources/splash.png` / `splash-dark.png` | Create | 2732×2732 splash masters |
| `docs/store/copy.md` | Create | Single source of truth for store listing copy (ko + en) |
| `docs/store/screenshots/` | Create | Final 12 PNGs (1290×2796) named consistently |
| `docs/store/beta-tester-guide-ko.md` | Create | One-pager for Korean testers |
| `docs/store/beta-tester-guide-en.md` | Create | One-pager for English testers |
| `docs/store/release-notes-1.0.0.md` | Create | "What's New" copy for both stores |
| `e2e/tools/screenshot-capture.spec.ts` | Create | Playwright job that captures the 6 baseline screens at iPhone 14 Pro viewport for compositing |

---

## Phase A — Day 1 critical registrations

These four tasks are **independent**. Start all four in parallel today. Most of the time spent is queueing for approvals — the active human time is < 1 hour total.

### Task A1: Buy domain (~10 min active, instant approval)

- [ ] **Step 1: Pick a name**

Candidates discussed: `aibaduk.app`, `baduk.kr`, `baduk.io`. **Pick one** and stick with it — every Bundle ID, store listing, and email channel below will reference this exact domain. If your top pick is taken, fall back: `aibaduk.app` → `aibaduk.kr` → `play-baduk.com`.

- [ ] **Step 2: Register at Cloudflare Registrar (preferred) or any registrar**

Cloudflare Registrar is at-cost (no markup). At the Cloudflare dashboard:

  Domains → Register Domains → search → check out

If using a Korean registrar (가비아 / 후이즈) for `.kr`, register first, then point the nameservers to Cloudflare in Step 3.

- [ ] **Step 3: Move nameservers to Cloudflare (skip if registered AT Cloudflare)**

Cloudflare → Add a Site → enter your domain → Free plan → Cloudflare gives you two nameservers (e.g. `nina.ns.cloudflare.com`, `paul.ns.cloudflare.com`). Set those at the registrar.

- [ ] **Step 4: Verify**

Wait 5~30 min. Then:

```bash
dig +short NS yourdomain
```

Expected: the two Cloudflare nameservers.

- [ ] **Step 5: Note the domain in your project notes**

Append to `docs/store/copy.md` (create the file if missing):

```markdown
# Store metadata source-of-truth

- Domain: <domain>
- Bundle ID (iOS) / Application ID (Android): <reverse.domain>.baduk
  (e.g. domain `aibaduk.app` → ID `app.aibaduk.baduk`)
```

- [ ] **Step 6: Commit (the doc, not credentials)**

```bash
git add docs/store/copy.md
git commit -m "docs(store): record domain + bundle id"
```

---

### Task A2: Enroll in Apple Developer Program (~20 min active, 1-3 day approval)

- [ ] **Step 1: Make sure you have an Apple ID with 2FA enabled**

Sign in at https://appleid.apple.com — confirm 2FA + a trusted phone number.

- [ ] **Step 2: Enroll**

Visit https://developer.apple.com/programs/enroll/

Choose **Individual** (not Organization). Organization requires a DUNS number which adds 1-4 weeks. Individual is sufficient for a personal launch — the developer name shown on the App Store will be your legal name.

Pay USD $99 (or local-currency equivalent).

- [ ] **Step 3: Wait for approval**

Apple emails you when the membership is active — usually within 24 hours, sometimes up to 3 days.

While waiting, proceed with A1, A3, A4. **No further Plan 3 task requires Apple approval until Phase B.**

---

### Task A3: Enroll in Google Play Console (~20 min active, 1-7 day approval)

- [ ] **Step 1: Sign up**

Visit https://play.google.com/console/signup. Pay USD $25 (one-time).

Choose **Individual account** (Organization adds verification overhead).

- [ ] **Step 2: Identity verification**

Google requires a government-issued ID photo. Upload it during signup. Approval window: hours to a week (usually 1-2 days).

- [ ] **Step 3: Watch for the verification email**

While waiting: A4 (Cloudflare) and Phase C (Privacy/Terms updates) and Phase D (assets) can all proceed.

> **2023.11+ policy reminder:** Once approved, **the 14-day Closed Testing requirement begins from your first Closed Testing release** (Phase G), not from account approval. So delays here only push the start of that 14-day window.

---

### Task A4: Cloudflare account setup (~10 min, instant)

- [ ] **Step 1: Create account**

https://dash.cloudflare.com/sign-up — confirm email, enable 2FA.

- [ ] **Step 2: Enable Free plan for the domain (already done if A1 used Cloudflare Registrar)**

- [ ] **Step 3: Generate an R2 bucket for backups (Plan 1 D4 dependency)**

R2 → Create Bucket → name `baduk-backups`. Generate API tokens with Object Read + Write. Save the credentials securely (1Password / macOS Keychain).

- [ ] **Step 4: Create a "Cloudflare Tunnel" placeholder**

This is just so the dashboard auth works when you actually configure the tunnel in Plan 1 D2. You don't need to start the tunnel yet.

Zero Trust → Networks → Tunnels → Create a tunnel → name `baduk` → Save.

- [ ] **Step 5: Move on**

A4 is done. Wait for A2/A3 approvals to come through.

---

## Phase B — Identity setup (after A2/A3 approve)

### Task B1: Register Bundle ID + App ID (after Apple approves A2)

- [ ] **Step 1: Apple Developer → Certificates, IDs & Profiles**

https://developer.apple.com/account → Identifiers → +

Type: **App IDs** → App.

Description: `AI Baduk`
Bundle ID: explicit, e.g. `app.aibaduk.baduk` (replace with your reverse-domain choice from A1).

Capabilities: leave defaults. We don't use push, sign-in-with-apple, in-app purchase, or HealthKit. Adding capabilities later requires re-signing.

Save.

- [ ] **Step 2: Cross-reference in `docs/store/copy.md`**

Update the Bundle ID line if you changed it from the A1 placeholder.

---

### Task B2: Create the App Store Connect app record (after B1)

- [ ] **Step 1: Visit App Store Connect → My Apps → +**

https://appstoreconnect.apple.com

- [ ] **Step 2: Fill the new-app form**

| Field | Value |
|---|---|
| Platform | iOS |
| App Name | `AI 바둑` (this is the primary localization; we'll set en-US below) |
| Primary Language | Korean (Korea) — `ko_KR` |
| Bundle ID | (select the one registered in B1) |
| SKU | `baduk-1` (any unique string) |
| User Access | Full Access |

Save. The app record now exists. Most fields are still blank — fill in Phase E.

- [ ] **Step 3: Add the English localization**

In the new app record: App Information → Localizable Information → +Add Language → `English (U.S.)`.

App Name: `AI Baduk`.

Save.

- [ ] **Step 4: Note app store record IDs**

Append to `docs/store/copy.md`:

```markdown
- App Store Connect app ID: <numeric ID from URL>
- App Store Connect localizations: ko-KR (primary), en-US
```

---

### Task B3: Create the Google Play Console app record (after A3 approves)

- [ ] **Step 1: Play Console → Create app**

https://play.google.com/console

| Field | Value |
|---|---|
| App name | `AI 바둑` |
| Default language | Korean (South Korea) — `ko-KR` |
| App or game | Game |
| Free or paid | Free |
| Declarations | Confirm: developer policies, US export laws, Play app signing, etc. |

Create.

- [ ] **Step 2: Add English store listing**

Grow → Store presence → Main store listing → +Add language → English (United States).

App name: `AI Baduk`.

- [ ] **Step 3: Set Application ID**

Inside Play Console there's no "create Application ID" step — the ID is bound when you upload your first .aab in Phase G. **It must match** your reverse-domain choice (e.g. `app.aibaduk.baduk`). Set this in `mobile/capacitor.config.ts` (Plan 2 Task C1) before you build the .aab.

- [ ] **Step 4: Note IDs**

Append to `docs/store/copy.md`:

```markdown
- Play Console app ID: <numeric ID from URL>
- Play Console localizations: ko-KR (default), en-US
```

---

## Phase C — Privacy / Terms / Support content (P0-6, P0-7)

### Task C1: Rewrite Privacy policy

**Files:**
- Modify: `web/app/privacy/page.tsx`
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

The current text predates the move to ephemeral nickname sessions and may still mention emails / passwords. Rewrite to match reality and to match the Apple/Google data-label declarations in Phase E.

- [ ] **Step 1: Read existing content**

```bash
cat web/app/privacy/page.tsx
```

Identify any mention of email, password, JWT, OAuth, refresh token, third-party login. None of these should remain.

- [ ] **Step 2: Replace privacy content with the model below**

Header: `개인정보처리방침 / Privacy Policy`. Effective date: today.

**Sections (apply in both ko and en):**

```
1. What we collect
   - A self-chosen nickname (not your real name)
   - Game records (board state, moves, timestamps, KataGo's analyses)
   - Your IP address, used only for rate limiting; never logged with the
     nickname together. Anonymized after 24h.

2. What we DO NOT collect
   - No email, phone number, real name, or any other personal identifier
   - No password (sessions are token-only, in HttpOnly cookies)
   - No payment, no in-app purchases, no advertising identifiers
   - No location, contacts, photos, microphone, camera, or files

3. Sharing
   - We do not share data with third parties.
   - The KataGo engine that generates AI moves runs on our own servers.

4. Storage and deletion
   - Sessions are deleted automatically after 1h of inactivity.
   - Game records are stored as long as the account exists. Since
     accounts are anonymous, you can erase yours by clearing your
     browser's site data; on the mobile app, by uninstalling.
   - You may request a manual deletion of game records at <support email>.

5. Legal
   - Service operator: <Your name>
   - Contact: <support email>
   - Korean youth-protection officer: <Your name> / <support email>
   - Last updated: 2026-05-XX
```

- [ ] **Step 3: Translate**

Korean version is the primary; produce a faithful English version. Keep both at the same level of detail. (You can run them through `korean-copy-qa` agent at the end of Phase C.)

- [ ] **Step 4: Wire i18n keys**

Add a `privacy.*` namespace with one key per section heading + body. The page reads from `t("privacy.section1Title")` etc. Avoid putting whole paragraphs into JSX as raw text.

- [ ] **Step 5: Verify**

```bash
npm run dev
# visit /privacy in both ko and en — content matches the model above
```

- [ ] **Step 6: Commit**

```bash
git add web/app/privacy web/lib/i18n
git commit -m "docs(privacy): rewrite for anonymous-session model + GRAC notice"
```

---

### Task C2: Rewrite Terms of Service + GRAC self-rating

**Files:**
- Modify: `web/app/terms/page.tsx`
- Modify: `web/lib/i18n/ko.json`, `web/lib/i18n/en.json`

Korean app distribution requires a **자체등급분류 사업자** notice. Apple and Google are themselves registered self-rating businesses (자체등급분류사업자), so we just **disclose** that fact and the rating they assigned (Everyone / 4+ / 전체이용가).

- [ ] **Step 1: Replace Terms content with the model below**

```
1. Service description
   AI Baduk lets you play Go (Baduk) against the KataGo Human-SL model.
   No real-time multiplayer, no advertising, no purchases.

2. Acceptable use
   Don't use the service to abuse, harass, or impersonate others.
   Don't attempt to overload the system (rate limits apply).

3. Account
   Sessions are anonymous. We may purge inactive sessions and game
   records to free server space.

4. Disclaimer
   The service is provided "as is" with no warranty. KataGo's analyses
   are advisory, not authoritative.

5. Termination
   We may terminate access if you violate Section 2.

6. Korean Game Rating (한국 게임물관리위원회)
   This game is distributed through Apple App Store / Google Play Store,
   both of which are registered Korean self-rating businesses
   (자체등급분류사업자). The assigned rating is 전체이용가 / Everyone /
   4+. The game is a strategy board game with no violence, sexual
   content, gambling, or drug content.

7. Youth-protection officer (청소년 보호 책임자)
   Name: <Your name>
   Contact: <support email>

8. Governing law
   Republic of Korea, Seoul Central District Court as the venue of
   first instance.

9. Last updated: 2026-05-XX
```

- [ ] **Step 2: Apply same i18n + verify pattern as C1**

- [ ] **Step 3: Commit**

```bash
git add web/app/terms web/lib/i18n
git commit -m "docs(terms): rewrite with GRAC self-rating + youth-protection officer"
```

---

### Task C3: Support page

**Files:**
- Create: `web/app/support/page.tsx`

- [ ] **Step 1: Decide on a support channel**

Options:
- (a) `support@<domain>` mailbox forwarded to your existing Gmail. Simple and good enough for V1.
- (b) Public GitHub Issues — creates noise, exposes the repo. Skip for V1.
- (c) Linear / Tally form — overkill for solo + free.

Pick (a). Set up a forward in Cloudflare Email Routing (free, takes 2 min).

- [ ] **Step 2: Create the page**

`web/app/support/page.tsx`:

```tsx
import { useT } from "@/lib/i18n";

export default function SupportPage() {
  const t = useT();
  return (
    <main className="prose-paper py-10">
      <h1 className="font-serif text-3xl mb-6">{t("support.title")}</h1>
      <p>{t("support.intro")}</p>
      <p>
        <a href="mailto:support@<domain>" className="text-oxblood underline">
          support@<domain>
        </a>
      </p>
      <h2 className="font-serif text-xl mt-10 mb-4">{t("support.faqTitle")}</h2>
      <details>
        <summary>{t("support.faq.q1")}</summary>
        <p>{t("support.faq.a1")}</p>
      </details>
      {/* repeat for q2..q5 */}
    </main>
  );
}
```

- [ ] **Step 3: Seed FAQ entries (5 most likely)**

In ko.json + en.json under `support.faq.*`:

| Q | A |
|---|---|
| AI가 너무 강해요 / 약해요 — 강도를 어떻게 바꾸나요? | Settings → Rank Picker. 18급부터 5단까지. |
| 기보(SGF)는 어디서 받나요? | 게임 종료 후 "공유" 버튼. 모바일은 시스템 공유 시트. |
| 핸디캡(접바둑)은 어떻게 두나요? | 새 게임 화면에서 2~9점. 한국 룰 자동 적용 (덤 0.5). |
| 모바일에서 게임이 끊겨요 | 백그라운드 60초 이상이면 재연결. 안 되면 앱 재시작. |
| 데이터를 삭제하고 싶어요 | 익명이라 별도 삭제 절차 불필요. 앱 삭제 또는 브라우저 데이터 삭제. |

- [ ] **Step 4: Add `support.*` keys to i18n**

- [ ] **Step 5: Wire footer / settings entry to it**

In `web/components/MobileMenu.tsx` (or settings page), add three rows:

```tsx
<a href="/privacy">{t("nav.privacy")}</a>
<a href="/terms">{t("nav.terms")}</a>
<a href="/support">{t("nav.support")}</a>
```

This is the **must-be-discoverable** path that App Store reviewers explicitly check.

- [ ] **Step 6: Commit**

```bash
git add web/app/support web/components web/lib/i18n
git commit -m "feat(support): public support page + nav links to privacy/terms/support"
```

---

## Phase D — Visual assets

### Task D1: 1024×1024 master icon

**Files:**
- Create: `mobile/resources/icon.png`

Concept (agreed in brainstorming): **black + white stones overlapping monogram** on `bg-paper` (`#F5EFE6`). No text. Two stones at ~30% offset; black on left, white on right; subtle 1px stroke on the white stone for separation.

- [ ] **Step 1: Open your vector tool**

Figma, Sketch, Affinity Designer, or even Pixelmator. 1024×1024 canvas.

- [ ] **Step 2: Layer the monogram**

- Background fill: `#F5EFE6`
- Black stone: 700px diameter circle, fill `#1A1814` (Editorial ink), centered at (350, 512)
- White stone: 700px diameter circle, fill `#F5EFE6`, 1px stroke `#1A1814`, centered at (674, 512)
- White stone is on top so the overlap appears as if the white is laid down second.

Tweak overlap until it visually balances. The final monogram should occupy ~85% of the canvas (leaving ~75px margin on every side for iOS rounded-corner mask + safe area).

- [ ] **Step 3: Export 1024×1024 PNG**

Save as `mobile/resources/icon.png`. No transparency — a fully opaque background.

- [ ] **Step 4: Sanity-check**

```bash
file mobile/resources/icon.png
# should print: PNG image data, 1024 x 1024
```

Open in Preview. Squint. If it reads as "two go stones, monogram-style" at 60×60 pt (your Mac's dock icon size when shrunk), you're done. If it looks fussy, simplify.

- [ ] **Step 5: Commit**

```bash
git add mobile/resources/icon.png
git commit -m "feat(brand): app icon master (stone monogram)"
```

---

### Task D2: Splash 2732×2732 + dark variant

**Files:**
- Create: `mobile/resources/splash.png`
- Create: `mobile/resources/splash-dark.png`

The splash sees the same monogram, just centered on a much larger canvas. Capacitor will auto-crop per device.

- [ ] **Step 1: 2732×2732 canvas, light variant**

- Background: `#F5EFE6`
- Monogram: same as D1 but scaled to ~30% of canvas (≈ 800px diameter total) and centered.
- No text, no glow.

Save as `mobile/resources/splash.png`.

- [ ] **Step 2: Dark variant**

- Background: `#1A1814` (Editorial ink-deep / paper-deep dark)
- Monogram colors INVERT: black stone now uses `#F5EFE6` (paper), white stone uses `#1A1814` (or `#0F0E0C` for slightly more contrast against the paper-deep BG).
- Stroke flips accordingly.

Save as `mobile/resources/splash-dark.png`.

- [ ] **Step 3: Commit**

```bash
git add mobile/resources/splash.png mobile/resources/splash-dark.png
git commit -m "feat(brand): splash masters (light + dark)"
```

---

### Task D3: Auto-generate platform variants

**Files:**
- Modifies generated platform asset directories under `mobile/ios` and `mobile/android`.

This is Plan 2 Task C4 (re-running it). Belongs here too if Plan 2 was deferred, since masters are now ready.

- [ ] **Step 1: Run @capacitor/assets**

```bash
cd mobile
npx capacitor-assets generate \
  --iconBackgroundColor "#F5EFE6" \
  --iconBackgroundColorDark "#1A1814" \
  --splashBackgroundColor "#F5EFE6" \
  --splashBackgroundColorDark "#1A1814"
```

- [ ] **Step 2: Sync**

```bash
npx cap sync
```

- [ ] **Step 3: Visual check**

Open Xcode (`npx cap open ios`) and Android Studio (`npx cap open android`). Run on simulator/emulator. Confirm:

- App icon shows monogram in light/dark
- Splash renders with monogram, fades out cleanly

- [ ] **Step 4: Commit (generated platform files)**

```bash
git add mobile/ios mobile/android
git commit -m "build(assets): regenerate platform icons + splashes from masters"
```

---

### Task D4: Feature graphic for Play (1024×500)

**Files:**
- Create: `mobile/resources/play-feature-graphic.png`

Play Console requires a 1024×500 banner shown at the top of the store listing.

- [ ] **Step 1: Design**

Wide horizontal canvas. Place the monogram on the left (vertically centered, occupying ~60% of canvas height). On the right, set in `font-serif` (Newsreader) two lines:

```
AI 바둑
KataGo와 한 판
```

(or English variant for the en listing — see E2 for canonical copy.)

Background: `#F5EFE6`. No drop shadows, no gradients.

- [ ] **Step 2: Save as PNG, 1024×500, RGB**

Path: `mobile/resources/play-feature-graphic.png`.

If you want a separate English version for `en-US`, save `play-feature-graphic-en.png` too.

- [ ] **Step 3: Commit**

```bash
git add mobile/resources/play-feature-graphic*.png
git commit -m "feat(brand): Play feature graphic (1024×500)"
```

---

### Task D5: Capture screenshots (12 total: 6 ko + 6 en)

**Files:**
- Create: `e2e/tools/screenshot-capture.spec.ts`
- Create: `docs/store/screenshots/{ko,en}/01..06.png`

Apple accepts a single 6.9" iPhone (1290×2796) screenshot per slot and auto-scales to other devices. Play wants 1080×1920 minimum. Use 1290×2796 for both — Play accepts any aspect ratio up to that.

- [ ] **Step 1: Write a Playwright capture spec**

`e2e/tools/screenshot-capture.spec.ts`:

```typescript
import { test } from "@playwright/test";

const VIEWPORT = { width: 393, height: 852 };       // iPhone 14 Pro CSS
const DEVICE_SCALE = 3;                              // → 1290×2796 raster

test.use({ viewport: VIEWPORT, deviceScaleFactor: DEVICE_SCALE });

const SCREENS = [
  { name: "01-home",     url: "/",          locale: "ko" },
  { name: "02-game",     url: "/game/play/<seed-id>", locale: "ko" },
  { name: "03-analysis", url: "/game/play/<seed-id>?hint=1", locale: "ko" },
  { name: "04-review",   url: "/game/<seed-id>/review", locale: "ko" },
  { name: "05-dark",     url: "/game/play/<seed-id>", locale: "ko" },
  { name: "06-stats",    url: "/history",   locale: "ko" },
];

for (const locale of ["ko", "en"] as const) {
  for (const s of SCREENS) {
    test(`${locale}/${s.name}`, async ({ page, context }) => {
      // Force locale
      await context.addCookies([{ name: "baduk.locale", value: locale, url: "http://localhost:3000" }]);
      // Force theme for the dark shot
      if (s.name.includes("dark")) {
        await page.emulateMedia({ colorScheme: "dark" });
      }
      await page.goto(s.url);
      await page.waitForLoadState("networkidle");
      await page.screenshot({
        path: `docs/store/screenshots/${locale}/${s.name}.png`,
        fullPage: false,
      });
    });
  }
}
```

You'll need to seed a game for `<seed-id>` — easiest is to create a fixture that creates a 19×19 game with 30 plies played, then store the id in env.

- [ ] **Step 2: Run capture**

Backend + frontend running locally:

```bash
cd e2e && npm test -- screenshot-capture
```

This produces 12 raw PNGs.

- [ ] **Step 3: Composite captions in a vector tool**

For each screen, add the caption text from the brainstorming spec (§7.4):

| # | Caption (ko) | Caption (en) |
|---|---|---|
| 01 | 18급에서 5단까지, 12개의 강도 | From 18-kyu to 5-dan |
| 02 | KataGo Human-SL이 사람처럼 둡니다 | KataGo plays like a human |
| 03 | 수마다 승률과 추천수 | Winrate and top moves, every move |
| 04 | 끝낸 게임, 한 수씩 복기 | Replay any game, move by move |
| 05 | 야간 모드 + 종이 결 | Editorial dark mode |
| 06 | 급수별 전적과 흐름 | Stats by rank and handicap |

Caption typography: `font-serif` Newsreader, 96pt, ink color, top 12% of the image; the captured screen scales to fit below.

- [ ] **Step 4: Save final composites**

`docs/store/screenshots/ko/01-home.png` etc., 1290×2796 each.

- [ ] **Step 5: Sanity check**

12 PNGs total, all sized 1290×2796. Drag into Preview slideshow — the captions should read as a coherent product story.

- [ ] **Step 6: Commit**

```bash
git add docs/store/screenshots e2e/tools/screenshot-capture.spec.ts
git commit -m "docs(store): launch screenshots (12 — ko + en)"
```

---

## Phase E — Store listing copy + console forms

This phase is mostly form-filling in the two web consoles, anchored by the canonical text in `docs/store/copy.md`.

### Task E1: Compose `docs/store/copy.md`

**Files:**
- Modify: `docs/store/copy.md` (created in A1)

Single source of truth. Whenever you edit a console field, copy from this file.

- [ ] **Step 1: Append the canonical copy**

```markdown
## App identity

| Field | ko | en |
|---|---|---|
| App name | AI 바둑 | AI Baduk |
| Subtitle | KataGo와 한 판 | Play against KataGo |
| Promotional text (iOS) | KataGo의 Human-SL 모델로 18급부터 5단까지 12단계 강도. 승률·복기·핸디캡 지원. | Play Go against KataGo Human-SL — 12 strength tiers from 18-kyu to 5-dan. |
| Short description (Play, ≤80) | 같은 텍스트 | 같은 텍스트 |

## Keywords (iOS, ≤100 chars each)

ko: `바둑,Go,KataGo,기원,복기,SGF,AI,두뇌,보드`
en: `Go,Baduk,Weiqi,KataGo,AI,SGF,review,board game,strategy`

## Full description

(ko)

> AI 바둑 — KataGo Human-SL과 두는 한국식 바둑.
>
> ▸ 12단계 강도 (18·15·12·10·7·5·3·1 급, 1·3·5 단)
> ▸ 핸디캡 2~9점, 한국 룰 (덤 6.5)
> ▸ 9×9 / 13×13 / 19×19 보드
> ▸ 매 수 승률·추천수 (힌트)
> ▸ 끝낸 게임 한 수씩 복기 + 분석 오버레이
> ▸ SGF 기보 저장·공유
> ▸ 한국어/영어, 라이트·다크 모드
> ▸ 익명 닉네임 — 이메일·비밀번호·결제 없음
>
> KataGo는 ELF/AlphaZero 계열의 오픈소스 바둑 엔진입니다. Human-SL 모델은 사람의 기보를 학습해 "약하게 두면서도 사람처럼 두는" 특성을 가집니다.
>
> 데이터 수집 없음. 광고 없음. 인앱 결제 없음.
>
> 문의: support@<domain>
> 약관: <domain>/terms
> 개인정보: <domain>/privacy

(en) — translate the above faithfully.

## Demo notes for reviewers (paste into App Store Connect Review Notes / Play Console internal notes)

> This app uses anonymous nickname sessions. Tap "Start" on the home
> screen, enter any nickname, and play immediately. No signup, login,
> or payment flow exists.
>
> KataGo (the AI engine) runs on our private server (api.<domain>),
> reachable from the App Store reviewer's network. Average AI response
> time: 0.5–2s.

## Age rating

iOS: 4+
Play: Everyone
GRAC: 전체이용가 (handled via self-rating businesses Apple/Google)

## Privacy
- Apple App Privacy: "Data Not Collected"
- Play Data Safety: No data collected, no data shared, encrypted in transit (HTTPS), no deletion request needed (data is anonymous)

## Pricing
Free, no IAP, no subscriptions.
```

- [ ] **Step 2: Sanity check character counts**

```bash
awk '/^- /{print length($0), $0}' docs/store/copy.md | sort -rn | head
```

Confirm: subtitle ≤ 30 chars (iOS), promotional text ≤ 170 chars, short desc ≤ 80 (Play).

- [ ] **Step 3: Run the i18n agent**

Dispatch `korean-copy-qa` agent on the new copy block. Apply any naturalness fixes.

- [ ] **Step 4: Commit**

```bash
git add docs/store/copy.md
git commit -m "docs(store): canonical listing copy ko + en"
```

---

### Task E2: Fill the App Store Connect listing

- [ ] **Step 1: App Store Connect → My Apps → AI Baduk → 1.0 Prepare for Submission**

For each language (ko-KR primary, en-US secondary):

- Promotional text: from `copy.md`
- Description: full description from `copy.md`
- Keywords: from `copy.md`
- Support URL: `https://<domain>/support`
- Marketing URL (optional): `https://<domain>/`
- Privacy Policy URL: `https://<domain>/privacy`

- [ ] **Step 2: Upload screenshots**

App Information → Screenshots → 6.9" iPhone → drag the 6 PNGs from `docs/store/screenshots/ko/` (and the en set into the en-US localization).

- [ ] **Step 3: App Privacy section**

App Information → App Privacy → Edit. Walk the questionnaire:

| Question | Answer |
|---|---|
| Do you or your third-party partners collect data from this app? | **No** |
| Anything else? | (skip — answer is No) |

Save. The label preview shows "Data Not Collected".

- [ ] **Step 4: Age Rating**

Pricing and Availability → Age Rating → Edit. All categories: None. Result: 4+.

- [ ] **Step 5: Review Notes**

App Review Information → Notes → paste the Demo notes from `copy.md`.

- [ ] **Step 6: Pricing & availability**

Free in all territories. Save.

- [ ] **Step 7: Tax forms**

Apple requires US tax forms (W-8BEN if non-US) before any free app can be released. Fill these now to avoid blocking the submission. Agreements, Tax, and Banking → Free Apps → accept the free-apps agreement → fill banking + tax. (Banking is required even for free apps, just for the legal record.)

- [ ] **Step 8: Save (don't submit yet)**

The build will be uploaded in Phase G.

---

### Task E3: Fill the Play Console listing

- [ ] **Step 1: Play Console → AI Baduk → Grow → Store presence → Main store listing**

For each language (ko-KR primary, en-US):

- App name: `AI 바둑` / `AI Baduk`
- Short description: from `copy.md`
- Full description: from `copy.md`
- App icon: upload 512×512 PNG (auto-generated by `@capacitor/assets`, located at `mobile/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png` or use the master 1024)
- Feature graphic: `mobile/resources/play-feature-graphic.png`
- Phone screenshots: drag 6 PNGs

- [ ] **Step 2: Privacy Policy URL**

Grow → Store presence → Main store listing → Privacy policy: `https://<domain>/privacy`.

- [ ] **Step 3: Data safety questionnaire**

Policy → App content → Data safety → Manage. Walk the questionnaire:

| Question | Answer |
|---|---|
| Does your app collect or share any of the required user data types? | **No** |
| Is all of the user data collected by your app encrypted in transit? | (n/a — no data collected) |
| Do you provide a way for users to request that their data be deleted? | (n/a) |

Submit. Label preview: "No data shared, no data collected".

- [ ] **Step 4: Content rating questionnaire**

Policy → App content → Content rating → Start questionnaire. Category: **Reference, news, or educational** is wrong — pick **Game** → **Card or board game** subcategory.

Walk the IARC questionnaire. All checkboxes: No (no violence, no language, no gambling, no etc.).

Result: Everyone (Korea: 전체이용가).

- [ ] **Step 5: Target audience**

Policy → App content → Target audience and content → 13+ (since it's not specifically for children — keeps the kid-friendly classification overhead off).

- [ ] **Step 6: Ads**

Policy → App content → Ads → Does your app contain ads? **No**.

- [ ] **Step 7: News app declaration**

Policy → App content → News apps → No.

- [ ] **Step 8: Save**

Phase G will upload the .aab.

---

## Phase F — Beta program (continuous, Day 1 → Day 24)

### Task F1: Recruit 12+ Closed Testing testers (start Day 1)

Play's 14-day requirement counts unique testers and active days. Aim for **15+** opt-ins to absorb churn.

- [ ] **Step 1: Create a Google Form**

Title: "AI 바둑 베타 테스트 (Play Store 14일 비공개)"

Fields:
- Name (optional)
- **Google Play account email** (required — used for Closed Testing membership)
- Phone OS (Android-only for Closed Testing, but ask about iOS for TestFlight too)
- Comments

Submit URL: a Google Sheet collects responses.

- [ ] **Step 2: Recruit channels**

Same-day starts:

- Family + close friends (1-on-1 message): 5-6 people
- Korean Go community (오로바둑 / 가오바둑 게시판) - 1 post each: 4-6 people
- Reddit r/baduk + r/AndroidBeta + r/playstore: 2-3 people
- Twitter/X with hashtag #바둑 #AlphaGo: 1-2 people

Bake the Google Form URL into each post.

- [ ] **Step 3: Track responses**

In `docs/store/beta-trackers.md` (gitignored or docs-only — never commit emails):

```
- 5/3: shared via family group, 3 sign-ups
- 5/4: posted oroBaduk thread, 2 sign-ups
- ...
- 5/9: 14 sign-ups, target reached
```

- [ ] **Step 4: Build the Closed Testing membership**

Once you have 12+ confirmed emails, in Play Console:

Release → Testing → Closed testing → Manage track → Testers → +Create email list → paste emails. Save.

---

### Task F2: TestFlight internal group (Day 14)

iOS doesn't have a 14-day requirement, but invite yourself + family early so you're testing on a real device through TestFlight.

- [ ] **Step 1: App Store Connect → TestFlight → Internal Testing → Create Group**

Add yourself + 2-3 family members by Apple ID.

- [ ] **Step 2: Once you upload your first build (Phase G2), invite the group**

Build → Manage → Internal Testing → Add Group.

---

### Task F3: Tester guides

**Files:**
- Create: `docs/store/beta-tester-guide-ko.md`
- Create: `docs/store/beta-tester-guide-en.md`

A 1-pager that goes in the Closed Testing welcome email. Korean version is primary.

- [ ] **Step 1: Korean version**

```markdown
# AI 바둑 베타 테스터 안내

안녕하세요, 시간 내주셔서 감사합니다.

## 설치 방법 (Android, 14일 비공개 테스트)
1. 옵트인 링크: <Play Console에서 발급되는 URL을 여기에 붙여넣기>
2. "테스터로 참여" 탭
3. Play Store에서 평소처럼 설치

## 무엇을 봐주시면 좋은가요
- 첫 진입 → 닉네임 → 새 게임까지 어색한 부분
- 강도별 응답 시간 (1단/3단/5단 비교)
- 백그라운드 갔다 돌아왔을 때 게임 상태 유지 여부
- 다크 모드 자동 전환
- 햅틱·사운드 토글
- 화면 깨짐, 글자 잘림, 이상한 한국어

## 피드백 채널
- 이메일: support@<domain>
- 또는 Google Form: <폼 URL>

## 참여 규칙 (Play 정책)
- 14일 이상 활성 사용을 채워주셔야 카운트가 됩니다 (하루 한 번 정도면 충분)
- 14일 후 정식 출시되면 자동으로 정식 버전으로 갱신됩니다
```

- [ ] **Step 2: English version (translation)**

- [ ] **Step 3: Commit**

```bash
git add docs/store/beta-tester-guide-*.md
git commit -m "docs(beta): tester onboarding guides ko + en"
```

---

## Phase G — Submission

### Task G1: First .aab → Play Closed Testing (Day 10, ⏰)

This is the **gate** for the 14-day countdown. Aim for **5/13 (Wed)**.

- [ ] **Step 1: In Android Studio, generate signed App Bundle**

Build → Generate Signed Bundle / APK → Android App Bundle.

If first run: create an upload keystore (Android Studio guides you). **Save the keystore + password + alias in 1Password.** Losing this means you can never update the app — Play app signing requires the same upload key.

Variant: `release`.

Output: `mobile/android/app/release/app-release.aab`.

- [ ] **Step 2: Play Console → Testing → Closed testing → New release**

Upload `app-release.aab`. Play extracts metadata (versionCode, versionName).

versionCode 1, versionName `1.0.0`.

- [ ] **Step 3: Release notes**

Both languages, content from `docs/store/release-notes-1.0.0.md` (create if not yet — minimal content for v1.0):

```
First release of AI Baduk.
Play KataGo Human-SL at 12 strength tiers.
```

- [ ] **Step 4: Review and roll out**

Click "Review release". Play scans for policy violations. Resolve any flags. Roll out to Closed Testing.

- [ ] **Step 5: Within ~hours, the build is live for testers**

Send the opt-in URL to your tester list. **Mark the date — this starts the 14-day clock.**

- [ ] **Step 6: Daily check-in**

For 14 days, every day:
- Confirm at least one tester has been active (Play Console → Testing → Closed testing → Statistics)
- Address any crash or feedback

If a critical bug surfaces, push a hotfix release on the SAME track. The 14-day clock does not reset for hotfixes — only for changing tracks.

---

### Task G2: First .ipa → TestFlight Internal (Day 14)

- [ ] **Step 1: Xcode → Product → Archive**

After ~5 minutes, the Organizer opens.

- [ ] **Step 2: Distribute App → App Store Connect → Upload**

Sign with your distribution cert (auto-generated when you ticked "Automatically manage signing" in Plan 2). Wait ~10 minutes for processing.

- [ ] **Step 3: First TestFlight build needs Beta App Review (~24-48h)**

This is a one-time review per app. Subsequent builds skip this step.

- [ ] **Step 4: Once approved, add Internal Testing group**

App Store Connect → TestFlight → Builds → 1.0 (build 1) → Internal Testing → Add yourself + Family group.

- [ ] **Step 5: Install on your iPhone via TestFlight**

Run the smoke checklist from Plan 2 Task F2 Step 4. Fix anything broken — push a new build (build 2 is fine; the version stays 1.0).

---

### Task G3: Submit App Store Connect for App Review (Day 24, ⏰)

**Wait until** TestFlight smoke testing finds no blockers.

- [ ] **Step 1: App Store Connect → 1.0 Prepare for Submission → Build → Select latest TestFlight build**

- [ ] **Step 2: Confirm every section is filled (top-of-page checklist green)**

If anything red, fix it. Most common red items:
- App icon missing (auto-injected from build, but if Xcode skipped a size you'll see it)
- Screenshots missing for a localization
- Privacy URL invalid (404)
- Review notes blank

- [ ] **Step 3: Click "Submit for Review"**

Status: Waiting for Review (24-48h typical).

- [ ] **Step 4: Watch email for the result**

If approved: status flips to **Pending Developer Release**. We will release **manually** in Phase H.

If rejected: see "Rejection response playbook" below.

---

### Task G4: Request Play Production access (Day 24, ⏰)

**Only after** the 14-day Closed Testing window has completed AND you have 12+ active testers logged.

- [ ] **Step 1: Play Console → Testing → Closed testing → Statistics → confirm 14 days + 12+ unique opted-in testers**

- [ ] **Step 2: Play Console → AI Baduk → Production → Apply for production access**

A multi-page form. Provide:
- Closed Testing track ID (auto-filled)
- Marketing screenshots / website link (`<domain>/`)
- Notes about how the app uses Play APIs (none beyond standard)

Submit.

- [ ] **Step 3: Approval window 1-3 days**

Once approved, Production track unlocks for upload.

- [ ] **Step 4: Upload the same .aab to Production track**

Production → Create new release → Upload (or "Promote from Closed testing"). Release notes identical.

- [ ] **Step 5: Don't roll out yet — set rollout to manual**

Save as draft. Phase H releases.

---

### Task G5: Rejection response playbook

If Apple rejects, the most likely reasons + responses:

| Reason | Response |
|---|---|
| **4.2 Minimum Functionality** ("essentially a website") | Reply with a video link showing the native enhancements (haptic feedback, system share sheet, Files app integration). Cite the specific Capacitor plugins used. Resubmit with no code change. |
| **5.1.1.iv Privacy: Data Collection and Storage** ("policy doesn't match what you collect") | Adjust either the Privacy URL or the App Privacy declaration to match exactly. Resubmit. |
| **3.1 Payments** | Shouldn't trigger — we have no IAP. If it does, screenshot the app to prove no payment flow. |
| **2.5 Software Requirements** ("crashes on launch") | Fix the crash. Common cause: missing privacy descriptions in Info.plist. |

For Play, rejections are less common at first launch. Most are policy-driven (data safety mismatch, content rating mismatch) and resolve by editing the form, not the code.

When rejected:
- [ ] Read the full rejection reason carefully (Apple's are sometimes copy-pasted; the specific cited section matters)
- [ ] Reply via App Store Connect Resolution Center if you disagree, or push a fix and resubmit
- [ ] Apple's median time to second-review is faster than first (~12-24h)

---

## Phase H — Launch

### Task H1: Manual production release (Day 28-32)

Once Apple status is "Pending Developer Release" AND Play status is "Ready to publish":

- [ ] **Step 1: App Store Connect → 1.0 → "Release this version" → Confirm**

App goes to "Processing for App Store" → live in ~1 hour (sometimes faster).

- [ ] **Step 2: Play Console → Production → Resume rollout → 100% rollout**

Live in 1-3 hours.

- [ ] **Step 3: Verify**

```bash
curl -sI "https://apps.apple.com/app/<your-app-id>" | head
curl -sI "https://play.google.com/store/apps/details?id=<your.bundle.id>" | head
```

Expected: 200 OK on both.

---

### Task H2: 24-hour monitoring

- [ ] **Step 1: Watch backend health**

```bash
ssh <mac mini> 'tail -f ~/Library/Logs/baduk-api.log'
```

Or (if you've set up Cloudflare Logpush): the dashboard shows req/s and 5xx rate.

- [ ] **Step 2: Crash reports**

App Store Connect → TestFlight → Crashes (this view also shows production once live).
Play Console → Quality → Android Vitals → Crashes.

Target: < 1% session crash rate.

- [ ] **Step 3: KataGo worker queue**

```bash
curl -s https://api.<domain>/api/admin/status | jq '.pool'
```

(requires admin nickname session). Watch worker depths — alert if > 4 sustained.

- [ ] **Step 4: Hotfix window**

Pre-position a 1-hour daily window in your calendar for the first 7 days for immediate hotfix push if needed.

---

### Task H3: 1.0.0 release notes + README

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`

- [ ] **Step 1: Add 1.0.0 entry to CHANGELOG.md**

```markdown
## [1.0.0] - 2026-06-XX

### Added
- iOS App Store + Google Play Store release
- KataGo Metal-accelerated worker pool (4 workers)
- Cloudflare Tunnel native deployment on Mac mini
- Capacitor 7 mobile shell with haptics, share sheet, dark mode
- Files-app .sgf import (iOS + Android)
- Real-time winrate update after each user move
- Hint button loading state

### Changed
- Strength capped at 5d (max_visits=256) for v1
- Removed JWT auth (already in 0.4.0 — fully ephemeral nickname sessions)
- Cookie samesite configurable for Capacitor WebView

### Security
- Next.js → 14.2.35 (CVE-2024-51479, CVE-2025-29927 + 15 more)
- Cloudflare CF-Connecting-IP for rate-limit attribution
- Permissions-Policy + CSP added to security headers
- WebSocket move/undo rate limited per session
- WebSocket heartbeat closes session on server-side expiry
```

- [ ] **Step 2: Update README**

Add to the top:

```markdown
[![App Store](https://img.shields.io/badge/App_Store-AI_Baduk-blue)](https://apps.apple.com/app/<your-app-id>)
[![Google Play](https://img.shields.io/badge/Google_Play-AI_Baduk-green)](https://play.google.com/store/apps/details?id=<your.bundle.id>)
```

- [ ] **Step 3: Commit + tag**

```bash
git add CHANGELOG.md README.md
git commit -m "docs: 1.0.0 release notes + store badges"
git tag -a v1.0.0 -m "Public release on App Store + Play Store"
```

---

## Final Verification

- [ ] App is live on App Store: `curl -sI "https://apps.apple.com/app/..."` returns 200
- [ ] App is live on Play Store: `curl -sI "https://play.google.com/store/apps/details?id=..."` returns 200
- [ ] Apple status: "Available on the App Store"
- [ ] Play status: "Available on Google Play"
- [ ] At least 5 friends have downloaded and run the app on real devices without reporting a crash
- [ ] `https://api.<domain>/api/health` has been up 24h without intervention
- [ ] Backups for the 24h immediately before launch are present in R2
- [ ] No Critical / High items remain on the Apple App Privacy / Play Data Safety labels

---

## Sign-off

Plan 3 — and the entire launch project — is done when:

- AI 바둑 / AI Baduk is publicly downloadable on both stores
- The 1.0.0 git tag is pushed
- The README has working store badges
- The 24h post-launch monitoring report shows < 1% crash rate
- One full 24h cycle of automated R2 backup has succeeded post-launch

V1.1 stack-ranked candidates (deferred from this launch):

1. 7d / 6d strength restored after KataGo profiling proves capacity
2. Push notifications (game finished, AI replied while backgrounded)
3. Time controls (byoyomi / Fischer)
4. User-vs-user games
5. iCloud kifu sync
6. Apple Pencil + iPad keyboard shortcuts
7. Widgets (today's joseki, in-progress preview)
8. Korean GRAC direct registration (if downloads warrant)
9. Multi-host scaling + Postgres (if concurrent active reaches 1000+)
