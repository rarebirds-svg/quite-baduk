// QuickStartForm의 세션 유/무 렌더와 성공·실패 경로를 검증한다.
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const pushMock = vi.hoisted(() => vi.fn());
const quickStartMock = vi.hoisted(() => vi.fn());
const ensureSessionMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));
vi.mock("@/lib/quickStart", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/quickStart")>();
  return { ...mod, quickStart: quickStartMock, ensureSession: ensureSessionMock };
});

import QuickStartForm from "@/components/QuickStartForm";
import { ApiError } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

const PLAY_NOW = /바로 두기/;
const PLAY_AGAIN = /바로 한 판/;

beforeEach(() => {
  pushMock.mockReset();
  quickStartMock.mockReset();
  ensureSessionMock.mockReset();
  useAuthStore.setState({ session: null, isAdmin: false });
});

describe("QuickStartForm — 세션 없음", () => {
  it("닉네임이 2자 미만이면 시작 버튼이 잠긴다", () => {
    render(<QuickStartForm />);
    const button = screen.getByRole("button", { name: PLAY_NOW });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "a" } });
    expect(button).toBeDisabled();
    expect(screen.getByText(/2–32/)).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "돌하나" } });
    expect(button).toBeEnabled();
  });

  it("제출하면 대국을 만들고 대국 화면으로 이동한다", async () => {
    quickStartMock.mockResolvedValueOnce(42);
    render(<QuickStartForm />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "돌하나" } });
    fireEvent.click(screen.getByRole("button", { name: PLAY_NOW }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/game/play/42"));
    expect(quickStartMock).toHaveBeenCalledWith("돌하나");
  });

  it("실패하면 에러 문구와 /game/new 폴백 링크를 보여준다", async () => {
    quickStartMock.mockRejectedValueOnce(new ApiError(500, "500"));
    render(<QuickStartForm />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "돌하나" } });
    fireEvent.click(screen.getByRole("button", { name: PLAY_NOW }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/다시 시도/);
    expect(screen.getByRole("link", { name: /다시 시도/ })).toHaveAttribute(
      "href",
      "/game/new",
    );
    expect(pushMock).not.toHaveBeenCalled();
  });

  it("상세 설정은 세션을 먼저 만든 뒤 /game/new로 보낸다", async () => {
    ensureSessionMock.mockResolvedValueOnce({ id: 1, nickname: "돌하나" });
    render(<QuickStartForm />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "돌하나" } });
    fireEvent.click(screen.getByRole("button", { name: /상세 설정으로 시작/ }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/game/new"));
    expect(ensureSessionMock).toHaveBeenCalledWith("돌하나");
  });
});

describe("QuickStartForm — 세션 있음", () => {
  beforeEach(() => {
    useAuthStore.setState({ session: { id: 3, nickname: "기존", token: null } });
  });

  it("입력창 없이 닉네임과 단독 버튼만 보여준다", () => {
    render(<QuickStartForm />);
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.getByText(/기존/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: PLAY_AGAIN })).toBeEnabled();
    expect(screen.getByRole("link", { name: /상세 설정으로 시작/ })).toHaveAttribute(
      "href",
      "/game/new",
    );
  });

  it("버튼 한 번으로 대국이 열린다", async () => {
    quickStartMock.mockResolvedValueOnce(7);
    render(<QuickStartForm />);

    fireEvent.click(screen.getByRole("button", { name: PLAY_AGAIN }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/game/play/7"));
  });
});
