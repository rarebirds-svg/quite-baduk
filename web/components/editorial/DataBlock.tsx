import * as React from "react";
import { cn } from "@/lib/cn";

export interface DataBlockProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: React.ReactNode;
  description?: string;
}

export const DataBlock = React.forwardRef<HTMLDivElement, DataBlockProps>(
  ({ label, value, description, className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-0.5 py-2", className)} {...props}>
      <div className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
        {label}
      </div>
      <div className="font-mono text-lg font-medium tabular-nums text-ink">{value}</div>
      {description && <div className="font-sans text-xs text-ink-mute">{description}</div>}
    </div>
  )
);
DataBlock.displayName = "DataBlock";
