import { describe, expect, it, beforeEach } from "vitest";

import { formatGameResult } from "@/lib/formatResult";
import { setLocale } from "@/lib/i18n";

describe("formatGameResult", () => {
  beforeEach(() => {
    setLocale("ko");
  });

  it("returns empty string for null/undefined/empty", () => {
    expect(formatGameResult(null)).toBe("");
    expect(formatGameResult(undefined)).toBe("");
    expect(formatGameResult("")).toBe("");
  });

  it("formats resignation for Korean", () => {
    setLocale("ko");
    expect(formatGameResult("B+R")).toBe("흑 불계승");
    expect(formatGameResult("W+R")).toBe("백 불계승");
  });

  it("formats resignation for English", () => {
    setLocale("en");
    expect(formatGameResult("B+R")).toBe("Black wins by resignation");
    expect(formatGameResult("W+R")).toBe("White wins by resignation");
  });

  it("formats numeric margins for Korean", () => {
    setLocale("ko");
    expect(formatGameResult("W+50.4")).toBe("백 50.4집 승");
    expect(formatGameResult("B+12.5")).toBe("흑 12.5집 승");
    expect(formatGameResult("B+0.5")).toBe("흑 0.5집 승");
  });

  it("formats numeric margins for English", () => {
    setLocale("en");
    expect(formatGameResult("W+50.4")).toBe("White wins by 50.4");
  });

  it("falls back to raw input for unrecognised formats", () => {
    // Backend never sends these today, but the helper must not throw.
    expect(formatGameResult("Draw")).toBe("Draw");
    expect(formatGameResult("Void")).toBe("Void");
    expect(formatGameResult("garbage")).toBe("garbage");
  });

  it("handles whitespace gracefully", () => {
    setLocale("ko");
    expect(formatGameResult(" W+12.5 ")).toBe("백 12.5집 승");
  });

  it("formats timeout (forward-compat) for Korean", () => {
    setLocale("ko");
    expect(formatGameResult("B+T")).toBe("흑 시간승");
    expect(formatGameResult("W+T")).toBe("백 시간승");
  });
});
