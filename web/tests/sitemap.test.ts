// sitemap.ts의 동적 생성 테스트 — fetch 모킹으로 검증한다.
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("sitemap", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it("includes static + dynamic pro game URLs", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          { id: 1, created_at: "2024-01-01T00:00:00" },
          { id: 42, created_at: "2024-06-15T12:00:00" },
        ],
      }),
    );
    const { default: sitemap } = await import("../app/sitemap");
    const urls = await sitemap();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/pro/1")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/pro/42")).toBeDefined();
  });

  it("falls back to static URLs when API fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    const { default: sitemap } = await import("../app/sitemap");
    const urls = await sitemap();
    // 정적 5개는 그대로
    expect(urls.find((u) => u.url === "https://inkbaduk.com/")).toBeDefined();
    // 동적 항목은 없음
    expect(urls.find((u) => u.url?.includes("/spectate/pro/"))).toBeUndefined();
  });
});
