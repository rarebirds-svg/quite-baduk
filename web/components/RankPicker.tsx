"use client";
import { useT, useLocale, type Locale } from "@/lib/i18n";
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

export function formatRank(r: Rank, locale: Locale): string {
  // CJK suffixes share the same kanji for dan/kyu, so ko / ja / zh all
  // get the same formatting; only English keeps the bare "5k" / "1d".
  const n = parseInt(r, 10);
  switch (locale) {
    case "ko":
      return r.endsWith("d") ? `${n}단` : `${n}급`;
    case "ja":
      return r.endsWith("d") ? `${n}段` : `${n}級`;
    case "zh":
      return r.endsWith("d") ? `${n}段` : `${n}级`;
    case "en":
    default:
      return r;
  }
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
