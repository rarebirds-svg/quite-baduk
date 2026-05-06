#!/usr/bin/env node
// 모바일 폭 (360 / 414) 으로 주요 화면을 캡처해 시각 점검 자료를 만든다

import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const BASE = process.env.E2E_BASE_URL || "http://localhost:3000";
const NICK = "Mobile" + Math.floor(1000 + Math.random() * 8999);
const WIDTHS = [360, 414];
const PAGES = [
  { name: "01-landing", path: "/" },
  { name: "02-game-new", path: "/game/new" },
  { name: "03-history", path: "/history" },
  { name: "04-daily", path: "/daily" },
  { name: "05-settings", path: "/settings" },
];

const OUT = path.resolve(process.cwd(), "screenshots-mobile");
await mkdir(OUT, { recursive: true });

const browser = await chromium.launch();

for (const w of WIDTHS) {
  const context = await browser.newContext({
    viewport: { width: w, height: 800 },
    deviceScaleFactor: 2,
    userAgent:
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
  });
  const page = await context.newPage();

  // 1. 닉네임 게이트 진입 + 세션 생성
  await page.goto(BASE + "/");
  await page.waitForLoadState("networkidle");
  await page.screenshot({
    path: path.join(OUT, `w${w}-00-gate.png`),
    fullPage: true,
  });

  // UI 흐름. 닉네임 폼 채우고 START 클릭 → /game/new 자동 리다이렉트
  await page.goto(BASE + "/", { waitUntil: "domcontentloaded" });
  await page.locator("input[type='text']").first().fill(NICK + "w" + w);
  // 가용성 디바운스 + 상태 변화 기다리기
  await page.waitForTimeout(900);
  await page.locator("button[type='submit']").first().click({ force: true });
  await page.waitForURL("**/game/new", { timeout: 10000 }).catch(() => {});
  await page.waitForLoadState("networkidle");
  console.log("after auth flow, url=", page.url());

  // 현재 /game/new 에 있음 — 그 자리에서 스크린샷
  await page.screenshot({
    path: path.join(OUT, `w${w}-02-game-new.png`),
    fullPage: true,
  });
  console.log("captured", `w${w}-02-game-new.png`, "→", page.url());

  // 다른 페이지는 page.evaluate 로 SPA 내부 라우팅 (router.push)
  const ROUTES = [
    { name: "03-history", path: "/history" },
    { name: "04-daily", path: "/daily" },
    { name: "05-settings", path: "/settings" },
  ];
  for (const r of ROUTES) {
    await page.evaluate((p) => {
      window.history.pushState({}, "", p);
      window.dispatchEvent(new PopStateEvent("popstate"));
    }, r.path);
    await page.goto(BASE + r.path); // SPA 가 안되면 정적 진입
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(600);
    await page.screenshot({
      path: path.join(OUT, `w${w}-${r.name}.png`),
      fullPage: true,
    });
    console.log("captured", `w${w}-${r.name}.png`, "→", page.url());
  }
  await context.close();
}

await browser.close();
console.log("done →", OUT);
