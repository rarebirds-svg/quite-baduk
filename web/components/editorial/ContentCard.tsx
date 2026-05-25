// 글로서리·콘텐츠용 카드 — title + 슬러그 + 짧은 excerpt + CTA, 전체가 Link.
import * as React from "react";
import Link from "next/link";

import { cn } from "@/lib/cn";
import { RuleDivider } from "./RuleDivider";

export interface ContentCardProps {
  href: string;
  title: string;
  slug: string;
  excerpt: string;
  ctaLabel: string;
  className?: string;
}

export function ContentCard({ href, title, slug, excerpt, ctaLabel, className }: ContentCardProps) {
  return (
    <Link
      href={href}
      className={cn(
        "group flex flex-col gap-3 border border-ink-faint bg-paper p-5 transition-base hover:border-oxblood",
        className,
      )}
    >
      <div className="flex flex-col gap-1">
        <h3 className="font-serif text-2xl font-semibold leading-tight text-ink">{title}</h3>
        <span className="font-mono text-[11px] font-semibold uppercase tracking-label text-ink-faint">
          {slug.toUpperCase()}
        </span>
      </div>
      <RuleDivider weight="faint" />
      <p className="font-sans text-sm leading-relaxed text-ink-mute line-clamp-2">{excerpt}</p>
      <span className="mt-auto font-mono text-xs font-semibold uppercase tracking-label text-oxblood transition-base group-hover:opacity-80">
        {ctaLabel}
      </span>
    </Link>
  );
}
