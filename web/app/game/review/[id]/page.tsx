"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Board from "@/components/Board";
import AnalysisOverlay from "@/components/AnalysisOverlay";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { gtpToXy, totalCells } from "@/lib/board";
import { Hero } from "@/components/editorial/Hero";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { KeybindHint } from "@/components/editorial/KeybindHint";
import { MoveList, type MoveEntry } from "@/components/editorial/MoveList";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface MoveEntryRaw {
  move_number: number;
  color: "B" | "W";
  coord: string | null;
  is_undone: boolean;
}
interface GameDetail {
  id: number;
  board_size: number;
  moves: MoveEntryRaw[];
  result: string | null;
  started_at?: string;
  finished_at?: string | null;
}
interface AnalysisResp {
  winrate: number;
  top_moves: { move: string; winrate: number; visits: number }[];
  ownership?: number[];
}

function replay(size: number, moves: MoveEntryRaw[], upto: number): string {
  const cells = Array.from({ length: totalCells(size) }, () => ".");
  for (let i = 0; i < Math.min(upto, moves.length); i++) {
    const m = moves[i];
    if (m.is_undone || !m.coord || m.coord === "pass") continue;
    const xy = gtpToXy(m.coord, size);
    if (!xy) continue;
    const [x, y] = xy;
    cells[y * size + x] = m.color;
  }
  return cells.join("");
}

export default function ReviewPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const gameId = parseInt(params.id, 10);
  const [game, setGame] = useState<GameDetail | null>(null);
  const [idx, setIdx] = useState(0);
  const [analysis, setAnalysis] = useState<AnalysisResp | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const g = await api<GameDetail>(`/api/games/${gameId}`);
        setGame(g);
        setIdx(g.moves.length);
      } catch {
        toast.error(t("errors.game_not_found"));
      }
    })();
  }, [gameId, t]);

  const board = useMemo(
    () => (game ? replay(game.board_size, game.moves, idx) : ""),
    [game, idx]
  );

  const lastMove = useMemo(() => {
    if (!game || idx === 0) return null;
    const m = game.moves[idx - 1];
    if (!m || m.is_undone || !m.coord || m.coord === "pass" || m.coord === "resign")
      return null;
    const xy = gtpToXy(m.coord, game.board_size);
    return xy ? { x: xy[0], y: xy[1] } : null;
  }, [game, idx]);

  const moves: MoveEntry[] = useMemo(
    () =>
      (game?.moves ?? [])
        .filter((m) => !m.is_undone)
        .map((m) => ({
          number: m.move_number,
          color: m.color,
          coord: m.coord ?? "pass",
        })),
    [game]
  );

  const analyze = useCallback(async () => {
    if (!game) return;
    try {
      const r = await api<AnalysisResp>(
        `/api/games/${gameId}/analyze?moveNum=${idx}`,
        { method: "POST" }
      );
      setAnalysis(r);
    } catch {
      toast.error(t("errors.validation"));
    }
  }, [game, gameId, idx, t]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!game) return;
      const target = e.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      if (e.key === "ArrowLeft") setIdx((i) => Math.max(0, i - 1));
      if (e.key === "ArrowRight")
        setIdx((i) => Math.min(game.moves.length, i + 1));
      if (e.key === "Home") setIdx(0);
      if (e.key === "End") setIdx(game.moves.length);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [game]);

  if (!game) {
    return <div className="py-6 font-sans text-sm text-ink-mute">…</div>;
  }

  const overlay = analysis
    ? analysis.top_moves
        .slice(0, 3)
        .map((m, i) => {
          const xy = gtpToXy(m.move, game.board_size);
          if (!xy) return null;
          return {
            x: xy[0],
            y: xy[1],
            color:
              i === 0
                ? ("primary" as const)
                : i === 1
                  ? ("secondary" as const)
                  : ("tertiary" as const),
            label: String(i + 1),
          };
        })
        .filter(
          (
            x
          ): x is {
            x: number;
            y: number;
            color: "primary" | "secondary" | "tertiary";
            label: string;
          } => x !== null
        )
    : undefined;

  const heroSubtitle = [
    game.started_at ? game.started_at.slice(0, 10) : null,
    `${game.board_size}×${game.board_size}`,
    game.result,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="flex flex-col gap-6 py-4">
      <Hero title={t("review.title")} subtitle={heroSubtitle} size="compact" />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-4">
          <Board
            size={game.board_size}
            board={board}
            lastMove={lastMove}
            overlay={overlay}
          />

          <div className="flex flex-col gap-2 border-t border-ink-faint pt-3">
            <input
              type="range"
              min={0}
              max={game.moves.length}
              value={idx}
              onChange={(e) => setIdx(Number(e.target.value))}
              className="w-full accent-oxblood"
              aria-label={t("review.scrubber")}
            />
            <div className="flex items-center justify-between font-mono text-xs text-ink-mute">
              <span>
                {idx} / {game.moves.length}
              </span>
              <div className="flex gap-2">
                <KeybindHint keys={["←"]} description={t("review.prev")} />
                <KeybindHint keys={["→"]} description={t("review.next")} />
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button variant="outline" size="sm" onClick={() => setIdx(0)}>
                {t("review.first")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIdx(Math.max(0, idx - 1))}
              >
                {t("review.prev")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIdx(Math.min(game.moves.length, idx + 1))}
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
              <Button size="sm" onClick={analyze} className="ml-auto">
                {t("review.analyze")}
              </Button>
            </div>
          </div>
        </div>

        <aside className="flex flex-col gap-6">
          {analysis && (
            <AnalysisOverlay
              topMoves={analysis.top_moves}
              winrate={analysis.winrate}
            />
          )}
          <RuleDivider label={t("game.moves")} />
          <div className="max-h-[60vh] overflow-y-auto border border-ink-faint">
            <MoveList
              moves={moves}
              currentIndex={idx - 1}
              onSelect={(i) => setIdx(i + 1)}
            />
          </div>
          <a
            href={`/api/games/${gameId}/sgf`}
            className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
          >
            {t("game.downloadSgf")}
          </a>
        </aside>
      </div>
    </div>
  );
}
