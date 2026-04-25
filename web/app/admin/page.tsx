"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { StatFigure } from "@/components/editorial/StatFigure";
import ReviewPlayer from "@/components/ReviewPlayer";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface AdminSessionRow {
  id: number;
  nickname: string;
  created_at: string;
  last_seen_at: string;
  game_count: number;
  active_game_count: number;
  is_connected_ws: boolean;
}

interface AdminGameRow {
  id: number;
  session_id: number | null;
  nickname: string | null;
  status: string;
  result: string | null;
  winner: string | null;
  board_size: number;
  handicap: number;
  ai_rank: string;
  ai_style: string;
  ai_player: string | null;
  move_count: number;
  undo_count: number;
  hint_count: number;
  is_live_ws: boolean;
  started_at: string;
  finished_at: string | null;
}

interface AdminSummary {
  total_games: number;
  active_games: number;
  finished_games: number;
  resigned_games: number;
  ai_resigned_games: number;
  decisive_games: number;
  user_wins: number;
  user_win_rate: number;
  total_moves: number;
  total_undos: number;
  total_hints: number;
  avg_moves_per_game: number;
  live_sessions: number;
  live_ws_games: number;
}

interface AdminEngineHealth {
  mode: "mock" | "real";
  is_alive: boolean;
  bin_path: string | null;
  model_path: string | null;
  model_name: string | null;
  human_model_path: string | null;
  human_model_name: string | null;
  config_path: string | null;
  backend_started_at: string;
}

const REFRESH_SEC = 5;
const GAME_FILTERS = ["all", "active", "finished", "resigned"] as const;
type GameFilter = (typeof GAME_FILTERS)[number];

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  } catch {
    return iso;
  }
}

function duration(startIso: string, endIso: string): string {
  try {
    const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
    const s = Math.round(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ${s % 60}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  } catch {
    return "";
  }
}

function fmtRelative(iso: string): string {
  try {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 5) return "now";
    if (diff < 60) return `${diff}s`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
    return `${Math.floor(diff / 86400)}d`;
  } catch {
    return "";
  }
}

