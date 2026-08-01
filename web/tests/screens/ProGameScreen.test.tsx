// ProGameScreen의 initialGame(서버 프리페치) 경로와 클라이언트 fetch 폴백 경로를 검증한다.
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import ProGameScreen, {
  type ProGameDetail,
} from "../../components/screens/ProGameScreen";

const apiMock = vi.hoisted(() => vi.fn());
vi.mock("../../lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("../../lib/api")>();
  return { ...mod, api: apiMock };
});

const game: ProGameDetail = {
  id: 7,
  // proLocale 매핑에 없는 가상 이름 — 로케일과 무관하게 그대로 렌더된다.
  black_player: "Blackstone Test",
  white_player: "Whitestone Test",
  black_rank: "9p",
  white_rank: "9p",
  event: "Samsung Cup",
  round: null,
  game_date: "2012-10-01",
  result: "B+R",
  board_size: 19,
  handicap: 0,
  komi: 6.5,
  move_count: 2,
  moves: [
    { move_number: 1, color: "B", coord: "Q16" },
    { move_number: 2, color: "W", coord: "D4" },
  ],
};

beforeEach(() => {
  apiMock.mockReset();
});

describe("ProGameScreen", () => {
  it("initialGame이 있으면 fetch 없이 즉시 렌더한다", () => {
    render(<ProGameScreen gameId={7} initialGame={game} />);
    expect(screen.getByText(/Blackstone Test/)).toBeInTheDocument();
    expect(screen.getByText(/Whitestone Test/)).toBeInTheDocument();
    expect(apiMock).not.toHaveBeenCalled();
  });

  it("initialGame이 없으면 기존대로 클라이언트 fetch로 로드한다", async () => {
    apiMock.mockResolvedValueOnce(game);
    render(<ProGameScreen gameId={7} />);
    await waitFor(() =>
      expect(screen.getByText(/Blackstone Test/)).toBeInTheDocument(),
    );
    expect(apiMock).toHaveBeenCalledWith("/api/spectate/pro/7");
  });
});
