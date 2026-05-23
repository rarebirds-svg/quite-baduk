// 검색엔진 제출용 사이트맵 — 정적 공개 페이지 + 동적 프로 기보 페이지(911+).
import type { MetadataRoute } from "next";
import { getContentSlugs } from "../lib/content";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const revalidate = 3600; // 1시간 캐시 — ingest 후 최대 1시간 내 노출.

interface ProSitemapItem {
  id: number;
  created_at: string;
}

async function fetchProList(): Promise<ProSitemapItem[]> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/sitemap`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return (await res.json()) as ProSitemapItem[];
  } catch {
    return [];
  }
}

interface ThemeItem {
  slug: string;
  label: string;
  description: string;
  count: number;
}

async function fetchThemesList(): Promise<ThemeItem[]> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/themes`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return (await res.json()) as ThemeItem[];
  } catch {
    return [];
  }
}

function monthlyPickMonths(): string[] {
  const now = new Date();
  const months: string[] = [];
  for (let delta = -12; delta <= 1; delta++) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + delta, 1));
    months.push(
      `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`,
    );
  }
  return months;
}

function contentUrls(kind: "glossary" | "faq"): MetadataRoute.Sitemap {
  const slugs = getContentSlugs(kind);
  return [
    {
      url: `${BASE}/${kind}`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.5,
    },
    ...slugs.map((s) => ({
      url: `${BASE}/${kind}/${s}`,
      lastModified: new Date(),
      changeFrequency: "monthly" as const,
      priority: 0.5,
    })),
  ];
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const proList = await fetchProList();

  const staticUrls: MetadataRoute.Sitemap = [
    { url: `${BASE}/`,           lastModified: now, changeFrequency: "weekly",  priority: 1 },
    { url: `${BASE}/support`,    lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${BASE}/supporters`, lastModified: now, changeFrequency: "weekly",  priority: 0.4 },
    { url: `${BASE}/privacy`,    lastModified: now, changeFrequency: "yearly",  priority: 0.3 },
    { url: `${BASE}/terms`,      lastModified: now, changeFrequency: "yearly",  priority: 0.3 },
  ];

  const proUrls: MetadataRoute.Sitemap = proList.map((p) => ({
    url: `${BASE}/spectate/pro/${p.id}`,
    lastModified: new Date(p.created_at),
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  const themesList = await fetchThemesList();
  const themeUrls: MetadataRoute.Sitemap = themesList.map((t) => ({
    url: `${BASE}/spectate/themes/${t.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.5,
  }));
  const picksIndex: MetadataRoute.Sitemap = [{
    url: `${BASE}/spectate/picks`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.5,
  }];
  const pickUrls: MetadataRoute.Sitemap = monthlyPickMonths().map((m) => ({
    url: `${BASE}/spectate/picks/monthly/${m}`,
    lastModified: now,
    changeFrequency: "yearly",
    priority: 0.4,
  }));

  const glossaryUrls = contentUrls("glossary");
  const faqUrls = contentUrls("faq");
  return [
    ...staticUrls,
    ...proUrls,
    ...themeUrls,
    ...picksIndex,
    ...pickUrls,
    ...glossaryUrls,
    ...faqUrls,
  ];
}
