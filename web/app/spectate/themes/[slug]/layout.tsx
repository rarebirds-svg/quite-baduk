// 테마 페이지 SEO 메타 — server component layout.
import type { Metadata } from "next";
import type { ReactNode } from "react";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ThemeMeta {
  slug: string;
  label: string;
  description: string;
  total: number;
}

export async function generateMetadata(
  { params }: { params: { slug: string } },
): Promise<Metadata> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/theme/${params.slug}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return { robots: { index: false, follow: false } };
    const t = (await res.json()) as ThemeMeta;
    const title = `${t.label} — inkbaduk`;
    const description = `${t.description} (총 ${t.total}국)`;
    const canonical = `${BASE}/spectate/themes/${t.slug}`;
    return {
      title,
      description,
      alternates: { canonical },
      openGraph: { title, description, url: canonical },
    };
  } catch {
    return {};
  }
}

export default function ThemeLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
