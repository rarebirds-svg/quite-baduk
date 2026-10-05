// 상단 테마·언어 토글의 접근성 이름 — 마운트 전(theme undefined)에도
// "Theme: undefined"가 아니라 i18n 라벨이어야 한다(제미나이 점검 1-①).
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));
vi.mock("@/lib/api", () => ({ api: vi.fn(), API_BASE: "", authHeaders: () => ({}) }));

import TopNav from "@/components/TopNav";

describe("TopNav theme toggle", () => {
  it("never exposes 'Theme: undefined' in the accessibility tree", () => {
    // ThemeProvider 없이 렌더 → next-themes의 theme는 undefined (SSR/첫 렌더와 동일).
    const { container } = render(<TopNav />);
    expect(container.innerHTML).not.toContain("undefined");
    expect(screen.getByRole("button", { name: "테마 전환" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "언어 전환" })).toBeTruthy();
    for (const b of container.querySelectorAll("button")) {
      expect(b.getAttribute("aria-label") ?? "").not.toMatch(/Theme:/);
    }
  });
});
