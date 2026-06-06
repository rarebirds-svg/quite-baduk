// 프로 기보 기전·단계·국수 표기 포매터 테스트.
import { describe, it, expect, beforeEach } from "vitest";
import { formatProEvent } from "@/lib/proEvent";
import { setLocale } from "@/lib/i18n";

describe("formatProEvent (ko)", () => {
  beforeEach(() => setLocale("ko"));

  it("기전+단계+국수", () => {
    expect(formatProEvent("10th Chunlan Cup Final", "Final 3", "ko")).toBe(
      "제10회 춘란배 결승 제3국",
    );
  });
  it("Final 키워드 없어도 국수로 결승 판정", () => {
    expect(formatProEvent("10th Ing Cup", "2", "ko")).toBe(
      "제10회 응씨배 결승 제2국",
    );
  });
  it("예선", () => {
    expect(formatProEvent("Ing Cup, Korean preliminary", null, "ko")).toBe(
      "응씨배 예선",
    );
  });
  it("미지 기전은 원문 + 국수", () => {
    expect(formatProEvent("Dosaku Castle Game", "1", "ko")).toBe(
      "Dosaku Castle Game 제1국",
    );
  });
  it("event 없으면 빈 문자열", () => {
    expect(formatProEvent(null, "3", "ko")).toBe("");
  });
});

describe("formatProEvent (en)", () => {
  beforeEach(() => setLocale("en"));

  it("원문 유지 + Game N", () => {
    expect(formatProEvent("10th Chunlan Cup Final", "Final 3", "en")).toBe(
      "10th Chunlan Cup Final · Game 3",
    );
  });
  it("국수 없으면 원문만", () => {
    expect(formatProEvent("Ing Cup, Korean preliminary", null, "en")).toBe(
      "Ing Cup, Korean preliminary",
    );
  });
});
