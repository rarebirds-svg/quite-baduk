"use client";
import { useEffect, useState } from "react";
import { COLS, starPoints } from "@/lib/board";
import { tokens } from "@/lib/tokens";
import { BOARD_THEMES, useBoardTheme } from "@/store/boardThemeStore";

type OverlayColor = "primary" | "secondary" | "tertiary";
type OverlayItem = { x: number; y: number; color: OverlayColor | string; label?: string };

const OVERLAY_TOKEN: Record<OverlayColor, string> = {
  primary: "rgb(var(--oxblood))",
  secondary: "rgb(var(--ink-mute))",
  tertiary: "rgb(var(--ink-faint))",
};
const resolveOverlayColor = (c: OverlayColor | string): string =>
  c in OVERLAY_TOKEN ? OVERLAY_TOKEN[c as OverlayColor] : c;

export default function Board({
  size,
  board,
  lastMove = null,
  onClick,
  disabled,
  overlay,
}: {
  size: number;
  board: string;
  lastMove?: { x: number; y: number } | null;
  onClick?: (x: number, y: number) => void;
  disabled?: boolean;
  overlay?: OverlayItem[];
}) {
  const CELL = 30;
  const pad = CELL;
  const W = CELL * (size - 1) + pad * 2;
  const pts = [...Array(size).keys()].map((i) => pad + i * CELL);
  const stars = starPoints(size);
  // Zustand persist rehydrates from localStorage synchronously on the
  // client, which can disagree with the SSR default. Use the default on
  // the server + first client render, then swap after mount to keep
  // hydration stable.
  const boardTheme = useBoardTheme((s) => s.theme);
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const palette = BOARD_THEMES[mounted ? boardTheme : "paper"];

  const handleClick = (evt: React.MouseEvent<SVGRectElement, MouseEvent>) => {
    if (!onClick || disabled) return;
    const svg = evt.currentTarget.ownerSVGElement as SVGSVGElement | null;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const scale = W / rect.width;
    const localX = (evt.clientX - rect.left) * scale;
    const localY = (evt.clientY - rect.top) * scale;
    const x = Math.round((localX - pad) / CELL);
    const y = Math.round((localY - pad) / CELL);
    if (x < 0 || x >= size || y < 0 || y >= size) return;
    onClick(x, y);
  };

  return (
    <svg
      viewBox={`0 0 ${W} ${W}`}
      width="100%"
      style={{
        maxWidth: "min(90vh, 90vw, 900px)",
        backgroundColor: palette.bg,
        transition: "background-color 200ms ease-out",
      }}
      className="block"
      role="img"
      aria-label={`${size}×${size} Go board`}
    >
      <rect
        x={0.5}
        y={0.5}
        width={W - 1}
        height={W - 1}
        fill="none"
        stroke={palette.lineInk}
        strokeWidth={1}
      />

      {pts.map((p, i) => (
        <g key={i}>
          <line
            x1={pad}
            y1={p}
            x2={W - pad}
            y2={p}
            stroke={palette.lineInk}
            strokeWidth={i === 0 || i === size - 1 ? 1.25 : 0.75}
          />
          <line
            x1={p}
            y1={pad}
            x2={p}
            y2={W - pad}
            stroke={palette.lineInk}
            strokeWidth={i === 0 || i === size - 1 ? 1.25 : 0.75}
          />
        </g>
      ))}

      {stars.flatMap((sx) =>
        stars.map((sy) => (
          <circle
            key={`s-${sx}-${sy}`}
            cx={pad + sx * CELL}
            cy={pad + sy * CELL}
            r={2.5}
            fill={palette.starInk}
          />
        ))
      )}

      {[...Array(size).keys()].map((i) => {
        const label = COLS[i];
        const x = pad + i * CELL;
        return (
          <g key={`c-${i}`} className="font-mono" fill={palette.labelInk} fontSize={10}>
            <text x={x} y={14} textAnchor="middle">
              {label}
            </text>
            <text x={x} y={W - 6} textAnchor="middle">
              {label}
            </text>
          </g>
        );
      })}
      {[...Array(size).keys()].map((i) => {
        const label = size - i;
        const y = pad + i * CELL + 3;
        return (
          <g key={`r-${i}`} className="font-mono" fill={palette.labelInk} fontSize={10}>
            <text x={10} y={y} textAnchor="middle">
              {label}
            </text>
            <text x={W - 10} y={y} textAnchor="middle">
              {label}
            </text>
          </g>
        );
      })}

      {Array.from(board).map((c, idx) => {
        if (c !== "B" && c !== "W") return null;
        const x = idx % size;
        const y = Math.floor(idx / size);
        const cx = pad + x * CELL;
        const cy = pad + y * CELL;
        const fill = c === "B" ? tokens.light["stone-black"] : tokens.light["stone-white"];
        const stroke = c === "W" ? palette.lineInk : "transparent";
        return (
          <circle
            key={`st-${idx}`}
            cx={cx}
            cy={cy}
            r={CELL * 0.45}
            fill={fill}
            stroke={stroke}
            strokeWidth={0.75}
          />
        );
      })}

      {lastMove && (
        <circle
          cx={pad + lastMove.x * CELL}
          cy={pad + lastMove.y * CELL}
          r={CELL * 0.38}
          fill="none"
          stroke="rgb(var(--oxblood))"
          strokeWidth={1.5}
        />
      )}

      {overlay?.map((o, i) => {
        const stroke = resolveOverlayColor(o.color);
        return (
          <g key={`ov-${i}`}>
            <circle
              cx={pad + o.x * CELL}
              cy={pad + o.y * CELL}
              r={CELL * 0.42}
              fill="none"
              stroke={stroke}
              strokeDasharray="3 2"
              strokeWidth={1.25}
            />
            {o.label && (
              <text
                x={pad + o.x * CELL}
                y={pad + o.y * CELL + 3}
                textAnchor="middle"
                className="font-mono"
                fontSize={9}
                fill={stroke}
              >
                {o.label}
              </text>
            )}
          </g>
        );
      })}

      {onClick && (
        <rect
          x={0}
          y={0}
          width={W}
          height={W}
          fill="transparent"
          style={{ cursor: disabled ? "not-allowed" : "pointer" }}
          onClick={handleClick}
        />
      )}
    </svg>
  );
}
