import { describe, it, expect } from "vitest";
import { xyToGtp, gtpToXy, starPoints, totalCells, applyMoveWithCaptures } from "@/lib/board";
import { BOARD_THEMES } from "@/store/boardThemeStore";

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

describe("applyMoveWithCaptures", () => {
  // Helpers for legible board fixtures on 5x5.
  const SIZE = 5;
  const toBoard = (rows: string[]): string =>
    rows.map((r) => r.replace(/\s/g, "")).join("");

  it("places a stone and leaves surrounding empties", () => {
    const before = toBoard([
      ". . . . .",
      ". . . . .",
      ". . . . .",
      ". . . . .",
      ". . . . .",
    ]);
    expect(applyMoveWithCaptures(before, SIZE, 2, 2, "B")).toBe(
      toBoard([
        ". . . . .",
        ". . . . .",
        ". . B . .",
        ". . . . .",
        ". . . . .",
      ]),
    );
  });

  it("captures a single stone in atari on the side", () => {
    // W at (0,2) has only one liberty: (1,2). Black plays there → W captured.
    const before = toBoard([
      ". . . . .",
      "B . . . .",
      "W . . . .",
      "B . . . .",
      ". . . . .",
    ]);
    const after = applyMoveWithCaptures(before, SIZE, 1, 2, "B");
    expect(after[2 * SIZE + 0]).toBe("."); // W at (0,2) removed
    expect(after[2 * SIZE + 1]).toBe("B"); // B placed at (1,2)
  });

  it("captures a multi-stone group", () => {
    // 2-stone White group at (0,1)+(0,2). Liberties of the group are (1,1)
    // only (since (0,0), (1,2), (0,3) are all Black). Black plays (1,1).
    const before = toBoard([
      "B . . . .",
      "W . . . .",
      "W B . . .",
      "B . . . .",
      ". . . . .",
    ]);
    const after = applyMoveWithCaptures(before, SIZE, 1, 1, "B");
    expect(after[1 * SIZE + 0]).toBe("."); // W at (0,1) removed
    expect(after[2 * SIZE + 0]).toBe("."); // W at (0,2) removed
    expect(after[1 * SIZE + 1]).toBe("B"); // B placed at (1,1)
  });

  it("does nothing when the target cell is occupied", () => {
    const before = toBoard([
      "B . . . .",
      ". . . . .",
      ". . . . .",
      ". . . . .",
      ". . . . .",
    ]);
    expect(applyMoveWithCaptures(before, SIZE, 0, 0, "W")).toBe(before);
  });

  it("does not capture when the opponent group still has liberties", () => {
    const before = toBoard([
      ". . . . .",
      ". B . . .",
      ". W . . .",
      ". . . . .",
      ". . . . .",
    ]);
    // W at (1,2) has 3 liberties; B playing (2,2) shouldn't capture.
    const after = applyMoveWithCaptures(before, SIZE, 2, 2, "B");
    expect(after[2 * SIZE + 1]).toBe("W"); // W still there
    expect(after[2 * SIZE + 2]).toBe("B");
  });
});

describe("BOARD_THEMES metadata", () => {
  it("paper is flat with no shadow", () => {
    expect(BOARD_THEMES.paper.surface).toBe("flat");
    expect(BOARD_THEMES.paper.stoneStyle).toBe("flat");
    expect(BOARD_THEMES.paper.shadow).toBe(false);
  });

  it("kaya uses wood surface and lithic stones", () => {
    expect(BOARD_THEMES.kaya.surface).toBe("wood");
    expect(BOARD_THEMES.kaya.stoneStyle).toBe("lithic");
    expect(BOARD_THEMES.kaya.shadow).toBe(true);
  });

  it("slate is flat surface but lithic stones", () => {
    expect(BOARD_THEMES.slate.surface).toBe("flat");
    expect(BOARD_THEMES.slate.stoneStyle).toBe("lithic");
    expect(BOARD_THEMES.slate.shadow).toBe(true);
  });
});
