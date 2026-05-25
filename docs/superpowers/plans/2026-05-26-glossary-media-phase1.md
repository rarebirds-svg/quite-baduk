# Glossary 미디어 Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 글로서리 마크다운에 보드 다이어그램 코드블록(`` ```board ``)과 정적 이미지(`![]()`)를 정적 figure로 렌더하고, 3 항목(chuk·bik·dan-gup)에 실제 미디어를 적용한다.

**Architecture:** server-side로 `lib/board-svg.ts`가 board 코드블록을 정적 SVG markup으로 변환. `lib/content.ts`가 marked v18의 `renderer.code`(`lang === "board"`)·`renderer.image` 시그니처를 override해 figure로 래핑. CSS `.editorial-prose figure/.board-diagram` 토큰만 추가. 자산은 `web/public/content/glossary/<slug>/`.

**Tech Stack:** Next.js 14 App Router, marked v18, vitest, Tailwind 토큰 CSS 변수, `lib/board.ts::starPoints` 재사용, lucide-react 미사용.

**Spec:** [`docs/superpowers/specs/2026-05-26-glossary-media-phase1-design.md`](../specs/2026-05-26-glossary-media-phase1-design.md)

**marked v18 시그니처 주의:** `renderer.code({ text, lang, escaped })`, `renderer.image({ href, title, text, tokens })` — v8 이전의 positional 인자(`code(code, infostring, escaped)`)가 아니다.

**자율성 게이트:** Task 1-11 = 🟢 자율. Task 12 PR 머지 + 라이브 적용 = 🟡 사람 승인.

---

## Task 1: `lib/board-svg.ts` `parseBoardCodeBlock` + 단위 테스트

