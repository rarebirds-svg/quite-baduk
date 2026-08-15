"use client";
// 프로 기보 목록 — 명국선·세계기전·최근 토글과 서버 검색·페이지네이션을 갖춘 관전 탭 본문.
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { formatProEvent } from "@/lib/proEvent";
import { localizePlayer, localizeRank } from "@/lib/proLocale";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";
import { proGameHref } from "@/lib/routes";
import { formatGameResult } from "@/lib/formatResult";

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
  view_count: number;
}

export interface ProListResponse {
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

// 서버가 미리 받아올 첫 화면 질의 — 아래 초기 state와 한 글자도 어긋나면 안 되므로
// 같은 상수에서 만들어 둔다. 서버 프리페치와 초기 클라이언트 질의를 일치시킨다.
export const PRO_LIST_INITIAL_QUERY = new URLSearchParams({
  collection: "masterpiece",
  sort: "recent",
  limit: String(PAGE_SIZE),
  offset: "0",
}).toString();

export function ProGameList({
  initialData = null,
}: {
  initialData?: ProListResponse | null;
}) {
  const t = useT();
  const [locale] = useLocale();
  const router = useRouter();
  const [collection, setCollection] = useState<Collection>("masterpiece");
  const [page, setPage] = useState(0);
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [sort, setSort] = useState<"recent" | "oldest" | "popular">("recent");
  const [data, setData] = useState<ProListResponse | null>(initialData);

  // 검색어 디바운스 — 입력이 멎고 300ms 뒤 서버 질의. 새 검색은 첫 페이지로.
  useEffect(() => {
    const id = setTimeout(() => {
      setDebouncedQ(q.trim());
      setPage(0);
    }, 300);
    return () => clearTimeout(id);
  }, [q]);

  // 서버가 실어준 첫 화면은 지우지 않고 그대로 둔 채 뒤에서 갱신만 한다 — SSR로 그린
  // 목록이 마운트 직후 "…"로 깜빡이는 것을 막는다. 필터가 바뀐 뒤로는 종전대로 비운다.
  // 서버 결과가 비어 있으면(일시 장애 등) 지킬 것이 없으므로 평소대로 다시 받는다.
  const keepInitial = useRef((initialData?.rows.length ?? 0) > 0);

  useEffect(() => {
    let cancelled = false;
    if (keepInitial.current) keepInitial.current = false;
    else setData(null);
    const params = new URLSearchParams({
      collection,
      sort,
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
  }, [collection, page, debouncedQ, sort, router]);

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
        <Select
          value={sort}
          onValueChange={(v) => {
            setSort(v as "recent" | "oldest" | "popular");
            setPage(0);
          }}
        >
          <SelectTrigger aria-label={t("spectate.sortLabel")} className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="recent">{t("spectate.sortRecent")}</SelectItem>
            <SelectItem value="oldest">{t("spectate.sortOldest")}</SelectItem>
            <SelectItem value="popular">{t("spectate.sortPopular")}</SelectItem>
          </SelectContent>
        </Select>
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
                  href={proGameHref(r.id)}
                  className="block border border-ink-faint p-3 hover:bg-paper-deep transition-base"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-sans text-sm text-ink">
                      {localizePlayer(r.black_player, locale)}
                      {localizeRank(r.black_rank, locale) && (
                        <span className="text-ink-faint text-xs"> {localizeRank(r.black_rank, locale)}</span>
                      )}
                      <span className="text-ink-faint"> vs </span>
                      {localizePlayer(r.white_player, locale)}
                      {localizeRank(r.white_rank, locale) && (
                        <span className="text-ink-faint text-xs"> {localizeRank(r.white_rank, locale)}</span>
                      )}
                    </span>
                    <span className="font-sans text-xs text-ink-faint shrink-0">
                      {r.result ? formatGameResult(r.result, locale) : "—"}
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
