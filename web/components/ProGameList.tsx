"use client";
// 프로 기보 목록 — 명국선·세계기전·최근 토글과 서버 검색·페이지네이션을 갖춘 관전 탭 본문.
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { formatProEvent } from "@/lib/proEvent";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface ProRow {
  id: number;
  collection: string;
  black_player: string;
  white_player: string;
  black_rank: string | null;
  white_rank: string | null;
  event: string | null;
  round: string | null;
  game_date: string | null;
  result: string | null;
  board_size: number;
  move_count: number;
}

interface ProListResponse {
  rows: ProRow[];
  total: number;
}

type Collection = "masterpiece" | "world" | "recent";

const COLLECTIONS: Collection[] = ["masterpiece", "world", "recent"];
const COLLECTION_LABEL: Record<Collection, string> = {
  masterpiece: "spectate.proMasterpiece",
  world: "spectate.proWorld",
  recent: "spectate.proRecent",
};
const PAGE_SIZE = 50;

export function ProGameList() {
  const t = useT();
  const [locale] = useLocale();
  const router = useRouter();
  const [collection, setCollection] = useState<Collection>("masterpiece");
  const [page, setPage] = useState(0);
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [data, setData] = useState<ProListResponse | null>(null);

  // 검색어 디바운스 — 입력이 멎고 300ms 뒤 서버 질의. 새 검색은 첫 페이지로.
  useEffect(() => {
    const id = setTimeout(() => {
      setDebouncedQ(q.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(id);
  }, [q]);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    const params = new URLSearchParams({
      collection,
      limit: String(PAGE_SIZE),
      offset: String(page * PAGE_SIZE),
    });
    if (debouncedQ) params.set("q", debouncedQ);
    api<ProListResponse>(`/api/spectate/pro?${params.toString()}`)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
        } else if (!cancelled) {
          setData({ rows: [], total: 0 });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [collection, page, debouncedQ, router]);

  const rows = data?.rows ?? null;
  const total = data?.total ?? 0;
  const pageCount = Math.ceil(total / PAGE_SIZE);
  const rangeFrom = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const rangeTo = page * PAGE_SIZE + (rows?.length ?? 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex border border-ink-faint">
          {COLLECTIONS.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => {
                setCollection(c);
                setPage(0);
              }}
              className={
                "px-3 py-1.5 font-sans text-xs uppercase tracking-label transition-base " +
                (collection === c
                  ? "bg-oxblood text-paper"
                  : "text-ink-mute hover:text-ink")
              }
            >
              {t(COLLECTION_LABEL[c])}
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

      {rows === null ? (
        <p className="text-sm text-ink-faint">…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-ink-mute">{t("spectate.proEmpty")}</p>
      ) : (
        <>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {rows.map((r) => (
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
                    {formatProEvent(r.event, r.round, locale) && (
                      <span>{formatProEvent(r.event, r.round, locale)}</span>
                    )}
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

          {pageCount > 1 && (
            <div className="flex items-center justify-between gap-3 pt-1">
              <span className="font-mono text-xs text-ink-faint tabular-nums">
                {rangeFrom}–{rangeTo} / {total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  {t("spectate.proPrev")}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                  disabled={page >= pageCount - 1}
                >
                  {t("spectate.proNext")}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