**Files:**
- Create: `web/lib/board-svg.ts`
- Create: `web/tests/board-svg.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

Create `web/tests/board-svg.test.ts`:

```ts
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
    expect(spec.position[3]).toBe("...WB....");
    expect(spec.caption).toBe("축의 시작");
  });

  it("defaults size to 19 when missing", () => {
    const src = `position: |
  ...................`.padEnd(0) + Array(19).fill("...................").join("\n  ").padEnd(0);
    // generate 19 rows of 19 dots
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
    expect(spec.position[0]).toBe("........."); // X → .
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
```

- [ ] **Step 2: 테스트 실패 확인**

```
cd web && npx vitest run tests/board-svg.test.ts
```
Expected: FAIL (module not found).

- [ ] **Step 3: `lib/board-svg.ts` 작성 (parser 부분만 우선)**

Create `web/lib/board-svg.ts`:

```ts
// board 코드블록 → 정적 SVG 변환. server-side에서 마크다운 변환 시 호출.
export interface BoardSpec {
  size: number;
  position: string[]; // 행별 size 문자 (.B W만)
  caption?: string;
}

const VALID_CELL = /[.BW]/;

/**
 * 마크다운 ```board 코드블록 내용을 파싱.
 * 형식: `size: <n>` `position: |` 다음 들여쓴 행들, `caption: <text>`.
 * 잘못된 입력은 fallback (size 기본 19, 행 padding, 잘못 문자 → .).
 */
export function parseBoardCodeBlock(source: string): BoardSpec {
  const lines = source.split("\n");
  let size = 19;
  let positionRaw: string[] = [];
  let caption: string | undefined;
  let inPosition = false;

  for (const line of lines) {
    const sizeMatch = line.match(/^\s*size:\s*(\d+)\s*$/);
    if (sizeMatch) {
      size = parseInt(sizeMatch[1], 10);
      inPosition = false;
      continue;
    }
    if (/^\s*position:\s*\|\s*$/.test(line)) {
      inPosition = true;
      continue;
    }
    const captionMatch = line.match(/^\s*caption:\s*(.+?)\s*$/);
    if (captionMatch) {
      caption = captionMatch[1];
      inPosition = false;
      continue;
    }
    if (inPosition) {
      const trimmed = line.replace(/^\s+/, "");
      if (trimmed === "") continue;
      positionRaw.push(trimmed);
    }
  }

  if (size !== 9 && size !== 13 && size !== 19) size = 19;

  // 행 padding + 잘못 문자 정규화
  const position: string[] = [];
  for (let r = 0; r < size; r++) {
    const raw = positionRaw[r] ?? "";
    const cells: string[] = [];
    for (let c = 0; c < size; c++) {
      const ch = raw[c] ?? ".";
      cells.push(VALID_CELL.test(ch) ? ch : ".");
    }
    position.push(cells.join(""));
  }

  return { size, position, caption };
}
```

- [ ] **Step 4: 테스트 통과 확인**

```
cd web && npx vitest run tests/board-svg.test.ts
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add web/lib/board-svg.ts web/tests/board-svg.test.ts
git commit -m "feat(board-svg): parseBoardCodeBlock — YAML 형식 board 코드블록 파서"
```

---

## Task 2: `boardToSvg` + 단위 테스트

**Files:**
- Modify: `web/lib/board-svg.ts`
- Modify: `web/tests/board-svg.test.ts`

- [ ] **Step 1: 테스트 추가**

Append to `web/tests/board-svg.test.ts`:

```ts
import { boardToSvg } from "../lib/board-svg";

describe("boardToSvg", () => {
  const emptyPos = (size: number) => Array(size).fill(".".repeat(size));

  it("includes svg root with viewBox 0 0 480 480", () => {
    const svg = boardToSvg({ size: 9, position: emptyPos(9) });
    expect(svg).toMatch(/<svg[^>]+viewBox="0 0 480 480"/);
  });

  it("renders size×size grid lines", () => {
    const svg = boardToSvg({ size: 9, position: emptyPos(9) });
    // 9 horizontal + 9 vertical = 18 line elements
    const lineCount = (svg.match(/<line\b/g) ?? []).length;
    expect(lineCount).toBe(18);
  });

  it("renders 5 star points on 9x9", () => {
    const svg = boardToSvg({ size: 9, position: emptyPos(9) });
    // star points use <circle class="star">
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
```

- [ ] **Step 2: 테스트 실패 확인**

```
cd web && npx vitest run tests/board-svg.test.ts
```
Expected: parse 6 PASS + boardToSvg 7 FAIL.

- [ ] **Step 3: `boardToSvg` 구현**

Append to `web/lib/board-svg.ts`:

```ts
const VIEWBOX = 480;
const PAD = 30;
const INNER = VIEWBOX - PAD * 2; // 420

interface CellCoord { x: number; y: number; }

function cellCenter(size: number, col: number, row: number): CellCoord {
  const step = INNER / (size - 1);
  return { x: PAD + col * step, y: PAD + row * step };
}

const STAR_POINTS: Record<number, [number, number][]> = {
  9: [[2,2],[6,2],[4,4],[2,6],[6,6]],
  13: [[3,3],[9,3],[6,6],[3,9],[9,9]],
  19: [[3,3],[9,3],[15,3],[3,9],[9,9],[15,9],[3,15],[9,15],[15,15]],
};

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * BoardSpec → 정적 SVG markup. 토큰은 CSS 변수(rgb(var(--...)))로 light/dark 자동 대응.
 */
export function boardToSvg(spec: BoardSpec): string {
  const { size, position, caption } = spec;
  const label = caption ? escapeXml(caption) : `${size}×${size} 바둑판 다이어그램`;
  const step = INNER / (size - 1);
  const stoneR = step * 0.45;
  const starR = step * 0.10;
  const parts: string[] = [];

  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VIEWBOX} ${VIEWBOX}" role="img" aria-label="${label}">`,
  );

  // grid lines
  for (let i = 0; i < size; i++) {
    const v = PAD + i * step;
    // horizontal
    parts.push(
      `<line x1="${PAD}" y1="${v}" x2="${PAD + INNER}" y2="${v}" stroke="rgb(var(--ink-mute))" stroke-width="1" />`,
    );
    // vertical
    parts.push(
      `<line x1="${v}" y1="${PAD}" x2="${v}" y2="${PAD + INNER}" stroke="rgb(var(--ink-mute))" stroke-width="1" />`,
    );
  }

  // star points
  const stars = STAR_POINTS[size] ?? [];
  for (const [c, r] of stars) {
    const { x, y } = cellCenter(size, c, r);
    parts.push(`<circle class="star" cx="${x}" cy="${y}" r="${starR}" fill="rgb(var(--ink-mute))" />`);
  }

  // stones
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const ch = position[r]?.[c];
      if (ch !== "B" && ch !== "W") continue;
      const { x, y } = cellCenter(size, c, r);
      if (ch === "B") {
        parts.push(
          `<circle class="stone-black" cx="${x}" cy="${y}" r="${stoneR}" fill="rgb(var(--stone-black))" />`,
        );
      } else {
        parts.push(
          `<circle class="stone-white" cx="${x}" cy="${y}" r="${stoneR}" fill="rgb(var(--stone-white))" stroke="rgb(var(--ink-mute))" stroke-width="1" />`,
        );
      }
    }
  }

  parts.push(`</svg>`);
  return parts.join("");
}
```

- [ ] **Step 4: 테스트 통과 확인**

```
cd web && npx vitest run tests/board-svg.test.ts
```
Expected: 13 passed (6 parse + 7 svg).

- [ ] **Step 5: Commit**

```bash
git add web/lib/board-svg.ts web/tests/board-svg.test.ts
git commit -m "feat(board-svg): boardToSvg — 정적 SVG (grid·star·stones, CSS 변수 토큰)"
```

---

## Task 3: `boardCodeBlockToHtml` (figure 래퍼)

**Files:**
- Modify: `web/lib/board-svg.ts`
- Modify: `web/tests/board-svg.test.ts`

- [ ] **Step 1: 테스트 추가**

Append to `web/tests/board-svg.test.ts`:

```ts
import { boardCodeBlockToHtml } from "../lib/board-svg";

describe("boardCodeBlockToHtml", () => {
  it("wraps svg in figure.board-diagram with figcaption when caption present", () => {
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
  .........
caption: 빈 보드`;
    const html = boardCodeBlockToHtml(src);
    expect(html).toMatch(/^<figure class="board-diagram"><svg/);
    expect(html).toMatch(/<figcaption>빈 보드<\/figcaption><\/figure>$/);
  });

  it("omits figcaption when caption is absent", () => {
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
    const html = boardCodeBlockToHtml(src);
    expect(html).toMatch(/^<figure class="board-diagram"><svg/);
    expect(html).not.toMatch(/<figcaption>/);
    expect(html).toMatch(/<\/svg><\/figure>$/);
  });

  it("escapes caption html-unsafe characters", () => {
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
  .........
caption: <script>alert(1)</script>`;
    const html = boardCodeBlockToHtml(src);
    expect(html).not.toMatch(/<script>/);
    expect(html).toMatch(/&lt;script&gt;/);
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

```
cd web && npx vitest run tests/board-svg.test.ts
```
Expected: boardCodeBlockToHtml 3 FAIL.

- [ ] **Step 3: 구현**

Append to `web/lib/board-svg.ts`:

```ts
/**
 * ```board 코드블록 source → <figure class="board-diagram"><svg/>{<figcaption/>}</figure>.
 */
export function boardCodeBlockToHtml(source: string): string {
  const spec = parseBoardCodeBlock(source);
  const svg = boardToSvg(spec);
  const caption = spec.caption
    ? `<figcaption>${escapeXml(spec.caption)}</figcaption>`
    : "";
  return `<figure class="board-diagram">${svg}${caption}</figure>`;
}
```

- [ ] **Step 4: 테스트 통과 확인**

```
cd web && npx vitest run tests/board-svg.test.ts
```
Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add web/lib/board-svg.ts web/tests/board-svg.test.ts
git commit -m "feat(board-svg): boardCodeBlockToHtml — figure.board-diagram 래퍼"
```

---

## Task 4: `lib/content.ts` marked `renderer.code` override (board)

**Files:**
- Modify: `web/lib/content.ts`
- Create: `web/tests/content.media.test.ts`

- [ ] **Step 1: 실패 테스트 작성**

Create `web/tests/content.media.test.ts`:

```ts
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
```

- [ ] **Step 2: 테스트 실패 확인**

```
cd web && npx vitest run tests/content.media.test.ts
```
Expected: FAIL (output에 board figure 없음, 기본 `<pre><code>` 그대로).

- [ ] **Step 3: `lib/content.ts` 수정 — marked renderer.code override**

Modify `web/lib/content.ts` — 기존 imports 아래에 marked Renderer 설정 추가, `getContent` 함수는 그대로:

```ts
// web/content/<kind>/<slug>.md 마크다운 콘텐츠 reader — frontmatter 파싱 + html 렌더.
import fs from "node:fs";
import path from "node:path";

import matter from "gray-matter";
import { marked } from "marked";

import { boardCodeBlockToHtml } from "./board-svg";

const CONTENT_ROOT = path.join(process.cwd(), "content");

export type ContentKind = "glossary" | "faq";

export interface ContentItem {
  slug: string;
  kind: ContentKind;
  title: string;
  created_at?: string;
  excerpt: string;
  html: string;
}

// marked v18: renderer 함수가 객체 인자를 받는다.
// ```board 코드블록은 board-svg가 figure로 변환, 나머지는 기본 처리.
const renderer = new marked.Renderer();
const defaultCode = renderer.code.bind(renderer);
renderer.code = function ({ text, lang, escaped }) {
  if (lang === "board") {
    return boardCodeBlockToHtml(text);
  }
  return defaultCode({ text, lang, escaped });
};
marked.use({ renderer });

function contentDir(kind: ContentKind): string {
  return path.join(CONTENT_ROOT, kind);
}

export function getContentSlugs(kind: ContentKind): string[] {
  const dir = contentDir(kind);
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => f.replace(/\.md$/, ""))
    .sort();
}

export function extractExcerpt(content: string, override?: string): string {
  if (override && override.trim()) return override.trim();
  if (!content) return "";
  const plain = content
    .replace(/^#+\s+.*$/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
  const firstPara = plain.split(/\n\n+/)[0]?.trim() ?? "";
  const sentenceMatch = firstPara.match(/^([\s\S]*?[.!?])(\s|$)/);
  const candidate = sentenceMatch ? sentenceMatch[1].trim() : firstPara;
  if ([...candidate].length > 100) {
    return [...candidate].slice(0, 100).join("") + "…";
  }
  return candidate;
}

export function getContent(kind: ContentKind, slug: string): ContentItem | null {
  const file = path.join(contentDir(kind), `${slug}.md`);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf-8");
  const { data, content } = matter(raw);
  if (data.kind !== kind) return null;
  if (data.slug !== slug) return null;
  const html = marked.parse(content, { async: false }) as string;
  const excerpt = extractExcerpt(
    content,
    typeof data.excerpt === "string" ? data.excerpt : undefined,
  );
  return {
    slug,
    kind,
    title: String(data.title ?? slug),
    created_at: data.created_at ? String(data.created_at) : undefined,
    excerpt,
    html,
  };
}
```

- [ ] **Step 4: 테스트 통과 확인**

```
cd web && npx vitest run tests/content.media.test.ts
```
Expected: 2 passed.

- [ ] **Step 5: 기존 테스트 회귀 확인**

```
cd web && npx vitest run tests/content.test.ts tests/content.excerpt.test.ts
```
Expected: 모두 PASS.

- [ ] **Step 6: Commit**

```bash
git add web/lib/content.ts web/tests/content.media.test.ts
git commit -m "feat(content): marked renderer.code override — ```board → figure.board-diagram"
```

---

## Task 5: `renderer.image` override → figure.content-image

**Files:**
- Modify: `web/lib/content.ts`
- Modify: `web/tests/content.media.test.ts`

- [ ] **Step 1: 테스트 추가**

Append to `web/tests/content.media.test.ts`:

```ts
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
});
```

- [ ] **Step 2: 테스트 실패 확인**

```
cd web && npx vitest run tests/content.media.test.ts
```
Expected: image 3 FAIL.

- [ ] **Step 3: 구현 — `renderer.image` 추가**

Modify `web/lib/content.ts` — 기존 renderer 설정 블록을 다음과 같이 확장:

```ts
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const renderer = new marked.Renderer();
const defaultCode = renderer.code.bind(renderer);
renderer.code = function ({ text, lang, escaped }) {
  if (lang === "board") {
    return boardCodeBlockToHtml(text);
  }
  return defaultCode({ text, lang, escaped });
};
renderer.image = function ({ href, text }) {
  const alt = escapeHtml(text ?? "");
  const src = escapeHtml(href ?? "");
  const caption = alt ? `<figcaption>${alt}</figcaption>` : "";
  return `<figure class="content-image"><img src="${src}" alt="${alt}" loading="lazy" />${caption}</figure>`;
};
marked.use({ renderer });
```

- [ ] **Step 4: 테스트 통과 확인**

```
cd web && npx vitest run tests/content.media.test.ts
```
Expected: 5 passed (board 2 + image 3).

- [ ] **Step 5: Commit**

```bash
git add web/lib/content.ts web/tests/content.media.test.ts
git commit -m "feat(content): marked renderer.image override — ![]() → figure.content-image"
```

---

## Task 6: `extractExcerpt` 보강 — board 코드블록·이미지 마크다운 제거

**Files:**
- Modify: `web/lib/content.ts`
- Modify: `web/tests/content.excerpt.test.ts`

- [ ] **Step 1: 테스트 추가**

Append to `web/tests/content.excerpt.test.ts`:

```ts
describe("extractExcerpt with media", () => {
  it("ignores board codeblock and finds following sentence", () => {
    const md = "```board\nsize: 9\nposition: |\n  .........\n```\n\n축은 기본 기술이다. 다음 문장.";
    expect(extractExcerpt(md)).toBe("축은 기본 기술이다.");
  });

  it("ignores image markdown and finds following sentence", () => {
    const md = "![alt](/path/x.svg)\n\n빅은 살아 있는 형태다. 다음 문장.";
    expect(extractExcerpt(md)).toBe("빅은 살아 있는 형태다.");
  });

  it("strips both board and image then takes first sentence", () => {
    const md = "![대표](/p.svg)\n\n```board\nsize: 9\nposition: |\n  .........\n```\n\n핵심 정의.";
    expect(extractExcerpt(md)).toBe("핵심 정의.");
  });
});
```

- [ ] **Step 2: 테스트 실패 확인**

```
cd web && npx vitest run tests/content.excerpt.test.ts
```
Expected: 신규 3 FAIL.

- [ ] **Step 3: `extractExcerpt` 보강**

Modify `web/lib/content.ts::extractExcerpt` — 정규식 체인 맨 앞에 board/image 제거 추가:

```ts
export function extractExcerpt(content: string, override?: string): string {
  if (override && override.trim()) return override.trim();
  if (!content) return "";
  const plain = content
    .replace(/```board[\s\S]*?```/g, "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/^#+\s+.*$/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
  const firstPara = plain.split(/\n\n+/)[0]?.trim() ?? "";
  const sentenceMatch = firstPara.match(/^([\s\S]*?[.!?])(\s|$)/);
  const candidate = sentenceMatch ? sentenceMatch[1].trim() : firstPara;
  if ([...candidate].length > 100) {
    return [...candidate].slice(0, 100).join("") + "…";
  }
  return candidate;
}
```

- [ ] **Step 4: 테스트 통과 + 회귀 확인**

```
cd web && npx vitest run tests/content.excerpt.test.ts
```
Expected: 11 passed (기존 8 + 신규 3).

- [ ] **Step 5: Commit**

```bash
git add web/lib/content.ts web/tests/content.excerpt.test.ts
git commit -m "feat(content): extractExcerpt가 board 코드블록·이미지 마크다운을 무시"
```

---

## Task 7: `editorial-prose` figure / .board-diagram 스타일

**Files:**
- Modify: `web/app/globals.css`

- [ ] **Step 1: globals.css의 `.editorial-prose` 블록 끝에 figure 스타일 추가**

Locate the existing `@layer components { .editorial-prose { ... } ... }` block (added in PR #37). After the last `.editorial-prose hr` rule, append:

```css
  .editorial-prose figure {
    @apply my-8 flex flex-col items-center gap-3;
  }
  .editorial-prose figure img {
    @apply max-w-full border border-ink-faint bg-paper;
  }
  .editorial-prose figure figcaption {
    @apply font-mono text-xs uppercase tracking-label text-ink-mute text-center;
  }
  .editorial-prose .board-diagram svg {
    @apply w-full max-w-[480px] border border-ink-faint bg-paper-deep;
  }
```

- [ ] **Step 2: build 검증 (CSS 컴파일)**

```
cd web && npm run build 2>&1 | tail -5
```
Expected: build success.

- [ ] **Step 3: Commit**

```bash
git add web/app/globals.css
git commit -m "feat(css): editorial-prose에 figure·board-diagram 토큰 추가"
```

---

## Task 8: `public/content/glossary/dan-gup/rank-ladder.svg` 자산 작성

**Files:**
- Create: `web/public/content/glossary/dan-gup/rank-ladder.svg`

- [ ] **Step 1: 디렉터리 생성 + SVG 작성**

```bash
mkdir -p web/public/content/glossary/dan-gup
```

Create `web/public/content/glossary/dan-gup/rank-ladder.svg`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 360" role="img" aria-label="단·급 체계 — 1단부터 9단·1급부터 18급까지 사다리">
  <style>
    .row-bg { fill: rgb(var(--paper-deep)); }
    .row-bg-alt { fill: rgb(var(--paper)); }
    .grid-line { stroke: rgb(var(--ink-faint)); stroke-width: 1; }
    .label-tier { font-family: "Newsreader", serif; font-size: 14px; font-weight: 600; fill: rgb(var(--ink)); }
    .label-rank { font-family: "IBM Plex Mono", monospace; font-size: 11px; fill: rgb(var(--ink-mute)); letter-spacing: 0.05em; text-transform: uppercase; }
    .accent { fill: rgb(var(--oxblood)); }
    .divider { stroke: rgb(var(--ink-mute)); stroke-width: 1.5; }
  </style>

  <!-- 상단: 단(段) 9단 -->
  <g transform="translate(20 20)">
    <rect class="row-bg" x="0" y="0" width="440" height="140" />
    <text class="label-tier" x="220" y="22" text-anchor="middle">DAN · 단 (高수)</text>
    <line class="grid-line" x1="0" y1="34" x2="440" y2="34" />
    <g transform="translate(0 60)">
      <!-- 9단 cells, 40px wide each -->
      <g>
        <!-- col labels 9~1 -->
      </g>
    </g>
    <g>
      <!-- 9 columns, each 44px wide -->
      <g transform="translate(22 60)">
        <text class="label-rank" x="0" y="14" text-anchor="middle">9D</text>
        <text class="label-rank" x="0" y="34" text-anchor="middle">★★★</text>
      </g>
      <g transform="translate(66 60)">
        <text class="label-rank" x="0" y="14" text-anchor="middle">8D</text>
      </g>
      <g transform="translate(110 60)">
        <text class="label-rank" x="0" y="14" text-anchor="middle">7D</text>
      </g>
      <g transform="translate(154 60)">
        <text class="label-rank" x="0" y="14" text-anchor="middle">6D</text>
      </g>
      <g transform="translate(198 60)">
        <text class="label-rank" x="0" y="14" text-anchor="middle">5D</text>
      </g>
      <g transform="translate(242 60)">
        <text class="label-rank" x="0" y="14" text-anchor="middle">4D</text>
      </g>
      <g transform="translate(286 60)">
        <text class="label-rank" x="0" y="14" text-anchor="middle">3D</text>
      </g>
      <g transform="translate(330 60)">
        <text class="label-rank" x="0" y="14" text-anchor="middle">2D</text>
      </g>
      <g transform="translate(374 60)">
        <text class="label-rank accent" x="0" y="14" text-anchor="middle">1D</text>
        <text class="label-rank" x="0" y="34" text-anchor="middle">입단</text>
      </g>
    </g>
    <line class="divider" x1="396" y1="100" x2="396" y2="130" />
  </g>

  <!-- 중간 구분선 -->
  <line class="divider" x1="20" y1="175" x2="460" y2="175" />
  <text class="label-tier" x="240" y="170" text-anchor="middle" fill="rgb(var(--ink-mute))" font-size="11" letter-spacing="0.1em">— 입단선 —</text>

  <!-- 하단: 급(級) 1~18급 -->
  <g transform="translate(20 190)">
    <rect class="row-bg-alt" x="0" y="0" width="440" height="150" />
    <text class="label-tier" x="220" y="22" text-anchor="middle">KYU · 급 (초~중급)</text>
    <line class="grid-line" x1="0" y1="34" x2="440" y2="34" />
    <!-- 1K accent (입단 직전) -->
    <g transform="translate(22 60)">
      <text class="label-rank accent" x="0" y="14" text-anchor="middle">1K</text>
      <text class="label-rank" x="0" y="34" text-anchor="middle">입단 직전</text>
    </g>
    <g transform="translate(66 60)">
      <text class="label-rank" x="0" y="14" text-anchor="middle">5K</text>
    </g>
    <g transform="translate(110 60)">
      <text class="label-rank" x="0" y="14" text-anchor="middle">10K</text>
    </g>
    <g transform="translate(154 60)">
      <text class="label-rank" x="0" y="14" text-anchor="middle">15K</text>
      <text class="label-rank" x="0" y="34" text-anchor="middle">초보</text>
    </g>
    <g transform="translate(198 60)">
      <text class="label-rank" x="0" y="14" text-anchor="middle">18K</text>
      <text class="label-rank" x="0" y="34" text-anchor="middle">입문</text>
    </g>

    <text class="label-rank" x="220" y="120" text-anchor="middle" fill="rgb(var(--ink-mute))">숫자가 작을수록 高수 — 1급 → 입단 → 1단 → 9단으로 진급</text>
  </g>
</svg>
```

- [ ] **Step 2: SVG가 정상 파일로 작성됐는지 확인**

```
ls -la web/public/content/glossary/dan-gup/rank-ladder.svg
head -3 web/public/content/glossary/dan-gup/rank-ladder.svg
```

- [ ] **Step 3: Commit**

```bash
git add web/public/content/glossary/dan-gup/rank-ladder.svg
git commit -m "feat(content): dan-gup rank-ladder.svg — 단·급 단계표 자산"
```

---

## Task 9: `chuk.md` 다이어그램 2개 삽입

**Files:**
- Modify: `web/content/glossary/chuk.md`

- [ ] **Step 1: chuk.md 본문에 board 코드블록 2개 삽입**

Replace the body content (frontmatter는 유지) so the file becomes:

````markdown
---
slug: chuk
kind: glossary
title: 축
created_at: 2026-05-25
draft_by: agent v1
---

축은 상대 돌을 직선으로 추격하면서 활로를 하나씩 줄여 잡는 기본 기술이다. 두 활로만 남은 돌을 한 칸씩 따라붙으며 단수를 반복해, 결국 반(바둑판)의 가장자리나 다른 돌에 막혀 도망갈 곳이 없게 만든다. 돌을 잡는 가장 기본적인 작전이지만, 한 수만 어긋나도 자기 돌이 거꾸로 잡히는 일이 흔하기 때문에 입문자가 가장 먼저 익혀야 할 형태로 꼽힌다.

```board
size: 9
position: |
  .........
  .........
  ....B....
  ...WB....
  ....W....
  .........
  .........
  .........
  .........
caption: 축의 시작 — 흑이 백을 단수하며 한 칸씩 추격.
```

축의 성패를 가르는 핵심 개념이 **축머리**다. 추격이 진행되는 경로 위에 상대편 돌이 미리 놓여 있다면, 그 지점에서 활로가 다시 늘어나 축은 성립하지 않는다. 따라서 축을 걸기 전에 추격 라인이 반의 어디까지 이어지는지, 그 경로 위에 상대의 돌이 있는지를 반드시 확인해야 한다. 반대로 축이 안 되는 상황에서 상대가 일부러 그 자리에 미리 두는 수를 두면, 이를 **축머리 활용**이라 부른다.

```board
size: 9
position: |
  .........
  .........
  ....B....
  ...WB....
  ....W....
  .........
  ....B....
  .........
  .........
caption: 축머리가 있는 경우 — 추격 경로 위에 흑 돌이 놓여 있어 축 무효.
```

초보자가 가장 자주 저지르는 실수는 두 가지다. 축머리가 있는데도 무리하게 축을 걸어 상대 돌을 키워 주는 경우, 그리고 자기 돌이 축에 걸렸음을 알면서도 빠져나가려 도망쳐 손해를 키우는 경우다. 축이 분명히 성립한다면 도망치지 말고 다른 큰 자리로 손을 돌리는 편이 거의 항상 이득이다. 축을 정확히 읽는 능력은 사활·수상전과 함께 기력 향상의 가장 기초적인 토대가 된다.
````

- [ ] **Step 2: build로 변환 결과 검증 (간접)**

```
cd web && npm run build 2>&1 | tail -5
```
Expected: build 성공. 라우트 `/glossary/[slug]`이 정적/동적 표시되며 에러 없음.

- [ ] **Step 3: Commit**

```bash
git add web/content/glossary/chuk.md
git commit -m "content(glossary): chuk에 축 시작·축머리 보드 다이어그램 2개 추가"
```

---

## Task 10: `bik.md` 다이어그램 1개 삽입

**Files:**
- Modify: `web/content/glossary/bik.md`

- [ ] **Step 1: 현재 본문 확인**

```
cat web/content/glossary/bik.md
```

확인한 frontmatter는 유지하고, 본문에 board 코드블록 1개를 첫 단락 다음에 삽입.

- [ ] **Step 2: 파일 수정 — board 다이어그램 1개 추가**

Add the following block after the first body paragraph (the paragraph that describes 빅 generally). 기존 본문 단락들은 그대로 유지하고 board 블록만 삽입:

````markdown
```board
size: 9
position: |
  .........
  .........
  ...BBB...
  ..BWWWB..
  ..BW.WB..
  ..BWWWB..
  ...BBB...
  .........
  .........
caption: 빅의 전형적 형태 — 양측 돌이 얽혀 양보 불가.
```
````

위치 가이드: bik.md의 첫 번째 본문 단락 끝에 빈 줄 + 위 코드블록 + 빈 줄 + (나머지 본문 단락).

- [ ] **Step 3: build 검증**

```
cd web && npm run build 2>&1 | tail -5
```
Expected: build 성공.

- [ ] **Step 4: Commit**

```bash
git add web/content/glossary/bik.md
git commit -m "content(glossary): bik에 전형적 빅 형태 보드 다이어그램 추가"
```

---

## Task 11: `dan-gup.md` 이미지 1개 삽입

**Files:**
- Modify: `web/content/glossary/dan-gup.md`

- [ ] **Step 1: 현재 본문 확인 + 이미지 추가**

`web/content/glossary/dan-gup.md`의 첫 본문 단락 직후에 다음 한 줄(빈 줄로 분리)을 추가:

```markdown
![단·급 체계 — 1급에서 입단(1단)을 거쳐 9단까지의 진급 사다리](/content/glossary/dan-gup/rank-ladder.svg)
```

frontmatter와 기존 본문은 그대로 유지.

- [ ] **Step 2: build 검증**

```
cd web && npm run build 2>&1 | tail -5
```
Expected: build 성공.

- [ ] **Step 3: Commit**

```bash
git add web/content/glossary/dan-gup.md
git commit -m "content(glossary): dan-gup에 rank-ladder.svg 이미지 삽입"
```

---

## Task 12: 전체 검증 + PR + 🟡 머지 + 라이브 활성화

**Files:** 변경 없음 — 검증·배포 단계

- [ ] **Step 1: 전체 type-check + lint + vitest + build**

```
cd web
npm run type-check
npm run lint
npx vitest run
npm run build 2>&1 | tail -10
```
Expected:
- type-check: no errors
- lint: clean
- vitest: 기존 + 신규 (board-svg 16, content.media 5, excerpt 추가 3 = 24 신규 PASS)
- build: 4 글로서리·FAQ 라우트 모두 정상

- [ ] **Step 2: branch rename + push + PR**

```bash
git branch -m feat/glossary-media-phase1
git push -u origin feat/glossary-media-phase1
gh pr create --title "feat(content): 글로서리 미디어 Phase 1 — 보드 다이어그램 + 정적 이미지" --body "$(cat <<'EOF'
## Summary

글로서리 마크다운에 미디어 통합 (Phase 1).

- ` ```board ` fenced code block → 정적 SVG 다이어그램 (`figure.board-diagram`)
- `![alt](path)` → `figure.content-image` (img + figcaption)
- 토큰 CSS 변수 활용 (light/dark 자동 대응)
- 3 글로서리 항목 콘텐츠 업데이트: chuk(다이어그램 2) · bik(다이어그램 1) · dan-gup(SVG 이미지 1)

신규: `lib/board-svg.ts` (parseBoardCodeBlock + boardToSvg + boardCodeBlockToHtml), `public/content/glossary/dan-gup/rank-ladder.svg`. 기존 `lib/content.ts`에 marked v18 renderer override (board·image) + `extractExcerpt` 보강. `.editorial-prose` 에 figure 토큰 추가.

동영상은 Phase 2 별도 spec.

## Test plan

- [x] vitest 신규: board-svg 16, content.media 5, excerpt 추가 3
- [x] type-check + lint OK
- [x] build 라우트 정상
- [ ] **머지 후**: `/glossary/chuk`·`/glossary/bik`·`/glossary/dan-gup` 라이브에서 다이어그램·이미지 렌더링 + Editorial 토큰 적용 시각 확인

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: 🟡 사람 승인 대기**

PR 링크를 사용자에게 보고 후 머지 승인 대기. 승인 전 stop.

- [ ] **Step 4: 승인 후 머지 + 라이브 적용**

```bash
gh pr merge --merge --delete-branch
cd /Users/daegong/projects/baduk
git fetch origin main
git merge --ff-only origin/main 2>&1 | tail -3 || { git reset origin/main; git restore .; }
cd web && npm run build 2>&1 | tail -10
launchctl kickstart -k "gui/$(id -u)/com.baduk.web"
sleep 7
# 라이브 verify
for path in /glossary/chuk /glossary/bik /glossary/dan-gup; do
  printf "  %-30s " "$path"
  /usr/bin/curl -fs -o /dev/null -w "%{http_code}\n" --max-time 10 "http://localhost:3000$path"
done
# SSR HTML에 board-diagram·content-image 클래스 포함 확인
/usr/bin/curl -fs http://localhost:3000/glossary/chuk | grep -oE '(board-diagram|content-image|<svg|figcaption)' | sort -u | head -10
```
Expected: 3 경로 모두 200, SSR HTML에 `board-diagram`·`<svg`·`figcaption` 포함.

- [ ] **Step 5: 워크트리 정리**

```bash
# main worktree에서 (cd /Users/daegong/projects/baduk)
# worktree 종료는 ExitWorktree(action="remove", discard_changes=true) 호출
git branch -D feat/glossary-media-phase1
```

---

## 자율성 요약

| Task | 등급 |
|---|---|
| 1–11 (코드·테스트·콘텐츠·SVG) | 🟢 자율 |
| 12 Step 1-2 (검증 + PR 생성) | 🟢 자율 |
| 12 Step 3 (사람 승인) | 🟡 |
| 12 Step 4 (머지 + build + kickstart) | 🟡 (Step 3과 묶어) |
| 12 Step 5 (정리) | 🟢 |

## 검증 통과 기준

- 신규 vitest 모두 PASS (board-svg 16 + content.media 5 + excerpt 추가 3 = 24)
- type-check + lint clean
- build 4 라우트 정상 (`/glossary`, `/glossary/[slug]`, `/faq`, `/faq/[slug]`)
- 라이브 3 글로서리 URL 200 + SSR HTML에 `board-diagram` 클래스 포함
- 시각: chuk/bik에 보드 다이어그램 (격자·돌·캡션), dan-gup에 단·급 사다리 SVG가 Editorial 톤으로 렌더
