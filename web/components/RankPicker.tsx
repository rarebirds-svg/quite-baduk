"use client";
import { useT } from "@/lib/i18n";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

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
  "7d",
] as const;
export type Rank = (typeof RANKS)[number];

export interface RankPickerProps {
  value: Rank;
  onChange: (rank: Rank) => void;
  label?: string;
}

export default function RankPicker({ value, onChange, label }: RankPickerProps) {
  const t = useT();
  const resolvedLabel = label ?? t("game.rank");
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="rank-picker">{resolvedLabel}</Label>
      <Select value={value} onValueChange={(v) => onChange(v as Rank)}>
        <SelectTrigger id="rank-picker" className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {RANKS.map((r) => (
            <SelectItem key={r} value={r}>
              {r}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
