import { describe, it, expect } from "vitest";
import { buildResultCardSvg, CARD_W, CARD_H } from "@/lib/resultCard";

describe("buildResultCardSvg", () => {
  const board = ".".repeat(81).split("");
  board[40] = "B"; // E5
  board[30] = "W";

  it("renders a standalone SVG with concrete colours and both stones", () => {
    const svg = buildResultCardSvg({
      size: 9,
      board: board.join(""),
      title: "daegong vs 이창호",
      subtitle: "9×9 · 5급 · 실리형",
      result: "백 불계승",
      lastMove: { x: 4, y: 4 },
    });
    expect(svg.startsWith("<svg")).toBe(true);
    expect(svg).toContain(`width="${CARD_W}" height="${CARD_H}"`);
    // 캔버스 래스터화에서 CSS 변수는 풀리지 않는다 — 실제 rgb 값만 있어야 한다.
    expect(svg).not.toContain("var(--");
    expect((svg.match(/<circle[^>]*r="[0-9.]+"[^>]*fill="rgb\(15 13 12\)"/g) ?? []).length).toBeGreaterThanOrEqual(1);
    expect(svg).toContain("rgb(250 245 236)");
    expect(svg).toContain("daegong vs 이창호");
    expect(svg).toContain("백 불계승");
  });

  it("escapes markup in user-provided text", () => {
    const svg = buildResultCardSvg({
      size: 9,
      board: ".".repeat(81),
      title: '<b>"x"</b> & y',
      subtitle: "",
      result: "",
    });
    expect(svg).toContain("&lt;b&gt;&quot;x&quot;&lt;/b&gt; &amp; y");
    expect(svg).not.toContain("<b>");
  });
});
