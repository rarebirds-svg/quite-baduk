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
