// SGF 결과 표기를 사람이 읽는 문장으로 바꾸는 formatGameResult의 동작을 고정한다.
import { describe, it, expect, beforeEach } from "vitest";
import { setLocale } from "@/lib/i18n";
import { formatGameResult } from "@/lib/formatResult";

describe("formatGameResult (ko)", () => {
  beforeEach(() => setLocale("ko"));

  it("renders a point margin as a sentence", () => {
    expect(formatGameResult("W+50.4")).toBe("백 50.4집 승");
  });

  it("renders black's point margin", () => {
    expect(formatGameResult("B+12.5")).toBe("흑 12.5집 승");
  });

  it("keeps a half-point margin unrounded", () => {
    expect(formatGameResult("W+0.5")).toBe("백 0.5집 승");
  });

  it("renders a resignation", () => {
    expect(formatGameResult("B+R")).toBe("흑 불계승");
  });

  it("accepts lowercase colour and suffix", () => {
    expect(formatGameResult("w+r")).toBe("백 불계승");
  });

  it("returns an empty string when the game is still in progress", () => {
    expect(formatGameResult(null)).toBe("");
    expect(formatGameResult(undefined)).toBe("");
    expect(formatGameResult("")).toBe("");
  });

  it("passes an unrecognised result through unchanged", () => {
    expect(formatGameResult("Void")).toBe("Void");
    expect(formatGameResult("B+")).toBe("B+");
  });
});

describe("formatGameResult (en)", () => {
  beforeEach(() => setLocale("en"));

  it("renders a point margin in English", () => {
    expect(formatGameResult("W+50.4")).toBe("White wins by 50.4");
  });

  it("renders a resignation in English", () => {
    expect(formatGameResult("B+R")).toBe("Black wins by resignation");
  });
});
