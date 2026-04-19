import * as React from "react";
import { cn } from "@/lib/cn";

export interface KeybindHintProps extends React.HTMLAttributes<HTMLSpanElement> {
  keys: string[];
  description?: string;
}

export const KeybindHint = React.forwardRef<HTMLSpanElement, KeybindHintProps>(
  ({ keys, description, className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn("inline-flex items-center gap-1.5 font-sans text-xs text-ink-mute", className)}
      {...props}
    >
      {keys.map((k, i) => (
        <kbd
          key={`${k}-${i}`}
          className="inline-flex h-5 min-w-[1.25rem] items-center justify-center border border-ink-faint bg-paper px-1 font-mono text-[10px] font-medium text-ink"
        >
          {k}
        </kbd>
      ))}
      {description && <span className="ml-1">{description}</span>}
    </span>
  )
);
KeybindHint.displayName = "KeybindHint";
