"use client";
import { useT } from "@/lib/i18n";

const HANDICAPS_BY_SIZE: Record<number, number[]> = {
  9: [2, 3, 4, 5],
  13: [2, 3, 4, 5, 6, 7, 8, 9],
  19: [2, 3, 4, 5, 6, 7, 8, 9],
};

interface Props {
  boardSize: number;
  value: number;
  onChange: (n: number) => void;
}

export default function HandicapPicker({ boardSize, value, onChange }: Props) {
  const t = useT();
  const options = HANDICAPS_BY_SIZE[boardSize] ?? [];
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm">{t("game.handicap")}</span>
      <select
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="border rounded px-2 py-1 dark:bg-gray-900 dark:border-gray-700"
      >
        <option value={0}>{t("game.handicapNone")}</option>
        {options.map((n) => (
          <option key={n} value={n}>{t("game.handicapStones", { n })}</option>
        ))}
      </select>
    </label>
  );
}
