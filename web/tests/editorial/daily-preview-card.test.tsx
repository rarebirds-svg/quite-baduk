// 홈 "오늘의 한 수" 프리뷰 — API 응답을 판으로 그리고 /daily로 보내는지 확인.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/api", () => ({ api: vi.fn(), API_BASE: "", authHeaders: () => ({}) }));
import { api } from "@/lib/api";
import { DailyPreviewCard, buildPreviewBoard } from "@/components/editorial/DailyPreviewCard";

const CHALLENGE = {
  id: "ch-001",
  board_size: 9,
  setup: [{ color: "B", coord: "E5" }, { color: "W", coord: "D4" }],
  to_move: "B",
  difficulty: "easy",
  topic: "opening",
  prompt_key: "daily.prompts.ch-001",
};

describe("DailyPreviewCard", () => {
  // 중괄호 필수 — 화살표가 mock을 반환하면 Vitest가 그것을 cleanup으로 호출한다.
  beforeEach(() => {
    vi.mocked(api).mockClear();
  });

  it("renders today's puzzle with a link to /daily", async () => {
    vi.mocked(api).mockResolvedValue(CHALLENGE);
    const { container } = render(<DailyPreviewCard />);
    await waitFor(() => expect(screen.getByRole("link", { name: /문제 풀러 가기/ })).toBeTruthy());
    expect(screen.getByRole("link", { name: /문제 풀러 가기/ }).getAttribute("href")).toBe("/daily");
    expect(container.querySelectorAll("[data-stone]")).toHaveLength(2);
    expect(screen.getByText("포석")).toBeTruthy();
    expect(vi.mocked(api)).toHaveBeenCalledWith("/api/daily-challenge");
  });

  it("renders nothing when the API fails", async () => {
    vi.mocked(api).mockImplementation(() => Promise.reject(new Error("down")));
    const { container } = render(<DailyPreviewCard />);
    await waitFor(() => expect(vi.mocked(api)).toHaveBeenCalled());
    expect(container.innerHTML).toBe("");
  });
});

describe("buildPreviewBoard", () => {
  it("places setup stones row-major", () => {
    const b = buildPreviewBoard(9, [{ color: "B", coord: "A9" }, { color: "W", coord: "J1" }]);
    expect(b[0]).toBe("B");
    expect(b[80]).toBe("W");
    expect(b.length).toBe(81);
  });
});
