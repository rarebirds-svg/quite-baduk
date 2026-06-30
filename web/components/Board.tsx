"use client";
import { useEffect, useId, useState } from "react";
import { COLS, starPoints, xyToGtp } from "@/lib/board";
import { tokens } from "@/lib/tokens";
import { BOARD_THEMES, useBoardTheme } from "@/store/boardThemeStore";
import { useT } from "@/lib/i18n";

type OverlayColor = "primary" | "secondary" | "tertiary";
type OverlayItem = { x: number; y: number; color: OverlayColor | string; label?: string };
type Pt = [number, number];

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
  lastMoveKind = null,
  onClick,
  disabled,
  overlay,
  territoryMarkers,
  ownership,
}: {
  size: number;
  board: string;
  lastMove?: { x: number; y: number } | null;
  // "blunder" — 패착 (mover lost ground), oxblood emphasis ring.
  // "decisive" — 승착 (mover gained ground), moss emphasis ring.
  // null/undefined — standard thin oxblood "this is the last move" ring.
  lastMoveKind?: "blunder" | "decisive" | null;
  onClick?: (x: number, y: number) => void;
  disabled?: boolean;
  overlay?: OverlayItem[];
  territoryMarkers?: {
    black: Pt[];
    white: Pt[];
    dame?: Pt[];
    deadStones?: Pt[];
  };
  // Row-major KataGo ownership read (length size*size, [-1, 1]).
  // When provided, paints a translucent heatmap behind the stones —
  // positive = Black-controlled, negative = White-controlled.
  ownership?: number[];
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

  const rawId = useId();
  // useId returns ":r0:" — strip the colons so the result is a valid SVG id fragment
  const uid = rawId.replace(/:/g, "");
  const grainId = `kayaGrain-${uid}`;
  const stoneBlackId = `stoneBlackLithic-${uid}`;
  const stoneWhiteId = `stoneWhiteLithic-${uid}`;

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

  // 키보드 착수 — onClick이 있고 비활성이 아닐 때만 보드를 포커스 가능하게 한다.
  // 화살표로 커서를 옮기고 Enter/Space로 착수. 마우스 사용자에게 커서가
  // 보이지 않도록 첫 화살표 입력 때 커서를 띄운다(클릭 포커스로는 안 뜸).
  const t = useT();
  const interactive = !!onClick && !disabled;
  const [kbCursor, setKbCursor] = useState<{ x: number; y: number } | null>(null);
  const mid = Math.floor(size / 2);

  const handleKeyDown = (e: React.KeyboardEvent<SVGSVGElement>) => {
    if (!interactive) return;
    const deltas: Record<string, [number, number]> = {
      ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
    };
    if (e.key in deltas) {
      e.preventDefault();
      const [dx, dy] = deltas[e.key];
      setKbCursor((c) => {
        const base = c ?? { x: mid, y: mid };
        return {
          x: Math.min(size - 1, Math.max(0, base.x + dx)),
          y: Math.min(size - 1, Math.max(0, base.y + dy)),
        };
      });
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!kbCursor) {
        setKbCursor({ x: mid, y: mid });
        return;
      }
      onClick?.(kbCursor.x, kbCursor.y);
    }
  };

  const baseAria = `${size}×${size} Go board`;
  const ariaLabel = !interactive
    ? baseAria
    : kbCursor
      ? `${baseAria}, ${t("game.boardKbCursor")} ${xyToGtp(kbCursor.x, kbCursor.y, size)}. ${t("game.boardKbHint")}`
      : `${baseAria}. ${t("game.boardKbHint")}`;

  return (
    <svg
      viewBox={`0 0 ${W} ${W}`}
      width="100%"
      style={{
        maxWidth: "min(90vh, 90vw, 900px)",
        backgroundColor: palette.bg,
        transition: "background-color 200ms ease-out",
      }}
      className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-oxblood"
      role="img"
      aria-label={ariaLabel}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={interactive ? handleKeyDown : undefined}
      onBlur={interactive ? () => setKbCursor(null) : undefined}
    >
      <defs>
        {palette.surface === "wood" && (
          <filter id={grainId} x="0" y="0" width="100%" height="100%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.012 0.6"
              numOctaves={2}
              seed={7}
              result="noise"
            />
            <feColorMatrix
              in="noise"
              values="0 0 0 0 0.55  0 0 0 0 0.38  0 0 0 0 0.20  0 0 0 0.10 0"
              result="grain"
            />
            <feBlend in="SourceGraphic" in2="grain" mode="multiply" />
          </filter>
        )}
        <radialGradient id={stoneBlackId} cx="35%" cy="32%" r="65%">
          <stop offset="0%" stopColor="rgb(74 66 60)" />
          <stop offset="55%" stopColor="rgb(28 24 21)" />
          <stop offset="100%" stopColor="rgb(8 6 6)" />
        </radialGradient>
        <radialGradient id={stoneWhiteId} cx="35%" cy="32%" r="70%">
          <stop offset="0%" stopColor="rgb(253 252 248)" />
          <stop offset="65%" stopColor="rgb(229 224 213)" />
          <stop offset="100%" stopColor="rgb(187 181 168)" />
        </radialGradient>
      </defs>
      {palette.surface === "wood" && (
        <rect
          x={0}
          y={0}
          width={W}
          height={W}
          fill={palette.bg}
          filter={`url(#${grainId})`}
        />
      )}
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

      {ownership && ownership.length === size * size && (
        <g aria-hidden="true">
          {ownership.map((val, idx) => {
            // Skip near-neutral cells so the board stays readable.
            if (Math.abs(val) < 0.1) return null;
            const xi = idx % size;
            const yi = Math.floor(idx / size);
            const cx = pad + xi * CELL;
            const cy = pad + yi * CELL;
            const a = Math.min(0.45, Math.abs(val) * 0.5);
            const fill = val > 0 ? `rgba(8, 6, 6, ${a})` : `rgba(253, 252, 248, ${a})`;
            return (
              <rect
                key={`own-${idx}`}
                x={cx - CELL / 2 + 1}
                y={cy - CELL / 2 + 1}
                width={CELL - 2}
                height={CELL - 2}
                fill={fill}
              />
            );
          })}
        </g>
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
        const isLithic = palette.stoneStyle === "lithic";
        const fill =
          c === "B"
            ? isLithic
              ? `url(#${stoneBlackId})`
              : tokens.light["stone-black"]
            : isLithic
              ? `url(#${stoneWhiteId})`
              : tokens.light["stone-white"];
        const stroke =
          c === "W" && !isLithic ? palette.lineInk : "transparent";
        return (
          <g key={`st-${idx}`}>
            {palette.shadow && (
              <ellipse
                data-stone-shadow
                cx={cx}
                cy={cy + CELL * 0.05}
                rx={CELL * 0.42}
                ry={CELL * 0.12}
                fill="rgba(0,0,0,0.18)"
              />
            )}
            <circle
              data-stone={c}
              cx={cx}
              cy={cy}
              r={CELL * 0.45}
              fill={fill}
              stroke={stroke}
              strokeWidth={c === "W" && !isLithic ? 0.5 : 0}
            />
          </g>
        );
      })}

      {lastMove && (() => {
        const emphasis = lastMoveKind === "blunder" || lastMoveKind === "decisive";
        const mcx = pad + lastMove.x * CELL;
        const mcy = pad + lastMove.y * CELL;
        if (!emphasis) {
          // 표준 마커 — 돌 중앙의 반대색 채움 원 (흑돌→백 점, 백돌→흑 점).
          // 링 방식 대비 돌 색과 무관하게 항상 최대 명도 대비가 보장된다.
          const stoneAt = board[lastMove.y * size + lastMove.x];
          if (stoneAt !== "B" && stoneAt !== "W") return null;
          const dotFill =
            stoneAt === "B"
              ? tokens.light["stone-white"]
              : tokens.light["stone-black"];
          return (
            <circle data-last-move cx={mcx} cy={mcy} r={CELL * 0.16} fill={dotFill} />
          );
        }
        // emphasis(패착/승착)는 의미 우선이라 기존 색 링을 유지한다.
        const stroke =
          lastMoveKind === "decisive" ? "rgb(var(--moss))" : "rgb(var(--oxblood))";
        return (
          <>
            <circle
              cx={mcx}
              cy={mcy}
              r={CELL * 0.38}
              fill="none"
              stroke={stroke}
              strokeWidth={3}
            />
            <circle
              cx={mcx}
              cy={mcy}
              r={CELL * 0.5}
              fill="none"
              stroke={stroke}
              strokeWidth={1.5}
              strokeDasharray="2 2"
            />
          </>
        );
      })()}

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

      {territoryMarkers && (
        <g aria-hidden>
          {territoryMarkers.black.map(([x, y]) => (
            <rect
              key={`tb-${x}-${y}`}
              data-territory="black"
              x={pad + x * CELL - CELL * 0.09}
              y={pad + y * CELL - CELL * 0.09}
              width={CELL * 0.18}
              height={CELL * 0.18}
              fill="rgb(26 23 21)"
            />
          ))}
          {territoryMarkers.white.map(([x, y]) => (
            <rect
              key={`tw-${x}-${y}`}
              data-territory="white"
              x={pad + x * CELL - CELL * 0.09}
              y={pad + y * CELL - CELL * 0.09}
              width={CELL * 0.18}
              height={CELL * 0.18}
              fill="rgb(248 246 240)"
              stroke={palette.lineInk}
              strokeWidth={0.5}
            />
          ))}
          {(territoryMarkers.dame ?? []).map(([x, y]) => (
            <circle
              key={`td-${x}-${y}`}
              data-territory="dame"
              cx={pad + x * CELL}
              cy={pad + y * CELL}
              r={1.5}
              fill={palette.labelInk}
              opacity={0.6}
            />
          ))}
          {(territoryMarkers.deadStones ?? []).map(([x, y]) => (
            <g key={`tx-${x}-${y}`} data-territory="dead">
              <line
                x1={pad + x * CELL - CELL * 0.25}
                y1={pad + y * CELL - CELL * 0.25}
                x2={pad + x * CELL + CELL * 0.25}
                y2={pad + y * CELL + CELL * 0.25}
                stroke="rgb(var(--oxblood))"
                strokeWidth={1.25}
              />
              <line
                x1={pad + x * CELL + CELL * 0.25}
                y1={pad + y * CELL - CELL * 0.25}
                x2={pad + x * CELL - CELL * 0.25}
                y2={pad + y * CELL + CELL * 0.25}
                stroke="rgb(var(--oxblood))"
                strokeWidth={1.25}
              />
            </g>
          ))}
        </g>
      )}

      {interactive && kbCursor && (() => {
        const ccx = pad + kbCursor.x * CELL;
        const ccy = pad + kbCursor.y * CELL;
        return (
          <g data-kb-cursor aria-hidden pointerEvents="none">
            <circle
              cx={ccx}
              cy={ccy}
              r={CELL * 0.42}
              fill="none"
              stroke="rgb(var(--oxblood))"
              strokeWidth={2}
            />
            <line x1={ccx - CELL * 0.5} y1={ccy} x2={ccx + CELL * 0.5} y2={ccy} stroke="rgb(var(--oxblood))" strokeWidth={0.75} opacity={0.5} />
            <line x1={ccx} y1={ccy - CELL * 0.5} x2={ccx} y2={ccy + CELL * 0.5} stroke="rgb(var(--oxblood))" strokeWidth={0.75} opacity={0.5} />
          </g>
        );
      })()}

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
