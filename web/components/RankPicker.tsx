"use client";
import { useT, useLocale } from "@/lib/i18n";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

// Mirrors backend SUPPORTED_AI_RANKS in app/core/katago/strength.py.
// v1.0 ships 18k..5d only — 6d/7d/9d ranks are temporarily withheld
// until the Metal pool's high-visit behaviour is profiled (Plan 1
// task A4). Granularity is sparse on purpose so users see meaningfully
// different opponents at each step rather than a 16-stop slider.
export const RANKS = [
  "18k",
  "15k",
  "12k",
  "10k",
  "7k",
  "5k",
  "3k",
  "1k",
  "1d",
  "3d",
  "5d",
] as const;
export type Rank = (typeof RANKS)[number];

export function formatRank(r: Rank, locale: "ko" | "en"): string {
  if (locale !== "ko") return r;
  const n = parseInt(r, 10);
  return r.endsWith("d") ? `${n}단` : `${n}급`;
}

export interface RankPickerProps {
  value: Rank;
  onChange: (rank: Rank) => void;
  triggerId?: string;
}

export default function RankPicker({ value, onChange, triggerId = "rank-picker" }: RankPickerProps) {
  const t = useT();
  const [locale] = useLocale();
  const ariaLabel = t("game.rank");
  return (
    <Select value={value} onValueChange={(v) => onChange(v as Rank)}>
      <SelectTrigger id={triggerId} aria-label={ariaLabel} className="w-full">
        <SelectValue>{formatRank(value, locale)}</SelectValue>
      </SelectTrigger>
      <SelectContent>
        {RANKS.map((r) => (
          <SelectItem key={r} value={r}>
            {formatRank(r, locale)}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
