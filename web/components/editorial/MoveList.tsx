import * as React from "react";
import { cn } from "@/lib/cn";

export interface MoveEntry {
  number: number;
  color: "B" | "W";
  coord: string;
}

export interface MoveListProps extends React.HTMLAttributes<HTMLOListElement> {
  moves: MoveEntry[];
  currentIndex: number;
  onSelect?: (index: number) => void;
}

export const MoveList = React.forwardRef<HTMLOListElement, MoveListProps>(
  ({ moves, currentIndex, onSelect, className, ...props }, ref) => (
    <ol
      ref={ref}
      className={cn("flex flex-col font-mono text-xs text-ink", className)}
      {...props}
    >
      {moves.map((m, i) => {
        const isCurrent = i === currentIndex;
        const isSpecial = m.coord === "pass" || m.coord === "resign";
        return (
          <li
            key={`${m.number}-${m.color}`}
            data-current={isCurrent}
            className={cn(
              "grid grid-cols-[2.5rem_1rem_1fr] items-baseline gap-2 px-2 py-1.5 border-b border-ink-faint/40",
              isCurrent && "bg-paper-deep",
              onSelect && "cursor-pointer hover:bg-paper-deep"
            )}
            onClick={onSelect ? () => onSelect(i) : undefined}
          >
            <span className="text-ink-mute tabular-nums">{m.number}</span>
            <span aria-hidden>
              <span
                className={cn(
                  "inline-block h-2 w-2 rounded-full",
                  m.color === "B"
                    ? "bg-stone-black"
                    : "bg-stone-white border border-ink"
                )}
              />
            </span>
            <span className={cn(isCurrent && "text-oxblood font-semibold")}>
              {isSpecial ? (
                <em className="not-italic text-ink-mute">{m.coord}</em>
              ) : (
                m.coord
              )}
            </span>
          </li>
        );
      })}
    </ol>
  )
);
MoveList.displayName = "MoveList";
