"use client";
import { useT } from "@/lib/i18n";

interface Props {
  onPass(): void;
  onResign(): void;
  onUndo(): void;
  onHint(): void;
  disabled?: boolean;
}

export default function GameControls({ onPass, onResign, onUndo, onHint, disabled }: Props) {
  const t = useT();
  const cls = "px-3 py-1 border rounded text-sm dark:border-gray-700 disabled:opacity-50";
  return (
    <div className="flex gap-2">
      <button className={cls} onClick={onPass} disabled={disabled}>{t("game.pass")}</button>
      <button className={cls} onClick={onResign} disabled={disabled}>{t("game.resign")}</button>
      <button className={cls} onClick={onUndo} disabled={disabled}>{t("game.undo")}</button>
      <button className={cls} onClick={onHint} disabled={disabled}>{t("game.hint")}</button>
    </div>
  );
}
