// FAQ 인덱스 — server fetch + client wrapper (Hero + accordion + CTA).
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";
import { FaqClient } from "./_FaqClient";

const BASE = "https://inkbaduk.com";

export const metadata: Metadata = {
  title: "자주 묻는 질문 — inkbaduk",
  description: "inkbaduk의 AI 바둑·복기·세션 등에 대한 자주 묻는 질문.",
  alternates: { canonical: `${BASE}/faq` },
};

export default function FaqIndex() {
  const slugs = getContentSlugs("faq");
  const items = slugs
    .map((s) => getContent("faq", s))
    .filter((c): c is NonNullable<typeof c> => c !== null)
    .map((c) => ({ slug: c.slug, title: c.title, html: c.html }));

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <FaqClient items={items} />
    </div>
  );
}
