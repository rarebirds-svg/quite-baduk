// 글로서리 상세 페이지 — 마크다운 본문을 server-side 렌더.
import { notFound } from "next/navigation";

import { getContent } from "../../../lib/content";

export default function GlossaryDetail({
  params,
}: {
  params: { slug: string };
}) {
  const c = getContent("glossary", params.slug);
  if (c === null) notFound();
  return (
    <article className="prose">
      <header>
        <h1>{c.title}</h1>
      </header>
      <div dangerouslySetInnerHTML={{ __html: c.html }} />
    </article>
  );
}
