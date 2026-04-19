import * as React from "react";
import { cn } from "@/lib/cn";

export interface StatFigureProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string | number;
  unit?: string;
  label: string;
  trend?: "up" | "down" | null;
}

export const StatFigure = React.forwardRef<HTMLDivElement, StatFigureProps>(
  ({ value, unit, label, trend, className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-1", className)} {...props}>
      <div className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {label}
      </div>
      <div className="flex items-baseline gap-1">
        <span
          data-stat-value
          className="font-mono text-4xl font-medium leading-none tracking-tight tabular-nums text-ink"
        >
          {typeof value === "number" ? value.toString() : value}
        </span>
        {unit && <span className="font-mono text-sm text-ink-mute">{unit}</span>}
        {trend === "up" && (
          <span className="text-moss ml-1" aria-label="up">
            ▲
          </span>
        )}
        {trend === "down" && (
          <span className="text-oxblood ml-1" aria-label="down">
            ▼
          </span>
        )}
      </div>
    </div>
  )
);
StatFigure.displayName = "StatFigure";
