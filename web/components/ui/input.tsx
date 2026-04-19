import * as React from "react";
import { cn } from "@/lib/cn";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-sm border border-ink-faint bg-paper px-3 py-2 text-sm",
        "placeholder:text-ink-mute",
        "focus-visible:outline-none focus-visible:border-ink focus-visible:ring-1 focus-visible:ring-ink",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "aria-[invalid=true]:border-oxblood aria-[invalid=true]:focus-visible:ring-oxblood",
        className
      )}
      {...props}
    />
  )
);
Input.displayName = "Input";
