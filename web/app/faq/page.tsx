// FAQ 인덱스 — server fetch + client wrapper (Hero + accordion + CTA).
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";
import { FaqClient } from "./_FaqClient";

// 콘텐츠 md 추가를 재빌드·재시작 없이 노출 — 요청 시 fs 재읽기.
export const dynamic = "force-dynamic";

const BASE = "https://inkbaduk.com";

export const metadata: Metadata = {
  title: "자주 묻는 질문 — inkbaduk",
  description: "inkbaduk의 AI 바둑·복기·세션 등에 대한 자주 묻는 질문.",
  alternates: { canonical: `${BASE}/faq` },
};

// FAQPage 구조화 데이터용 — 렌더된 html에서 태그·엔티티를 제거해 순수 텍스트로 축약.
function htmlToText(html: string): string {
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

export default function FaqIndex() {
  const slugs = getContentSlugs("faq");
  const items = slugs
    .map((s) => getContent("faq", s))
    .filter((c): c is NonNullable<typeof c> => c !== null)
    .map((c) => ({ slug: c.slug, title: c.title, html: c.html }));

  // 검색 결과 FAQ 리치 표시를 위한 구조화 데이터 (schema.org FAQPage).
  const faqJsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((it) => ({
      "@type": "Question",
      name: it.title,
      acceptedAnswer: { "@type": "Answer", text: htmlToText(it.html) },
    })),
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd).replace(/</g, "\\u003c") }}
      />
      <FaqClient items={items} />
    </div>
  );
}
