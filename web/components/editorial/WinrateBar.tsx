import * as React from "react";
import { cn } from "@/lib/cn";

export interface WinrateBarProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Black winrate in [0, 1]. Null renders a neutral placeholder. */
  value: number | null;
  label?: string;
  blackLabel?: string;
  whiteLabel?: string;
}

/**
 * Editorial position evaluation bar. A horizontal rule split between Black
 * (filled ink) on the left and White (paper) on the right. Matches the
 * hardcover aesthetic — no gradients, no shadows, pure contrast.
 */
export const WinrateBar = React.forwardRef<HTMLDivElement, WinrateBarProps>(
  (
    { value, label, blackLabel = "Black", whiteLabel = "White", className, ...props },
    ref
  ) => {
    const hasValue = typeof value === "number" && !Number.isNaN(value);
    const pct = hasValue ? Math.max(0, Math.min(1, value as number)) : 0.5;
    const blackPct = Math.round(pct * 1000) / 10;
    const whitePct = Math.round((1 - pct) * 1000) / 10;

    return (
      <div ref={ref} className={cn("flex flex-col gap-2", className)} {...props}>
        {label && (
          <div className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
            {label}
          </div>
        )}
        <div
          role="progressbar"
          aria-label={label}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={hasValue ? blackPct : undefined}
          className="relative h-2 w-full border border-ink overflow-hidden"
        >
          <div
            className="absolute inset-y-0 left-0 bg-ink transition-[width] duration-300"
            style={{ width: `${pct * 100}%` }}
          />
        </div>
        <div className="flex items-baseline justify-between font-mono text-xs tabular-nums">
          <span className="text-ink">
            <span className="text-ink-mute mr-1">{blackLabel}</span>
            {hasValue ? `${blackPct.toFixed(1)}%` : "—"}
          </span>
          <span className="text-ink-mute">
            {whiteLabel}{" "}
            <span className="text-ink">
              {hasValue ? `${whitePct.toFixed(1)}%` : "—"}
            </span>
          </span>
        </div>
      </div>
    );
  }
);
WinrateBar.displayName = "WinrateBar";
