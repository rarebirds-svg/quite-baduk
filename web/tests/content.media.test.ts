// 마크다운 board 코드블록 + 이미지 marked renderer override 테스트.
import { describe, it, expect } from "vitest";
import { marked } from "marked";
// content.ts import 자체가 marked 글로벌 use() 부수효과를 일으킨다 — import 자체로 충분.
import "../lib/content";

describe("marked board codeblock override", () => {
  it("converts ```board fenced block to figure.board-diagram with svg", () => {
    const md = "```board\nsize: 9\nposition: |\n  .........\n  .........\n  .........\n  .........\n  .........\n  .........\n  .........\n  .........\n  .........\ncaption: 빈 보드\n```";
    const html = marked.parse(md, { async: false }) as string;
    expect(html).toMatch(/<figure class="board-diagram">/);
    expect(html).toMatch(/<svg[^>]+viewBox="0 0 480 480"/);
    expect(html).toMatch(/<figcaption>빈 보드<\/figcaption>/);
  });

  it("falls back to <pre><code> for non-board fenced blocks", () => {
    const md = "```ts\nconst x = 1;\n```";
    const html = marked.parse(md, { async: false }) as string;
    expect(html).toMatch(/<pre>/);
    expect(html).toMatch(/<code/);
    expect(html).not.toMatch(/<figure class="board-diagram">/);
  });
});
