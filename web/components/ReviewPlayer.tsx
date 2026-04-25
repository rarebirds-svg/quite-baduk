"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import Board from "@/components/Board";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { gtpToXy, totalCells } from "@/lib/board";
import { Button } from "@/components/ui/button";

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
  user_nickname?: string | null;
  ai_player?: string | null;
  ai_style?: string;
  ai_rank?: string;
  started_at?: string;
  finished_at?: string | null;
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

export interface ReviewPlayerProps {
  gameId: number;
  /** Default ~700ms — compact modals feel better slightly faster. */
  intervalMs?: number;
  /** Auto-start playback on mount. Default true. */
  autoplay?: boolean;
}

/**
 * Self-contained kifu replay player. Fetches the game, renders the board,
 * and offers play/pause + scrubber + step controls. Designed to fit inside
 * dialogs / popups without pulling in the full review page's analysis UI.
 */
export default function ReviewPlayer({
  gameId,
  intervalMs = 700,
  autoplay = true,
}: ReviewPlayerProps) {
  const t = useT();
  const [game, setGame] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(false);
  // Track the current gameId to cancel a stale fetch if the caller swaps
  // games while one is in flight (clicking review on a different row).
  const activeId = useRef(gameId);

  useEffect(() => {
    activeId.current = gameId;
    setGame(null);
    setError(null);
    setIdx(0);
    setPlaying(false);
    (async () => {
      try {
        const g = await api<GameDetail>(`/api/games/${gameId}`);
        if (activeId.current !== gameId) return;
        setGame(g);
        setIdx(0);
        setPlaying(autoplay);
      } catch {
        if (activeId.current !== gameId) return;
        setError("load_failed");
      }
    })();
  }, [gameId, autoplay]);

  useEffect(() => {
    if (!playing || !game) return;
    if (idx >= game.moves.length) { setPlaying(false); return; }
    const id = setInterval(() => {
      setIdx((i) => (game && i >= game.moves.length ? i : i + 1));
    }, intervalMs);
    return () => clearInterval(id);
  }, [playing, game, idx, intervalMs]);

  const board = useMemo(
    () => (game ? replay(game.board_size, game.moves, idx) : ""),
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

  if (error) {
    return (
      <p className="text-sm text-oxblood p-4 text-center">
        {t("errors.game_not_found")}
      </p>
    );
  }
  if (!game) {
    return (
      <p className="text-sm text-ink-mute p-4 text-center">…</p>
    );
  }

  const currentMove = idx > 0 ? game.moves[idx - 1] : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between font-mono text-xs text-ink-mute">
        <span className="tabular-nums">
          {idx} / {game.moves.length}
          {currentMove && (
            <span className="ml-2 text-ink">
              {currentMove.color === "B" ? "●" : "○"}{" "}
              <span className="tabular-nums">
                {currentMove.coord ?? "pass"}
              </span>
            </span>
          )}
        </span>
        <span className="text-ink-faint">
          {game.user_nickname ?? "—"} · {game.ai_player ?? game.ai_rank ?? ""}
          {game.result ? ` · ${game.result}` : ""}
        </span>
      </div>

      <div className="max-w-[min(560px,100%)] mx-auto">
        <Board size={game.board_size} board={board} lastMove={lastMove} />
      </div>

      <input
        type="range"
        min={0}
        max={game.moves.length}
        value={idx}
        onChange={(e) => { setIdx(Number(e.target.value)); setPlaying(false); }}
        className="w-full accent-oxblood"
        aria-label={t("review.scrubber")}
      />

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm"
          onClick={() => { setIdx(0); setPlaying(false); }}>
          {t("review.first")}
        </Button>
        <Button variant="outline" size="sm"
          onClick={() => { setIdx(Math.max(0, idx - 1)); setPlaying(false); }}>
          {t("review.prev")}
        </Button>
        <Button size="sm"
          onClick={() => {
            if (idx >= game.moves.length) setIdx(0);
            setPlaying((p) => !p);
          }}>
          {playing ? t("review.pause") : t("review.play")}
        </Button>
        <Button variant="outline" size="sm"
          onClick={() => { setIdx(Math.min(game.moves.length, idx + 1)); setPlaying(false); }}>
          {t("review.next")}
        </Button>
        <Button variant="outline" size="sm"
          onClick={() => { setIdx(game.moves.length); setPlaying(false); }}>
          {t("review.last")}
        </Button>
        <a
          href={`/api/games/${gameId}/sgf`}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto self-center font-sans text-xs font-semibold uppercase tracking-label text-oxblood hover:underline"
        >
          SGF
        </a>
      </div>
    </div>
  );
}
