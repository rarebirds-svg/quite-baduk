"use client";
// 글로서리 인덱스의 client 부분 — Hero + i18n + 검색·초성 필터 + 카드 그리드.
import { useT } from "@/lib/i18n";
import { Hero } from "@/components/editorial/Hero";
import { ContentCard } from "@/components/editorial/ContentCard";
import { ContentSearchFilter } from "@/components/editorial/ContentSearchFilter";

export interface GlossaryClientItem {
  slug: string;
  title: string;
  excerpt: string;
}

export function GlossaryClient({ items }: { items: GlossaryClientItem[] }) {
  const t = useT();
  const subtitle = t("glossary.heroSubtitle", { count: items.length });
  return (
    <>
      <Hero
        size="compact"
        volume={t("glossary.heroVolume")}
        title={t("glossary.heroTitle")}
        subtitle={subtitle}
      />
      <div className="mt-10">
        <ContentSearchFilter
          items={items}
          searchPlaceholder={t("glossary.searchPlaceholder")}
          filterAllLabel={t("glossary.filterAll")}
          emptyLabel={t("glossary.empty")}
          renderItem={(it) => (
            <ContentCard
              key={it.slug}
              href={`/glossary/${it.slug}`}
              title={it.title}
              slug={it.slug}
              excerpt={it.excerpt}
              ctaLabel={t("glossary.cardMore")}
            />
          )}
        />
      </div>
    </>
  );
}
