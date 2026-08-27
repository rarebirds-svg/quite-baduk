// news-hook.json 로더의 계약(필드 형태·누락/손상 파일 처리)을 검증한다 — 시드 내용 자체는 주간 자동화가 덮어쓰므로 값 고정 assert는 하지 않는다.
import fs from "node:fs";
import { describe, it, expect, vi, afterEach } from "vitest";
import { getNewsHook } from "../lib/newsHook";

describe("getNewsHook", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("실제 시드 파일에서 6개 필드를 모두 비어있지 않은 문자열로 반환한다", () => {
    const data = getNewsHook();
    expect(data).not.toBeNull();
    const fields = [
      "updated_at",
      "source_url",
      "body_ko",
      "body_en",
      "guide_ko",
      "guide_en",
    ] as const;
    for (const field of fields) {
      expect(typeof data![field]).toBe("string");
      expect(data![field].length).toBeGreaterThan(0);
    }
  });

  it("updated_at은 YYYY-MM-DD 형식이다", () => {
    const data = getNewsHook();
    expect(data!.updated_at).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("source_url은 https 프로토콜의 유효한 URL이다", () => {
    const data = getNewsHook();
    expect(new URL(data!.source_url).protocol).toBe("https:");
  });

  it("파일이 없으면 null을 반환한다", () => {
    vi.spyOn(fs, "existsSync").mockReturnValue(false);
    expect(getNewsHook()).toBeNull();
  });

  it("JSON이 손상돼 있으면 예외를 던지지 않고 null을 반환한다", () => {
    vi.spyOn(fs, "existsSync").mockReturnValue(true);
    vi.spyOn(fs, "readFileSync").mockReturnValue("{ not valid json");
    expect(getNewsHook()).toBeNull();
  });
});
