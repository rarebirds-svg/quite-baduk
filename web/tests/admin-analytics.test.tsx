// 어드민 방문 통계 페이지가 집계를 렌더하는지 검증.
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/store/authStore", () => ({ useAuthStore: () => ({ session: { nickname: "대공" } }) }));
vi.mock("@/lib/api", () => ({
  api: vi.fn().mockResolvedValue({
    totals: { pageviews: 42, unique_visitors: 30 },
    daily: [], top_pages: [{ path: "/faq", pageviews: 20, uniques: 15 }],
    sources: [{ source: "search", referrer_host: "google.com", pageviews: 30 }],
    countries: [{ country: "KR", pageviews: 40, uniques: 28 }],
  }),
  ApiError: class extends Error { status = 0 },
}));

import AnalyticsPage from "@/app/admin/analytics/page";

describe("AnalyticsPage", () => {
  it("KPI·인기페이지 렌더", async () => {
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText("42")).toBeInTheDocument());
    expect(screen.getByText("/faq")).toBeInTheDocument();
  });
});
