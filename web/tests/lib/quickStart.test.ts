// quickStart의 세션 유/무 분기와 실패 전파를 검증한다.
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMock = vi.hoisted(() => vi.fn());
const setSessionTokenMock = vi.hoisted(() => vi.fn(async () => {}));

vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>();
  return { ...mod, api: apiMock };
});
vi.mock("@/lib/sessionToken", () => ({ setSessionToken: setSessionTokenMock }));

import { ApiError } from "@/lib/api";
import { isNicknameFormatValid, quickStart, QUICK_START_GAME } from "@/lib/quickStart";
import { useAuthStore } from "@/store/authStore";

beforeEach(() => {
  apiMock.mockReset();
  setSessionTokenMock.mockClear();
  useAuthStore.setState({ session: null, isAdmin: false });
});

describe("isNicknameFormatValid", () => {
  it.each([
    ["a", false],
    ["ab", true],
    [" ab ", true],
    ["  ", false],
    ["", false],
    ["a".repeat(32), true],
    ["a".repeat(33), false],
  ])("%s → %s", (name, expected) => {
    expect(isNicknameFormatValid(name as string)).toBe(expected);
  });
});

describe("quickStart", () => {
  it("세션이 없으면 세션을 만들고 기본 설정으로 대국을 연다", async () => {
    apiMock
      .mockResolvedValueOnce({ id: 7, nickname: "돌하나", token: "tok" })
      .mockResolvedValueOnce({ id: 42 });

    const id = await quickStart("  돌하나  ");

    expect(id).toBe(42);
    expect(apiMock).toHaveBeenNthCalledWith(1, "/api/session", {
      method: "POST",
      body: JSON.stringify({ nickname: "돌하나" }),
    });
    expect(apiMock).toHaveBeenNthCalledWith(2, "/api/games", {
      method: "POST",
      body: JSON.stringify(QUICK_START_GAME),
    });
    expect(JSON.parse(apiMock.mock.calls[1][1].body)).toEqual({
      board_size: 9,
      ai_rank: "9k",
      handicap: 0,
      user_color: "black",
    });
    expect(setSessionTokenMock).toHaveBeenCalledWith("tok");
    expect(useAuthStore.getState().session).toEqual({
      id: 7,
      nickname: "돌하나",
      token: "tok",
    });
  });

  it("세션이 있으면 세션 생성을 건너뛴다", async () => {
    useAuthStore.setState({ session: { id: 3, nickname: "기존", token: null } });
    apiMock.mockResolvedValueOnce({ id: 99 });

    const id = await quickStart("무시됨");

    expect(id).toBe(99);
    expect(apiMock).toHaveBeenCalledTimes(1);
    expect(apiMock).toHaveBeenCalledWith("/api/games", expect.anything());
    expect(setSessionTokenMock).not.toHaveBeenCalled();
  });

  it("대국 생성이 실패하면 예외를 그대로 던진다", async () => {
    apiMock
      .mockResolvedValueOnce({ id: 7, nickname: "돌하나", token: "tok" })
      .mockRejectedValueOnce(new ApiError(500, "500"));

    await expect(quickStart("돌하나")).rejects.toBeInstanceOf(ApiError);
    // 세션은 이미 만들어졌으므로 폴백 화면(/game/new)에서 재시도할 수 있다.
    expect(useAuthStore.getState().session?.id).toBe(7);
  });

  it("세션 생성이 실패하면 대국을 만들지 않는다", async () => {
    apiMock.mockRejectedValueOnce(new ApiError(429, "rate_limited"));

    await expect(quickStart("돌하나")).rejects.toBeInstanceOf(ApiError);
    expect(apiMock).toHaveBeenCalledTimes(1);
    expect(useAuthStore.getState().session).toBeNull();
  });
});
