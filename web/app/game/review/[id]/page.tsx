"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Board from "@/components/Board";
import AnalysisOverlay from "@/components/AnalysisOverlay";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { gtpToXy, totalCells } from "@/lib/board";

interface MoveEntry { move_number: number; color: string; coord: string | null; is_undone: boolean; }
interface GameDetail { id: number; board_size: number; moves: MoveEntry[]; result: string | null; }
interface AnalysisResp { winrate: number; top_moves: { move: string; winrate: number; visits: number }[]; ownership: number[] }

function replay(size: number, moves: MoveEntry[], upto: number): string {
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
    api<GameDetail>(`/api/games/${gameId}`).then(setGame);
  }, [gameId]);

  if (!game) return <div className="mt-6">Loading...</div>;
  const board = replay(game.board_size, game.moves, idx);

  const analyze = async () => {
    const r = await api<AnalysisResp>(`/api/games/${gameId}/analyze?moveNum=${idx}`, { method: "POST" });
    setAnalysis(r);
  };

  return (
    <div className="mt-4 space-y-4">
      <Board size={game.board_size} board={board} />
      <div className="flex gap-2 text-sm">
        <button className="border rounded px-2 py-1" onClick={() => setIdx(0)}>{t("review.first")}</button>
        <button className="border rounded px-2 py-1" onClick={() => setIdx(Math.max(0, idx - 1))}>{t("review.prev")}</button>
        <button className="border rounded px-2 py-1" onClick={() => setIdx(Math.min(game.moves.length, idx + 1))}>{t("review.next")}</button>
        <button className="border rounded px-2 py-1" onClick={() => setIdx(game.moves.length)}>{t("review.last")}</button>
        <button className="border rounded px-2 py-1" onClick={analyze}>{t("review.analyze")}</button>
        <span className="ml-2">Move {idx}/{game.moves.length}</span>
      </div>
      {analysis && <AnalysisOverlay winrate={analysis.winrate} topMoves={analysis.top_moves} />}
    </div>
  );
}
