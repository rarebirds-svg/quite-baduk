"use client";
import { useT } from "@/lib/i18n";

export const RANKS = ["18k","15k","12k","10k","7k","5k","3k","1k","1d","3d","5d","7d"] as const;
export type Rank = typeof RANKS[number];

export default function RankPicker({ value, onChange }: { value: Rank; onChange: (r: Rank) => void }) {
  const t = useT();
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm">{t("game.rank")}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as Rank)}
        className="border rounded px-2 py-1 dark:bg-gray-900 dark:border-gray-700"
      >
        {RANKS.map((r) => <option key={r} value={r}>{r}</option>)}
      </select>
    </label>
  );
}
