import * as React from "react";
import { cn } from "@/lib/cn";

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "md";
  label?: string;
}

export const Spinner = React.forwardRef<HTMLDivElement, SpinnerProps>(
  ({ size = "md", label = "Loading", className, ...props }, ref) => {
    const h = size === "sm" ? "h-0.5" : "h-1";
    return (
      <div
        ref={ref}
        role="status"
        aria-label={label}
        className={cn("relative w-full overflow-hidden bg-ink-faint/30", h, className)}
        {...props}
      >
        <div className={cn("absolute inset-y-0 w-1/3 bg-oxblood ed-spinner-bar")} />
      </div>
    );
  }
);
Spinner.displayName = "Spinner";
