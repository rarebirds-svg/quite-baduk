"use client";
import { useT } from "@/lib/i18n";
import { SUPPORTED_SIZES, type BoardSize } from "@/lib/board";

interface Props {
  value: BoardSize;
  onChange: (size: BoardSize) => void;
}

export default function BoardSizePicker({ value, onChange }: Props) {
  const t = useT();
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm">{t("game.boardSize")}</span>
      <div role="radiogroup" aria-label={t("game.boardSize")} className="flex gap-2">
        {SUPPORTED_SIZES.map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            onClick={() => onChange(n)}
            className={
              "px-3 py-1 rounded border text-sm " +
              (value === n
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700")
            }
          >
            {n}×{n}
          </button>
        ))}
      </div>
    </label>
  );
}
