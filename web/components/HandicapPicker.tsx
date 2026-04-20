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

const HANDICAP_BY_SIZE: Record<number, number[]> = {
  9: [2, 3, 4, 5],
  13: [2, 3, 4, 5, 6, 7, 8, 9],
  19: [2, 3, 4, 5, 6, 7, 8, 9],
};

export interface HandicapPickerProps {
  boardSize: number;
  value: number;
  onChange: (n: number) => void;
  label?: string;
}

export default function HandicapPicker({
  boardSize,
  value,
  onChange,
  label,
}: HandicapPickerProps) {
  const t = useT();
  const valid = HANDICAP_BY_SIZE[boardSize] ?? [];
  const resolvedLabel = label ?? t("game.handicap");
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="handicap-picker">{resolvedLabel}</Label>
      <Select value={String(value)} onValueChange={(v) => onChange(Number(v))}>
        <SelectTrigger id="handicap-picker" className="w-full">
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
    </div>
  );
}
