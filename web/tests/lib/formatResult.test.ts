// SGF 결과 표기를 사람이 읽는 문장으로 바꾸는 formatGameResult의 동작을 고정한다.
import { describe, it, expect } from "vitest";
import { formatGameResult } from "@/lib/formatResult";

describe("formatGameResult (ko)", () => {
  it("renders a point margin as a sentence", () => {
    expect(formatGameResult("W+50.4", "ko")).toBe("백 50.4집 승");
  });

  it("renders a whole-point margin", () => {
    expect(formatGameResult("B+2", "ko")).toBe("흑 2집 승");
  });

  // 한국 바둑 표기는 .5를 소수로 읽지 않는다 — 0.5는 반집, 2.5는 2집반.
  it("renders a half-point win as 반집승", () => {
    expect(formatGameResult("W+0.5", "ko")).toBe("백 반집승");
  });

  it("renders an n-and-a-half point margin as n집반", () => {
    expect(formatGameResult("B+12.5", "ko")).toBe("흑 12집반 승");
  });

  it("keeps an irregular non-half margin as a decimal", () => {
    expect(formatGameResult("W+50.4", "ko")).toBe("백 50.4집 승");
  });

  it("renders a resignation", () => {
    expect(formatGameResult("B+R", "ko")).toBe("흑 불계승");
  });

  it("accepts lowercase colour and suffix", () => {
    expect(formatGameResult("w+r", "ko")).toBe("백 불계승");
  });

  it("defaults to Korean when no locale is given", () => {
    expect(formatGameResult("B+R")).toBe("흑 불계승");
  });

  it("returns an empty string when the game is still in progress", () => {
    expect(formatGameResult(null, "ko")).toBe("");
    expect(formatGameResult(undefined, "ko")).toBe("");
    expect(formatGameResult("", "ko")).toBe("");
  });

  it("passes an unrecognised result through unchanged", () => {
    expect(formatGameResult("B+", "ko")).toBe("B+");
  });
});

describe("formatGameResult (en)", () => {
  it("renders a point margin in English with its unit", () => {
    expect(formatGameResult("W+50.4", "en")).toBe("White wins by 50.4 points");
  });

  it("renders a half-point win in English", () => {
    expect(formatGameResult("W+0.5", "en")).toBe("White wins by half a point");
  });

  it("renders an n-and-a-half margin in English", () => {
    expect(formatGameResult("B+2.5", "en")).toBe("Black wins by 2.5 points");
  });

  it("renders a resignation in English", () => {
    expect(formatGameResult("B+R", "en")).toBe("Black wins by resignation");
  });
});

// 아래 값들은 pro_games 테이블 실제 분포에서 확인한 것만 다룬다.
describe("formatGameResult — pro kifu values (ko)", () => {
  it("renders the spelled-out resignation form", () => {
    expect(formatGameResult("W+Resign", "ko")).toBe("백 불계승");
  });

  it("renders a win on time", () => {
    expect(formatGameResult("B+T", "ko")).toBe("흑 시간승");
  });

  it("renders a win by forfeit", () => {
    expect(formatGameResult("W+F", "ko")).toBe("백 반칙승");
  });

  it("renders a drawn game", () => {
    expect(formatGameResult("Jigo", "ko")).toBe("무승부");
  });

  it("renders an unfinished game", () => {
    expect(formatGameResult("Unfinished", "ko")).toBe("미완국");
  });

  it("renders a void game", () => {
    expect(formatGameResult("Void", "ko")).toBe("무효국");
  });

  it("renders an unknown result", () => {
    expect(formatGameResult("Unknown", "ko")).toBe("결과 불명");
  });
});

describe("formatGameResult — pro kifu values (en)", () => {
  it("renders a win on time in English", () => {
    expect(formatGameResult("B+T", "en")).toBe("Black wins on time");
  });

  it("renders a drawn game in English", () => {
    expect(formatGameResult("Jigo", "en")).toBe("Draw");
  });
});
