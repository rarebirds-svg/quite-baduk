// 검색 유입 탭이 검색어 표를 렌더하는지 검증.
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/store/authStore", () => ({ useAuthStore: () => ({ session: { nickname: "대공" } }) }));
vi.mock("@/lib/api", () => ({
  api: vi.fn((path: string) =>
    path.startsWith("/api/admin/search-queries")
      ? Promise.resolve([{ query: "바둑 사활", page: "/g/s", clicks: 5, impressions: 50, ctr: 0.1, position: 3, source: "google" }])
      : Promise.resolve({ totals: { pageviews: 0, unique_visitors: 0 }, daily: [], top_pages: [], sources: [], countries: [] })),
  ApiError: class extends Error { status = 0 },
}));

import AnalyticsPage from "@/app/admin/analytics/page";

describe("검색 유입 탭", () => {
  it("검색어 렌더", async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText("바둑 사활")).toBeInTheDocument());
  });
});
