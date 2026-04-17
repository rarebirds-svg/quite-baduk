"use client";
import { useT } from "@/lib/i18n";

export default function HandicapPicker({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const t = useT();
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm">{t("game.handicap")}</span>
      <select
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="border rounded px-2 py-1 dark:bg-gray-900 dark:border-gray-700"
      >
        <option value={0}>{t("game.handicapNone")}</option>
        {[2,3,4,5,6,7,8,9].map((n) => <option key={n} value={n}>{t("game.handicapStones", { n })}</option>)}
      </select>
    </label>
  );
}
