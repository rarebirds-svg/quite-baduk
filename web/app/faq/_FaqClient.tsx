"use client";
// FAQ 인덱스의 client 부분 — Hero + Accordion + 푸터 CTA (모두 i18n).
import Link from "next/link";

import { useT } from "@/lib/i18n";
import { Hero } from "@/components/editorial/Hero";
import {
  ContentAccordion,
  type AccordionContentItem,
} from "@/components/editorial/ContentAccordion";

export function FaqClient({ items }: { items: AccordionContentItem[] }) {
  const t = useT();
  const subtitle = t("faq.heroSubtitle", { count: items.length });
  return (
    <>
      <Hero
        size="compact"
        volume="자주 묻는 질문"
        title={t("faq.heroTitle")}
        subtitle={subtitle}
      />
      <div className="mt-10 flex flex-col gap-12">
        <ContentAccordion items={items} />
        <div className="border-t border-ink-faint pt-6 text-center">
          <Link
            href="/support"
            className="font-mono text-xs font-semibold uppercase tracking-label text-oxblood transition-base hover:opacity-80"
          >
            {t("faq.notFoundCta")}
          </Link>
        </div>
      </div>
    </>
  );
}
