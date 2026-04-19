import * as React from "react";
import { cn } from "@/lib/cn";

export interface BrandMarkProps extends React.SVGAttributes<SVGSVGElement> {
  size?: 16 | 20 | 24 | 32;
}

/**
 * A single stone intersecting a horizontal grid line — the moment of a move.
 * Uses currentColor so it inherits text color (text-ink etc).
 */
export const BrandMark = React.forwardRef<SVGSVGElement, BrandMarkProps>(
  ({ size = 20, className, ...props }, ref) => (
    <svg
      ref={ref}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className={cn("text-ink", className)}
      role="img"
      aria-label="Baduk"
      {...props}
    >
      <line x1="2" y1="12" x2="22" y2="12" stroke="currentColor" strokeWidth="1" />
      <circle cx="12" cy="12" r="5.5" fill="currentColor" />
    </svg>
  )
);
BrandMark.displayName = "BrandMark";
