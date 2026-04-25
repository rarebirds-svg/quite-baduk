"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";

interface AdminLoginRow {
  id: number;
  session_id: number | null;
  nickname: string;
  created_at: string;
  ended_at: string | null;
  end_reason: string | null;
  is_active: boolean;
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

const REFRESH_SEC = 10;

export default function AdminLoginHistoryPage() {
  const t = useT();
  const router = useRouter();
  const { session } = useAuthStore();
  const [rows, setRows] = useState<AdminLoginRow[] | null>(null);
  const [forbidden, setForbidden] = useState(false);

  useEffect(() => {
    if (!session) { router.replace("/"); return; }
    let cancelled = false;
    const poll = async () => {
      try {
        const r = await api<AdminLoginRow[]>("/api/admin/login-history?limit=500");
        if (!cancelled) setRows(r);
      } catch (e) {
        if (!cancelled && e instanceof ApiError && e.status === 403) {
          setForbidden(true);
        }
      }
    };
    poll();
    const id = setInterval(poll, REFRESH_SEC * 1000);
    return () => { cancelled = true; clearInterval(id); };
  }, [session, router]);

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
    <div className="mx-auto max-w-5xl py-8 px-4">
      <Link href="/admin" className="font-sans text-xs text-ink-mute hover:underline">
        {t("admin.backToConsole")}
      </Link>
      <Hero title={t("admin.historySection")} subtitle={t("admin.subtitle")} />

      <RuleDivider weight="strong" className="my-6" />

      <div className="overflow-x-auto border border-ink-faint">
        <table className="w-full font-mono text-sm">
          <thead>
            <tr className="border-b border-ink-faint bg-paper-deep text-ink-mute">
              <th className="text-left p-2 font-sans text-xs font-semibold uppercase tracking-label">
                {t("admin.colNickname")}
              </th>
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
            {rows === null ? (
              <tr><td colSpan={5} className="p-4 text-center text-ink-faint">…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={5} className="p-4 text-center text-ink-faint">{t("admin.empty")}</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="border-b border-ink-faint/40">
                  <td className="p-2 font-sans text-ink">
                    {r.session_id ? (
                      <Link href={`/admin/sessions/${r.session_id}`} className="text-oxblood hover:underline">
                        {r.nickname}
                      </Link>
                    ) : (
                      <span>{r.nickname}</span>
                    )}
                  </td>
                  <td className="p-2 tabular-nums text-ink-mute">{fmtTime(r.created_at)}</td>
                  <td className="p-2 tabular-nums text-ink-mute">
                    {r.ended_at ? fmtTime(r.ended_at) : (
                      <span className="inline-flex items-center gap-1 text-moss">
                        <span className="w-2 h-2 rounded-full bg-moss" aria-hidden />
                        {t("admin.liveBadge")}
                      </span>
                    )}
                  </td>
                  <td className="p-2 tabular-nums text-ink-mute">{duration(r.created_at, r.ended_at)}</td>
                  <td className="p-2 text-ink-mute">{endReasonLabel(r.end_reason)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