export default function AdminPage() {
  const t = useT();
  const router = useRouter();
  const { session, isAdmin, setIsAdmin } = useAuthStore();
  const [sessions, setSessions] = useState<AdminSessionRow[] | null>(null);
  const [games, setGames] = useState<AdminGameRow[] | null>(null);
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [engine, setEngine] = useState<AdminEngineHealth | null>(null);
  const [filter, setFilter] = useState<GameFilter>("all");
  const [forbidden, setForbidden] = useState(false);
  const [reviewGameId, setReviewGameId] = useState<number | null>(null);
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    let cancelled = false;
    const poll = async () => {
      try {
        const [s, g, sum, eng] = await Promise.all([
          api<AdminSessionRow[]>("/api/admin/sessions"),
          api<AdminGameRow[]>(`/api/admin/games${filter === "all" ? "" : `?status_=${filter}`}`),
          api<AdminSummary>("/api/admin/summary"),
          api<AdminEngineHealth>("/api/admin/engine"),
        ]);
        if (cancelled) return;
        setSessions(s);
        setGames(g);
        setSummary(sum);
        setEngine(eng);
        setIsAdmin(true);
        setForbidden(false);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 403) {
          setForbidden(true);
          setIsAdmin(false);
        }
      }
    };
    poll();
    const id = setInterval(poll, REFRESH_SEC * 1000);
    // Tick once per second to refresh the "last seen N s ago" relative labels.
    const tickId = setInterval(() => setTick((n) => n + 1), 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
      clearInterval(tickId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, filter]);

  const liveCount = useMemo(() => sessions?.filter((s) => s.is_connected_ws).length ?? 0, [sessions]);
  const activeGameCount = useMemo(() => games?.filter((g) => g.status === "active").length ?? 0, [games]);

  if (!session) return null;
  if (forbidden || (session && isAdmin === false && sessions === null)) {
    // The fetch already failed with 403 — show the denial banner.
    if (forbidden) {
      return (
        <div className="mx-auto max-w-xl py-20">
          <p className="text-sm text-oxblood">{t("admin.forbidden")}</p>
        </div>
      );
    }
  }

  return (
    <div className="mx-auto max-w-6xl py-8 px-4">
      <Hero title={t("admin.heading")} subtitle={t("admin.subtitle")} />
      <div className="mt-2 flex flex-wrap items-center gap-3 font-mono text-xs text-ink-mute">
        <span className="inline-flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-moss" aria-hidden />
          {liveCount} {t("admin.liveBadge")}
        </span>
        <span className="text-ink-faint">·</span>
        <span>{t("admin.refreshed").replace("{sec}", String(REFRESH_SEC))}</span>
        {engine && (
          <>
            <span className="text-ink-faint">·</span>
            <span>
              <Link href="#engine" className="hover:underline">
                <span className={"inline-block w-2 h-2 rounded-full align-middle mr-1 " + (engine.is_alive ? "bg-moss" : "bg-ink-faint")} aria-hidden />
                {t("admin.engineLabel")}
              </Link>
            </span>
          </>
        )}
      </div>

      <RuleDivider weight="strong" className="my-6" />

      <section>
        <h2 className="font-serif text-xl mb-3">{t("admin.sectionSummary")}</h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatFigure
            value={summary?.total_games ?? "—"}
            label={t("admin.statTotalGames")}
          />
          <StatFigure
            value={summary?.active_games ?? "—"}
            label={t("admin.statActive")}
          />
          <StatFigure
            value={summary?.finished_games ?? "—"}
            label={t("admin.statFinished")}
          />
          <StatFigure
            value={summary?.resigned_games ?? "—"}
            label={t("admin.statResigned")}
          />
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatFigure
            value={
              summary && summary.decisive_games > 0
                ? `${Math.round(summary.user_win_rate * 100)}%`
                : "—"
            }
            label={t("admin.statUserWinRate")}
          />
          <StatFigure
            value={summary?.ai_resigned_games ?? "—"}
            label={t("admin.statAiResigned")}
          />
          <StatFigure
            value={
              summary
                ? Math.round(summary.avg_moves_per_game)
                : "—"
            }
            label={t("admin.statAvgMoves")}
          />
          <StatFigure
            value={summary?.total_moves ?? "—"}
            label={t("admin.statTotalMoves")}
          />
        </div>
      </section>

      <RuleDivider weight="faint" className="my-6" />

      <section id="engine">
        <h2 className="font-serif text-xl mb-3">{t("admin.sectionEngine")}</h2>
        {engine ? (
          <div className="border border-ink-faint p-4 grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-4 font-mono text-xs">
            <div>
              <span className="text-ink-mute">KataGo · </span>
              <span className={engine.is_alive ? "text-moss" : "text-ink-mute"}>
                {engine.is_alive ? "ALIVE" : engine.mode === "mock" ? "MOCK" : "IDLE"}
              </span>
              <span className="text-ink-faint"> · {engine.mode}</span>
            </div>
            <div className="text-ink-mute">
              {t("admin.engineUptime")}: {fmtTime(engine.backend_started_at)}
            </div>
            <div className="text-ink truncate" title={engine.model_path ?? ""}>
              <span className="text-ink-mute">model · </span>
              {engine.model_name ?? "—"}
            </div>
            <div className="text-ink truncate" title={engine.human_model_path ?? ""}>
              <span className="text-ink-mute">human-SL · </span>
              {engine.human_model_name ?? "—"}
            </div>
          </div>
        ) : (
          <p className="text-sm text-ink-faint">…</p>
        )}
      </section>

      <RuleDivider weight="strong" className="my-6" />

      <section>
        <h2 className="font-serif text-xl mb-3">{t("admin.sectionSessions")}</h2>
        <div className="overflow-x-auto border border-ink-faint">
          <table className="w-full font-mono text-sm">
            <thead>
              <tr className="border-b border-ink-faint bg-paper-deep text-ink-mute">
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colLive")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colNickname")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colCreated")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colLastSeen")}</th>
                <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colActive")}</th>
                <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colGames")}</th>
              </tr>
            </thead>
            <tbody>
              {sessions === null ? (
                <tr><td colSpan={6} className="p-4 text-center text-ink-faint">…</td></tr>
              ) : sessions.length === 0 ? (
                <tr><td colSpan={6} className="p-4 text-center text-ink-faint">{t("admin.empty")}</td></tr>
              ) : (
                sessions.map((s) => (
                  <tr key={s.id} className="border-b border-ink-faint/40">
                    <td className="p-2">
                      {s.is_connected_ws ? (
                        <span className="inline-flex items-center gap-1 text-moss">
                          <span className="w-2 h-2 rounded-full bg-moss" aria-hidden />
                          {t("admin.liveBadge")}
                        </span>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </td>
                    <td className="p-2 font-sans text-ink">
                      <Link href={`/admin/sessions/${s.id}`} className="hover:underline text-oxblood">
                        {s.nickname}
                      </Link>
                    </td>
                    <td className="p-2 tabular-nums text-ink-mute">{fmtTime(s.created_at)}</td>
                    <td className="p-2 tabular-nums text-ink-mute">{fmtRelative(s.last_seen_at)}</td>
                    <td className="p-2 text-right tabular-nums">{s.active_game_count}</td>
                    <td className="p-2 text-right tabular-nums">{s.game_count}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="mt-3">
          <Link href="/admin/login-history" className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline">
            {t("admin.viewLoginHistory")}
          </Link>
        </div>
      </section>

      <RuleDivider weight="faint" className="my-8" />

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="font-serif text-xl">{t("admin.sectionGames")}</h2>
          <div className="flex gap-1 text-xs font-sans">
            {GAME_FILTERS.map((f) => {
              const count =
                !summary ? null
                : f === "all" ? summary.total_games
                : f === "active" ? summary.active_games
                : f === "finished" ? summary.finished_games
                : summary.resigned_games;
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  className={
                    "border px-2 py-1 transition-base inline-flex items-center gap-1.5 " +
                    (filter === f
                      ? "border-ink bg-ink text-paper"
                      : "border-ink-faint text-ink-mute hover:bg-paper-deep")
                  }
                >
                  <span>{t(`admin.filter${f.charAt(0).toUpperCase() + f.slice(1)}`)}</span>
                  {count !== null && (
                    <span className={filter === f ? "font-mono tabular-nums opacity-70" : "font-mono tabular-nums text-ink-faint"}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
        <div className="overflow-x-auto border border-ink-faint">
          <table className="w-full font-mono text-sm">
            <thead>
              <tr className="border-b border-ink-faint bg-paper-deep text-ink-mute">
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colGameId")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colLive")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colNickname")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colStatus")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colResult")}</th>
                <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colBoard")}</th>
                <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colHandicap")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colAi")}</th>
                <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colMoves")}</th>
                <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colUndos")}</th>
                <th className="text-right p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colHints")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colStarted")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colDuration")}</th>
                <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label" />
              </tr>
            </thead>
            <tbody>
              {games === null ? (
                <tr><td colSpan={14} className="p-4 text-center text-ink-faint">…</td></tr>
              ) : games.length === 0 ? (
                <tr><td colSpan={14} className="p-4 text-center text-ink-faint">{t("admin.empty")}</td></tr>
              ) : (
                games.map((g) => (
                  <tr key={g.id} className="border-b border-ink-faint/40">
                    <td className="p-2 tabular-nums text-ink-mute">#{g.id}</td>
                    <td className="p-2">
                      {g.is_live_ws ? (
                        <span className="inline-flex items-center gap-1 text-moss">
                          <span className="w-2 h-2 rounded-full bg-moss" aria-hidden />
                          {t("admin.liveBadge")}
                        </span>
                      ) : (
                        <span className="text-ink-faint">—</span>
                      )}
                    </td>
                    <td className="p-2 font-sans text-ink">
                      {g.session_id ? (
                        <Link href={`/admin/sessions/${g.session_id}`} className="text-oxblood hover:underline">
                          {g.nickname ?? "—"}
                        </Link>
                      ) : (
                        <span className="text-ink-mute">{g.nickname ?? "—"}</span>
                      )}
                    </td>
                    <td className="p-2">
                      {g.winner === "user" ? (
                        <span className="text-moss font-sans font-semibold">{t("admin.win")}</span>
                      ) : g.winner === "ai" ? (
                        <span className="text-oxblood font-sans font-semibold">{t("admin.loss")}</span>
                      ) : (
                        <span className="text-ink-mute">{t("admin.inProgress")}</span>
                      )}
                    </td>
                    <td className="p-2 text-ink-mute">{g.result ?? "—"}</td>
                    <td className="p-2 text-right tabular-nums">{g.board_size}×{g.board_size}</td>
                    <td className="p-2 text-right tabular-nums">{g.handicap}</td>
                    <td className="p-2 text-ink-mute">
                      {g.ai_player ?? g.ai_rank} · {g.ai_style}
                    </td>
                    <td className="p-2 text-right tabular-nums">{g.move_count}</td>
                    <td className="p-2 text-right tabular-nums">{g.undo_count}</td>
                    <td className="p-2 text-right tabular-nums">{g.hint_count}</td>
                    <td className="p-2 tabular-nums text-ink-mute">{fmtTime(g.started_at)}</td>
                    <td className="p-2 tabular-nums text-ink-mute">
                      {g.finished_at ? duration(g.started_at, g.finished_at) : "—"}
                    </td>
                    <td className="p-2">
                      <span className="flex gap-2">
                        <button
                          type="button"
                          className="text-oxblood hover:underline bg-transparent border-0 p-0 font-inherit cursor-pointer"
                          onClick={() => setReviewGameId(g.id)}
                        >
                          review
                        </button>
                        <a className="text-oxblood hover:underline" href={`/api/games/${g.id}/sgf`}>SGF</a>
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <Dialog
        open={reviewGameId !== null}
        onOpenChange={(open) => {
          if (!open) setReviewGameId(null);
        }}
      >
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              {t("admin.reviewDialogTitle")}
              {reviewGameId !== null && (
                <span className="ml-2 font-mono text-sm text-ink-mute">
                  #{reviewGameId}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          {reviewGameId !== null && <ReviewPlayer gameId={reviewGameId} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}
