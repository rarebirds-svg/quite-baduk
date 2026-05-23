// 글로서리 인덱스 — web/content/glossary/ 디렉터리의 모든 슬러그 리스트.
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";

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
    .filter((c): c is NonNullable<typeof c> => c !== null);
  return (
    <article className="prose">
      <h1>바둑 용어</h1>
      <p>총 {items.length}개 항목.</p>
      <ul className="not-prose grid gap-1">
        {items.map((c) => (
          <li key={c.slug}>
            <a href={`/glossary/${c.slug}`}>{c.title}</a>
          </li>
        ))}
      </ul>
    </article>
  );
}
