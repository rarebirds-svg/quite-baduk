"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
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
interface AdminLoginRow {
  id: number;
  session_id: number | null;
  nickname: string;
  created_at: string;
  ended_at: string | null;
  end_reason: string | null;
  is_active: boolean;
}
interface AdminSessionDetail {
  session: AdminSessionRow | null;
  nickname: string;
  total_games: number;
  active_games: number;
  wins: number;
  losses: number;
  total_moves: number;
  total_undos: number;
  total_hints: number;
  games: AdminGameRow[];
  history: AdminLoginRow[];
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: "2-digit", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hour12: false,
    });
  } catch { return iso; }
}

function duration(a: string, b: string | null): string {
  if (!b) return "—";
  try {
    const ms = new Date(b).getTime() - new Date(a).getTime();
    const s = Math.round(ms / 1000);
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ${s % 60}s`;
    const h = Math.floor(m / 60);
    return `${h}h ${m % 60}m`;
  } catch { return ""; }
}

const REFRESH_SEC = 5;

export default function AdminSessionDetailPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const sessionId = parseInt(params.id, 10);
  const router = useRouter();
  const { session } = useAuthStore();
  const [detail, setDetail] = useState<AdminSessionDetail | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [reviewGameId, setReviewGameId] = useState<number | null>(null);

  useEffect(() => {
    if (!session) { router.replace("/"); return; }
    let cancelled = false;
    const poll = async () => {
      try {
        const d = await api<AdminSessionDetail>(`/api/admin/sessions/${sessionId}`);
        if (!cancelled) setDetail(d);
      } catch (e) {
        if (!cancelled && e instanceof ApiError && e.status === 403) {
          setForbidden(true);
        }
      }
    };
    poll();
    const id = setInterval(poll, REFRESH_SEC * 1000);
    return () => { cancelled = true; clearInterval(id); };
  }, [session, sessionId, router]);

  if (!session) return null;
  if (forbidden) {
    return (
      <div className="mx-auto max-w-xl py-20">
        <p className="text-sm text-oxblood">{t("admin.forbidden")}</p>
      </div>
    );
  }

  const endReasonLabel = (reason: string | null): string => {
    if (!reason) return t("admin.endReasonActive");
    if (reason === "logout") return t("admin.endReasonLogout");
    if (reason === "idle_purge") return t("admin.endReasonIdle");
    if (reason === "replaced") return t("admin.endReasonReplaced");
    return reason;
  };

  return (
    <div className="mx-auto max-w-6xl py-8 px-4">
      <Link href="/admin" className="font-sans text-xs text-ink-mute hover:underline">
        {t("admin.backToConsole")}
      </Link>
      <Hero
        title={detail?.nickname || t("admin.sessionDetail")}
        subtitle={detail?.session
          ? `${t("admin.colLastSeen")}: ${fmtTime(detail.session.last_seen_at)}`
          : t("admin.endReasonActive")}
      />

      {detail && (
        <>
          <RuleDivider weight="strong" className="my-6" />
          <section>
            <h2 className="font-serif text-lg mb-3">{t("admin.sessionSummary")}</h2>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatFigure value={detail.total_games} label={t("admin.statTotalGames")} />
              <StatFigure value={detail.active_games} label={t("admin.statActive")} />
              <StatFigure value={detail.wins} label={t("admin.win")} />
              <StatFigure value={detail.losses} label={t("admin.loss")} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatFigure value={detail.total_moves} label={t("admin.statTotalMoves")} />
              <StatFigure value={detail.total_undos} label={t("admin.colUndos")} />
              <StatFigure value={detail.total_hints} label={t("admin.colHints")} />
              <StatFigure
                value={detail.history.length}
                label={t("admin.historySection")}
              />
            </div>
          </section>

          <RuleDivider weight="faint" className="my-8" />

          <section>
            <h2 className="font-serif text-lg mb-3">{t("admin.historySection")}</h2>
            <div className="overflow-x-auto border border-ink-faint">
              <table className="w-full font-mono text-sm">
                <thead>
                  <tr className="border-b border-ink-faint bg-paper-deep text-ink-mute">
                    <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">
                      {t("admin.colCreated")}
                    </th>
                    <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">
                      {t("admin.colLastSeen")}
                    </th>
                    <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">
                      {t("admin.colDuration")}
                    </th>
                    <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">
                      {t("admin.endReason")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {detail.history.length === 0 ? (
                    <tr><td colSpan={4} className="p-4 text-center text-ink-faint">{t("admin.empty")}</td></tr>
                  ) : (
                    detail.history.map((h) => (
                      <tr key={h.id} className="border-b border-ink-faint/40">
                        <td className="p-2 tabular-nums text-ink-mute">{fmtTime(h.created_at)}</td>
                        <td className="p-2 tabular-nums text-ink-mute">
                          {h.ended_at ? fmtTime(h.ended_at) : (
                            <span className="inline-flex items-center gap-1 text-moss">
                              <span className="w-2 h-2 rounded-full bg-moss" aria-hidden />
                              {t("admin.liveBadge")}
                            </span>
                          )}
                        </td>
                        <td className="p-2 tabular-nums text-ink-mute">
                          {h.ended_at ? duration(h.created_at, h.ended_at) : "—"}
                        </td>
                        <td className="p-2 text-ink-mute">{endReasonLabel(h.end_reason)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <RuleDivider weight="faint" className="my-8" />

          <section>
            <h2 className="font-serif text-lg mb-3">{t("admin.allGamesSection")}</h2>
            <div className="overflow-x-auto border border-ink-faint">
              <table className="w-full font-mono text-sm">
                <thead>
                  <tr className="border-b border-ink-faint bg-paper-deep text-ink-mute">
                    <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">{t("admin.colGameId")}</th>
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
                  {detail.games.length === 0 ? (
                    <tr><td colSpan={12} className="p-4 text-center text-ink-faint">{t("admin.empty")}</td></tr>
                  ) : (
                    detail.games.map((g) => (
                      <tr key={g.id} className="border-b border-ink-faint/40">
                        <td className="p-2 tabular-nums text-ink-mute">#{g.id}</td>
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
                        <td className="p-2 tabular-nums text-ink-mute">{duration(g.started_at, g.finished_at)}</td>
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
        </>
      )}

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
