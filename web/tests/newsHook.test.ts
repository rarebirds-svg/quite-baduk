// news-hook.json 로더가 실제 시드 파일을 올바르게 읽는지 검증한다.
import { describe, it, expect } from "vitest";
import { getNewsHook } from "../lib/newsHook";

describe("getNewsHook", () => {
  it("시드 파일의 필드를 그대로 반환한다", () => {
    const data = getNewsHook();
    expect(data).not.toBeNull();
    expect(data!.source_url).toBe(
      "https://news.sbs.co.kr/news/endPage.do?news_id=N1008664048",
    );
    expect(data!.body_ko).toContain("신진서");
    expect(data!.body_en).toContain("Shin Jinseo");
    expect(data!.guide_ko).toContain("닉네임");
    expect(typeof data!.updated_at).toBe("string");
  });
});
