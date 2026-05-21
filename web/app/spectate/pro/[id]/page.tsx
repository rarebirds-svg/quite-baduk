"use client";
// 프로 기보 재생 화면 — 저장된 SGF 수순을 스크러버로 되짚어 보는 페이지.
import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Board from "@/components/Board";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useAuthStore } from "@/store/authStore";
import { gtpToXy, replay, type ReplayMove } from "@/lib/board";
import { Button } from "@/components/ui/button";
import { Hero } from "@/components/editorial/Hero";

interface ProMove {
  move_number: number;
  color: "B" | "W";
  coord: string | null;
}
interface ProGameDetail {
  id: number;
  black_player: string;
  white_player: string;
  black_rank: string | null;
  white_rank: string | null;
  event: string | null;
  game_date: string | null;
  result: string | null;
  board_size: number;
  handicap: number;
  komi: number;
  move_count: number;
  moves: ProMove[];
}

export default function ProGameWatchPage() {
  const t = useT();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const gameId = parseInt(params.id, 10);
  const { session } = useAuthStore();

  const [game, setGame] = useState<ProGameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (!session) {
      router.replace("/");
      return;
    }
    api<ProGameDetail>(`/api/spectate/pro/${gameId}`)
      .then((g) => {
        setGame(g);
        setError(null);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) setError("not_found");
        else if (e instanceof ApiError && e.status === 401) router.replace("/");
        else setError("load_failed");
      });
  }, [session, gameId, router]);

  const replayMoves: ReplayMove[] = useMemo(
    () =>
      game
        ? game.moves.map((m) => ({
            color: m.color,
            coord: m.coord,
            is_undone: false,
          }))
        : [],
    [game],
  );

  const board = useMemo(
    () =>
      game
        ? replay(game.board_size, replayMoves, idx, game.handicap ?? 0)
        : "",
    [game, replayMoves, idx],
  );
  const lastMove = useMemo(() => {
    if (!game || idx === 0) return null;
    const m = game.moves[idx - 1];
    if (!m || !m.coord || m.coord === "pass") return null;
    const xy = gtpToXy(m.coord, game.board_size);
    return xy ? { x: xy[0], y: xy[1] } : null;
  }, [game, idx]);

  if (!session) return null;

  if (error === "not_found") {
    return (
      <div className="space-y-4">
        <Hero title={t("spectate.tabPro")} subtitle="" />
        <p className="text-sm text-oxblood">{t("spectate.proNotFound")}</p>
        <Link href="/spectate" className="text-oxblood hover:underline text-sm">
          ← {t("spectate.proBackToList")}
        </Link>
      </div>
    );
  }
  if (!game) {
    return <p className="text-sm text-ink-mute p-4 text-center">…</p>;
  }

  const blackLabel = `${game.black_player}${
    game.black_rank ? ` ${game.black_rank}` : ""
  }`;
  const whiteLabel = `${game.white_player}${
    game.white_rank ? ` ${game.white_rank}` : ""
  }`;

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <Hero title={t("spectate.tabPro")} subtitle="" />
        <Link
          href="/spectate"
          className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
        >
          ← {t("spectate.proBackToList")}
        </Link>
      </div>

      <div className="flex flex-wrap items-baseline justify-between gap-2 font-mono text-xs text-ink-mute">
        <span className="tabular-nums">
          {idx} / {game.moves.length}
        </span>
        <span className="flex items-baseline gap-2 text-ink">
          <span className="font-sans">{blackLabel}</span>
          <span className="text-ink-faint">vs</span>
          <span className="font-sans">{whiteLabel}</span>
          {game.result && (
            <span className="text-ink-faint ml-1">· {game.result}</span>
          )}
        </span>
      </div>

      {(game.event || game.game_date) && (
        <p className="font-sans text-xs text-ink-faint">
          {[game.event, game.game_date].filter(Boolean).join(" · ")}
        </p>
      )}

      <div className="w-full mx-auto">
        <Board size={game.board_size} board={board} lastMove={lastMove} />
      </div>

      <div className="relative">
        <input
          type="range"
          min={0}
          max={game.moves.length}
          value={idx}
          onChange={(e) => setIdx(Number(e.target.value))}
          className="w-full accent-oxblood block"
          aria-label={t("review.scrubber")}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={() => setIdx(0)}>
          {t("review.first")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
        >
          {t("review.prev")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIdx((i) => Math.min(game.moves.length, i + 1))}
        >
          {t("review.next")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIdx(game.moves.length)}
        >
          {t("review.last")}
        </Button>
      </div>
    </div>
  );
}
