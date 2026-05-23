// 글로서리 상세 페이지 SEO 메타.
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { getContent } from "../../../lib/content";

const BASE = "https://inkbaduk.com";

export function generateMetadata(
  { params }: { params: { slug: string } },
): Metadata {
  const c = getContent("glossary", params.slug);
  if (c === null) return { robots: { index: false, follow: false } };
  const title = `${c.title} — inkbaduk 바둑 용어`;
  const description = `바둑 용어 "${c.title}" 해설.`;
  const canonical = `${BASE}/glossary/${c.slug}`;
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: { title, description, url: canonical },
  };
}

export default function GlossaryLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
