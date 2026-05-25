// 한글 초성 추출 유틸 단위 테스트.
import { describe, it, expect } from "vitest";
import { leadConsonant, CHOSEONG_BASE } from "../lib/hangul";

describe("leadConsonant", () => {
  it("returns ㅂ for 빅", () => expect(leadConsonant("빅")).toBe("ㅂ"));
  it("returns ㅊ for 축", () => expect(leadConsonant("축")).toBe("ㅊ"));
  it("returns ㄷ for 단·급", () => expect(leadConsonant("단·급")).toBe("ㄷ"));
  it("maps tense ㄲ → ㄱ", () => expect(leadConsonant("까")).toBe("ㄱ"));
  it("returns null for ascii start", () => expect(leadConsonant("dan-gup")).toBe(null));
  it("returns null for empty string", () => expect(leadConsonant("")).toBe(null));
  it("returns null for emoji or symbol start", () => expect(leadConsonant("★축")).toBe(null));
});

describe("CHOSEONG_BASE", () => {
  it("has 14 base consonants in order", () => {
    expect(CHOSEONG_BASE).toEqual(["ㄱ","ㄴ","ㄷ","ㄹ","ㅁ","ㅂ","ㅅ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]);
  });
});
