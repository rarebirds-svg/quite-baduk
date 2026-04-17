import { describe, it, expect } from "vitest";
import { gtpToXy, xyToGtp } from "@/lib/board";

describe("board coords", () => {
  it("converts Q16 to (15,3)", () => {
    expect(gtpToXy("Q16")).toEqual([15, 3]);
  });
  it("converts (0,18) to A1", () => {
    expect(xyToGtp(0, 18)).toBe("A1");
  });
  it("rejects invalid coords", () => {
    expect(gtpToXy("XX99")).toBe(null);
  });
  it("roundtrips all 361 coords", () => {
    for (let x = 0; x < 19; x++) {
      for (let y = 0; y < 19; y++) {
        const g = xyToGtp(x, y);
        expect(gtpToXy(g)).toEqual([x, y]);
      }
    }
  });
});
