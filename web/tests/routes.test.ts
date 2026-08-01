import { describe, expect, it } from "vitest";
import { gamePlayHref, gameReviewHref, proGameHref, spectateWatchHref } from "../lib/routes";

describe("routes (web mode)", () => {
  it("path 세그먼트 형태를 반환한다", () => {
    expect(gamePlayHref(7)).toBe("/game/play/7");
    expect(gameReviewHref(7)).toBe("/game/review/7");
    expect(spectateWatchHref(7)).toBe("/spectate/7");
    expect(proGameHref(12)).toBe("/spectate/pro/12");
  });
});
