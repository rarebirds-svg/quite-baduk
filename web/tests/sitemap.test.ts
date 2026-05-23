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

describe("sitemap themes and picks", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it("includes theme + picks index + monthly pick URLs", async () => {
    const themesList = [
      { slug: "masterpieces", label: "명국선", description: "", count: 10 },
      { slug: "honinbo", label: "본인방전", description: "", count: 5 },
    ];
    const proList = [{ id: 1, created_at: "2024-01-01T00:00:00" }];

    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation(async (url: string) => {
        if (url.endsWith("/api/spectate/pro/sitemap")) {
          return { ok: true, json: async () => proList };
        }
        if (url.endsWith("/api/spectate/pro/themes")) {
          return { ok: true, json: async () => themesList };
        }
        return { ok: false, json: async () => [] };
      }),
    );

    const { default: sitemap } = await import("../app/sitemap");
    const urls = await sitemap();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/themes/masterpieces")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/themes/honinbo")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/spectate/picks")).toBeDefined();
    // monthly picks 최근 12 + 현재 + 다음 = 14 URL
    const monthlyCount = urls.filter((u) =>
      u.url.startsWith("https://inkbaduk.com/spectate/picks/monthly/"),
    ).length;
    expect(monthlyCount).toBe(14);
  });
});

describe("sitemap glossary and faq", () => {
  it("includes glossary + faq slug URLs from content directory", async () => {
    // sitemap.ts가 web/content/<kind>/를 스캔. 실제 dan-gup·ai-baduk-vs-human이 있어야.
    const { default: sitemap } = await import("../app/sitemap");
    const urls = await sitemap();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/glossary")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/glossary/dan-gup")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/faq")).toBeDefined();
    expect(urls.find((u) => u.url === "https://inkbaduk.com/faq/ai-baduk-vs-human")).toBeDefined();
  });
});
