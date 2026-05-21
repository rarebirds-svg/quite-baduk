"use client";
// 프로 기보 목록 — 명국선/최근 토글과 기사·기전 검색을 갖춘 관전 탭 본문.
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Input } from "@/components/ui/input";

interface ProRow {
  id: number;
  collection: string;
  black_player: string;
  white_player: string;
  black_rank: string | null;
  white_rank: string | null;
  event: string | null;
  game_date: string | null;
  result: string | null;
  board_size: number;
  move_count: number;
}

type Collection = "masterpiece" | "recent";

export function ProGameList() {
  const t = useT();
  const router = useRouter();
  const [collection, setCollection] = useState<Collection>("masterpiece");
  const [rows, setRows] = useState<ProRow[] | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    api<{ rows: ProRow[] }>(`/api/spectate/pro?collection=${collection}`)
      .then((d) => {
        if (!cancelled) setRows(d.rows);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
        } else if (!cancelled) {
          setRows([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [collection, router]);

  const filtered = useMemo(() => {
    if (!rows) return null;
    const needle = q.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter((r) =>
      [r.black_player, r.white_player, r.event ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [rows, q]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex border border-ink-faint">
          {(["masterpiece", "recent"] as Collection[]).map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCollection(c)}
              className={
                "px-3 py-1.5 font-sans text-xs uppercase tracking-label transition-base " +
                (collection === c
                  ? "bg-oxblood text-paper"
                  : "text-ink-mute hover:text-ink")
              }
            >
              {c === "masterpiece"
                ? t("spectate.proMasterpiece")
                : t("spectate.proRecent")}
            </button>
          ))}
        </div>
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("spectate.proSearch")}
          className="max-w-xs"
        />
      </div>

      {filtered === null ? (
        <p className="text-sm text-ink-faint">…</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-ink-mute">{t("spectate.proEmpty")}</p>
      ) : (
        <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {filtered.map((r) => (
            <li key={r.id}>
              <Link
                href={`/spectate/pro/${r.id}`}
                className="block border border-ink-faint p-3 hover:bg-paper-deep transition-base"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-sans text-sm text-ink">
                    {r.black_player}
                    {r.black_rank && (
                      <span className="text-ink-faint text-xs"> {r.black_rank}</span>
                    )}
                    <span className="text-ink-faint"> vs </span>
                    {r.white_player}
                    {r.white_rank && (
                      <span className="text-ink-faint text-xs"> {r.white_rank}</span>
                    )}
                  </span>
                  <span className="font-mono text-xs text-ink-faint shrink-0">
                    {r.result ?? "—"}
                  </span>
                </div>
                <div className="mt-1 font-mono text-[11px] text-ink-faint tabular-nums flex flex-wrap gap-3">
                  {r.event && <span>{r.event}</span>}
                  {r.game_date && <span>{r.game_date}</span>}
                  <span>
                    {r.board_size}×{r.board_size}
                  </span>
                  <span>
                    {r.move_count}
                    {t("spectate.movesSuffix")}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
