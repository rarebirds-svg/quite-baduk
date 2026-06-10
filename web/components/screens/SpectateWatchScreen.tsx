"use client";
// 라이브 관전 화면 본체 — path/query 두 진입점이 공유한다.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Board from "@/components/Board";
import { api, ApiError } from "@/lib/api";
import { useT, useLocale } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { gtpToXy, replay } from "@/lib/board";
import { Button } from "@/components/ui/button";
import { Hero } from "@/components/editorial/Hero";
import { formatRank } from "@/components/RankPicker";
import { CountryFlag } from "@/components/CountryFlag";
import { PLAYER_COUNTRY, type PlayerId } from "@/components/PlayerPicker";

interface MoveEntryRaw {
  move_number: number;
  color: "B" | "W";
  coord: string | null;
  is_undone: boolean;
}
interface SpectateGame {
  id: number;
  board_size: number;
  handicap?: number;
  moves: MoveEntryRaw[];
  status: string;
  result: string | null;
  user_nickname?: string | null;
  user_rank?: string | null;
  user_country?: string | null;
  user_color?: "black" | "white";
  ai_player?: string | null;
  ai_rank?: string;
}

const POLL_MS = 4000;

export default function SpectateWatchScreen({ gameId }: { gameId: number }) {
  const t = useT();
  const [locale] = useLocale();
  const router = useRouter();
  const { session } = useAuthStore();

  const [game, setGame] = useState<SpectateGame | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  // 사용자가 최신 수에 머물러 있으면 새 수 도착 시 자동 추적.
  const followLive = useRef(true);

  const load = useCallback(async () => {
    try {
      const g = await api<SpectateGame>(`/api/spectate/${gameId}`);
      setGame(g);
      setError(null);
      setIdx((prev) => (followLive.current ? g.moves.length : prev));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setError("not_found");
      else if (e instanceof ApiError && e.status === 401) router.replace("/");
      else setError("load_failed");
    }
  }, [gameId, router]);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    load();
  }, [session, load, router]);

  // 진행 중 대국만 폴링.
  useEffect(() => {
    if (!game || game.status !== "active") return;
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [game, load]);

  const board = useMemo(
    () =>
      game ? replay(game.board_size, game.moves, idx, game.handicap ?? 0) : "",
    [game, idx],
  );
  const lastMove = useMemo(() => {
    if (!game || idx === 0) return null;
    const m = game.moves[idx - 1];
    if (!m || m.is_undone || !m.coord || m.coord === "pass" || m.coord === "resign")
      return null;
    const xy = gtpToXy(m.coord, game.board_size);
    return xy ? { x: xy[0], y: xy[1] } : null;
  }, [game, idx]);

  if (!session) return null;

  if (error === "not_found") {
    return (
      <div className="space-y-4">
        <Hero title={t("spectate.watchHeading")} subtitle="" />
        <p className="text-sm text-oxblood">{t("spectate.notFound")}</p>
        <Link href="/spectate" className="text-oxblood hover:underline text-sm">
          ← {t("spectate.backToList")}
        </Link>
      </div>
    );
  }
  if (!game) {
    return <p className="text-sm text-ink-mute p-4 text-center">…</p>;
  }

  const isLive = game.status === "active";
  const userIsBlack = (game.user_color ?? "black") === "black";
  const userLabel = game.user_nickname ?? "—";
  const userRankLabel = game.user_rank
    ? ` (${formatRank(game.user_rank, locale)})`
    : "";
  const aiLabel = game.ai_player
    ? t(`game.players.${game.ai_player}.name`)
    : game.ai_rank
    ? formatRank(game.ai_rank, locale)
    : "AI";
  const blackName = userIsBlack ? `${userLabel}${userRankLabel}` : aiLabel;
  const whiteName = userIsBlack ? aiLabel : `${userLabel}${userRankLabel}`;

  // 기존 대국은 country가 비어 한국 국기로 폴백. AI는 기풍 기사 국적.
  const userCountry = game.user_country ?? "KR";
  const aiCountry = game.ai_player
    ? PLAYER_COUNTRY[game.ai_player as PlayerId]
    : null;
  const blackCountry = userIsBlack ? userCountry : aiCountry;
  const whiteCountry = userIsBlack ? aiCountry : userCountry;

  const atLive = idx >= game.moves.length;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <Hero title={t("spectate.watchHeading")} subtitle="" />
        <Link
          href="/spectate"
          className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
        >
          ← {t("spectate.backToList")}
        </Link>
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-2 font-mono text-xs text-ink-mute">
        <span className="tabular-nums">
          {idx} / {game.moves.length}
        </span>
        <span className="flex items-baseline gap-2 text-ink">
          <span className="inline-flex items-baseline gap-1">
            <span>●</span>
            <CountryFlag code={blackCountry} />
            <span className="font-sans text-xs">{blackName}</span>
          </span>
          <span className="text-ink-faint">vs</span>
          <span className="inline-flex items-baseline gap-1">
            <span>○</span>
            <CountryFlag code={whiteCountry} />
            <span className="font-sans text-xs">{whiteName}</span>
          </span>
          {isLive ? (
            <span className="ml-1 inline-flex items-center gap-1 text-moss">
              <span className="w-1.5 h-1.5 rounded-full bg-moss" aria-hidden />
              {t("spectate.liveBadge")}
            </span>
          ) : (
            game.result && (
              <span className="text-ink-faint ml-1">· {game.result}</span>
            )
          )}
        </span>
      </div>

      <div className="w-full mx-auto">
        <Board size={game.board_size} board={board} lastMove={lastMove} />
      </div>

      <div className="relative">
        <input
          type="range"
          min={0}
          max={game.moves.length}
          value={idx}
          onChange={(e) => {
            const v = Number(e.target.value);
            setIdx(v);
            followLive.current = v >= game.moves.length;
          }}
          className="w-full accent-oxblood block"
          aria-label={t("review.scrubber")}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setIdx(0);
            followLive.current = false;
          }}
        >
          {t("review.first")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setIdx((i) => Math.max(0, i - 1));
            followLive.current = false;
          }}
        >
          {t("review.prev")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setIdx((i) => {
              const next = Math.min(game.moves.length, i + 1);
              followLive.current = next >= game.moves.length;
              return next;
            });
          }}
        >
          {t("review.next")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setIdx(game.moves.length);
            followLive.current = true;
          }}
        >
          {isLive ? t("spectate.toLive") : t("review.last")}
        </Button>
        {isLive && !atLive && (
          <span className="self-center font-sans text-xs text-ink-faint">
            {t("spectate.behindLive")}
          </span>
        )}
      </div>
    </div>
  );
}
