// NewsHook이 data prop을 로케일에 맞게 렌더링하는지 검증한다.
import { describe, it, expect, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { NewsHook } from "@/components/editorial/NewsHook";
import { setLocale } from "@/lib/i18n";
import type { NewsHookData } from "@/lib/newsHook";

const SAMPLE: NewsHookData = {
  updated_at: "2026-08-27",
  source_url: "https://example.com/article",
  body_ko: "한국어 본문",
  body_en: "English body",
  guide_ko: "한국어 안내",
  guide_en: "English guide",
};

afterEach(() => setLocale("ko"));

describe("NewsHook", () => {
  it("data가 없으면 아무것도 렌더링하지 않는다", () => {
    const { container } = render(<NewsHook data={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("한국어 로케일에서 ko 필드를 보여준다", () => {
    setLocale("ko");
    render(<NewsHook data={SAMPLE} />);
    expect(screen.getByText("한국어 본문")).toBeInTheDocument();
    expect(screen.getByText("한국어 안내")).toBeInTheDocument();
  });

  it("영어 로케일에서 en 필드를 보여준다", () => {
    setLocale("en");
    render(<NewsHook data={SAMPLE} />);
    expect(screen.getByText("English body")).toBeInTheDocument();
    expect(screen.getByText("English guide")).toBeInTheDocument();
  });
});
