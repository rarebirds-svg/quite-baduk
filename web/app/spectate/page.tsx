"use client";
// 관전 목록 — 진행 중/종료된 대국을 모아 보여주는 페이지.
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { formatRank } from "@/components/RankPicker";
import { CountryFlag } from "@/components/CountryFlag";

interface SpectateRow {
  id: number;
  user_nickname: string | null;
  user_rank: string | null;
  user_country: string | null;
  ai_player: string | null;
  ai_rank: string;
  ai_style: string;
  board_size: number;
  handicap: number;
  status: string;
  result: string | null;
  move_count: number;
  started_at: string;
  finished_at: string | null;
  is_live: boolean;
}

const REFRESH_SEC = 10;

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

export default function SpectateListPage() {
  const t = useT();
  const [locale] = useLocale();
  const router = useRouter();
  const { session } = useAuthStore();
  const [rows, setRows] = useState<SpectateRow[] | null>(null);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const data = await api<{ rows: SpectateRow[] }>("/api/spectate");
        if (!cancelled) setRows(data.rows);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) router.replace("/");
      }
    };
    poll();
    const id = setInterval(poll, REFRESH_SEC * 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [session, router]);

  if (!session) return null;

  const live = rows?.filter((r) => r.is_live) ?? [];
  const ended = rows?.filter((r) => !r.is_live) ?? [];

  return (
    <div className="space-y-6">
      <Hero title={t("spectate.heading")} subtitle={t("spectate.subtitle")} />

      {rows === null ? (
        <p className="text-sm text-ink-faint">…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-mute">{t("spectate.empty")}</p>
      ) : (
        <>
          <section>
            <h2 className="font-serif text-xl mb-3 flex items-baseline gap-2">
              {t("spectate.liveSection")}
              <span className="font-mono text-xs text-ink-faint tabular-nums">
                {live.length}
              </span>
            </h2>
            {live.length === 0 ? (
              <p className="text-xs text-ink-faint font-sans">
                {t("spectate.noLive")}
              </p>
            ) : (
              <SpectateGrid rows={live} locale={locale} t={t} live />
            )}
          </section>

          <RuleDivider weight="faint" />

          <section>
            <h2 className="font-serif text-xl mb-3 flex items-baseline gap-2">
              {t("spectate.endedSection")}
              <span className="font-mono text-xs text-ink-faint tabular-nums">
                {ended.length}
              </span>
            </h2>
            {ended.length === 0 ? (
              <p className="text-xs text-ink-faint font-sans">
                {t("spectate.noEnded")}
              </p>
            ) : (
              <SpectateGrid rows={ended} locale={locale} t={t} live={false} />
            )}
          </section>
        </>
      )}
    </div>
  );
}

function SpectateGrid({
  rows,
  locale,
  t,
  live,
}: {
  rows: SpectateRow[];
  locale: "ko" | "en";
  t: (key: string) => string;
  live: boolean;
}) {
  return (
    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {rows.map((r) => {
        const blackName = r.user_nickname ?? "—";
        const blackRank = r.user_rank ? formatRank(r.user_rank, locale) : null;
        const aiName = r.ai_player
          ? t(`game.players.${r.ai_player}.name`)
          : formatRank(r.ai_rank, locale);
        return (
          <li key={r.id}>
            <Link
              href={`/spectate/${r.id}`}
              className="block border border-ink-faint p-3 hover:bg-paper-deep transition-base"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-sans text-sm text-ink inline-flex items-baseline gap-1.5">
                  <CountryFlag code={r.user_country} />
                  <span>
                    {blackName}
                    {blackRank && (
                      <span className="text-ink-faint text-xs"> ({blackRank})</span>
                    )}
                    <span className="text-ink-faint"> vs </span>
                    {aiName}
                  </span>
                </span>
                {live ? (
                  <span className="inline-flex items-center gap-1 font-sans text-[10px] uppercase tracking-label text-moss shrink-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-moss" aria-hidden />
                    {t("spectate.liveBadge")}
                  </span>
                ) : (
                  <span className="font-mono text-xs text-ink-faint shrink-0">
                    {r.result ?? "—"}
                  </span>
                )}
              </div>
              <div className="mt-1 font-mono text-[11px] text-ink-faint tabular-nums flex gap-3">
                <span>{r.board_size}×{r.board_size}</span>
                <span>{r.move_count}{t("spectate.movesSuffix")}</span>
                <span>{fmtTime(r.started_at)}</span>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
