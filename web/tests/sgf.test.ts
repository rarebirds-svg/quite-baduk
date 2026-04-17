import { describe, it, expect } from "vitest";
import { parseSgf, buildSgf } from "@/lib/sgf";

describe("sgf", () => {
  it("parses a minimal SGF", () => {
    const s = "(;GM[1]FF[4]SZ[19]KM[6.5];B[pd];W[dp])";
    const g = parseSgf(s);
    expect(g.size).toBe(19);
    expect(g.komi).toBe(6.5);
    expect(g.moves.length).toBe(2);
    expect(g.moves[0].color).toBe("B");
    expect(g.moves[0].coord).toBe("Q16");
  });

  it("builds and re-parses symmetrically", () => {
    const g = { size: 19, komi: 6.5, handicap: 0, result: null, moves: [{ color: "B" as const, coord: "Q16" }, { color: "W" as const, coord: "D4" }] };
    const sgf = buildSgf(g);
    const back = parseSgf(sgf);
    expect(back.moves[0].coord).toBe("Q16");
    expect(back.moves[1].coord).toBe("D4");
  });

  it("handles pass moves", () => {
    const g = parseSgf("(;GM[1]SZ[19];B[];W[])");
    expect(g.moves[0].coord).toBe(null);
  });
});
