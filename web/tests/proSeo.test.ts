// 프로 기보 상세 SEO 제목·설명 생성기 테스트 — 한글 기사명·기전명으로 검색어에 맞춘다.
import { describe, it, expect, beforeEach } from "vitest";
import { proGameTitle, proGameDescription, proGameSummary } from "@/lib/proSeo";
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
  board_size: 19,
  handicap: 0,
  komi: 6.5,
  move_count: 187,
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

  it("요약 본문에 기전·날짜·수순·결과·규칙을 사실대로 담는다", () => {
    expect(proGameSummary(base, "ko")).toBe(
      "제10회 춘란배 결승 제3국에서 열린 흑 이세돌 9단, 백 구리 9단의 대국입니다. " +
        "대국일은 2015-03-01입니다. 총 187수로 진행되었습니다. " +
        "결과는 흑 불계승입니다. 19로 바둑판, 덤 6.5집.",
    );
  });

  it("요약은 없는 값의 절을 통째로 생략한다", () => {
    const s = proGameSummary(
      { id: 3, black_player: "Nobody Known", white_player: "Gu Li", board_size: 19, handicap: 0, komi: 6.5 },
      "ko",
    );
    expect(s).toBe("흑 Nobody Known, 백 구리의 대국입니다. 19로 바둑판, 덤 6.5집.");
  });

  it("요약은 접바둑 치수와 판 크기를 밝힌다", () => {
    const s = proGameSummary({ ...base, board_size: 9, handicap: 2, komi: 0.5 }, "ko");
    expect(s).toContain("9로 바둑판, 2점 접바둑, 덤 0.5집.");
  });

  it("요약은 영어 로케일도 지원한다", () => {
    const s = proGameSummary({ ...base, event: null, round: null }, "en");
    expect(s).toContain("Lee Sedol");
    expect(s).toContain("Played on 2015-03-01.");
    expect(s).toContain("19×19 board, komi 6.5.");
  });
});
