"use client";
// 관리자 프로 기보 관리 — 최근 기보 SGF 업로드와 등록 목록·삭제 화면.
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { Hero } from "@/components/editorial/Hero";
import { Button } from "@/components/ui/button";

interface AdminProRow {
  id: number;
  collection: string;
  black_player: string;
  white_player: string;
  event: string | null;
  game_date: string | null;
  result: string | null;
  move_count: number;
  source_note: string | null;
}

interface UploadResult {
  inserted: number;
  skipped: number;
  failed: string[];
}

export default function AdminProGamesPage() {
  const t = useT();
  const router = useRouter();
  const { session } = useAuthStore();
  const [rows, setRows] = useState<AdminProRow[] | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const d = await api<{ rows: AdminProRow[] }>("/api/admin/pro-games");
      setRows(d.rows);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403))
        router.replace("/");
    }
  }, [router]);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    load();
  }, [session, load, router]);

  const onUpload = async () => {
    const files = fileRef.current?.files;
    if (!files || files.length === 0) return;
    const form = new FormData();
    for (const f of Array.from(files)) form.append("files", f);
    setBusy(true);
    try {
      const res = await fetch("/api/admin/pro-games", {
        method: "POST",
        body: form,
        credentials: "include",
      });
      if (res.ok) {
        setResult((await res.json()) as UploadResult);
        if (fileRef.current) fileRef.current.value = "";
        await load();
      }
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (id: number) => {
    if (!window.confirm(t("adminPro.deleteConfirm"))) return;
    await api(`/api/admin/pro-games/${id}`, { method: "DELETE" });
    await load();
  };

  if (!session) return null;

  return (
    <div className="space-y-6">
      <Hero title={t("adminPro.heading")} subtitle="" />

      <div className="flex flex-wrap items-center gap-3 border border-ink-faint p-3">
        <input
          ref={fileRef}
          type="file"
          accept=".sgf"
          multiple
          aria-label={t("adminPro.uploadLabel")}
          className="font-sans text-sm text-ink-mute"
        />
        <Button size="sm" onClick={onUpload} disabled={busy}>
          {t("adminPro.uploadButton")}
        </Button>
        {result && (
          <span className="font-mono text-xs text-ink-mute tabular-nums">
            {t("adminPro.uploadResult")
              .replace("{inserted}", String(result.inserted))
              .replace("{skipped}", String(result.skipped))
              .replace("{failed}", String(result.failed.length))}
          </span>
        )}
      </div>

      {rows === null ? (
        <p className="text-sm text-ink-faint">…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-mute">{t("adminPro.empty")}</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li
              key={r.id}
              className="flex items-baseline justify-between gap-3 border border-ink-faint p-3"
            >
              <span className="font-sans text-sm text-ink">
                {r.black_player} vs {r.white_player}
                <span className="text-ink-faint text-xs">
                  {" "}
                  · {r.collection}
                  {r.event ? ` · ${r.event}` : ""}
                  {r.game_date ? ` · ${r.game_date}` : ""}
                  {` · ${r.move_count}`}
                  {t("spectate.movesSuffix")}
                </span>
              </span>
              <button
                type="button"
                onClick={() => onDelete(r.id)}
                className="font-sans text-xs uppercase tracking-label text-oxblood hover:underline shrink-0"
              >
                {t("adminPro.delete")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
