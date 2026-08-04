// SGF 결과 표기를 사람이 읽는 문장으로 바꾸는 formatGameResult의 동작을 고정한다.
import { describe, it, expect } from "vitest";
import { formatGameResult } from "@/lib/formatResult";

describe("formatGameResult (ko)", () => {
  it("renders a point margin as a sentence", () => {
    expect(formatGameResult("W+50.4", "ko")).toBe("백 50.4집 승");
  });

  it("renders black's point margin", () => {
    expect(formatGameResult("B+12.5", "ko")).toBe("흑 12.5집 승");
  });

  it("keeps a half-point margin unrounded", () => {
    expect(formatGameResult("W+0.5", "ko")).toBe("백 0.5집 승");
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
  it("renders a point margin in English", () => {
    expect(formatGameResult("W+50.4", "en")).toBe("White wins by 50.4");
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
