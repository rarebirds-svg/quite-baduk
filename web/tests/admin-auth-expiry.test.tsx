// 어드민 화면이 401(세션 만료)을 감지해 폴링을 멈추고 만료를 알리는지 검증.
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const apiMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  useParams: () => ({ id: "1" }),
}));
vi.mock("@/store/authStore", () => ({
  useAuthStore: () => ({
    session: { id: 1, nickname: "대공" },
    isAdmin: true,
    setIsAdmin: vi.fn(),
  }),
}));
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, api: apiMock };
});

import { ApiError } from "@/lib/api";
import AdminPage from "@/app/admin/page";
import AdminLoginHistoryPage from "@/app/admin/login-history/page";
import AdminStatsPage from "@/app/admin/stats/page";

beforeEach(() => {
  apiMock.mockReset();
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

const screens = [
  { name: "대시보드", Screen: AdminPage, refreshSec: 5 },
  { name: "로그인 이력", Screen: AdminLoginHistoryPage, refreshSec: 10 },
  { name: "통계", Screen: AdminStatsPage, refreshSec: 30 },
];

describe.each(screens)("어드민 $name — 세션 만료(401)", ({ Screen, refreshSec }) => {
  it("만료를 알리고 폴링 루프를 멈춘다", async () => {
    apiMock.mockRejectedValue(new ApiError(401, "unauthorized"));

    render(<Screen />);

    await waitFor(() => expect(screen.getByText(/세션이 만료/)).toBeInTheDocument());

    const callsAtExpiry = apiMock.mock.calls.length;
    await act(async () => {
      vi.advanceTimersByTime(refreshSec * 3 * 1000);
    });

    expect(apiMock.mock.calls.length).toBe(callsAtExpiry);
  });
});

describe("어드민 대시보드 — 권한 없음(403)", () => {
  it("권한 안내를 보여주고 폴링 루프를 멈춘다", async () => {
    apiMock.mockRejectedValue(new ApiError(403, "forbidden"));

    render(<AdminPage />);

    await waitFor(() => expect(screen.getByText(/관리자만 접근/)).toBeInTheDocument());

    const callsAtDenial = apiMock.mock.calls.length;
    await act(async () => {
      vi.advanceTimersByTime(15_000);
    });

    expect(apiMock.mock.calls.length).toBe(callsAtDenial);
  });
});
