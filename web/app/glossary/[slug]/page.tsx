// 글로서리 상세 페이지 — 마크다운 본문을 server-side 렌더.
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
    </article>
  );
}
