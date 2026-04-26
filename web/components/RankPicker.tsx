"use client";
import { useT, useLocale } from "@/lib/i18n";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

export const RANKS = [
  "9k",
  "8k",
  "7k",
  "6k",
  "5k",
  "4k",
  "3k",
  "2k",
  "1k",
  "1d",
  "2d",
  "3d",
  "4d",
  "5d",
  "6d",
  "7d",
  "8d",
  "9d",
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
