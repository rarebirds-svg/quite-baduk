"use client";
import { BOARD, STAR_POINTS, COLS } from "@/lib/board";

interface Props {
  board: string;          // 361 chars
  lastMove?: { x: number; y: number } | null;
  onClick?(x: number, y: number): void;
  disabled?: boolean;
  overlay?: { x: number; y: number; color: string; label?: string }[];
}

const CELL = 30;
const OFFSET = 24;
const SIZE = OFFSET * 2 + CELL * (BOARD - 1);

export default function Board({ board, lastMove, onClick, disabled, overlay }: Props) {
  const cells = board.split("");
  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="w-full max-w-[640px] bg-board-bg dark:bg-board-dark rounded-lg shadow" role="grid" aria-label="Go board">
      {Array.from({ length: BOARD }, (_, i) => (
        <g key={`g-${i}`}>
          <line x1={OFFSET} y1={OFFSET + i * CELL} x2={OFFSET + (BOARD - 1) * CELL} y2={OFFSET + i * CELL} stroke="black" strokeWidth={0.8} />
          <line y1={OFFSET} x1={OFFSET + i * CELL} y2={OFFSET + (BOARD - 1) * CELL} x2={OFFSET + i * CELL} stroke="black" strokeWidth={0.8} />
        </g>
      ))}
      {STAR_POINTS.flatMap((sx) =>
        STAR_POINTS.map((sy) => (
          <circle key={`s-${sx}-${sy}`} cx={OFFSET + sx * CELL} cy={OFFSET + sy * CELL} r={3} fill="black" />
        ))
      )}
      {Array.from({ length: BOARD }, (_, i) => (
        <g key={`lab-${i}`}>
          <text x={OFFSET + i * CELL} y={10} textAnchor="middle" fontSize={10} fill="currentColor">{COLS[i]}</text>
          <text x={OFFSET + i * CELL} y={SIZE - 4} textAnchor="middle" fontSize={10} fill="currentColor">{COLS[i]}</text>
          <text x={8} y={OFFSET + i * CELL + 3} textAnchor="start" fontSize={10} fill="currentColor">{BOARD - i}</text>
          <text x={SIZE - 18} y={OFFSET + i * CELL + 3} textAnchor="start" fontSize={10} fill="currentColor">{BOARD - i}</text>
        </g>
      ))}
      {cells.map((c, i) => {
        const x = i % BOARD;
        const y = Math.floor(i / BOARD);
        if (c === "B" || c === "W") {
          return (
            <circle
              key={`st-${i}`}
              cx={OFFSET + x * CELL}
              cy={OFFSET + y * CELL}
              r={CELL / 2 - 1}
              fill={c === "B" ? "#111" : "#fff"}
              stroke={c === "W" ? "#333" : "none"}
            />
          );
        }
        return null;
      })}
      {lastMove && (
        <circle
          cx={OFFSET + lastMove.x * CELL}
          cy={OFFSET + lastMove.y * CELL}
          r={5}
          fill="none"
          stroke="red"
          strokeWidth={1.5}
        />
      )}
      {overlay?.map((o, i) => (
        <g key={`o-${i}`}>
          <circle cx={OFFSET + o.x * CELL} cy={OFFSET + o.y * CELL} r={CELL / 2 - 3} fill={o.color} opacity={0.35} />
          {o.label && <text x={OFFSET + o.x * CELL} y={OFFSET + o.y * CELL + 3} textAnchor="middle" fontSize={8}>{o.label}</text>}
        </g>
      ))}
      {/* click layer */}
      <rect
        x={OFFSET - CELL / 2}
        y={OFFSET - CELL / 2}
        width={CELL * BOARD}
        height={CELL * BOARD}
        fill="transparent"
        onClick={(e) => {
          if (disabled || !onClick) return;
          const svg = e.currentTarget.ownerSVGElement!;
          const rect = svg.getBoundingClientRect();
          const scale = SIZE / rect.width;
          const px = (e.clientX - rect.left) * scale - OFFSET;
          const py = (e.clientY - rect.top) * scale - OFFSET;
          const x = Math.round(px / CELL);
          const y = Math.round(py / CELL);
          if (x >= 0 && x < BOARD && y >= 0 && y < BOARD) onClick(x, y);
        }}
      />
    </svg>
  );
}
