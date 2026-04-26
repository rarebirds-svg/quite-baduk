"use client";
import { SUPPORTED_SIZES, type BoardSize } from "@/lib/board";
import { useT } from "@/lib/i18n";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

export interface BoardSizePickerProps {
  value: BoardSize;
  onChange: (size: BoardSize) => void;
}

export default function BoardSizePicker({ value, onChange }: BoardSizePickerProps) {
  const t = useT();
  return (
    <ToggleGroup
      type="single"
      value={String(value)}
      onValueChange={(v) => v && onChange(Number(v) as BoardSize)}
      aria-label={t("game.boardSize")}
    >
      {SUPPORTED_SIZES.map((s) => (
        <ToggleGroupItem key={s} value={String(s)}>
          {s}×{s}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
