"use client";
import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Board from "@/components/Board";
import GameControls from "@/components/GameControls";
import ScorePanel from "@/components/ScorePanel";
import { openGameWS, type WSMessage, type GameWS } from "@/lib/ws";
import { useGameStore } from "@/store/gameStore";
import { api } from "@/lib/api";
import { gtpToXy, xyToGtp } from "@/lib/board";
import { useT } from "@/lib/i18n";

export default function PlayPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const gameId = parseInt(params.id, 10);
  const g = useGameStore();
  const wsRef = useRef<GameWS | null>(null);
  const [hint, setHint] = useState<{ move: string; winrate: number; visits: number }[]>([]);

  useEffect(() => {
    const ws = openGameWS(gameId, (msg: WSMessage) => {
      if (msg.type === "state") {
        g.set({ board: msg.board, toMove: msg.to_move, moveCount: msg.move_count, captures: msg.captures, error: null });
      } else if (msg.type === "ai_move") {
        g.set({ lastAiMove: msg.coord, aiThinking: false });
      } else if (msg.type === "game_over") {
        g.set({ gameOver: true, result: msg.result, aiThinking: false });
      } else if (msg.type === "error") {
        g.set({ error: msg.code, aiThinking: false });
      }
    });
    wsRef.current = ws;
    return () => { ws.close(); g.reset(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId]);

  const sendMove = (x: number, y: number) => {
    if (g.gameOver || g.aiThinking) return;
    const coord = xyToGtp(x, y);
    g.set({ aiThinking: true, error: null });
    wsRef.current?.send({ type: "move", coord });
  };

  const pass = () => { g.set({ aiThinking: true }); wsRef.current?.send({ type: "pass" }); };
  const undo = () => wsRef.current?.send({ type: "undo", steps: 2 });
  const resign = async () => {
    await api(`/api/games/${gameId}/resign`, { method: "POST" });
    g.set({ gameOver: true });
  };
  const hintMe = async () => {
    const r = await api<{ hints: typeof hint }>(`/api/games/${gameId}/hint`, { method: "POST" });
    setHint(r.hints);
  };

  const lastMoveXy = g.lastAiMove ? gtpToXy(g.lastAiMove) : null;

  return (
    <div className="mt-4 space-y-4">
      <Board
        board={g.board}
        lastMove={lastMoveXy ? { x: lastMoveXy[0], y: lastMoveXy[1] } : null}
        onClick={sendMove}
        disabled={g.aiThinking || g.gameOver}
        overlay={hint.map((h) => {
          const xy = gtpToXy(h.move);
          return xy ? { x: xy[0], y: xy[1], color: "rgba(0,200,0,0.6)", label: `${Math.round(h.winrate * 100)}` } : null;
        }).filter((x): x is { x: number; y: number; color: string; label: string } => x !== null)}
      />
      <ScorePanel captures={g.captures} />
      <GameControls onPass={pass} onResign={resign} onUndo={undo} onHint={hintMe} disabled={g.gameOver || g.aiThinking} />
      {g.aiThinking && <div className="text-sm text-gray-500">{t("game.aiThinking")}</div>}
      {g.error && <div className="text-sm text-red-600">{t(`errors.${g.error}`)}</div>}
      {g.gameOver && (
        <div className="text-sm font-medium">
          {t("game.resultLabel")}: {g.result || ""}{" "}
          <a className="underline ml-2" href={`/api/games/${gameId}/sgf`} target="_blank" rel="noreferrer">{t("game.downloadSgf")}</a>
        </div>
      )}
    </div>
  );
}
