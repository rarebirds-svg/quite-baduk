"use client";
// 어드민 방문 통계 화면 — 방문 현황(PV·UV·유입경로·국가·인기페이지) 탭.
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { api, authFailure, type AuthFailure } from "@/lib/api";
import { AdminAuthNotice } from "@/components/admin/AdminAuthNotice";
import { useAuthStore } from "@/store/authStore";

interface Overview {
  totals: { pageviews: number; unique_visitors: number };
  daily: { date: string; pageviews: number; uniques: number }[];
  top_pages: { path: string; pageviews: number; uniques: number }[];
  sources: { source: string; referrer_host: string | null; pageviews: number }[];
  countries: { country: string | null; pageviews: number; uniques: number }[];
}

interface SearchRow {
  query: string;
  page: string | null;
  clicks: number;
  impressions: number;
  ctr: number;
  position: number | null;
  source: string;
}

export default function AnalyticsPage() {
  const { session } = useAuthStore();
  const router = useRouter();
  const [days, setDays] = useState(30);
  const [data, setData] = useState<Overview | null>(null);
  const [authError, setAuthError] = useState<AuthFailure | null>(null);
  const [queries, setQueries] = useState<SearchRow[]>([]);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!session) { router.replace("/"); return; }
  }, [session, router]);

  useEffect(() => {
    api<Overview>(`/api/admin/analytics?days=${days}`)
      .then(setData)
      .catch((e) => { const f = authFailure(e); if (f) setAuthError(f); });
  }, [days]);

  useEffect(() => {
    api<SearchRow[]>("/api/admin/search-queries?source=all&days=90&top=50")
      .then((rows) => setQueries(Array.isArray(rows) ? rows : []))
      .catch(() => {});
  }, []);

  async function uploadNaver(e: React.ChangeEvent<HTMLInputElement>) {
    const input = e.target;
    const file = input.files?.[0];
    if (!file) return;
    setUploadMsg("업로드 중…");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/admin/search-queries/import", {
        method: "POST",
        body: fd,
        credentials: "include",
      });
      if (!res.ok) {
        setUploadMsg(`업로드 실패 (HTTP ${res.status})`);
        return;
      }
      const result = (await res.json()) as { imported?: number };
      const rows = await api<SearchRow[]>("/api/admin/search-queries?source=all&days=90&top=50");
      setQueries(Array.isArray(rows) ? rows : []);
      setUploadMsg(`${result.imported ?? 0}건 반영됨`);
    } catch {
      setUploadMsg("업로드 실패");
    } finally {
      input.value = ""; // 같은 파일 재선택 가능하도록 리셋
    }
  }

  if (authError) return <div className="p-8"><AdminAuthNotice kind={authError} /></div>;

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
          <div className="mt-1 font-sans text-xs text-ink-faint">일 단위 익명 해시 기준</div>
        </div>
      </div>

      {data && data.daily.length > 0 && <DailyTrend daily={data.daily} />}

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
      <Section title="검색 유입 (검색어)">
        <li className="flex items-center justify-end gap-3 py-2">
          {uploadMsg && <span className="font-mono text-xs text-ink-faint">{uploadMsg}</span>}
          <label className="cursor-pointer font-mono text-xs text-oxblood hover:underline focus-within:underline">
            네이버 CSV 업로드
            <input
              type="file"
              accept=".csv"
              onChange={uploadNaver}
              className="sr-only"
              aria-label="네이버 검색어 CSV 업로드"
            />
          </label>
        </li>
        {queries.map((q, i) => (
          <li key={i} className="flex items-center justify-between py-2 font-sans text-sm text-ink">
            <span className="truncate">{q.query} <span className="font-mono text-xs text-ink-faint">· {q.source}</span></span>
            <span className="font-mono tabular-nums text-ink-mute">{q.clicks}↑ / {q.impressions}노출</span>
          </li>
        ))}
      </Section>
    </div>
  );
}

function DailyTrend({ daily }: { daily: Overview["daily"] }) {
  const max = Math.max(...daily.map((d) => d.pageviews), 1);
  return (
    <section className="mb-8">
      <h2 className="mb-2 border-b border-ink-faint pb-1 font-mono text-xs uppercase tracking-label text-ink-faint">
        일별 추이 (방문수)
      </h2>
      <div className="flex h-20 items-end gap-px">
        {daily.map((d) => (
          <div
            key={d.date}
            className="flex-1 bg-ink-mute transition-base hover:bg-oxblood"
            style={{ height: `${Math.round((d.pageviews / max) * 100)}%` }}
            title={`${d.date} · ${d.pageviews}회`}
          />
        ))}
      </div>
    </section>
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
