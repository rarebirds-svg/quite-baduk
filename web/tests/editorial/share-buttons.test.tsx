// 공유 버튼 동작 테스트 — 클립보드 피드백·navigator.share 분기·X intent 인코딩.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import ShareButtons from "../../components/editorial/ShareButtons";

const URL_UNDER_TEST = "https://inkbaduk.com/glossary/축 머리";

function setClipboard(writeText: () => Promise<void>) {
  Object.defineProperty(navigator, "clipboard", {
    value: { writeText },
    configurable: true,
  });
}

function setShare(share: ((data: ShareData) => Promise<void>) | undefined) {
  Object.defineProperty(navigator, "share", { value: share, configurable: true });
}

describe("ShareButtons", () => {
  beforeEach(() => {
    setShare(undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("copies the url and shows success feedback", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);

    render(<ShareButtons title="축" url={URL_UNDER_TEST} />);
    fireEvent.click(screen.getByRole("button", { name: "링크 복사" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(URL_UNDER_TEST));
    expect(await screen.findByRole("button", { name: "복사했습니다" })).toBeInTheDocument();
  });

  it("shows a failure message when the clipboard rejects", async () => {
    setClipboard(vi.fn().mockRejectedValue(new Error("denied")));

    render(<ShareButtons title="축" url={URL_UNDER_TEST} />);
    fireEvent.click(screen.getByRole("button", { name: "링크 복사" }));

    expect(await screen.findByRole("button", { name: "복사하지 못했습니다" })).toBeInTheDocument();
  });

  it("hides the device share button when navigator.share is unavailable", () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    render(<ShareButtons title="축" url={URL_UNDER_TEST} />);
    expect(screen.queryByRole("button", { name: "공유하기" })).not.toBeInTheDocument();
  });

  it("uses navigator.share when the browser supports it", async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    const share = vi.fn().mockResolvedValue(undefined);
    setShare(share);

    render(<ShareButtons title="축" url={URL_UNDER_TEST} />);
    const button = await screen.findByRole("button", { name: "공유하기" });
    fireEvent.click(button);

    await waitFor(() =>
      expect(share).toHaveBeenCalledWith({ title: "축", url: URL_UNDER_TEST }),
    );
  });

  it("encodes url and text into the X intent link", () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    render(<ShareButtons title="축 & 장문" url={URL_UNDER_TEST} />);

    const link = screen.getByRole("link", { name: "X에 공유" });
    expect(link).toHaveAttribute(
      "href",
      `https://twitter.com/intent/tweet?url=${encodeURIComponent(
        URL_UNDER_TEST,
      )}&text=${encodeURIComponent("축 & 장문")}`,
    );
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("falls back to the current location when no url is given", async () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    render(<ShareButtons title="축" />);

    await waitFor(() =>
      expect(screen.getByRole("link", { name: "X에 공유" })).toHaveAttribute(
        "href",
        `https://twitter.com/intent/tweet?url=${encodeURIComponent(
          window.location.href,
        )}&text=${encodeURIComponent("축")}`,
      ),
    );
  });

  it("does not render the KakaoTalk button without a JS key", () => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
    render(<ShareButtons title="축" url={URL_UNDER_TEST} />);
    expect(screen.queryByRole("button", { name: "카카오톡 공유" })).not.toBeInTheDocument();
  });
});
