// 글로서리 상세 페이지 — 마크다운 본문을 server-side 렌더.
import Link from "next/link";
import { notFound } from "next/navigation";

import { getContent } from "../../../lib/content";

const BASE = "https://inkbaduk.com";

export default function GlossaryDetail({
  params,
}: {
  params: { slug: string };
}) {
  const c = getContent("glossary", params.slug);
  if (c === null) notFound();

  // 관련 용어 — 존재하는 항목만 링크로 노출(크롤 가능한 내부링크).
  const relatedItems = (c.related ?? [])
    .map((slug) => getContent("glossary", slug))
    .filter((r): r is NonNullable<typeof r> => r !== null);

  // 검색 결과 용어 리치 표시를 위한 구조화 데이터 (schema.org DefinedTerm).
  const definedTermJsonLd = {
    "@context": "https://schema.org",
    "@type": "DefinedTerm",
    name: c.title,
    description: c.excerpt,
    inDefinedTermSet: `${BASE}/glossary`,
  };

  // 탐색 경로 리치 표시를 위한 구조화 데이터 (schema.org BreadcrumbList).
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: `${BASE}/` },
      { "@type": "ListItem", position: 2, name: "용어사전", item: `${BASE}/glossary` },
      {
        "@type": "ListItem",
        position: 3,
        name: c.title,
        item: `${BASE}/glossary/${c.slug}`,
      },
    ],
  };

  return (
    <article className="prose">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(definedTermJsonLd).replace(/</g, "\\u003c") }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd).replace(/</g, "\\u003c") }}
      />
      <header>
        <h1>{c.title}</h1>
      </header>
      <div dangerouslySetInnerHTML={{ __html: c.html }} />
      {relatedItems.length > 0 && (
        <nav aria-label="관련 용어" className="not-prose mt-10 border-t border-ink-faint pt-6">
          <h2 className="mb-3 font-mono text-xs uppercase tracking-label text-ink-faint">
            관련 용어
          </h2>
          <ul className="flex flex-wrap gap-x-4 gap-y-2">
            {relatedItems.map((r) => (
              <li key={r.slug}>
                <Link
                  href={`/glossary/${r.slug}`}
                  className="font-sans text-sm text-oxblood transition-base hover:underline"
                >
                  {r.title}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </article>
  );
}
