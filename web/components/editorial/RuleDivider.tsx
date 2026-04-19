import * as React from "react";
import { cn } from "@/lib/cn";

export interface RuleDividerProps extends React.HTMLAttributes<HTMLDivElement> {
  weight?: "faint" | "strong";
  label?: string;
}

/**
 * Editorial rule line. Horizontal only. Optional centered uppercase label
 * bisects the line (like magazine section markers).
 */
export const RuleDivider = React.forwardRef<HTMLDivElement, RuleDividerProps>(
  ({ weight = "faint", label, className, ...props }, ref) => {
    const borderColor = weight === "strong" ? "border-ink" : "border-ink-faint";
    if (!label) {
      return (
        <div
          ref={ref}
          role="separator"
          className={cn("h-px w-full border-t", borderColor, className)}
          {...props}
        />
      );
    }
    return (
      <div
        ref={ref}
        role="separator"
        aria-label={label}
        className={cn("flex items-center gap-3 w-full", className)}
        {...props}
      >
        <div className={cn("h-px flex-1 border-t", borderColor)} />
        <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
          {label}
        </span>
        <div className={cn("h-px flex-1 border-t", borderColor)} />
      </div>
    );
  }
);
RuleDivider.displayName = "RuleDivider";
