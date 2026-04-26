"use client";
import { useT } from "@/lib/i18n";
import { Label } from "@/components/ui/label";

export const AI_STYLES = [
  "balanced",
  "territorial",
  "influence",
  "combative",
  "speed",
  "classical",
  "rustic",
] as const;

export type AiStyle = (typeof AI_STYLES)[number];

export interface StylePickerProps {
  value: AiStyle;
  onChange: (s: AiStyle) => void;
  label?: string;
}

export default function StylePicker({ value, onChange, label }: StylePickerProps) {
  const t = useT();
  const resolvedLabel = label ?? t("game.aiStyle");

  return (
    <div className="flex flex-col gap-3">
      <Label>{resolvedLabel}</Label>
      <div
        role="radiogroup"
        aria-label={resolvedLabel}
        className="grid grid-cols-1 gap-2 sm:grid-cols-2"
      >
        {AI_STYLES.map((s) => {
          const selected = s === value;
          return (
            <button
              key={s}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(s)}
              className={
                "flex flex-col gap-1 border px-3 py-2 text-left transition-base " +
                (selected
                  ? "border-oxblood bg-paper-deep"
                  : "border-ink-faint hover:border-ink-mute")
              }
            >
              <span className="font-sans text-xs font-semibold uppercase tracking-label text-ink-mute">
                {t(`game.aiStyleName.${s}`)}
              </span>
              <span className="font-serif text-sm text-ink">
                {t(`game.aiStyleRep.${s}`)}
              </span>
              <span className="font-sans text-xs text-ink-mute">
                {t(`game.aiStyleDesc.${s}`)}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
