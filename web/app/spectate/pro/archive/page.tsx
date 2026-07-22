// 프로 기보 전체 크롤 허브 — 911개 상세 페이지로 가는 SSR 내부 링크를 한 페이지에 모아 검색 로봇 도달성을 보장한다.
import type { Metadata } from "next";
import Link from "next/link";

import { Hero } from "@/components/editorial/Hero";

const BASE = "https://inkbaduk.com";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const revalidate = 3600; // 1시간 캐시 — ingest 후 최대 1시간 내 신규 기보 반영.

export const metadata: Metadata = {
  title: "프로 기보 전체 목록 — inkbaduk",
  description:
    "KataGo로 복기하는 프로 바둑 명국 전체 목록. 신진서·알파고 시대 명국을 한 곳에서 관전·복기하세요.",
  alternates: { canonical: `${BASE}/spectate/pro/archive` },
};

interface ArchiveItem {
  id: number;
  created_at: string;
}

async function fetchAll(): Promise<ArchiveItem[]> {
  try {
    const res = await fetch(`${API}/api/spectate/pro/sitemap`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return (await res.json()) as ArchiveItem[];
  } catch {
    return [];
  }
}

export default async function ProArchivePage() {
  const items = await fetchAll();
  return (
    <article className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
      <Hero
        title="프로 기보 전체 목록"
        subtitle={`관전·복기 가능한 명국 ${items.length}국 전체`}
      />
      <nav className="mb-6 font-mono text-xs uppercase tracking-label text-ink-faint">
        <Link href="/spectate/pro" className="transition-base hover:text-oxblood">
          ← 프로 기보 관전으로
        </Link>
      </nav>
      <ul className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3">
        {items.map((g) => (
          <li key={g.id}>
            <Link
              href={`/spectate/pro/${g.id}`}
              className="block py-1 font-mono text-sm tabular-nums text-ink-mute transition-base hover:text-oxblood"
            >
              프로 기보 #{g.id}
            </Link>
          </li>
        ))}
      </ul>
    </article>
  );
}
