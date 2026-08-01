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

describe("marked image override", () => {
  it("converts ![alt](path) to figure.content-image with img + figcaption", () => {
    const md = "![빅의 형태](/content/glossary/bik/figure-1.svg)";
    const html = marked.parse(md, { async: false }) as string;
    expect(html).toMatch(/<figure class="content-image">/);
    expect(html).toMatch(/<img src="\/content\/glossary\/bik\/figure-1\.svg" alt="빅의 형태" loading="lazy"/);
    expect(html).toMatch(/<figcaption>빅의 형태<\/figcaption>/);
  });

  it("omits figcaption when alt is empty", () => {
    const md = "![](/content/glossary/bik/no-alt.svg)";
    const html = marked.parse(md, { async: false }) as string;
    expect(html).toMatch(/<figure class="content-image">/);
    expect(html).toMatch(/alt=""/);
    expect(html).not.toMatch(/<figcaption>/);
  });

  it("escapes html-unsafe characters in alt and src", () => {
    const md = '![alt with <script>](/path?q="x")';
    const html = marked.parse(md, { async: false }) as string;
    expect(html).not.toMatch(/<script>/);
    expect(html).toMatch(/&lt;script&gt;/);
    expect(html).toMatch(/&quot;/);
  });

  // <figure>는 <p>의 허용 자식이 아니다. 브라우저가 <p>를 자동 종료해 빈 문단이 남고
  // .editorial-prose p 여백이 어긋나므로, 단독 이미지 문단은 <p> 없이 figure만 낸다.
  it("does not wrap a standalone image figure in a paragraph", () => {
    const html = marked.parse("![캡션](/a.svg)", { async: false }) as string;
    expect(html).toMatch(/<figure class="content-image">/);
    expect(html).not.toMatch(/<p>\s*<figure/);
    expect(html).not.toMatch(/<\/figure>\s*<\/p>/);
  });

  // 문단 중간의 인라인 이미지는 figure로 승격하지 않는다 — 문단을 쪼갤 수 없기 때문.
  it("keeps an inline image as a plain img inside its paragraph", () => {
    const md = "앞 텍스트 ![캡션](/a.svg) 뒤 텍스트";
    const html = marked.parse(md, { async: false }) as string;
    expect(html).toMatch(/<p>앞 텍스트 <img src="\/a\.svg" alt="캡션" loading="lazy" \/> 뒤 텍스트<\/p>/);
    expect(html).not.toMatch(/<figure/);
  });
});
