import * as React from "react";
import { cn } from "@/lib/cn";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ icon, title, description, action, className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex flex-col items-center justify-center gap-4 border border-ink-faint bg-paper-deep px-8 py-16 text-center",
        className
      )}
      {...props}
    >
      {icon && <div className="text-ink-mute">{icon}</div>}
      <div className="flex flex-col gap-2">
        <h3 className="font-serif text-xl font-semibold text-ink">{title}</h3>
        {description && (
          <p className="font-sans text-sm text-ink-mute max-w-md">{description}</p>
        )}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
);
EmptyState.displayName = "EmptyState";
