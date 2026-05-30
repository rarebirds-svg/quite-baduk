// 글로서리 인덱스 — server에서 데이터 fetch, client wrapper가 Hero + 검색 + 그리드 렌더.
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";
import { GlossaryClient } from "./_GlossaryClient";

// 콘텐츠 md 추가를 재빌드·재시작 없이 노출 — 요청 시 fs 재읽기.
export const dynamic = "force-dynamic";

const BASE = "https://inkbaduk.com";

export const metadata: Metadata = {
  title: "바둑 용어 — inkbaduk",
  description: "단·급·계가·축·패 등 바둑 용어 해설.",
  alternates: { canonical: `${BASE}/glossary` },
};

export default function GlossaryIndex() {
  const slugs = getContentSlugs("glossary");
  const items = slugs
    .map((s) => getContent("glossary", s))
    .filter((c): c is NonNullable<typeof c> => c !== null)
    .map((c) => ({ slug: c.slug, title: c.title, excerpt: c.excerpt }));

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 lg:px-8">
      <GlossaryClient items={items} />
    </div>
  );
}
