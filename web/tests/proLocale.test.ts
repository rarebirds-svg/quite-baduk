// 프로 기보 기사명·단 한글 표기 헬퍼 테스트.
import { describe, it, expect } from "vitest";
import { localizePlayer, localizeRank } from "@/lib/proLocale";

describe("localizePlayer", () => {
  it("ko: 매핑 있으면 한글", () => {
    expect(localizePlayer("Lee Changho", "ko")).toBe("이창호");
    expect(localizePlayer("Honinbo Dosaku", "ko")).toBe("혼인보 도사쿠");
  });
  it("ko: 매핑 없으면 원문", () => {
    expect(localizePlayer("Nonexistent Player", "ko")).toBe("Nonexistent Player");
  });
  it("en: 항상 원문", () => {
    expect(localizePlayer("Lee Changho", "en")).toBe("Lee Changho");
  });
});

describe("localizeRank", () => {
  it("ko: 선행 단 토큰만 한글", () => {
    expect(localizeRank("9p", "ko")).toBe("9단");
    expect(localizeRank("9p, Kisei, Judan, Oza", "ko")).toBe("9단");
    expect(localizeRank("7d", "ko")).toBe("7단");
  });
  it("ko: 비표준/빈값", () => {
    expect(localizeRank("insei", "ko")).toBe("insei");
    expect(localizeRank(null, "ko")).toBe("");
  });
  it("en: 원문", () => {
    expect(localizeRank("9p, Kisei", "en")).toBe("9p, Kisei");
    expect(localizeRank(null, "en")).toBe("");
  });
});
