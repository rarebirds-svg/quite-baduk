// FAQ 인덱스 — web/content/faq/의 모든 슬러그.
import type { Metadata } from "next";

import { getContent, getContentSlugs } from "../../lib/content";

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
    .filter((c): c is NonNullable<typeof c> => c !== null);
  return (
    <article className="prose">
      <h1>자주 묻는 질문</h1>
      <p>총 {items.length}개 질문.</p>
      <ul className="not-prose grid gap-1">
        {items.map((c) => (
          <li key={c.slug}>
            <a href={`/faq/${c.slug}`}>{c.title}</a>
          </li>
        ))}
      </ul>
    </article>
  );
}
