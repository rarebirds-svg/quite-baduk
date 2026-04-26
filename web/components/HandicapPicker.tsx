"use client";
import { useT } from "@/lib/i18n";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

const HANDICAP_BY_SIZE: Record<number, number[]> = {
  9: [2, 3, 4, 5],
  13: [2, 3, 4, 5, 6, 7, 8, 9],
  19: [2, 3, 4, 5, 6, 7, 8, 9],
};

export interface HandicapPickerProps {
  boardSize: number;
  value: number;
  onChange: (n: number) => void;
  triggerId?: string;
}

export default function HandicapPicker({
  boardSize,
  value,
  onChange,
  triggerId = "handicap-picker",
}: HandicapPickerProps) {
  const t = useT();
  const valid = HANDICAP_BY_SIZE[boardSize] ?? [];
  return (
    <Select value={String(value)} onValueChange={(v) => onChange(Number(v))}>
      <SelectTrigger id={triggerId} aria-label={t("game.handicap")} className="w-full">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="0">{t("game.handicapNone")}</SelectItem>
        {valid.map((n) => (
          <SelectItem key={n} value={String(n)}>
            {t("game.handicapStones", { n: String(n) })}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
