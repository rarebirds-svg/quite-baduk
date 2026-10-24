// 프로 기보 상세 SEO 제목·설명 생성기 테스트 — 한글 기사명·기전명으로 검색어에 맞춘다.
import { describe, it, expect, beforeEach } from "vitest";
import { proGameTitle, proGameDescription } from "@/lib/proSeo";
import { setLocale } from "@/lib/i18n";

const base = {
  id: 1,
  black_player: "Lee Sedol",
  white_player: "Gu Li",
  black_rank: "9p",
  white_rank: "9p",
  event: "10th Chunlan Cup Final",
  round: "Final 3",
  game_date: "2015-03-01",
  result: "B+R",
};

describe("proSeo", () => {
  beforeEach(() => setLocale("ko"));

  it("제목에 한글 기사명·기전명을 쓴다", () => {
    expect(proGameTitle(base)).toBe(
      "이세돌 vs 구리 바둑 기보 (제10회 춘란배 결승 제3국, 2015-03-01) — inkbaduk",
    );
  });

  it("미매핑 이름은 영문 그대로 둔다", () => {
    const t = proGameTitle({ ...base, black_player: "Nobody Known", event: null });
    expect(t).toBe("Nobody Known vs 구리 바둑 기보 — inkbaduk");
  });

  it("설명에 한글 단수와 기전·날짜·결과를 담는다", () => {
    const d = proGameDescription(base);
    expect(d).toContain("이세돌 9단 vs 구리 9단");
    expect(d).toContain("제10회 춘란배 결승 제3국");
    expect(d).toContain("2015-03-01");
  });

  it("기사명이 없으면 Black/White로 대체한다", () => {
    expect(proGameTitle({ id: 2 })).toBe("Black vs White 바둑 기보 — inkbaduk");
  });
});
