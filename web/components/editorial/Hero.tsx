import * as React from "react";
import { cn } from "@/lib/cn";
import { RuleDivider } from "./RuleDivider";

export interface HeroProps extends React.HTMLAttributes<HTMLElement> {
  title: string;
  subtitle?: string;
  volume?: string;
  size?: "default" | "compact";
}

export const Hero = React.forwardRef<HTMLElement, HeroProps>(
  ({ title, subtitle, volume, size = "default", className, ...props }, ref) => {
    const titleClass =
      size === "compact"
        ? "font-serif text-3xl font-semibold leading-tight tracking-tight"
        : "font-serif text-5xl font-semibold leading-tight tracking-tight";
    return (
      <section ref={ref} className={cn("flex flex-col gap-3", className)} {...props}>
        {volume && (
          <div className="font-sans text-xs font-semibold uppercase tracking-label text-oxblood">
            {volume}
          </div>
        )}
        <h1 className={titleClass}>{title}</h1>
        {subtitle && (
          <p className="font-sans text-base text-ink-mute max-w-prose">{subtitle}</p>
        )}
        <RuleDivider weight="strong" className="mt-2" />
      </section>
    );
  }
);
Hero.displayName = "Hero";
