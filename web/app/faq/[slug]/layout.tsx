// FAQ 상세 페이지 SEO 메타.
import type { Metadata } from "next";
import type { ReactNode } from "react";

import { getContent } from "../../../lib/content";

const BASE = "https://inkbaduk.com";

export function generateMetadata(
  { params }: { params: { slug: string } },
): Metadata {
  const c = getContent("faq", params.slug);
  if (c === null) return { robots: { index: false, follow: false } };
  const title = `${c.title} — inkbaduk FAQ`;
  const description = c.title;
  const canonical = `${BASE}/faq/${c.slug}`;
  return {
    title,
    description,
    alternates: { canonical },
    openGraph: { title, description, url: canonical },
  };
}

export default function FaqLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
