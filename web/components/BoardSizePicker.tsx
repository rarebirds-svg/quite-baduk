"use client";
import { SUPPORTED_SIZES, type BoardSize } from "@/lib/board";
import { useT } from "@/lib/i18n";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Label } from "@/components/ui/label";

export interface BoardSizePickerProps {
  value: BoardSize;
  onChange: (size: BoardSize) => void;
  label?: string;
}

export default function BoardSizePicker({
  value,
  onChange,
  label,
}: BoardSizePickerProps) {
  const t = useT();
  const resolvedLabel = label ?? t("game.boardSize");
  return (
    <div className="flex flex-col gap-2">
      <Label>{resolvedLabel}</Label>
      <ToggleGroup
        type="single"
        value={String(value)}
        onValueChange={(v) => v && onChange(Number(v) as BoardSize)}
      >
        {SUPPORTED_SIZES.map((s) => (
          <ToggleGroupItem key={s} value={String(s)}>
            {s}×{s}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
}
