import { StatFigure } from "@/components/editorial/StatFigure";
import { RuleDivider } from "@/components/editorial/RuleDivider";
import { cn } from "@/lib/cn";

export interface AnalysisOverlayProps {
  topMoves: { move: string; winrate: number; visits: number }[];
  winrate: number;
  className?: string;
}

export default function AnalysisOverlay({
  topMoves,
  winrate,
  className,
}: AnalysisOverlayProps) {
  const pct = (winrate * 100).toFixed(1);
  const trend = winrate > 0.5 ? "up" : winrate < 0.5 ? "down" : null;
  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <StatFigure value={pct} unit="%" label="WIN RATE" trend={trend} />
      <RuleDivider label="TOP MOVES" />
      <ol className="flex flex-col font-mono text-xs">
        {topMoves.slice(0, 5).map((m, i) => (
          <li
            key={m.move}
            className="grid grid-cols-[1.25rem_1fr_4rem_auto] items-baseline gap-2 border-b border-ink-faint/40 py-1.5"
          >
            <span className="font-sans text-[10px] font-semibold uppercase tracking-label text-oxblood">
              {i + 1}
            </span>
            <span className="text-ink font-semibold">{m.move}</span>
            <span className="text-ink-mute tabular-nums text-right">
              {(m.winrate * 100).toFixed(1)}%
            </span>
            <span className="text-ink-faint tabular-nums text-right">{m.visits}v</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
