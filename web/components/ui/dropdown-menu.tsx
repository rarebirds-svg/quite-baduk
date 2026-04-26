"use client";
import * as React from "react";
import * as DMPrimitive from "@radix-ui/react-dropdown-menu";
import { cn } from "@/lib/cn";

export const DropdownMenu = DMPrimitive.Root;
export const DropdownMenuTrigger = DMPrimitive.Trigger;
export const DropdownMenuGroup = DMPrimitive.Group;
export const DropdownMenuPortal = DMPrimitive.Portal;
export const DropdownMenuSub = DMPrimitive.Sub;
export const DropdownMenuRadioGroup = DMPrimitive.RadioGroup;

export const DropdownMenuContent = React.forwardRef<
  React.ElementRef<typeof DMPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DMPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <DMPrimitive.Portal>
    <DMPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 min-w-[8rem] overflow-hidden border border-ink-faint bg-paper p-1 text-ink ed-anim-fade",
        className
      )}
      {...props}
    />
  </DMPrimitive.Portal>
));
DropdownMenuContent.displayName = DMPrimitive.Content.displayName;

export const DropdownMenuItem = React.forwardRef<
  React.ElementRef<typeof DMPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof DMPrimitive.Item> & { inset?: boolean }
>(({ className, inset, ...props }, ref) => (
  <DMPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex cursor-default select-none items-center gap-2 px-3 py-2 text-sm outline-none",
      "focus:bg-paper-deep data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      inset && "pl-8",
      className
    )}
    {...props}
  />
));
DropdownMenuItem.displayName = DMPrimitive.Item.displayName;

export const DropdownMenuSeparator = React.forwardRef<
  React.ElementRef<typeof DMPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof DMPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <DMPrimitive.Separator
    ref={ref}
    className={cn("-mx-1 my-1 h-px bg-ink-faint", className)}
    {...props}
  />
));
DropdownMenuSeparator.displayName = DMPrimitive.Separator.displayName;

export const DropdownMenuLabel = React.forwardRef<
  React.ElementRef<typeof DMPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof DMPrimitive.Label>
>(({ className, ...props }, ref) => (
  <DMPrimitive.Label
    ref={ref}
    className={cn(
      "px-3 py-1.5 font-sans text-xs font-semibold uppercase tracking-label text-ink-mute",
      className
    )}
    {...props}
  />
));
DropdownMenuLabel.displayName = DMPrimitive.Label.displayName;
