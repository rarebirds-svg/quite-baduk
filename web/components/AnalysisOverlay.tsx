"use client";

interface Move { move: string; winrate: number; visits: number }

export default function AnalysisOverlay({ topMoves, winrate }: { topMoves: Move[]; winrate: number }) {
  return (
    <div className="rounded border dark:border-gray-800 p-3 text-sm space-y-2">
      <div>승률 (to-move): {(winrate * 100).toFixed(1)}%</div>
      <ol className="list-decimal ml-5">
        {topMoves.map((m) => (
          <li key={m.move}>{m.move} — {(m.winrate * 100).toFixed(1)}% (visits {m.visits})</li>
        ))}
      </ol>
    </div>
  );
}
