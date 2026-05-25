// FAQ 상세 — Breadcrumb + Hero + editorial-prose 본문 + prev/next + CTA (글로서리 상세와 동일 패턴).
import { notFound } from "next/navigation";
import Link from "next/link";

import { getContent, getContentSlugs } from "../../../lib/content";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { Button } from "@/components/ui/button";

interface AdjacentEntry {
  slug: string;
  title: string;
}

function adjacents(currentSlug: string): { prev: AdjacentEntry | null; next: AdjacentEntry | null } {
  const slugs = getContentSlugs("faq");
  const idx = slugs.indexOf(currentSlug);
  if (idx < 0) return { prev: null, next: null };
  const toEntry = (s: string | undefined): AdjacentEntry | null => {
    if (!s) return null;
    const c = getContent("faq", s);
    return c ? { slug: c.slug, title: c.title } : null;
  };
  return { prev: toEntry(slugs[idx - 1]), next: toEntry(slugs[idx + 1]) };
}

export default function FaqDetail({ params }: { params: { slug: string } }) {
  const c = getContent("faq", params.slug);
  if (c === null) notFound();
  const { prev, next } = adjacents(params.slug);

  return (
    <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <nav className="mb-6 flex items-center gap-2 font-mono text-xs uppercase tracking-label text-ink-faint">
        <Link href="/faq" className="transition-base hover:text-oxblood">
          FAQ
        </Link>
        <span aria-hidden>/</span>
        <span className="text-ink-mute">{c.title}</span>
      </nav>

      <Hero size="compact" volume="FAQ" title={c.title} subtitle={c.excerpt} />

      <div
        className="editorial-prose mt-8"
        dangerouslySetInnerHTML={{ __html: c.html }}
      />

      <RuleDivider weight="strong" className="mt-12" />

      <footer className="mt-6 flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:gap-6">
          {prev && (
            <Link
              href={`/faq/${prev.slug}`}
              className="group flex flex-col gap-1 font-sans text-sm text-ink-mute transition-base hover:text-oxblood"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-ink-faint">
                ← 이전
              </span>
              <span className="font-serif text-base">{prev.title}</span>
            </Link>
          )}
          {next && (
            <Link
              href={`/faq/${next.slug}`}
              className="group flex flex-col gap-1 font-sans text-sm text-ink-mute transition-base hover:text-oxblood sm:items-end sm:text-right"
            >
              <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-ink-faint">
                다음 →
              </span>
              <span className="font-serif text-base">{next.title}</span>
            </Link>
          )}
        </div>
        <Button asChild>
          <Link href="/game/new">대국 시작 →</Link>
        </Button>
      </footer>
    </article>
  );
}
