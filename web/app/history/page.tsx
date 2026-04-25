"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { StatFigure } from "@/components/editorial/StatFigure";
import { formatRank, type Rank } from "@/components/RankPicker";

interface BucketRow {
  total: number;
  wins: number;
  losses: number;
  winrate: number;
  [k: string]: string | number | null;
}

interface Stats {
  total: number;
  wins: number;
  losses: number;
  winrate: number;
  total_moves: number;
  total_undos: number;
  total_hints: number;
  avg_moves_per_game: number;
  by_rank: (BucketRow & { ai_rank: string })[];
  by_board_size: (BucketRow & { board_size: number })[];
  by_ai_player: (BucketRow & { ai_player: string })[];
}

interface GameRow {
  id: number;
  user_nickname: string | null;
  user_rank: string | null;
  ai_rank: string;
  ai_style: string;
  ai_player: string | null;
  handicap: number;
  board_size: number;
  status: string;
  result: string | null;
  winner: string | null;
  move_count: number;
  undo_count: number;
  hint_count: number;
  started_at: string;
  finished_at: string | null;
}

function fmtDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "2-digit", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
    });
  } catch { return iso; }
}

function duration(start: string, end: string | null): string {
  if (!end) return "—";
  try {
    const ms = new Date(end).getTime() - new Date(start).getTime();
    const s = Math.round(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const rs = s % 60;
    if (m < 60) return `${m}m ${rs}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  } catch { return ""; }
}

export default function HistoryPage() {
  const t = useT();
  const [locale] = useLocale();
  const [stats, setStats] = useState<Stats | null>(null);
  const [games, setGames] = useState<GameRow[]>([]);

  useEffect(() => {
    api<Stats>("/api/stats").then(setStats).catch(() => {});
    api<GameRow[]>("/api/games").then(setGames).catch(() => {});
  }, []);

  const formatRankLabel = (r: string | null | undefined) => {
    if (!r) return "—";
    try { return formatRank(r as Rank, locale); } catch { return r; }
  };

  return (
    <div className="mx-auto max-w-6xl py-8 px-4">
      <Hero title={t("nav.history")} subtitle={t("session.ephemeralNote")} />

      {stats && (
        <>
          <RuleDivider weight="strong" className="my-6" />
          <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatFigure value={stats.total} label={t("history.total")} />
            <StatFigure value={stats.wins} label={t("history.wins")} />
            <StatFigure value={stats.losses} label={t("history.losses")} />
            <StatFigure
              value={stats.total === 0 ? "—" : `${Math.round(stats.winrate * 100)}%`}
              label={t("history.winrate")}
            />
          </section>
          <section className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatFigure value={stats.total_moves} label={t("history.totalMoves")} />
            <StatFigure
              value={stats.total === 0 ? "—" : Math.round(stats.avg_moves_per_game)}
              label={t("history.avgMoves")}
            />
            <StatFigure value={stats.total_undos} label={t("history.totalUndos")} />
            <StatFigure value={stats.total_hints} label={t("history.totalHints")} />
          </section>

          {stats.by_rank.length > 0 && (
            <>
              <RuleDivider weight="faint" className="my-6" />
              <section>
                <h2 className="font-serif text-lg mb-3">{t("history.byRank")}</h2>
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  {stats.by_rank.map((r) => (
                    <div key={r.ai_rank} className="border border-ink-faint p-3">
                      <div className="font-mono text-xs text-ink-mute">
                        {formatRankLabel(r.ai_rank)}
                      </div>
                      <div className="font-serif text-2xl tabular-nums">
                        {Math.round(r.winrate * 100)}%
                      </div>
                      <div className="font-mono text-xs text-ink-faint tabular-nums">
                        {r.wins} / {r.total}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
        </>
      )}

      <RuleDivider weight="strong" className="my-8" />

      <section>
        <h2 className="font-serif text-lg mb-3">{t("history.allGames")}</h2>
        {games.length === 0 ? (
          <p className="text-sm text-ink-faint">{t("history.empty")}</p>
        ) : (
          <div className="overflow-x-auto border border-ink-faint">
            <table className="w-full font-mono text-sm">
              <thead>
                <tr className="border-b border-ink-faint bg-paper-deep text-ink-mute">
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">#</th>
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colNickname")}</th>
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colUserRank")}</th>
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colAi")}</th>
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colAiRank")}</th>
                  <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colBoard")}</th>
                  <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colHandicap")}</th>
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colResult")}</th>
                  <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colMoves")}</th>
                  <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colUndos")}</th>
                  <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colHints")}</th>
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colStarted")}</th>
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("history.colDuration")}</th>
                  <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label" />
                </tr>
              </thead>
              <tbody>
                {games.map((g) => (
                  <tr key={g.id} className="border-b border-ink-faint/40">
                    <td className="p-2 tabular-nums text-ink-mute">#{g.id}</td>
                    <td className="p-2 font-sans text-ink">{g.user_nickname ?? "—"}</td>
                    <td className="p-2">{formatRankLabel(g.user_rank)}</td>
                    <td className="p-2 text-ink-mute">{g.ai_player ?? "KataGo"} · {g.ai_style}</td>
                    <td className="p-2">{formatRankLabel(g.ai_rank)}</td>
                    <td className="p-2 text-right tabular-nums">{g.board_size}×{g.board_size}</td>
                    <td className="p-2 text-right tabular-nums">{g.handicap}</td>
                    <td className="p-2">
                      {g.winner === "user" ? (
                        <span className="font-sans font-semibold text-moss">
                          {t("admin.win")}
                          {g.result ? <span className="ml-1 font-mono text-xs text-ink-mute">{g.result}</span> : null}
                        </span>
                      ) : g.winner === "ai" ? (
                        <span className="font-sans font-semibold text-oxblood">
                          {t("admin.loss")}
                          {g.result ? <span className="ml-1 font-mono text-xs text-ink-mute">{g.result}</span> : null}
                        </span>
                      ) : (
                        <span className="text-ink-mute">{g.status}</span>
                      )}
                    </td>
                    <td className="p-2 text-right tabular-nums">{g.move_count}</td>
                    <td className="p-2 text-right tabular-nums">{g.undo_count}</td>
                    <td className="p-2 text-right tabular-nums">{g.hint_count}</td>
                    <td className="p-2 tabular-nums text-ink-mute">{fmtDateTime(g.started_at)}</td>
                    <td className="p-2 tabular-nums text-ink-mute">{duration(g.started_at, g.finished_at)}</td>
                    <td className="p-2">
                      <span className="flex gap-2">
                        <Link className="text-oxblood hover:underline" href={`/game/review/${g.id}`}>review</Link>
                        <a className="text-oxblood hover:underline" href={`/api/games/${g.id}/sgf`}>SGF</a>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
