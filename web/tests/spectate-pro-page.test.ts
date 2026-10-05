// /spectate/pro 서버 페이지의 초기 질의 테스트 — SSR fetch URL과 상수 import 출처(use client 금지)를 검증한다.
import { readFileSync } from "fs";
import path from "path";
import { describe, it, expect, vi, beforeEach } from "vitest";

const WEB_ROOT = path.resolve(__dirname, "..");
const PAGE_PATH = path.join(WEB_ROOT, "app/spectate/pro/page.tsx");

// page.tsx가 PRO_LIST_INITIAL_QUERY를 어느 모듈에서 가져오는지 소스에서 찾아 파일 경로로 푼다.
function resolveInitialQueryModule(): string {
  const src = readFileSync(PAGE_PATH, "utf8");
  const match = src.match(/import\s*\{[^}]*PRO_LIST_INITIAL_QUERY[^}]*\}\s*from\s*"([^"]+)"/);
  if (!match) throw new Error("page.tsx가 PRO_LIST_INITIAL_QUERY를 import하지 않는다");
  const spec = match[1].replace(/^@\//, "");
  for (const ext of [".ts", ".tsx"]) {
    const candidate = path.join(WEB_ROOT, spec + ext);
    try {
      readFileSync(candidate);
      return candidate;
    } catch {
      /* 다음 확장자 */
    }
  }
  throw new Error(`모듈을 찾을 수 없다: ${spec}`);
}

describe("/spectate/pro page", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it("초기 질의 상수는 use client 모듈에서 가져오지 않는다 (#99 — RSC 클라이언트 참조가 [object Object]로 직렬화됨)", () => {
    const modulePath = resolveInitialQueryModule();
    const src = readFileSync(modulePath, "utf8");
    // 선행 줄 주석 뒤에 오는 directive도 잡는다.
    expect(/^(\s*\/\/[^\n]*\n)*\s*["']use client["']/.test(src)).toBe(false);
  });

  it("SSR이 명국선·최신순·첫 페이지 질의로 백엔드를 호출한다", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ rows: [], total: 0 }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const { default: Page } = await import("../app/spectate/pro/page");
    await Page();
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/api/spectate/pro?collection=masterpiece&sort=recent&limit=50&offset=0");
    expect(url).not.toContain("[object");
  });
});
