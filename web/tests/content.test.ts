// 마크다운 콘텐츠 reader 테스트 — 실제 web/content/ 디렉터리의 샘플 파일을 fixture로.
import { describe, it, expect } from "vitest";
import { getContentSlugs, getContent } from "../lib/content";

describe("content", () => {
  it("getContentSlugs lists glossary slugs", () => {
    const slugs = getContentSlugs("glossary");
    expect(slugs).toContain("dan-gup");
  });

  it("getContentSlugs lists faq slugs", () => {
    const slugs = getContentSlugs("faq");
    expect(slugs).toContain("ai-baduk-vs-human");
  });

  it("getContent returns metadata + html for glossary", () => {
    const c = getContent("glossary", "dan-gup");
    expect(c).not.toBeNull();
    expect(c!.slug).toBe("dan-gup");
    expect(c!.title).toBe("단·급");
    expect(c!.kind).toBe("glossary");
    expect(c!.html).toContain("<p>");
    expect(c!.html).toContain("단·급은");
  });

  it("getContent returns null for missing slug", () => {
    expect(getContent("glossary", "does-not-exist")).toBeNull();
  });

  it("getContent returns null for unknown kind", () => {
    expect(getContent("glossary", "ai-baduk-vs-human")).toBeNull(); // wrong kind
  });
});
