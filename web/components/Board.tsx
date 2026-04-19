"use client";
import { starPoints, COLS } from "@/lib/board";

interface Props {
  size: number;
  board: string;               // size*size chars
  lastMove?: { x: number; y: number } | null;
  onClick?(x: number, y: number): void;
  disabled?: boolean;
  overlay?: { x: number; y: number; color: string; label?: string }[];
}

const CELL = 30;
const OFFSET = 24;
const LINE = "#3B2412";
const LABEL = "#4A2F17";

export default function Board({ size, board, lastMove, onClick, disabled, overlay }: Props) {
  const SIZE_PX = OFFSET * 2 + CELL * (size - 1);
  const STONE_R = CELL / 2 - 1;
  const cells = board.split("");
  const stars = starPoints(size);

  return (
    <svg
      viewBox={`0 0 ${SIZE_PX} ${SIZE_PX}`}
      className="w-full max-w-[640px] bg-board-bg dark:bg-board-dark rounded-lg shadow-lg"
      role="grid"
      aria-label={`${size}x${size} Go board`}
    >
      <defs>
        <radialGradient id="black-stone" cx="35%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#5a5a5a" />
          <stop offset="60%" stopColor="#1a1a1a" />
          <stop offset="100%" stopColor="#000000" />
        </radialGradient>
        <radialGradient id="white-stone" cx="35%" cy="35%" r="75%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="70%" stopColor="#f2f0eb" />
          <stop offset="100%" stopColor="#cfcac0" />
        </radialGradient>
      </defs>

      {Array.from({ length: size }, (_, i) => (
        <g key={`g-${i}`}>
          <line
            x1={OFFSET}
            y1={OFFSET + i * CELL}
            x2={OFFSET + (size - 1) * CELL}
            y2={OFFSET + i * CELL}
            stroke={LINE}
            strokeWidth={0.9}
          />
          <line
            y1={OFFSET}
            x1={OFFSET + i * CELL}
            y2={OFFSET + (size - 1) * CELL}
            x2={OFFSET + i * CELL}
            stroke={LINE}
            strokeWidth={0.9}
          />
        </g>
      ))}

      {stars.flatMap((sx) =>
        stars.map((sy) => (
          <circle key={`s-${sx}-${sy}`} cx={OFFSET + sx * CELL} cy={OFFSET + sy * CELL} r={3.2} fill={LINE} />
        ))
      )}

      {Array.from({ length: size }, (_, i) => (
        <g key={`lab-${i}`}>
          <text x={OFFSET + i * CELL} y={12} textAnchor="middle" fontSize={10} fontWeight={600} fill={LABEL}>
            {COLS[i]}
          </text>
          <text x={OFFSET + i * CELL} y={SIZE_PX - 4} textAnchor="middle" fontSize={10} fontWeight={600} fill={LABEL}>
            {COLS[i]}
          </text>
          <text x={9} y={OFFSET + i * CELL + 3} textAnchor="start" fontSize={10} fontWeight={600} fill={LABEL}>
            {size - i}
          </text>
          <text x={SIZE_PX - 18} y={OFFSET + i * CELL + 3} textAnchor="start" fontSize={10} fontWeight={600} fill={LABEL}>
            {size - i}
          </text>
        </g>
      ))}

      {cells.map((c, i) => {
        const x = i % size;
        const y = Math.floor(i / size);
        if (c === "B" || c === "W") {
          return (
            <g key={`st-${i}`}>
              <circle cx={OFFSET + x * CELL + 0.8} cy={OFFSET + y * CELL + 1.2} r={STONE_R} fill="rgba(0,0,0,0.22)" />
              <circle
                cx={OFFSET + x * CELL}
                cy={OFFSET + y * CELL}
                r={STONE_R}
                fill={c === "B" ? "url(#black-stone)" : "url(#white-stone)"}
                stroke={c === "W" ? "#8a8579" : "none"}
                strokeWidth={c === "W" ? 0.5 : 0}
              />
            </g>
          );
        }
        return null;
      })}

      {lastMove && (() => {
        const idx = lastMove.y * size + lastMove.x;
        const c = cells[idx];
        const dotFill = c === "B" ? "#ffffff" : "#d0342c";
        return (
          <circle cx={OFFSET + lastMove.x * CELL} cy={OFFSET + lastMove.y * CELL} r={4} fill={dotFill} />
        );
      })()}

      {overlay?.map((o, i) => (
        <g key={`o-${i}`}>
          <circle cx={OFFSET + o.x * CELL} cy={OFFSET + o.y * CELL} r={CELL / 2 - 3} fill={o.color} opacity={0.4} />
          {o.label && (
            <text x={OFFSET + o.x * CELL} y={OFFSET + o.y * CELL + 3} textAnchor="middle" fontSize={9} fontWeight={700} fill="#ffffff">
              {o.label}
            </text>
          )}
        </g>
      ))}

      <rect
        x={OFFSET - CELL / 2}
        y={OFFSET - CELL / 2}
        width={CELL * size}
        height={CELL * size}
        fill="transparent"
        onClick={(e) => {
          if (disabled || !onClick) return;
          const svg = e.currentTarget.ownerSVGElement!;
          const rect = svg.getBoundingClientRect();
          const scale = SIZE_PX / rect.width;
          const px = (e.clientX - rect.left) * scale - OFFSET;
          const py = (e.clientY - rect.top) * scale - OFFSET;
          const x = Math.round(px / CELL);
          const y = Math.round(py / CELL);
          if (x >= 0 && x < size && y >= 0 && y < size) onClick(x, y);
        }}
      />
    </svg>
  );
}
