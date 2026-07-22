// web/content/<kind>/<slug>.md 마크다운 콘텐츠 reader — frontmatter 파싱 + html 렌더.
import fs from "node:fs";
import path from "node:path";

import matter from "gray-matter";
import { marked } from "marked";

const CONTENT_ROOT = path.join(process.cwd(), "content");

export type ContentKind = "glossary" | "faq";

export interface ContentItem {
  slug: string;
  kind: ContentKind;
  title: string;
  // 검색 결과 노출용 제목 — frontmatter에 있으면 <title>에 우선 사용(검색 의도형 롱테일).
  // 없으면 title 기반 기본 템플릿으로 폴백한다.
  seoTitle?: string;
  created_at?: string;
  excerpt: string;
  html: string;
}

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
    created_at: data.created_at ? String(data.created_at) : undefined,
    excerpt,
    html,
  };
}
