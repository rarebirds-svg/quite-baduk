"use client";
// 관리자 통계 페이지 — 접속자 추이, 대국 추이, 시간대 활동, AI/판 선호도 등.
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { formatRank } from "@/components/RankPicker";

interface DailyBucket {
  date: string;
  count: number;
}
interface DailyGameBucket {
  date: string;
  started: number;
  finished: number;
}
interface HourlyBucket {
  hour: number;
  count: number;
}
interface LabeledCount {
  label: string;
  count: number;
}
interface NicknameSummary {
  nickname: string;
  games: number;
  wins: number;
  losses: number;
  decisive: number;
  win_rate: number;
}
interface AdminStats {
  daily_logins: DailyBucket[];
  daily_games: DailyGameBucket[];
  hourly_activity: HourlyBucket[];
  rank_distribution: LabeledCount[];
  ai_player_picks: LabeledCount[];
  ai_style_picks: LabeledCount[];
  board_size_picks: LabeledCount[];
  handicap_picks: LabeledCount[];
  nickname_summary: NicknameSummary[];
  window_days_daily: number;
  window_days_hourly: number;
}

const REFRESH_SEC = 30;
const DAYS_OPTIONS = [7, 14, 30] as const;
type DaysOption = (typeof DAYS_OPTIONS)[number];

export default function AdminStatsPage() {
  const t = useT();
  const [locale] = useLocale();
  const router = useRouter();
  const { session } = useAuthStore();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [days, setDays] = useState<DaysOption>(14);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const s = await api<AdminStats>(`/api/admin/stats?days=${days}`);
        if (cancelled) return;
        setStats(s);
        setForbidden(false);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 403) setForbidden(true);
      }
    };
    poll();
    const id = setInterval(poll, REFRESH_SEC * 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [session, days, router]);

  if (forbidden) {
    return (
      <div className="space-y-6">
        <Hero title={t("admin.statsHeading")} subtitle={t("admin.statsSubtitle")} />
        <p className="text-sm text-oxblood">{t("admin.forbidden")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <Hero title={t("admin.statsHeading")} subtitle={t("admin.statsSubtitle")} />
        <Link
          href="/admin"
          className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
        >
          {t("admin.backToConsole")}
        </Link>
      </div>

      <div className="flex items-baseline gap-2 font-sans text-xs">
        <span className="text-ink-mute uppercase tracking-label">
          {t("admin.statsWindow")}
        </span>
        {DAYS_OPTIONS.map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDays(d)}
            className={
              "px-2 py-1 border transition-base " +
              (days === d
                ? "border-oxblood text-oxblood bg-paper-deep"
                : "border-ink-faint text-ink-mute hover:border-ink-mute")
            }
          >
            {d}d
          </button>
        ))}
      </div>

      {!stats ? (
        <p className="text-sm text-ink-faint">…</p>
      ) : (
        <>
          <RuleDivider weight="strong" />

          <section>
            <h2 className="font-serif text-xl mb-3">{t("admin.statsDailyLogins")}</h2>
            <DailyBarChart
              buckets={stats.daily_logins}
              valueLabel={t("admin.statsLogins")}
            />
          </section>

          <RuleDivider weight="faint" />

          <section>
            <h2 className="font-serif text-xl mb-3">{t("admin.statsDailyGames")}</h2>
            <DailyDualBarChart
              buckets={stats.daily_games}
              startedLabel={t("admin.statsStarted")}
              finishedLabel={t("admin.statsFinished")}
            />
          </section>

          <RuleDivider weight="faint" />

          <section>
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="font-serif text-xl">{t("admin.statsHourly")}</h2>
              <span className="font-sans text-xs text-ink-mute">
                {t("admin.statsHourlyWindow").replace(
                  "{n}",
                  String(stats.window_days_hourly),
                )}
              </span>
            </div>
            <HourlyChart buckets={stats.hourly_activity} />
          </section>

          <RuleDivider weight="faint" />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section>
              <h2 className="font-serif text-xl mb-3">{t("admin.statsRanks")}</h2>
              <LabeledBarList
                rows={stats.rank_distribution.map((r) => ({
                  ...r,
                  label: formatRank(r.label, locale),
                }))}
              />
            </section>
            <section>
              <h2 className="font-serif text-xl mb-3">{t("admin.statsAiPlayers")}</h2>
              <LabeledBarList
                rows={stats.ai_player_picks.map((r) => ({
                  ...r,
                  label:
                    r.label !== "—"
                      ? t(`game.players.${r.label}.name`)
                      : r.label,
                }))}
              />
            </section>
            <section>
              <h2 className="font-serif text-xl mb-3">{t("admin.statsAiStyles")}</h2>
              <LabeledBarList
                rows={stats.ai_style_picks.map((r) => ({
                  ...r,
                  label:
                    r.label !== "—"
                      ? t(`game.aiStyleName.${r.label}`)
                      : r.label,
                }))}
              />
            </section>
            <section>
              <h2 className="font-serif text-xl mb-3">{t("admin.statsBoards")}</h2>
              <LabeledBarList
                rows={stats.board_size_picks.map((r) => ({
                  ...r,
                  label: r.label !== "—" ? `${r.label}×${r.label}` : r.label,
                }))}
              />
            </section>
            <section className="md:col-span-2">
              <h2 className="font-serif text-xl mb-3">{t("admin.statsHandicaps")}</h2>
              <LabeledBarList rows={stats.handicap_picks} />
            </section>
          </div>

          <RuleDivider weight="faint" />

          <section>
            <h2 className="font-serif text-xl mb-3">{t("admin.statsNicknames")}</h2>
            <NicknameTable rows={stats.nickname_summary} t={t} />
          </section>
        </>
      )}
    </div>
  );
}

