import { describe, it, expect } from "vitest";
import { xyToGtp, gtpToXy, starPoints, totalCells } from "@/lib/board";

describe("coord conversion", () => {
  it("round-trips on 19x19", () => {
    for (let x = 0; x < 19; x++) {
      for (let y = 0; y < 19; y++) {
        const g = xyToGtp(x, y, 19);
        expect(gtpToXy(g, 19)).toEqual([x, y]);
      }
    }
  });

  it("round-trips on 13x13", () => {
    expect(xyToGtp(0, 0, 13)).toBe("A13");
    expect(xyToGtp(12, 12, 13)).toBe("N1");
    expect(gtpToXy("G7", 13)).toEqual([6, 6]);
  });

  it("round-trips on 9x9", () => {
    expect(xyToGtp(0, 0, 9)).toBe("A9");
    expect(xyToGtp(8, 8, 9)).toBe("J1");
    expect(gtpToXy("E5", 9)).toEqual([4, 4]);
  });

  it("pass returns null", () => {
    expect(gtpToXy("pass", 19)).toBeNull();
  });

  it("out-of-range returns null", () => {
    expect(gtpToXy("A14", 13)).toBeNull();
    expect(gtpToXy("K1", 9)).toBeNull(); // col K doesn't exist in 9x9 (A-J)
  });
});

describe("star points", () => {
  it("9x9", () => {
    expect(starPoints(9)).toEqual([2, 4, 6]);
  });
  it("13x13", () => {
    expect(starPoints(13)).toEqual([3, 6, 9]);
  });
  it("19x19", () => {
    expect(starPoints(19)).toEqual([3, 9, 15]);
  });
});

describe("totalCells", () => {
  it("n*n", () => {
    expect(totalCells(9)).toBe(81);
    expect(totalCells(13)).toBe(169);
    expect(totalCells(19)).toBe(361);
  });
});
