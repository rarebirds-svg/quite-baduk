"use client";
import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { useT } from "@/lib/i18n";
import {
  BOARD_THEMES,
  useBoardTheme,
  type BoardTheme,
} from "@/store/boardThemeStore";

const ORDER: BoardTheme[] = ["paper", "wood", "kaya", "slate"];

export default function BoardBgSwitcher({
  compact = false,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  const t = useT();
  const theme = useBoardTheme((s) => s.theme);
  const setTheme = useBoardTheme((s) => s.setTheme);
  // Same persist-vs-SSR rationale as Board: render the "paper" selection
  // until after mount so hydration matches.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const activeTheme = mounted ? theme : "paper";

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {!compact && (
        <span className="font-sans text-[10px] font-semibold uppercase tracking-label text-ink-mute">
          {t("settings.boardBg")}
        </span>
      )}
      <div className="flex items-center gap-2" role="radiogroup" aria-label={t("settings.boardBg")}>
        {ORDER.map((key) => {
          const active = activeTheme === key;
          return (
            <button
              key={key}
              type="button"
              role="radio"
              aria-checked={active}
              aria-label={t(`settings.boardBg_${key}`)}
              title={t(`settings.boardBg_${key}`)}
              onClick={() => setTheme(key)}
              className={cn(
                "h-7 w-7 rounded-full border transition-[transform,border-color] duration-150",
                active
                  ? "border-oxblood scale-110"
                  : "border-ink-faint hover:border-ink"
              )}
              style={{ backgroundColor: BOARD_THEMES[key].bg }}
            />
          );
        })}
      </div>
    </div>
  );
}
