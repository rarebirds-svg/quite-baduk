import * as React from "react";
import { cn } from "@/lib/cn";

export interface PlayerCaptionProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  rank?: string;
  color: "black" | "white";
  subtitle?: string;
}

export const PlayerCaption = React.forwardRef<HTMLDivElement, PlayerCaptionProps>(
  ({ name, rank, color, subtitle, className, ...props }, ref) => {
    const stoneClass =
      color === "black"
        ? "bg-stone-black border-stone-black"
        : "bg-stone-white border-ink";
    return (
      <div ref={ref} className={cn("flex items-center gap-3", className)} {...props}>
        <span aria-hidden className={cn("h-4 w-4 rounded-full border", stoneClass)} />
        <div className="flex flex-col gap-0.5">
          <div className="flex items-baseline gap-2">
            <span className="font-sans text-sm font-semibold text-ink">{name}</span>
            {rank && <span className="font-mono text-xs text-ink-mute">{rank}</span>}
          </div>
          {subtitle && <span className="font-sans text-xs text-ink-mute">{subtitle}</span>}
        </div>
      </div>
    );
  }
);
PlayerCaption.displayName = "PlayerCaption";
