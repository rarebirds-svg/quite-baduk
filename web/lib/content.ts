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