function NicknameTable({
  rows,
  t,
}: {
  rows: NicknameSummary[];
  t: (key: string) => string;
}) {
  if (rows.length === 0) {
    return <p className="text-xs text-ink-faint font-sans">—</p>;
  }
  return (
    <div className="overflow-x-auto border border-ink-faint">
      <table className="w-full font-mono text-sm">
        <thead>
          <tr className="border-b border-ink-faint bg-paper-deep text-ink-mute">
            <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">
              {t("admin.colNickname")}
            </th>
            <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">
              {t("admin.colGames")}
            </th>
            <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">
              {t("admin.statsWins")}
            </th>
            <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">
              {t("admin.statsLosses")}
            </th>
            <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">
              {t("admin.statsWinRate")}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.nickname} className="border-b border-ink-faint/40">
              <td className="p-2 font-sans text-ink">{r.nickname}</td>
              <td className="p-2 text-right tabular-nums">{r.games}</td>
              <td className="p-2 text-right tabular-nums text-moss">{r.wins}</td>
              <td className="p-2 text-right tabular-nums text-oxblood">{r.losses}</td>
              <td className="p-2 text-right tabular-nums text-ink-mute">
                {r.decisive > 0
                  ? `${(r.win_rate * 100).toFixed(1)}%`
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DailyBarChart({
  buckets,
  valueLabel,
}: {
  buckets: DailyBucket[];
  valueLabel: string;
}) {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  return (
    <div>
      <div className="flex items-end gap-1 h-32 border-b border-ink-faint">
        {buckets.map((b) => {
          const pct = (b.count / max) * 100;
          return (
            <div
              key={b.date}
              className="flex-1 min-w-0 flex flex-col justify-end h-full"
              title={`${b.date} · ${valueLabel} ${b.count}`}
            >
              <div
                className="bg-oxblood/80 hover:bg-oxblood transition-base"
                style={{ height: `${pct}%` }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-[10px] text-ink-faint mt-1 font-mono tabular-nums">
        <span>{buckets[0]?.date}</span>
        <span>
          {valueLabel} {valueLabel ? `(${buckets.reduce((acc, b) => acc + b.count, 0)})` : ""}
        </span>
        <span>{buckets[buckets.length - 1]?.date}</span>
      </div>
    </div>
  );
}

function DailyDualBarChart({
  buckets,
  startedLabel,
  finishedLabel,
}: {
  buckets: DailyGameBucket[];
  startedLabel: string;
  finishedLabel: string;
}) {
  const max = Math.max(
    1,
    ...buckets.map((b) => Math.max(b.started, b.finished)),
  );
  return (
    <div>
      <div className="flex items-end gap-1 h-32 border-b border-ink-faint">
        {buckets.map((b) => {
          const startedPct = (b.started / max) * 100;
          const finishedPct = (b.finished / max) * 100;
          return (
            <div
              key={b.date}
              className="flex-1 min-w-0 flex items-end justify-center gap-px h-full"
              title={`${b.date} · ${startedLabel} ${b.started} · ${finishedLabel} ${b.finished}`}
            >
              <div
                className="flex-1 bg-oxblood/80"
                style={{ height: `${startedPct}%` }}
              />
              <div
                className="flex-1 bg-moss/80"
                style={{ height: `${finishedPct}%` }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex items-baseline justify-between text-[10px] text-ink-faint mt-1 font-mono tabular-nums">
        <span>{buckets[0]?.date}</span>
        <span className="flex gap-3">
          <span className="text-oxblood">■ {startedLabel}</span>
          <span className="text-moss">■ {finishedLabel}</span>
        </span>
        <span>{buckets[buckets.length - 1]?.date}</span>
      </div>
    </div>
  );
}

function HourlyChart({ buckets }: { buckets: HourlyBucket[] }) {
  const max = Math.max(1, ...buckets.map((b) => b.count));
  return (
    <div>
      <div className="flex items-end gap-1 h-24 border-b border-ink-faint">
        {buckets.map((b) => {
          const pct = (b.count / max) * 100;
          return (
            <div
              key={b.hour}
              className="flex-1 flex flex-col justify-end h-full"
              title={`${String(b.hour).padStart(2, "0")}:00 · ${b.count}`}
            >
              <div className="bg-oxblood/70" style={{ height: `${pct}%` }} />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-[10px] text-ink-faint mt-1 font-mono tabular-nums">
        <span>00</span>
        <span>06</span>
        <span>12</span>
        <span>18</span>
        <span>24</span>
      </div>
    </div>
  );
}

function LabeledBarList({ rows }: { rows: LabeledCount[] }) {
  if (rows.length === 0) {
    return <p className="text-xs text-ink-faint font-sans">—</p>;
  }
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <div className="border border-ink-faint divide-y divide-ink-faint">
      {rows.map((r) => {
        const pct = (r.count / max) * 100;
        return (
          <div
            key={r.label}
            className="px-3 py-2 grid grid-cols-[100px_1fr_auto] gap-3 items-center font-sans text-sm"
          >
            <span className="font-mono text-xs text-ink truncate" title={r.label}>
              {r.label}
            </span>
            <div className="h-2 bg-paper-deep relative">
              <div className="absolute inset-y-0 left-0 bg-oxblood/60" style={{ width: `${pct}%` }} />
            </div>
            <span className="font-mono tabular-nums text-xs text-ink-mute">
              {r.count}
            </span>
          </div>
        );
      })}
    </div>
  );
}
