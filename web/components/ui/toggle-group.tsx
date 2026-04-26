"use client";
import * as React from "react";
import * as TGPrimitive from "@radix-ui/react-toggle-group";
import { cn } from "@/lib/cn";

export const ToggleGroup = React.forwardRef<
  React.ElementRef<typeof TGPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof TGPrimitive.Root>
>(({ className, ...props }, ref) => (
  <TGPrimitive.Root
    ref={ref}
    className={cn("inline-flex border border-ink-faint divide-x divide-ink-faint", className)}
    {...props}
  />
));
ToggleGroup.displayName = TGPrimitive.Root.displayName;

export const ToggleGroupItem = React.forwardRef<
  React.ElementRef<typeof TGPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof TGPrimitive.Item>
>(({ className, ...props }, ref) => (
  <TGPrimitive.Item
    ref={ref}
    className={cn(
      "inline-flex h-9 items-center justify-center gap-1 bg-paper px-3 text-xs font-semibold uppercase tracking-label text-ink-mute",
      "hover:bg-paper-deep",
      "data-[state=on]:bg-ink data-[state=on]:text-paper",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink focus-visible:ring-inset",
      className
    )}
    {...props}
  />
));
ToggleGroupItem.displayName = TGPrimitive.Item.displayName;
