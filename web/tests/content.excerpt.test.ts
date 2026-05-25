// excerpt 추출 헬퍼 단위 테스트.
import { describe, it, expect } from "vitest";
import { extractExcerpt } from "../lib/content";

describe("extractExcerpt", () => {
  it("returns override when frontmatter excerpt exists", () => {
    expect(extractExcerpt("Body text.", "Manual excerpt.")).toBe("Manual excerpt.");
  });

  it("returns first sentence terminated by .", () => {
    expect(extractExcerpt("축은 기본 기술이다. 두 번째 문장.")).toBe("축은 기본 기술이다.");
  });

  it("returns first sentence terminated by ?", () => {
    expect(extractExcerpt("질문인가요? 답변 문장.")).toBe("질문인가요?");
  });

  it("returns first sentence terminated by !", () => {
    expect(extractExcerpt("강조! 다음.")).toBe("강조!");
  });

  it("strips markdown headers and list markers from leading content", () => {
    expect(extractExcerpt("# 제목\n\n첫 문단 시작. 다음.")).toBe("첫 문단 시작.");
  });

  it("strips bold and inline code markers", () => {
    expect(extractExcerpt("이건 **굵은** `코드` 문장.")).toBe("이건 굵은 코드 문장.");
  });

  it("falls back to first paragraph then truncates over 100 chars", () => {
    const long = "가".repeat(150);
    const out = extractExcerpt(long);
    expect(out.endsWith("…")).toBe(true);
    expect([...out].length).toBeLessThanOrEqual(101);
  });

  it("returns empty string for empty content with no override", () => {
    expect(extractExcerpt("")).toBe("");
  });
});

describe("extractExcerpt with media", () => {
  it("ignores board codeblock and finds following sentence", () => {
    const md = "```board\nsize: 9\nposition: |\n  .........\n```\n\n축은 기본 기술이다. 다음 문장.";
    expect(extractExcerpt(md)).toBe("축은 기본 기술이다.");
  });

  it("ignores image markdown and finds following sentence", () => {
    const md = "![alt](/path/x.svg)\n\n빅은 살아 있는 형태다. 다음 문장.";
    expect(extractExcerpt(md)).toBe("빅은 살아 있는 형태다.");
  });

  it("strips both board and image then takes first sentence", () => {
    const md = "![대표](/p.svg)\n\n```board\nsize: 9\nposition: |\n  .........\n```\n\n핵심 정의.";
    expect(extractExcerpt(md)).toBe("핵심 정의.");
  });
});
