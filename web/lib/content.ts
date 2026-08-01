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
  // 검색 결과 노출용 제목 — frontmatter에 있으면 <title>에 우선 사용(검색 의도형 롱테일).
  // 없으면 title 기반 기본 템플릿으로 폴백한다.
  seoTitle?: string;
  // 같은 kind 내 관련 항목 slug 목록 — 상세 페이지 상호 내부링크(크롤 깊이·주제 권위)용.
  related?: string[];
  created_at?: string;
  excerpt: string;
  html: string;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// marked v18: renderer 함수가 객체 인자를 받는다.
// ```board 코드블록은 board-svg가 figure로 변환, 나머지는 기본 처리.
const renderer = new marked.Renderer();
// 기본 구현은 prototype에서 꺼내 call로 위임한다. bind로 고정하면 marked가 렌더 직전에
// 주입하는 this.parser 참조가 끊겨 paragraph 같은 inline 파싱 메서드가 죽는다.
const base = marked.Renderer.prototype;
renderer.code = function (token) {
  if (token.lang === "board") {
    return boardCodeBlockToHtml(token.text);
  }
  return base.code.call(this, token);
};
function imgTag(href?: string | null, text?: string | null): string {
  const alt = escapeHtml(text ?? "");
  const src = escapeHtml(href ?? "");
  return `<img src="${src}" alt="${alt}" loading="lazy" />`;
}

// 인라인 이미지는 문단을 쪼갤 수 없으므로 <img> 그대로 둔다.
// figure 승격은 아래 paragraph override가 "이미지 단독 문단"일 때만 수행한다.
renderer.image = function ({ href, text }) {
  return imgTag(href, text);
};

// <figure>는 <p>의 허용 자식이 아니다. marked는 이미지 하나짜리 줄도 문단으로 감싸므로,
// 그 경우에만 <p>를 걷어내고 figure를 직접 낸다. 나머지 문단은 기본 처리.
renderer.paragraph = function (token) {
  const inline = (token.tokens ?? []).filter(
    (t) => !(t.type === "space" || (t.type === "text" && t.raw.trim() === "")),
  );
  const only = inline.length === 1 ? inline[0] : null;
  if (only && only.type === "image") {
    const { href, text } = only as { href?: string; text?: string };
    const alt = escapeHtml(text ?? "");
    const caption = alt ? `<figcaption>${alt}</figcaption>` : "";
    return `<figure class="content-image">${imgTag(href, text)}${caption}</figure>`;
  }
  return base.paragraph.call(this, token);
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

// 렌더된 html에서 태그·엔티티를 제거해 순수 텍스트로 축약 — 구조화 데이터(JSON-LD)용.
export function htmlToText(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#(?:39|x27);/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ")
    .trim();
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
    seoTitle:
      typeof data.seoTitle === "string" && data.seoTitle.trim()
        ? data.seoTitle.trim()
        : undefined,
    related: Array.isArray(data.related)
      ? data.related.filter((r): r is string => typeof r === "string" && r.trim() !== "")
      : undefined,
    created_at: data.created_at ? String(data.created_at) : undefined,
    excerpt,
    html,
  };
}
