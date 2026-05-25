// board-svg 유틸 단위 테스트.
import { describe, it, expect } from "vitest";
import { parseBoardCodeBlock } from "../lib/board-svg";

describe("parseBoardCodeBlock", () => {
  it("parses size, position rows, caption", () => {
    const src = `size: 9
position: |
  .........
  ....B....
  ...WB....
  ....W....
  .........
  .........
  .........
  .........
  .........
caption: 축의 시작`;
    const spec = parseBoardCodeBlock(src);
    expect(spec.size).toBe(9);
    expect(spec.position).toHaveLength(9);
    expect(spec.position[1]).toBe("....B....");
    expect(spec.position[2]).toBe("...WB....");
    expect(spec.caption).toBe("축의 시작");
  });

  it("defaults size to 19 when missing", () => {
    const lines = ["position: |"].concat(Array(19).fill("  ...................")).join("\n");
    const spec = parseBoardCodeBlock(lines);
    expect(spec.size).toBe(19);
    expect(spec.position).toHaveLength(19);
  });

  it("pads short position rows with dots", () => {
    const src = `size: 9
position: |
  ....B
  .........
  .........
  .........
  .........
  .........
  .........
  .........
  .........`;
    const spec = parseBoardCodeBlock(src);
    expect(spec.position[0]).toBe("....B....");
  });

  it("pads missing position rows with empty rows", () => {
    const src = `size: 9
position: |
  ....B....
  ....W....`;
    const spec = parseBoardCodeBlock(src);
    expect(spec.position).toHaveLength(9);
    expect(spec.position[2]).toBe(".........");
    expect(spec.position[8]).toBe(".........");
  });

  it("replaces invalid characters with dot", () => {
    const src = `size: 9
position: |
  X.X......
  .........
  .........
  .........
  .........
  .........
  .........
  .........
  .........`;
    const spec = parseBoardCodeBlock(src);
    expect(spec.position[0]).toBe(".........");
  });

  it("omits caption when not present", () => {
    const src = `size: 9
position: |
  .........
  .........
  .........
  .........
  .........
  .........
  .........
  .........
  .........`;
    const spec = parseBoardCodeBlock(src);
    expect(spec.caption).toBeUndefined();
  });
});

import { boardToSvg } from "../lib/board-svg";

describe("boardToSvg", () => {
  const emptyPos = (size: number) => Array(size).fill(".".repeat(size));

  it("includes svg root with viewBox 0 0 480 480", () => {
    const svg = boardToSvg({ size: 9, position: emptyPos(9) });
    expect(svg).toMatch(/<svg[^>]+viewBox="0 0 480 480"/);
  });

  it("renders size×size grid lines", () => {
    const svg = boardToSvg({ size: 9, position: emptyPos(9) });
    const lineCount = (svg.match(/<line\b/g) ?? []).length;
    expect(lineCount).toBe(18);
  });

  it("renders 5 star points on 9x9", () => {
    const svg = boardToSvg({ size: 9, position: emptyPos(9) });
    const stars = (svg.match(/class="star"/g) ?? []).length;
    expect(stars).toBe(5);
  });

  it("renders 9 star points on 19x19", () => {
    const svg = boardToSvg({ size: 19, position: emptyPos(19) });
    const stars = (svg.match(/class="star"/g) ?? []).length;
    expect(stars).toBe(9);
  });

  it("renders black and white stones at correct positions", () => {
    const pos = [
      "B........",
      ".........",
      ".........",
      ".........",
      ".........",
      ".........",
      ".........",
      ".........",
      "........W",
    ];
    const svg = boardToSvg({ size: 9, position: pos });
    const black = (svg.match(/class="stone-black"/g) ?? []).length;
    const white = (svg.match(/class="stone-white"/g) ?? []).length;
    expect(black).toBe(1);
    expect(white).toBe(1);
  });

  it("includes role=img and aria-label from caption when present", () => {
    const svg = boardToSvg({ size: 9, position: emptyPos(9), caption: "축의 시작" });
    expect(svg).toMatch(/role="img"/);
    expect(svg).toMatch(/aria-label="축의 시작"/);
  });

  it("uses generic aria-label when caption missing", () => {
    const svg = boardToSvg({ size: 9, position: emptyPos(9) });
    expect(svg).toMatch(/aria-label="9×9 바둑판 다이어그램"/);
  });
});
