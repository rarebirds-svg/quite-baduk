"use client";
// 어드민 방문 통계 화면 — 방문 현황(PV·UV·유입경로·국가·인기페이지) 탭.
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

interface Overview {
  totals: { pageviews: number; unique_visitors: number };
  daily: { date: string; pageviews: number; uniques: number }[];
  top_pages: { path: string; pageviews: number; uniques: number }[];
  sources: { source: string; referrer_host: string | null; pageviews: number }[];
  countries: { country: string | null; pageviews: number; uniques: number }[];
}

export default function AnalyticsPage() {
  const { session } = useAuthStore();
  const router = useRouter();
  const [days, setDays] = useState(30);
  const [data, setData] = useState<Overview | null>(null);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    if (!session) { router.replace("/"); return; }
  }, [session, router]);

  useEffect(() => {
    api<Overview>(`/api/admin/analytics?days=${days}`)
      .then(setData)
      .catch((e) => { if (e instanceof ApiError && e.status === 403) setForbidden(true); });
  }, [days]);

  if (forbidden) return <p className="p-8 text-ink-mute">관리자 전용 페이지입니다.</p>;

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-serif text-2xl text-ink">방문 통계</h1>
        <Link href="/admin" className="font-mono text-xs text-ink-mute hover:text-oxblood">← 어드민</Link>
      </div>

      <div className="mb-6 flex gap-2">
        {[7, 30, 90].map((d) => (
          <button key={d} onClick={() => setDays(d)}
            className={`border border-ink-faint px-3 py-1 font-mono text-xs ${days === d ? "bg-ink text-paper" : "text-ink-mute"}`}>
            {d}일
          </button>
        ))}
      </div>

      <div className="mb-8 grid grid-cols-2 gap-4">
        <div className="border border-ink-faint p-4">
          <div className="font-mono text-xs uppercase tracking-label text-ink-faint">방문수(PV)</div>
          <div className="font-mono text-3xl tabular-nums text-ink">{data?.totals.pageviews ?? "–"}</div>
        </div>
        <div className="border border-ink-faint p-4">
          <div className="font-mono text-xs uppercase tracking-label text-ink-faint">순방문자</div>
          <div className="font-mono text-3xl tabular-nums text-ink">{data?.totals.unique_visitors ?? "–"}</div>
        </div>
      </div>

      <Section title="유입 경로">
        {data?.sources.map((s, i) => (
          <Row key={i} label={`${s.source}${s.referrer_host ? ` · ${s.referrer_host}` : ""}`} value={s.pageviews} />
        ))}
      </Section>
      <Section title="국가별">
        {data?.countries.map((c, i) => <Row key={i} label={c.country ?? "미상"} value={c.pageviews} />)}
      </Section>
      <Section title="인기 페이지">
        {data?.top_pages.map((p, i) => <Row key={i} label={p.path} value={p.pageviews} />)}
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-2 border-b border-ink-faint pb-1 font-mono text-xs uppercase tracking-label text-ink-faint">{title}</h2>
      <ul className="divide-y divide-ink-faint">{children}</ul>
    </section>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <li className="flex items-center justify-between py-2 font-sans text-sm text-ink">
      <span className="truncate">{label}</span>
      <span className="font-mono tabular-nums text-ink-mute">{value}</span>
    </li>
  );
}
